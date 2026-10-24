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

Usage: python3 tools/clean_worlds.py
Needs: numpy, Pillow.
"""
import gzip
import json
import struct
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
    return {"yaw": shrink([y0, y1], 175, 60), "pitch": shrink([p0, p1], 80, 40), "radius": float(np.percentile(dist, 50))}


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


def main():
    manifest = json.loads((ROOT / "worlds" / "manifest.json").read_text())
    crops = {e["id"]: ROOT / "worlds" / e["crop"] for e in manifest["elements"]}
    # reliefs built from the page (tools/make_bob_head.py) are the page's own ink: leave them alone
    reliefs_file = WORLDS / "reliefs.json"
    reliefs = {w["id"] for w in json.loads(reliefs_file.read_text()).get("worlds", [])} if reliefs_file.exists() else set()
    views = {}
    for src in sorted(WORLDS.glob("*.spz")):
        name = src.name
        if ".clean." in name or ".full." in name:
            continue
        wid = name.split(".")[0]
        if wid in reliefs:
            continue
        spz = read_columns(src)
        pos, alpha, rgb, radius = decode(spz)
        keep = prune_mask(pos, alpha, radius)
        dest = src.with_name(name.replace(".spz", ".clean.spz"))
        n = write_columns(spz, keep, dest)
        print(f"{dest.name:32} {n} of {spz['n']} splats kept ({spz['n'] - n} removed), {dest.stat().st_size / 1048576:.1f} MB")
        if ".100k." not in name:
            views[wid] = view_limits(pos[keep], rgb[keep])
            if wid in crops:
                views[wid]["grade"] = grade_for(crops[wid], pos[keep], rgb[keep])
            phone = WORLDS / f"{wid}.100k.spz"
            views[wid]["files"] = {"500k": f"worlds/{dest.name}", "100k": f"worlds/{wid}.100k.clean.spz" if phone.exists() else None}
            print(f"{'':32} look limits yaw {views[wid]['yaw']} pitch {views[wid]['pitch']}")
            if "grade" in views[wid]:
                g = views[wid]["grade"]
                print(f"{'':32} grade lo {g['lo']} hi {g['hi']} shares {g['shares']} mid {g['mid']}")
    (WORLDS / "views.json").write_text(json.dumps(views, indent=2) + "\n")
    print(f"wrote {WORLDS / 'views.json'}")


if __name__ == "__main__":
    main()
