"""Clean the Marble worlds for the page, and work out where each can be looked at.

For each worlds/worlds/<id>.spz (and its .100k.spz) this writes <id>.clean.spz
(and <id>.100k.clean.spz) with stray splats removed:
  - far floaters, more than 1.5x the 99.5th percentile distance from the origin
  - oversized "taffy" splats, more than 4x the 99.9th percentile radius
  - nearly invisible splats (opacity under 2%)

It also writes worlds/worlds/views.json. For each world it holds the ink grade:
the ink, mid and paper colours sampled from the world's source crop, and the two
luminance thresholds that give the world the same shares of ink, mid and paper
as the crop. And it holds the yaw and pitch range
around the forward view that holds drawn content (splats brighter than the dark
fill Marble puts where it had nothing to go on), never narrower than 60 degrees
of yaw and 40 of pitch either side, because dark ink does not count as lit. The page limits looking around
to that range so the reader stays inside what Marble actually made.

Marble worlds put the input view at the origin, looking down +z with y down
(OpenCV axes). Angles here are in degrees in that frame: yaw positive to the
right, pitch positive up.

A colour comic (its manifest says "grade": {"mode": "palette"}) gets a palette grade instead of the
three tones: the world's colours are moved to the crop's (mean and spread of luma and the two colour
axes, over the front view) and then pulled towards the crop's own main colours (k-means over the crop
in Lab, "colours" of them, 8 by default), so Marble's invented regions take the painting's colours.

Usage: python3 tools/clean_worlds.py [--comic <id>] [--only <id>,<id>]
  --only: just these worlds; the rest of views.json and their clean files are kept as they are (a full run
  rewrites every clean file, so tools/replace_blobs.py and make_occluder.py must be run again after it)
  (another comic: its manifest and crops in comics/<id>/worlds, its splats in comics/<id>/worlds/worlds)
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
WORLDS = ROOT / "worlds" / "worlds"
LIT = 0.18          # luminance above which a splat counts as drawn content
LIT_SHARE = 0.10    # share of lit splats a direction needs to count as content
MARGIN = 10.0       # degrees kept clear of the content edge
SH_DIM = {0: 0, 1: 3, 2: 8, 3: 15}
LUMA = np.array([0.299, 0.587, 0.114])
CROP_INK, CROP_PAPER = 0.16, 0.5  # luminance bands that read as ink and paper on the page
PAPER_FLOOR = 0.42                 # lowest world luminance allowed to become paper


def read_columns(path):
    raw = path.read_bytes()
    d = gzip.decompress(raw) if raw[:2] == b"\x1f\x8b" else raw
    magic, version, n, sh_deg, frac, flags, reserved = struct.unpack("<IIIBBBB", d[:16])
    if magic != 0x5053474E or version not in (2, 3):
        raise ValueError(f"{path.name}: unsupported spz (version {version})")
    rot = 3 if version == 2 else 4
    sizes = [("pos", 9), ("alpha", 1), ("color", 3), ("scale", 3), ("rot", rot), ("sh", SH_DIM[sh_deg] * 3)]
    cols, o = {}, 16
    for name, k in sizes:
        cols[name] = np.frombuffer(d, np.uint8, n * k, o).reshape(n, k) if k else np.zeros((n, 0), np.uint8)
        o += n * k
    return {"header": (magic, version, sh_deg, frac, flags, reserved), "n": n, "cols": cols, "order": [s[0] for s in sizes]}


def decode(spz):
    c, frac = spz["cols"], spz["header"][3]
    p = c["pos"].reshape(-1, 3, 3).astype(np.int32)
    v = p[..., 0] | (p[..., 1] << 8) | (p[..., 2] << 16)
    v = np.where(v & 0x800000, v - 0x1000000, v)
    pos = v.astype(np.float32) / (1 << frac)
    alpha = c["alpha"][:, 0].astype(np.float32) / 255.0
    rgb = np.clip(0.5 + 0.28209479 * ((c["color"].astype(np.float32) / 255.0 - 0.5) / 0.15), 0, 1)
    radius = np.exp(c["scale"].astype(np.float32) / 16.0 - 10.0).max(axis=1)
    return pos, alpha, rgb, radius


def write_columns(spz, keep, path):
    magic, version, sh_deg, frac, flags, reserved = spz["header"]
    n = int(keep.sum())
    body = b"".join(np.ascontiguousarray(spz["cols"][k][keep]).tobytes() for k in spz["order"])
    head = struct.pack("<IIIBBBB", magic, version, n, sh_deg, frac, flags, reserved)
    path.write_bytes(gzip.compress(head + body, compresslevel=9, mtime=0))
    return n


def prune_mask(pos, alpha, radius):
    dist = np.linalg.norm(pos, axis=1)
    return (dist <= 1.5 * np.percentile(dist, 99.5)) & (radius <= 4 * np.percentile(radius, 99.9)) & (alpha >= 0.02)


def content_range(angle, lit, lo, hi, step=5.0):
    """Widest contiguous range around 0 whose bins hold enough lit splats."""
    edges = np.arange(lo, hi + step, step)
    tot, _ = np.histogram(angle, bins=edges)
    hit, _ = np.histogram(angle, bins=edges, weights=lit)
    ok = (tot > 0) & (hit >= LIT_SHARE * np.maximum(tot, 1))
    centre = int(np.searchsorted(edges, 0.0) - 1)
    if not ok[centre]:
        return [0.0, 0.0]
    a = b = centre
    while a > 0 and ok[a - 1]:
        a -= 1
    while b < len(ok) - 1 and ok[b + 1]:
        b += 1
    return [float(edges[a]), float(edges[b + 1])]


def view_limits(pos, rgb):
    dist = np.linalg.norm(pos, axis=1) + 1e-9
    yaw = np.degrees(np.arctan2(pos[:, 0], pos[:, 2]))
    pitch = np.degrees(np.arcsin(np.clip(-pos[:, 1] / dist, -1, 1)))
    lit = (rgb @ LUMA > LIT).astype(np.float32)
    y0, y1 = content_range(yaw, lit, -180, 180)
    front = np.abs(yaw) < 60
    p0, p1 = content_range(pitch[front], lit[front], -90, 90)
    # dark ink (black ribbons, shadows) does not count as lit, so never limit below a floor
    def shrink(r, cap, floor):
        lo, hi = (r[0] + MARGIN, r[1] - MARGIN) if r[1] - r[0] > 2 * MARGIN else (0.0, 0.0)
        return [max(-cap, min(lo, -floor)), min(cap, max(hi, floor))]
    # how far the nearest things ahead are (3rd percentile within 35 degrees of forward): the camera's wander
    # is kept within this, as deep worlds (OBTRAN 001's ruins: median 7, ground 0.46 ahead) have near scenery
    fwd = pos[:, 2] / dist > np.cos(np.radians(35))
    clear = float(np.percentile(dist[fwd], 3)) if fwd.sum() > 100 else float(np.percentile(dist, 3))
    return {"yaw": shrink([y0, y1], 175, 60), "pitch": shrink([p0, p1], 80, 40), "radius": float(np.percentile(dist, 50)),
            "clear": round(clear, 3)}


def grade_for(crop_path, pos, rgb):
    """Palette from the crop; thresholds that give the world's front view the crop's tone shares."""
    a = np.asarray(Image.open(crop_path).convert("RGB"), np.float32) / 255.0
    lum = a @ LUMA
    ink, paper = lum < CROP_INK, lum > CROP_PAPER
    mid = ~ink & ~paper
    # match over what the reader mostly sees: the front, not the dark fill behind
    dist = np.linalg.norm(pos, axis=1) + 1e-9
    yaw = np.degrees(np.arctan2(pos[:, 0], pos[:, 2]))
    pitch = np.degrees(np.arcsin(np.clip(-pos[:, 1] / dist, -1, 1)))
    front = (np.abs(yaw) < 70) & (np.abs(pitch) < 50)
    world = rgb[front] @ LUMA
    lo = float(np.quantile(world, ink.mean()))
    hi = float(np.quantile(world, 1 - paper.mean()))
    colour = lambda m: [round(float(x), 3) for x in a[m].mean(axis=0)]
    # paper has to be genuinely bright: a crop with little paper must not turn haze white
    hi = max(hi, PAPER_FLOOR, lo + 0.02)
    return {"lo": round(lo, 4), "hi": round(hi, 4),
            "ink": colour(ink), "mid": colour(mid), "paper": colour(paper),
            "shares": [round(float(ink.mean()), 3), round(float(mid.mean()), 3), round(float(paper.mean()), 3)]}


# YCbCr (full range, BT.601): luma and two colour axes, a cheap space for moving colours on the GPU
YCC = np.array([[0.299, 0.587, 0.114], [-0.168736, -0.331264, 0.5], [0.5, -0.418688, -0.081312]])


def srgb_to_lab(rgb):
    c = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    xyz = c @ np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]]).T
    xyz /= np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[:, 1] - 16, 500 * (f[:, 0] - f[:, 1]), 200 * (f[:, 1] - f[:, 2])], axis=1)


def kmeans(x, k, iters=30, seed=5):
    rng = np.random.default_rng(seed)
    c = x[rng.choice(len(x), 1)]
    for _ in range(1, k):  # k-means++ seeding
        d = ((x[:, None, :] - c[None]) ** 2).sum(-1).min(1)
        c = np.vstack([c, x[rng.choice(len(x), 1, p=d / d.sum())]])
    for _ in range(iters):
        lab = ((x[:, None, :] - c[None]) ** 2).sum(-1).argmin(1)
        c = np.array([x[lab == j].mean(0) if (lab == j).any() else c[j] for j in range(k)])
    return c, lab


def palette_grade_for(crop_path, pos, rgb, colours=8):
    """Move the world's front view to the crop's colour statistics, then pull towards the crop's main colours."""
    a = (np.asarray(Image.open(crop_path).convert("RGB"), np.float32) / 255.0).reshape(-1, 3)
    rng = np.random.default_rng(1)
    a = a[rng.choice(len(a), min(len(a), 40000), replace=False)]
    dist = np.linalg.norm(pos, axis=1) + 1e-9
    yaw = np.degrees(np.arctan2(pos[:, 0], pos[:, 2]))
    pitch = np.degrees(np.arcsin(np.clip(-pos[:, 1] / dist, -1, 1)))
    front = (np.abs(yaw) < 70) & (np.abs(pitch) < 50)
    yc, yw = a @ YCC.T, rgb[front] @ YCC.T
    centres, lab = kmeans(srgb_to_lab(a), colours)
    pal = np.array([a[lab == j].mean(0) for j in range(colours) if (lab == j).any()])
    share = np.array([(lab == j).mean() for j in range(colours) if (lab == j).any()])
    order = np.argsort(pal @ LUMA)
    pal, share = pal[order], share[order]
    lum = rgb[front] @ LUMA
    r3 = lambda v: [round(float(x), 4) for x in v]
    return {"mode": "palette",
            "mw": r3(yw.mean(0)), "sw": r3(np.maximum(yw.std(0), 1e-3)),
            "mc": r3(yc.mean(0)), "sc": r3(np.maximum(yc.std(0), 1e-3)),
            "palette": [r3(p) for p in pal], "shares": r3(share),
            # luminance bands for the extrusion and echoes (bright things come forward): the world's own quartiles
            "lo": round(float(np.quantile(lum, 0.25)), 4), "hi": round(float(np.quantile(lum, 0.75)), 4),
            # how far to move towards the crop's statistics, how hard to pull to the palette, and how soft the pull is
            # (a strong pull posterises: Lyra's red ground went yellow and the manifold's nebulae turned to blotches)
            "transfer": 0.6, "pull": 0.45, "soft": 0.08}


