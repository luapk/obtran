"""OBTRAN 001's manifold panel cut out for the fold (Paul, 25 October: "fold space" at the manifold, the reader drags
the panel's slabs together, a tick per crease, and the ship slingshots through when they close).

The panel is space folded into slanted slabs on white. This cuts its bounding box from the full resolution page,
keys out the page's white (only the white joined to the panel's edge, so the ship's white trails stay), paints out
the caption box (it rides as the card), and writes:
  - comics/obtran001/assets/props/fold-panel.webp: the panel with alpha, FOLD_W px wide;
  - comics/obtran001/assets/props/fold-ship.webp: the right-hand ship and its trails, for the slingshot;
  - setPieces.fold in comic.json: the facets (polygons between the panel's dominant diagonals, the zigzag between
    its top and bottom points), as fractions of the panel image, and the image sizes.
Positions are in the 1800 wide page.jpg; the cut is made from source/page_rgb.png at full resolution.
Usage: python3 tools/cut_fold_panel.py
Needs: numpy, scipy, Pillow, opencv-python.
"""
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "comics" / "obtran001"
PAGE_W = 1800                                        # the grid the positions below are read in (assets/page.jpg)
BOX = (14, 822, 1774, 1300)                          # the panel's bounding box
T, B = 828, 1294                                     # top and bottom of the slabs
# the zigzag: the panel's dominant creases run between these top and bottom points
FACETS = [
    [(18, T), (272, T), (548, B), (18, B)],
    [(272, T), (692, T), (548, B)],
    [(692, T), (835, B), (548, B)],
    [(692, T), (1045, T), (835, B)],
    [(1045, T), (1115, B), (835, B)],
    [(1045, T), (1770, T), (1770, B), (1115, B)],
]
CAPTION = (1257, 846, 1761, 977)                     # the lettering box, painted out
SHIP = (1088, 978, 1312, 1146)                       # the right-hand ship with its trails
FOLD_W = 2048


