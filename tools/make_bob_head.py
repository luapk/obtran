"""Build Bob's head as a 3D relief made from the page itself, as Gaussian splats.

Marble turns Bob's head into a flat picture inside an invented room, so this
builds him from the scan instead. There are no source layers, so the shapes are
found in the drawing:
  - the face: an ellipse fitted to the thick ink outline of the head
  - the halo: the bright disc around the head
  - the helmet ring: the thin white arc of the glass helmet, fitted as a circle
Three layers of splats are made from the scan's own pixels:
  - back: the crop and its surroundings on the page, curving away behind the
    head (halo, rays, cockpit) and fading to ink at the edges, with the face
    area filled with halo colour so nothing opens up behind it
  - face: a dome, so the face comes forward and turns as the reader moves
  - ring: the helmet rim, floating in front of the face

Writes worlds/worlds/bob-head-relief.spz (one splat per pixel), a lighter
bob-head-relief.100k.spz for phones, and worlds/worlds/reliefs.json, which the
page reads alongside worlds.json. Axes match Marble's worlds (OpenCV: x right,
y down, the viewer at the origin looking down +z), so the page treats it like
any other world.

Usage: python3 tools/extract_page.py && python3 tools/make_bob_head.py [--debug out.png]
Needs: numpy, Pillow.
"""
import gzip
import json
import struct
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "source" / "page_rgb.png"
OUT = ROOT / "worlds" / "worlds"
CROP = (440, 840, 500, 580)          # bob-head in worlds/manifest.json: x, y, w, h on the page
MARGIN = 260                         # page pixels around the crop kept as surroundings, fading to ink
LUMA = np.array([0.299, 0.587, 0.114], np.float32)

# Starting guesses in crop pixels, refined against the ink below.
FACE_GUESS = dict(cx=250.0, cy=322.0, a=150.0, b=88.0, theta=np.radians(-72.0))
RING_GUESS = [(45.0, 100.0), (20.0, 250.0), (47.0, 430.0)]

# Depth in crop pixels, positive towards the reader.
FACE_EDGE, FACE_DOME = 15.0, 110.0
HALO_NEAR, HALO_FAR, HALO_RADIUS = -80.0, -260.0, 235.0
RING_DEPTH, RING_HALF_WIDTH = 45.0, 7.0

WIDTH_UNITS = 1.3                    # the crop spans this many units across
DISTANCE = 1.0                       # from the viewer to the face, in units


def ellipse_r(x, y, e):
    dx, dy = x - e["cx"], y - e["cy"]
    c, s = np.cos(e["theta"]), np.sin(e["theta"])
    u, v = dx * c + dy * s, -dx * s + dy * c
    return np.sqrt((u / e["a"]) ** 2 + (v / e["b"]) ** 2)


def fit_ellipse(x, y):
    """Least squares conic fit, returned as centre, semi axes and angle."""
    D = np.stack([x * x, x * y, y * y, x, y, np.ones_like(x)], axis=1)
    _, _, vt = np.linalg.svd(D, full_matrices=False)
    A, B, C, Dd, E, F = vt[-1]
    M = np.array([[A, B / 2], [B / 2, C]])
    centre = np.linalg.solve(2 * M, [-Dd, -E])
    Fc = F + 0.5 * (Dd * centre[0] + E * centre[1])
    w, V = np.linalg.eigh(M)
    axes = np.sqrt(-Fc / w)
    major = int(np.argmax(axes))
    theta = np.arctan2(V[1, major], V[0, major])
    return dict(cx=float(centre[0]), cy=float(centre[1]), a=float(axes[major]), b=float(axes[1 - major]), theta=float(theta))


def circle_from(points):
    (x1, y1), (x2, y2), (x3, y3) = points
    a = np.array([[x2 - x1, y2 - y1], [x3 - x1, y3 - y1]], float) * 2
    b = np.array([x2 ** 2 - x1 ** 2 + y2 ** 2 - y1 ** 2, x3 ** 2 - x1 ** 2 + y3 ** 2 - y1 ** 2], float)
    cx, cy = np.linalg.solve(a, b)
    return cx, cy, float(np.hypot(x1 - cx, y1 - cy))