def main():
    global WORLDS
    base = ROOT / "worlds"
    if "--comic" in sys.argv:
        cid = sys.argv[sys.argv.index("--comic") + 1]
        if cid != "obtran003":
            base = ROOT / "comics" / cid / "worlds"
            WORLDS = base / "worlds"
    manifest = json.loads((base / "manifest.json").read_text())
    crops = {e["id"]: base / e["crop"] for e in manifest["elements"]}
    gmode = manifest.get("grade", {})
    # reliefs built from the page (tools/make_bob_head.py) are the page's own ink: leave them alone
    reliefs_file = WORLDS / "reliefs.json"
    reliefs = {w["id"] for w in json.loads(reliefs_file.read_text()).get("worlds", [])} if reliefs_file.exists() else set()
    only = set(sys.argv[sys.argv.index("--only") + 1].split(",")) if "--only" in sys.argv else None
    old = WORLDS / "views.json"
    views = json.loads(old.read_text()) if only and old.exists() else {}
    for src in sorted(WORLDS.glob("*.spz")):
        name = src.name
        if ".clean." in name or ".full." in name:
            continue
        wid = name.split(".")[0]
        if wid in reliefs or (only and wid not in only):
            continue
        spz = read_columns(src)
        pos, alpha, rgb, radius = decode(spz)
        keep = prune_mask(pos, alpha, radius)
        dest = src.with_name(name.replace(".spz", ".clean.spz"))
        n = write_columns(spz, keep, dest)
        print(f"{dest.name:32} {n} of {spz['n']} splats kept ({spz['n'] - n} removed), {dest.stat().st_size / 1048576:.1f} MB")
        if ".100k." not in name:
            views[wid] = view_limits(pos[keep], rgb[keep])
            if wid in crops and gmode.get("mode") == "palette":
                views[wid]["grade"] = palette_grade_for(crops[wid], pos[keep], rgb[keep], gmode.get("colours", 8))
            elif wid in crops:
                views[wid]["grade"] = grade_for(crops[wid], pos[keep], rgb[keep])
            phone = WORLDS / f"{wid}.100k.spz"
            views[wid]["files"] = {"500k": f"worlds/{dest.name}", "100k": f"worlds/{wid}.100k.clean.spz" if phone.exists() else None}
            print(f"{'':32} look limits yaw {views[wid]['yaw']} pitch {views[wid]['pitch']}")
            if "grade" in views[wid] and views[wid]["grade"].get("mode") == "palette":
                print(f"{'':32} palette {len(views[wid]['grade']['palette'])} colours, shares {views[wid]['grade']['shares']}")
            elif "grade" in views[wid]:
                g = views[wid]["grade"]
                print(f"{'':32} grade lo {g['lo']} hi {g['hi']} shares {g['shares']} mid {g['mid']}")
    (WORLDS / "views.json").write_text(json.dumps(views, indent=2) + "\n")
    print(f"wrote {WORLDS / 'views.json'}")


if __name__ == "__main__":
    main()
