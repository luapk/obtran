"""Replace painted objects in a Marble world with 3D props, one for one, where they stand.

Paul, 25 October (OBTRAN 001's skulls): "more of them, matching position of illustrations exactly". The world
holds Marble's rendering of every painted skull: blobs of light, unsaturated splats on the ground. This finds
them the way the eye does, in a panorama seen from the viewpoint (nearest opaque splat per pixel, so hidden
splats do not count): light unsaturated pixels below the horizon, split into blobs by the dark sockets and the
ground between them. Each blob's splats give its place (median position, as [yaw, pitch, distance] in the
world's frame, Marble units) and its size (90th to 10th percentile across x and z). A blob must lie on the ground
(Paul: "some of the skulls appear to be floating above and in front of structures"): light patches painted on a
wall or on top of a ruin are found too, and a 3D skull there stands out of the wall. So the surface round each blob
(a ring of pixels just outside it) must be within --tilt (40) degrees of level, against the floor's up (a plane
fitted to the splats below the horizon), and the blob no higher than --height (0.2, Marble units) above the floor.
Then:
  - the prop's copies in comic.json (setPieces.props, the entry with this id) are replaced, one per blob: near
    ones (distance under --near) take the detailed models, far ones the light ones, cycling the designs, each
    turned at random;
  - the blobs' splats, and the dark splats inside each blob's radius (sockets, outlines), are dropped from the
    world's .clean.spz and .100k.clean.spz, so the painted object is gone where the 3D one stands.
Run it after tools/clean_worlds.py (which rewrites the clean files).

Usage: python3 tools/replace_blobs.py --comic <id> --world <id> --prop <id> [--near 0.95] [--min-area 40]
       [--size 0.025,0.14] [--yaw -100,100] [--pitch -72,-4] [--dist 2.0] [--tilt 40] [--height 0.2] [--dry-run]
Needs: numpy, scipy, Pillow.
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

sys.path.insert(0, str(Path(__file__).resolve().parent))
import clean_worlds as CW  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def opt(name, default):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def pair(s):
    a, b = s.split(",")
    return float(a), float(b)


def detect(pos, rgb, alpha, W=2048, min_area=40):
    keep = np.nonzero(alpha > 0.35)[0]
    p, c = pos[keep], rgb[keep]
    d = np.linalg.norm(p, axis=1)
    yaw = np.degrees(np.arctan2(p[:, 0], p[:, 2]))
    pit = np.degrees(np.arcsin(np.clip(-p[:, 1] / d, -1, 1)))
    mx, mn = c.max(1), c.min(1)
    sat = (mx - mn) / np.maximum(mx, 1e-4)
    lum = c @ CW.LUMA
    H = W // 2
    px = ((yaw / 360 + 0.5) * W).astype(int).clip(0, W - 1)
    py = ((0.5 - pit / 180) * H).astype(int).clip(0, H - 1)
    order = np.argsort(-d)
    img = np.full((H, W), -1, np.int64)
    img[py[order], px[order]] = order
    vis = img >= 0
    for _ in range(2):
        near = ndi.grey_dilation(np.where(vis, img, -1), size=3)
        img = np.where(vis, img, near)
        vis = img >= 0
    idx = img[vis]
    m = np.zeros((H, W), bool)
    m[vis] = ((lum > 0.6) & (sat < 0.22) & (pit < -2) & (d < 3.5))[idx]
    m = ndi.binary_opening(m, iterations=1)
    lab, _ = ndi.label(m)
    blobs = []
    for k, sl in enumerate(ndi.find_objects(lab), 1):
        comp = lab[sl] == k
        if comp.sum() < min_area:
            continue
        # the surface just outside the blob: a ring a few pixels wide round it
        pad = 6
        y0, y1, x0, x1 = max(sl[0].start - pad, 0), min(sl[0].stop + pad, H), max(sl[1].start - pad, 0), min(sl[1].stop + pad, W)
        inside = lab[y0:y1, x0:x1] == k
        ring = ndi.binary_dilation(inside, iterations=pad) & ~ndi.binary_dilation(inside, iterations=2) & vis[y0:y1, x0:x1]
        rid = img[y0:y1, x0:x1][ring]
        ring_d = float(np.median(d[rid])) if len(rid) else 0.0
        # the slope of that surface: the normal of a plane through the ring's points
        rp = p[np.unique(rid)]
        normal = np.linalg.svd(rp - rp.mean(0), full_matrices=False)[2][2] if len(rp) >= 6 else np.zeros(3)
        ids = np.unique(img[sl][comp])
        ids = ids[ids >= 0]
        q = p[ids]
        ctr = np.median(q, axis=0)
        dist = float(np.linalg.norm(ctr))
        ext = np.percentile(q, 90, axis=0) - np.percentile(q, 10, axis=0)
        blobs.append({"at": [round(float(np.degrees(np.arctan2(ctr[0], ctr[2]))), 2), round(float(np.degrees(np.arcsin(-ctr[1] / dist))), 2), round(dist, 3)],
                      "size": round(float(max(ext[0], ext[2], 0.02) * 1.1), 3), "centre": ctr.tolist(), "area": int(comp.sum()),
                      "ring": round(ring_d, 3), "normal": normal.tolist()})
    return blobs


def ground_up(pos, alpha, seed=1):
    """The floor's up direction and level: a plane fitted (RANSAC) to the opaque splats well below the horizon."""
    p = pos[alpha > 0.35]
    d = np.linalg.norm(p, axis=1)
    fl = p[np.degrees(np.arcsin(np.clip(-p[:, 1] / d, -1, 1))) < -12]
    rng, best = np.random.default_rng(seed), None
    for _ in range(300):
        s = fl[rng.choice(len(fl), 3, replace=False)]
        n = np.cross(s[1] - s[0], s[2] - s[0])
        if np.linalg.norm(n) < 1e-9:
            continue
        n /= np.linalg.norm(n)
        inl = int((np.abs((fl - s[0]) @ n) < 0.02).sum())
        if best is None or inl > best[0]:
            best = (inl, n)
    n = best[1]
    n = -n if n[1] > 0 else n                        # OpenCV axes: up is -y
    h = fl @ n
    return n, float(np.median(h[np.abs(h - np.median(h)) < 0.05]))


