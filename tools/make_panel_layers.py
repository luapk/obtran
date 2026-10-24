"""Cut Bob's panel from the page into layers, to float in the opening space with parallax.

  python3 tools/make_panel_layers.py

Paul, 24 October: in the opening space the illustration of Bob was unclear, so his black
panel is cut out to float above the splat background, with elements inside it sliced
into layers for parallax. Three layers, all on the same canvas (the panel's bounds):
  panel-back.webp    the panel, with the figure and the controls filled in behind them
  panel-figure.webp  Bob: halo, helmet ring, body and arms, with the controls filled in
  panel-front.webp   the controls: the four dials, the coffee cup and the stick
The fill is the surrounding ink diffused into the gap and darkened, so when the layers slide apart
there is plausible panel behind rather than a hole or a second copy. Outlines are traced
by eye in the 1000 wide page grid (PANEL is make_assets.py's).
"""
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy.ndimage import gaussian_filter

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "source" / "page_rgb.png"
OUT = ROOT / "prototype" / "assets" / "props"
SCALE = 0.6                              # of the full resolution scan

PANEL = [(0, 262), (185, 197), (440, 280), (312, 352), (312, 700), (215, 745), (0, 745)]
FIGURE = [(148.5, 266.5), (211.5, 232.8), (288.0, 253.0), (324.0, 307.0), (315.0, 370.0), (288.0, 401.5), (310.5, 442.0),
          (315.0, 505.0), (297.0, 568.0), (252.0, 613.0), (202.5, 622.0), (148.5, 586.0), (90.0, 581.5), (54.0, 532.0),
          (27.0, 478.0), (36.0, 442.0), (67.5, 424.0), (103.5, 401.5), (135.0, 370.0)]
FRONT = [(78.8, 417.2), (135.0, 415.0), (171.0, 424.0), (211.5, 442.0), (222.8, 412.8), (276.8, 415.0), (281.2, 460.0),
         (252.0, 480.2), (211.5, 500.5), (184.5, 505.0), (182.2, 604.0), (130.5, 606.2), (114.8, 514.0), (83.2, 464.5)]


def fill(rgb, hole):
    """Fill the hole by diffusing the colours around it in, coarse to fine."""
    known = (~hole).astype(np.float32)
    out = rgb.copy()
    for sigma in (40, 20, 10, 5):
        w = gaussian_filter(known, sigma)
        est = np.stack([gaussian_filter(rgb[..., c] * known, sigma) for c in range(3)], -1) / np.maximum(w, 1e-4)[..., None]
        out = np.where(hole[..., None], est, out)
    # mostly ink: a diffused edge of white would show as a grey halo when the layers part
    return np.where(hole[..., None], out * 0.3, rgb)


def main():
    page = Image.open(PAGE).convert("RGB")
    s = page.width / 1000
    xs, ys = [p[0] for p in PANEL], [p[1] for p in PANEL]
    box = (int(min(xs) * s), int(min(ys) * s), int(max(xs) * s), int(max(ys) * s))
    crop = page.crop(box)
    w, h = int(crop.width * SCALE), int(crop.height * SCALE)
    crop = crop.resize((w, h), Image.LANCZOS)
    rgb = np.asarray(crop).astype(np.float32) / 255

    def mask(poly, grow=0):
        m = Image.new("L", (w, h), 0)
        ImageDraw.Draw(m).polygon([((x * s - box[0]) * SCALE, (y * s - box[1]) * SCALE) for x, y in poly], fill=255)
        if grow:
            m = m.filter(ImageFilter.MaxFilter(grow * 2 + 1))
        return m

    panel, figure, front = mask(PANEL), mask(FIGURE), mask(FRONT)
    fig_hole = np.asarray(figure.filter(ImageFilter.MaxFilter(9))) > 0
    front_hole = np.asarray(front.filter(ImageFilter.MaxFilter(9))) > 0
    soft = lambda m: np.asarray(m.filter(ImageFilter.GaussianBlur(1.6)))
    layers = {
        "panel-back.webp": (fill(rgb, fig_hole | front_hole), soft(panel)),
        "panel-figure.webp": (fill(rgb, front_hole), soft(figure)),
        "panel-front.webp": (rgb, soft(front)),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    for name, (img, a) in layers.items():
        rgba = np.dstack([(np.clip(img, 0, 1) * 255).astype(np.uint8), a.astype(np.uint8)])
        Image.fromarray(rgba, "RGBA").save(OUT / name, quality=84, method=6)   # WebP keeps the alpha, at a fraction of PNG
        print(f"{name} {w}x{h} {(OUT / name).stat().st_size // 1024} KB")
    # the canvas in page UV, for placing the layers
    print("PANEL_UV =", json.dumps([round(box[0] / page.width, 5), round(box[1] / page.height, 5),
                                    round(box[2] / page.width, 5), round(box[3] / page.height, 5)]))


if __name__ == "__main__":
    main()