def main():
    src = Image.open(BASE / "source" / "page_rgb.png").convert("RGB")
    k = src.width / PAGE_W
    box = tuple(round(v * k) for v in BOX)
    rgb = np.asarray(src.crop(box)).copy()
    h, w = rgb.shape[:2]
    # the caption box: inpainted from the space round it
    cx0, cy0, cx1, cy1 = (round((CAPTION[0] - BOX[0]) * k), round((CAPTION[1] - BOX[1]) * k), round((CAPTION[2] - BOX[0]) * k), round((CAPTION[3] - BOX[1]) * k))
    mask = np.zeros((h, w), np.uint8)
    mask[cy0:cy1, cx0:cx1] = 255
    # a membrane fill: smooth from the sky round the box's sides and bottom, the top carrying on from below it
    # (inpainting a hole this big streaked, and pulled the slab's black edge in from above)
    q = 4
    m = round(6 * k)                                 # a margin of sky round the box to fill from
    y0, y1, x0, x1 = cy0, cy1 + m, cx0 - m, cx1 + m
    reg = cv2.resize(rgb[y0:y1, x0:x1].astype(np.float32), ((x1 - x0) // q, (y1 - y0) // q), interpolation=cv2.INTER_AREA)
    hole = np.zeros(reg.shape[:2], bool)
    hole[:-(m // q) or None, m // q:-(m // q) or None] = True
    f = reg.copy()
    f[hole] = reg[~hole].mean(0)
    for _ in range(4000):
        g = f.copy()
        g[1:-1, 1:-1] = 0.25 * (f[:-2, 1:-1] + f[2:, 1:-1] + f[1:-1, :-2] + f[1:-1, 2:])
        g[0, 1:-1] = (f[1, 1:-1] * 2 + f[0, :-2] + f[0, 2:]) / 4    # the top edge: no flow across it
        f = np.where(hole[..., None], g, reg)
    fill = np.zeros_like(rgb, dtype=np.float32)
    fill[y0:y1, x0:x1] = cv2.resize(f, (x1 - x0, y1 - y0), interpolation=cv2.INTER_CUBIC)
    fill += np.random.default_rng(5).normal(0, 4, fill.shape)
    fill = np.clip(fill, 0, 255).astype(np.uint8)
    rng = np.random.default_rng(3)                   # a few stars back in the painted-out sky
    stars = (rng.random((h, w)) > 0.9996) & (mask > 0)
    fill[ndi.binary_dilation(stars, iterations=1)] = (235, 235, 250)
    # blended in at the sides and bottom; at the top it meets the slab's own edge
    soft = cv2.GaussianBlur(mask.astype(np.float32) / 255, (0, 0), 4 * k)[..., None]
    soft[cy0:cy0 + round(8 * k), cx0 + round(8 * k):cx1 - round(8 * k)] = 1
    rgb = (rgb * (1 - soft) + fill * soft).astype(np.uint8)
    # the page's white: near white, joined to the box's edge
    white = (rgb.min(2) > 228) & (rgb.max(2) - rgb.min(2) < 24)
    lab, _ = ndi.label(white)
    edge = np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
    bg = np.isin(lab, edge[edge > 0])
    bg = ndi.binary_dilation(bg, iterations=2) & (rgb.min(2) > 200) | bg   # the soft fringe at the slab edges
    alpha = np.where(bg, 0, 255).astype(np.uint8)
    alpha = cv2.GaussianBlur(alpha, (3, 3), 0)
    out = Image.fromarray(np.dstack([rgb, alpha]), "RGBA")
    scale = FOLD_W / w
    out = out.resize((FOLD_W, round(h * scale)), Image.LANCZOS)
    props = BASE / "assets" / "props"
    out.save(props / "fold-panel.webp", quality=88, method=6)
    # the ship, from the same cut
    sx0, sy0, sx1, sy1 = [round((v - o) * k * scale) for v, o in zip(SHIP, (BOX[0], BOX[1], BOX[0], BOX[1]))]
    ship = np.asarray(out.crop((sx0, sy0, sx1, sy1))).copy()
    # only the ship: its mint hull and white glow, with the ink outlines round them; the space behind goes
    hsv = cv2.cvtColor(np.ascontiguousarray(ship[..., :3]), cv2.COLOR_RGB2HSV).astype(np.float32)
    hue, sat, val = hsv[..., 0] * 2, hsv[..., 1] / 255, hsv[..., 2] / 255
    keep = ((hue > 95) & (hue < 185) & (sat > 0.22) & (val > 0.35)) | ((val > 0.86) & (sat < 0.3))
    keep = ndi.binary_opening(keep, iterations=1)
    lab, nl = ndi.label(keep)
    if nl:
        sizes = ndi.sum(keep, lab, range(1, nl + 1))
        keep = np.isin(lab, 1 + np.nonzero(sizes >= sizes.max() * 0.02)[0])
    keep = ndi.binary_closing(keep, iterations=3)
    keep = ndi.binary_fill_holes(keep)
    keep = ndi.binary_dilation(keep, iterations=3) & ((val < 0.35) | ndi.binary_dilation(keep, iterations=1)) | keep   # the outline
    a = cv2.GaussianBlur((keep * 255).astype(np.uint8), (5, 5), 0)
    ship[..., 3] = np.minimum(ship[..., 3], a)
    ramp = np.clip(np.arange(ship.shape[1]) / (ship.shape[1] * 0.35), 0, 1) ** 1.5   # the trails fade out behind it
    ship[..., 3] = (ship[..., 3] * ramp[None, :]).astype(np.uint8)
    Image.fromarray(ship, "RGBA").save(props / "fold-ship.webp", quality=90, method=6)
    bw, bh = BOX[2] - BOX[0], BOX[3] - BOX[1]
    facets = [[[round((x - BOX[0]) / bw, 4), round((y - BOX[1]) / bh, 4)] for x, y in f] for f in FACETS]
    comic_path = BASE / "comic.json"
    comic = json.loads(comic_path.read_text())
    fold = comic["setPieces"].get("fold", {})
    fold.update({"note": "the manifold panel cut by tools/cut_fold_panel.py: facets as fractions of fold-panel.webp; the reader drags to fold them together (a tick per crease) and the ship slingshots through",
                 "image": "fold-panel.webp", "ship": "fold-ship.webp", "aspect": round(bw / bh, 4), "facets": facets})
    comic["setPieces"]["fold"] = fold
    comic_path.write_text(json.dumps(comic, indent=2, ensure_ascii=False) + "\n")
    print(f"fold-panel.webp {out.size}, ship {sx1 - sx0} x {sy1 - sy0}, {len(facets)} facets")


if __name__ == "__main__":
    main()
