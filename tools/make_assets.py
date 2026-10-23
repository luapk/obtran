"""Make the prototype's page assets from source/page_rgb.png.

Writes three files to prototype/assets:
  page.jpg   page texture, 1800 wide, sRGB
  depth.png  512 wide. R = depth (128 is the page plane, lower recedes),
             G = lettering box index * 20 (0 = none), B = Bob's panel mask
  meta.json  page aspect, singularity centre, lettering boxes, panel polygon,
             all in page UV with the origin top left

With --crops it also cuts any missing worlds/crops/*.jpg from the full
resolution page, using the pixel rectangles in worlds/manifest.json. Add
--recut to recut the ones that already exist too.

Positions are authored in a 1000 wide grid over the page (1000 x 1352).
The depth map is a heuristic: a radial tunnel that recedes at the
singularity, with Bob's panel and the lettering boxes raised flat. If layered
artwork or separate ink scans turn up, a hand made depth map replaces this.

Usage: python3 tools/make_assets.py [--crops [--recut]]
Needs: Pillow, numpy.
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "source" / "page_rgb.png"
OUT = ROOT / "prototype" / "assets"

GRID_W = 1000
CENTRE = (455, 575)

# Lettering boxes, in beat order, then the ending. (id, speaker, x0, y0, x1, y1, text)
BOXES = [
    ("caption", "narrator", 30, 15, 310, 105,
     "Canes Crescenza, 3091 AD. Spomenik Operative Bob sips his morning coffee, when suddenly the vessel's transmitter erupts..."),
    ("crsh", "transmitter", 500, 140, 722, 180, "CRSSHKKKKK!"),
    ("smoke1", "smokehouse", 575, 178, 937, 252,
     "Smokehouse Shift for Bob, this is Smokehouse Shift for Bob. You are cleared to initiate your Pulsar Protocol."),
    ("engage", "smokehouse", 745, 268, 947, 332, "Engage Chemical Digital Cryptoflage!"),
    ("bob1", "bob", 343, 328, 662, 422,
     "W-what the hell Smokehouse? I've been out here for like, 3 kalpas metascanning intergalactic tumbleweed. Are you winding..."),
    ("drill", "smokehouse", 700, 673, 962, 777,
     "This is not a drill, Bob. Engage the Spomenik Transfer Protocol. Just like you were trained to do."),
    ("unlock", "smokehouse", 578, 828, 907, 867, "Unlock your biometric key, Bob."),
    ("holy", "bob", 138, 896, 372, 937, "Holy smokes! Er, ok."),
    ("qntm", "bob", 168, 948, 432, 997, "Initiating QNTM CTRL..."),
    ("tbc", "narrator", 726, 1293, 917, 1337, "To be continued..."),
]

# Bob's panel, clockwise from the top left corner of the page edge.
PANEL = [(0, 262), (185, 197), (440, 280), (312, 352), (312, 700), (215, 745), (0, 745)]

# Measured radial depth profile (distance from the core in page widths, depth value).
PROFILE = [(0.0, 28.5), (0.075, 30.5), (0.125, 38.5), (0.175, 50), (0.225, 62), (0.275, 74),
           (0.325, 84.5), (0.375, 94), (0.425, 101), (0.475, 106), (0.525, 110), (0.575, 112.5),
           (0.625, 114.5), (0.675, 116), (0.725, 117.5), (0.775, 119), (0.825, 120.5),
           (0.875, 121.5), (0.925, 123), (2.0, 126)]
PANEL_DEPTH = 148
BOX_DEPTH = 158
DEPTH_W = 512


def fractal_noise(h, w, seed=3):
    rng = np.random.default_rng(seed)
    out = np.zeros((h, w), np.float32)
    amp = 1.0
    for cells in (4, 8, 16, 32):
        g = rng.standard_normal((cells + 1, cells + 1)).astype(np.float32)
        im = Image.fromarray(g, "F").resize((w, h), Image.BICUBIC)
        out += np.asarray(im) * amp
        amp *= 0.5
    return out / np.abs(out).max()


def main():
    page = Image.open(SRC).convert("RGB")
    W, H = page.size
    aspect = H / W
    grid_h = GRID_W * aspect
    OUT.mkdir(parents=True, exist_ok=True)

    # page texture
    tex = page.resize((1800, round(1800 * aspect)), Image.LANCZOS)
    tex.save(OUT / "page.jpg", quality=88, progressive=True, optimize=True)

    # meta
    to_uv = lambda x, y: [x / GRID_W, y / grid_h]
    meta = {
        "aspect": aspect,
        "centre": to_uv(*CENTRE),
        "bubbles": [
            {"id": i, "uv": to_uv(x0, y0) + to_uv(x1, y1), "speaker": s, "text": t}
            for (i, s, x0, y0, x1, y1, t) in BOXES
        ],
        "panel": [to_uv(x, y) for (x, y) in PANEL],
    }
    (OUT / "meta.json").write_text(json.dumps(meta))

    # depth
    dw, dh = DEPTH_W, round(DEPTH_W * aspect)
    yy, xx = np.mgrid[0:dh, 0:dw].astype(np.float32)
    u, v = (xx + 0.5) / dw, (yy + 0.5) / dh
    cu, cv = meta["centre"]
    r = np.hypot(u - cu, (v - cv) * aspect)
    pr, pd = zip(*PROFILE)
    depth = np.interp(r, pr, pd).astype(np.float32)
    # a little irregularity in the tunnel wall, strongest mid way out
    depth += fractal_noise(dh, dw) * 9.0 * np.exp(-((r - 0.3) / 0.18) ** 2)

    scale = dw / GRID_W
    panel = Image.new("L", (dw, dh), 0)
    ImageDraw.Draw(panel).polygon([(x * scale, y * scale) for x, y in PANEL], fill=255)
    panel = panel.filter(ImageFilter.GaussianBlur(2.0))
    pm = np.asarray(panel).astype(np.float32) / 255.0
    depth = depth * (1 - pm) + PANEL_DEPTH * pm

    ids = Image.new("L", (dw, dh), 0)
    boxes = Image.new("L", (dw, dh), 0)
    di, db = ImageDraw.Draw(ids), ImageDraw.Draw(boxes)
    for n, (_, _, x0, y0, x1, y1, _) in enumerate(BOXES):
        rect = [x0 * scale, y0 * scale, x1 * scale, y1 * scale]
        di.rectangle(rect, fill=(n + 1) * 20)
        db.rectangle(rect, fill=255)
    bm = np.asarray(boxes.filter(ImageFilter.GaussianBlur(1.5))).astype(np.float32) / 255.0
    depth = depth * (1 - bm) + BOX_DEPTH * bm

    rgb = np.stack([np.clip(depth + 0.5, 0, 255).astype(np.uint8), np.asarray(ids),
                    np.asarray(panel)], axis=-1)
    Image.fromarray(rgb, "RGB").save(OUT / "depth.png", optimize=True)
    print(f"wrote page.jpg {tex.size}, depth.png {dw}x{dh}, meta.json to {OUT}")

    if "--crops" in sys.argv:
        manifest = json.loads((ROOT / "worlds" / "manifest.json").read_text())
        for el in manifest["elements"]:
            x, y, w, h = el["crop_px"]
            dest = ROOT / "worlds" / el["crop"]
            if dest.exists() and "--recut" not in sys.argv:
                continue
            page.crop((x, y, x + w, y + h)).save(dest, quality=92)
            print(f"wrote {dest.relative_to(ROOT)} {w}x{h}")


if __name__ == "__main__":
    main()