def fit_circle(x, y):
    A = np.stack([x, y, np.ones_like(x)], axis=1)
    sol, *_ = np.linalg.lstsq(A, x * x + y * y, rcond=None)
    cx, cy = sol[0] / 2, sol[1] / 2
    return float(cx), float(cy), float(np.sqrt(sol[2] + cx * cx + cy * cy))


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def find_shapes(lum):
    h, w = lum.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    # face: dark outline pixels near the guessed ellipse, refitted twice
    face = dict(FACE_GUESS)
    for band in (0.25, 0.12):
        r = ellipse_r(xx, yy, face)
        m = (lum < 0.3) & (np.abs(r - 1) < band)
        face = fit_ellipse(xx[m].astype(float), yy[m].astype(float))
    # helmet ring: brightest pixel along each ray near the guessed circle, refitted
    cx, cy, rad = circle_from(RING_GUESS)
    pts = []
    for ang in np.linspace(0, 2 * np.pi, 720, endpoint=False):
        rs = rad + np.arange(-14, 15)
        px, py = cx + rs * np.cos(ang), cy + rs * np.sin(ang)
        ok = (px >= 0) & (px < w - 1) & (py >= 0) & (py < h - 1)
        if ok.sum() < 20:
            continue
        vals = lum[py[ok].astype(int), px[ok].astype(int)]
        if vals.max() > 0.75:
            i = int(np.argmax(vals))
            pts.append((px[ok][i], py[ok][i]))
    pts = np.array(pts)
    ring = fit_circle(pts[:, 0], pts[:, 1]) if len(pts) > 30 else (cx, cy, rad)
    return face, ring


def build(rgb, face, ring, stride_back=1, stride_front=1, crop_w=CROP[2]):
    """rgb is the crop plus MARGIN on every side; face and ring are in crop pixels."""
    h, w, _ = rgb.shape
    face = dict(face, cx=face["cx"] + MARGIN, cy=face["cy"] + MARGIN)
    ring = (ring[0] + MARGIN, ring[1] + MARGIN, ring[2])
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    lum = rgb @ LUMA
    e = ellipse_r(xx, yy, face)
    hr = np.hypot(xx - face["cx"], yy - face["cy"]) / HALO_RADIUS
    rc = np.hypot(xx - ring[0], yy - ring[1])

    face_mask = e < 1.03
    ring_mask = (np.abs(rc - ring[2]) < RING_HALF_WIDTH) & ~face_mask

    # back layer: halo curving away, the face area filled with nearby halo colour
    back = rgb.copy()
    around = (e > 1.08) & (e < 1.35) & (lum > 0.5)
    back[face_mask] = np.median(rgb[around], axis=0) if around.any() else [0.9, 0.9, 0.88]
    z_back = HALO_NEAR + (HALO_FAR - HALO_NEAR) * smoothstep(0.45, 1.0, hr)

    z_face = FACE_EDGE + FACE_DOME * np.sqrt(np.clip(1 - np.minimum(e, 1) ** 2, 0, 1))
    # the head sits in its drawn surroundings, which fade to ink towards the edges
    edge = np.minimum.reduce([xx, yy, w - 1 - xx, h - 1 - yy])
    fade = smoothstep(0, MARGIN * 0.9, edge)
    layers = []
    sb, sf = stride_back, stride_front
    inner = (xx >= MARGIN) & (xx < w - MARGIN) & (yy >= MARGIN) & (yy < h - MARGIN)
    sel = np.zeros((h, w), bool); sel[::sb, ::sb] = True
    outer = np.zeros((h, w), bool); outer[::sb * 2, ::sb * 2] = True
    sel = (sel & inner) | (outer & ~inner)     # full density on the head, half around it
    layers.append((sel & (fade > 0.02), back, z_back, sb, fade))
    sel = np.zeros((h, w), bool); sel[::sf, ::sf] = True
    one = np.ones((h, w), np.float32)
    layers.append((sel & face_mask, rgb, z_face, sf, one))
    layers.append((ring_mask & inner, rgb, np.full((h, w), RING_DEPTH, np.float32), 1, one))

    s = crop_w / WIDTH_UNITS
    pos, col, scl, alp = [], [], [], []
    for m, colour, z, stride, alpha in layers:
        py, px = np.nonzero(m)
        x = (px - face["cx"]) / s
        y = (py - face["cy"]) / s
        zz = DISTANCE - z[py, px] / s
        pos.append(np.stack([x, y, zz], axis=1))
        col.append(colour[py, px])
        st = np.where(inner[py, px], stride, stride * 2) if stride == stride_back else np.full(len(px), stride)
        sz = 0.62 * st / s
        scl.append(np.stack([sz, sz, np.full(len(px), 0.25 / s)], axis=1))
        alp.append(alpha[py, px] * 0.96)
    return (np.concatenate(pos).astype(np.float32), np.concatenate(col).astype(np.float32),
            np.concatenate(scl).astype(np.float32), np.concatenate(alp).astype(np.float32))


