"""Cut the white slab out of the singularity world, to float it in 3D.

  python3 tools/cut_slab.py

Marble invented a large white slab, like a console panel, up and left of the nucleus
in the singularity world (it is not in the drawing). Paul asked for it to be cut out
and float in the 3D space. This reprojects that part of the world's panorama into a
flat view from the viewpoint (no equirectangular distortion), masks it to the outline
traced below, grades it to the page's tones, and writes:
  prototype/assets/props/slab.png    the cut out, with a transparent surround
  printed constants for index.src.html (SLAB): where the card sits, and the angular box
  and depth range of the slab's own splats, which the page hides in that world.

The panorama's angles are offset from the splats' by PANO_YAW_OFFSET (measured on the
nucleus: the panorama puts it at yaw -1.9, the splats at -4.2).
"""
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
PANO = ROOT / "worlds" / "worlds" / "singularity-core.pano.png"
OUT = ROOT / "prototype" / "assets" / "props"
VIEW = (-27.0, 21.0, 52.0, 1000)        # yaw, pitch, field of view (degrees), size of the flat view
# the slab's outline in the flat view, traced by eye, clockwise
OUTLINE = [(418, 108), (468, 66), (552, 70), (702, 262), (668, 420), (620, 640), (585, 835),
           (520, 880), (235, 950), (162, 880), (175, 820)]
GROW = 8                                # pixels added around the outline, to keep its white border
PANO_YAW_OFFSET = -2.3
DIST = (1.08, 1.48)                     # the slab's splats lie this far out (Marble units)


def rays(yaw0, pit0, fov, n, u, v):
    """Directions (yaw, pitch in degrees) through pixels u, v of the flat view."""
    f = 0.5 * n / np.tan(np.radians(fov / 2))
    d = np.stack([u - n / 2 + 0.5, -(v - n / 2 + 0.5), np.full_like(u, f, dtype=np.float64)], -1)
    d = d / np.linalg.norm(d, axis=-1, keepdims=True)
    cp, sp, cy, sy = np.cos(np.radians(pit0)), np.sin(np.radians(pit0)), np.cos(np.radians(yaw0)), np.sin(np.radians(yaw0))
    x, y, z = d[..., 0], d[..., 1], d[..., 2]
    y2, z2 = y * cp + z * sp, -y * sp + z * cp
    x3, z3 = x * cy + z2 * sy, -x * sy + z2 * cy
    return np.degrees(np.arctan2(x3, z3)), np.degrees(np.arcsin(np.clip(y2, -1, 1)))


def main():
    pano = np.asarray(Image.open(PANO).convert("RGB")).astype(np.float32) / 255
    H, W, _ = pano.shape
    yaw0, pit0, fov, n = VIEW
    v, u = np.mgrid[0:n, 0:n].astype(np.float64)
    yaw, pit = rays(yaw0, pit0, fov, n, u, v)
    px = (((yaw + 180) / 360 * W) % W).astype(int)
    py = np.clip(((90 - pit) / 180 * H).astype(int), 0, H - 1)
    img = pano[py, px]
    # the page's tones: luminance, lifted blacks crushed, a faint warm paper
    lum = img @ np.array([0.299, 0.587, 0.114])
    lum = np.clip((lum - 0.06) / 0.86, 0, 1) ** 1.1
    rgb = np.stack([lum * 0.94, lum * 0.915, lum * 0.875], -1)
    mask = Image.new("L", (n, n), 0)
    ImageDraw.Draw(mask).polygon(OUTLINE, fill=255)
    mask = mask.filter(ImageFilter.MaxFilter(GROW * 2 + 1)).filter(ImageFilter.GaussianBlur(1.5))
    m = np.asarray(mask)
    ys, xs = np.nonzero(m > 8)
    x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    rgba = np.dstack([(rgb * 255).astype(np.uint8), m.astype(np.uint8)])[y0:y1, x0:x1]
    OUT.mkdir(parents=True, exist_ok=True)
    Image.fromarray(rgba, "RGBA").save(OUT / "slab.png", optimize=True)

    # where the card goes: a plane facing the view's centre, at the slab's depth
    half = np.tan(np.radians(fov / 2))
    card = {
        "view": [yaw0 + PANO_YAW_OFFSET, pit0],
        # card centre and size on the view plane, in units of the plane's distance
        "offset": [((x0 + x1) / 2 - n / 2) / (n / 2) * half, -((y0 + y1) / 2 - n / 2) / (n / 2) * half],
        "size": [(x1 - x0) / (n / 2) * half, (y1 - y0) / (n / 2) * half],
    }
    # the angular box the slab's splats fall in: the outline's directions, fitted with an oriented box
    ou = np.array([p[0] for p in OUTLINE], float)
    ov = np.array([p[1] for p in OUTLINE], float)
    oy, op = rays(yaw0, pit0, fov, n, ou, ov)
    pts = np.stack([oy + PANO_YAW_OFFSET, op], 1)
    c = pts.mean(0)
    w, vecs = np.linalg.eigh(np.cov((pts - c).T))
    axis = vecs[:, 1]
    along, across = (pts - c) @ axis, (pts - c) @ vecs[:, 0]
    box = {"centre": c.round(2).tolist(), "angle": round(float(np.degrees(np.arctan2(axis[1], axis[0]))), 2),
           "half": [round(float(np.abs(along).max()) + 1.0, 2), round(float(np.abs(across).max()) + 1.0, 2)],
           "dist": list(DIST)}
    print("SLAB =", json.dumps({"card": {k: [round(float(x), 4) for x in v] for k, v in card.items()}, "hide": box}))
    print(f"slab.png {x1 - x0}x{y1 - y0}")


if __name__ == "__main__":
    main()
