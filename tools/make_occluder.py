"""An invisible depth shell for a world, so 3D props are hidden behind the world's own structures.

Splats write no depth, so a prop (OBTRAN 001's skulls) drew over the world wherever the camera drifted: skulls by the
ruins showed through the ruins (Paul: "some of the skulls appear to be floating above and in front of structures").
This writes the world's surface as seen from the viewpoint: a 256 x 128 equirectangular map of the distance to the
nearest opaque splat (in the world's frame, Marble units), holes filled from their neighbours, pushed back 3% so the
ground under a prop does not cut into it. The page builds a mesh from it (only in worlds with props), drawn into
depth only, after the splats and before the props, leaving out triangles across a jump in depth so a structure's
edge does not hide what stands beside it.

Output: <worlds>/<id>.occ.bin: uint16 little endian, row by row from the top (pitch +90) and from yaw -180,
q = log(d / 0.05) / log(2000) * 65535 (0 where nothing is there: open sky).
Usage: python3 tools/make_occluder.py --comic <id> --world <id>
Needs: numpy, scipy.
"""
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

sys.path.insert(0, str(Path(__file__).resolve().parent))
import clean_worlds as CW  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
W, H = 256, 128


def main():
    if "--comic" not in sys.argv or "--world" not in sys.argv:
        sys.exit(__doc__)
    cid = sys.argv[sys.argv.index("--comic") + 1]
    wid = sys.argv[sys.argv.index("--world") + 1]
    worlds = ROOT / "worlds" / "worlds" if cid == "obtran003" else ROOT / "comics" / cid / "worlds" / "worlds"
    pos, alpha, _, _ = CW.decode(CW.read_columns(worlds / f"{wid}.clean.spz"))
    p = pos[alpha > 0.35]
    d = np.linalg.norm(p, axis=1)
    yaw = np.degrees(np.arctan2(p[:, 0], p[:, 2]))
    pit = np.degrees(np.arcsin(np.clip(-p[:, 1] / d, -1, 1)))
    px = ((yaw / 360 + 0.5) * W).astype(int).clip(0, W - 1)
    py = ((0.5 - pit / 180) * H).astype(int).clip(0, H - 1)
    # the nearest opaque splat per pixel
    dep = np.full((H, W), np.inf)
    order = np.argsort(-d)
    dep[py[order], px[order]] = d[order]
    seen = np.isfinite(dep)
    filled = dep.copy()
    for _ in range(4):                               # holes from their neighbours
        near = ndi.grey_erosion(np.where(np.isfinite(filled), filled, np.inf), size=3)
        filled = np.where(np.isfinite(filled), filled, near)
    filled = ndi.median_filter(np.where(np.isfinite(filled), filled, 0), size=3)
    filled = np.where(filled > 0, filled * 1.03, 0)
    q = np.where(filled > 0, np.log(np.maximum(filled, 0.05) / 0.05) / np.log(2000) * 65535, 0).round().clip(0, 65535).astype("<u2")
    out = worlds / f"{wid}.occ.bin"
    out.write_bytes(q.tobytes())
    print(f"wrote {out} ({W} x {H}, {seen.mean():.0%} of pixels seen, distance {np.percentile(filled[filled > 0], 5):.2f} to {np.percentile(filled[filled > 0], 95):.2f})")


if __name__ == "__main__":
    main()