def write_spz(path, pos, rgb, scales, opacity, frac_bits=12):
    n = len(pos)
    q = np.round(pos * (1 << frac_bits)).astype(np.int64)
    q = np.where(q < 0, q + (1 << 24), q).astype(np.uint32)
    pbytes = np.stack([q & 255, (q >> 8) & 255, (q >> 16) & 255], axis=-1).astype(np.uint8).reshape(n, 9)
    alpha = np.clip(np.round(np.asarray(opacity) * 255), 0, 255).astype(np.uint8).reshape(n, 1)
    sh = (rgb - 0.5) / 0.28209479177387814
    colour = np.clip(np.round((sh * 0.15 + 0.5) * 255), 0, 255).astype(np.uint8)
    sbytes = np.clip(np.round((np.log(scales) + 10.0) * 16.0), 0, 255).astype(np.uint8)
    rot = np.full((n, 3), 128, np.uint8)          # identity rotation
    head = struct.pack("<IIIBBBB", 0x5053474E, 2, n, 0, frac_bits, 0, 0)
    body = b"".join(a.tobytes() for a in (pbytes, alpha, colour, sbytes, rot))
    path.write_bytes(gzip.compress(head + body, compresslevel=9, mtime=0))
    return n


def main():
    x, y, w, h = CROP
    page = Image.open(PAGE).convert("RGB")
    rgb = np.asarray(page.crop((x, y, x + w, y + h)), np.float32) / 255.0
    lum = rgb @ LUMA
    face, ring = find_shapes(lum)
    # the surroundings, padded with ink where they run off the page
    m = MARGIN
    wide = Image.new("RGB", (w + 2 * m, h + 2 * m), (5, 4, 3))
    wide.paste(page.crop((max(0, x - m), max(0, y - m), x + w + m, y + h + m)), (max(0, m - x), max(0, m - y)))
    wide = np.asarray(wide, np.float32) / 255.0
    print(f"face ellipse centre ({face['cx']:.0f}, {face['cy']:.0f}) axes {face['a']:.0f} x {face['b']:.0f} at {np.degrees(face['theta']):.0f} deg")
    print(f"helmet ring centre ({ring[0]:.0f}, {ring[1]:.0f}) radius {ring[2]:.0f}")
    OUT.mkdir(parents=True, exist_ok=True)
    for name, sb, sf in (("bob-head-relief.spz", 1, 1), ("bob-head-relief.100k.spz", 2, 2)):
        pos, col, scl, alp = build(wide, face, ring, sb, sf)
        n = write_spz(OUT / name, pos, col, scl, alp)
        print(f"wrote {name}: {n} splats, {(OUT / name).stat().st_size / 1048576:.1f} MB")
    reliefs = {"worlds": [{
        "id": "bob-head-relief", "title": "Bob's head (page)", "relief": True,
        "splats": {"500k": "worlds/bob-head-relief.spz", "100k": "worlds/bob-head-relief.100k.spz"},
        "yaw": [-30, 30], "pitch": [-24, 24], "parallax": 3.2,
        "shapes": {"face": {k: round(v, 2) for k, v in face.items()}, "ring": [round(v, 1) for v in ring]},
    }]}
    (OUT / "reliefs.json").write_text(json.dumps(reliefs, indent=2) + "\n")
    print(f"wrote {OUT / 'reliefs.json'}")

    if "--debug" in sys.argv:
        from PIL import ImageDraw
        im = Image.fromarray((rgb * 255).astype(np.uint8)).convert("RGB")
        d = ImageDraw.Draw(im)
        t = np.linspace(0, 2 * np.pi, 200)
        c, s = np.cos(face["theta"]), np.sin(face["theta"])
        ex = face["cx"] + face["a"] * np.cos(t) * c - face["b"] * np.sin(t) * s
        ey = face["cy"] + face["a"] * np.cos(t) * s + face["b"] * np.sin(t) * c
        d.line(list(zip(ex, ey)) + [(ex[0], ey[0])], fill=(255, 0, 0), width=3)
        rx, ry = ring[0] + ring[2] * np.cos(t), ring[1] + ring[2] * np.sin(t)
        d.line(list(zip(rx, ry)), fill=(0, 160, 255), width=3)
        r = HALO_RADIUS
        d.ellipse([face["cx"] - r, face["cy"] - r, face["cx"] + r, face["cy"] + r], outline=(255, 200, 0), width=2)
        im.save(sys.argv[sys.argv.index("--debug") + 1])


if __name__ == "__main__":
    main()