def strip(path, blobs, pad=0.75):
    spz = CW.read_columns(path)
    pos, alpha, rgb, radius = CW.decode(spz)
    mx, mn = rgb.max(1), rgb.min(1)
    sat = (mx - mn) / np.maximum(mx, 1e-4)
    lum = rgb @ CW.LUMA
    drop = np.zeros(len(pos), bool)
    for b in blobs:
        r = b["size"] * pad
        near = np.linalg.norm(pos - np.array(b["centre"]), axis=1) < r
        # the bone (light, unsaturated) and the dark sockets and outlines inside it; coloured ground stays
        drop |= near & (sat < 0.45) & ((lum > 0.45) | (lum < 0.25))
    n = CW.write_columns(spz, ~drop, path)
    return int(drop.sum()), n


def main():
    cid, wid, pid = opt("--comic", None), opt("--world", None), opt("--prop", None)
    if not (cid and wid and pid):
        sys.exit(__doc__)
    base = ROOT / "comics" / cid
    worlds = base / "worlds" / "worlds"
    src = worlds / f"{wid}.clean.spz"
    spz = CW.read_columns(src)
    pos, alpha, rgb, _ = CW.decode(spz)
    blobs = detect(pos, rgb, alpha, min_area=int(opt("--min-area", 40)))
    s0, s1 = pair(opt("--size", "0.025,0.14"))
    y0, y1 = pair(opt("--yaw", "-100,100"))
    p0, p1 = pair(opt("--pitch", "-72,-4"))
    dmax = float(opt("--dist", 2.0))
    blobs = [b for b in blobs if y0 < b["at"][0] < y1 and p0 < b["at"][1] < p1 and b["at"][2] < dmax and s0 <= b["size"] <= s1]
    up, floor = ground_up(pos, alpha)
    tilt_max, h_max = float(opt("--tilt", 40)), float(opt("--height", 0.2))
    ground = []
    for b in blobs:
        tilt = float(np.degrees(np.arccos(min(1.0, abs(float(np.dot(b["normal"], up)))))))
        h = float(np.dot(b["centre"], up)) - floor
        if tilt <= tilt_max and h <= h_max:
            ground.append(b)
        else:
            print(f"  not on the ground, left alone: at {b['at']}, surface {tilt:.0f} degrees from level, {h:.2f} above the floor")
    blobs = ground
    near_d = float(opt("--near", 0.95))
    print(f"{len(blobs)} blobs ({sum(b['at'][2] < near_d for b in blobs)} near)")
    comic_path = base / "comic.json"
    comic = json.loads(comic_path.read_text())
    prop = next((p for p in comic["setPieces"].get("props", []) if p.get("id") == pid), None)
    if prop is None:
        sys.exit(f"no prop with id {pid} in {comic_path}")
    designs = prop.get("designs", 3)
    rng = np.random.default_rng(7)
    copies = []
    for k, b in enumerate(sorted(blobs, key=lambda b: b["at"][0])):
        far = b["at"][2] >= near_d
        copies.append({"at": b["at"], "size": round(b["size"] * prop.get("grow", 1.15), 3), "model": (k % designs) + (designs if far else 0),
                       "turn": [int(rng.integers(-15, 16)), int(rng.integers(-40, 41)), int(rng.integers(-12, 13))]})
    prop["copies"] = copies
    if "--dry-run" in sys.argv:
        print(json.dumps(copies[:5], indent=1))
        return
    comic_path.write_text(json.dumps(comic, indent=2, ensure_ascii=False) + "\n")
    for f in (src, worlds / f"{wid}.100k.clean.spz"):
        if f.exists():
            dropped, kept = strip(f, blobs)
            print(f"{f.name}: dropped {dropped} splats, {kept} kept")
    print(f"wrote {len(copies)} copies to {comic_path}")


if __name__ == "__main__":
    main()
