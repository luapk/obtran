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
       python3 tools/make_assets.py --comic <id>
Another comic reads its layout (grid, focal point, boxes, glow panel, depths) from
comics/<id>/layout.json and its page from comics/<id>/source/page_rgb.png, and
writes to comics/<id>/assets. Its boxes are axis-aligned rectangles: each box's
poly is its rect, and no outline tracing runs. Its crops come from
tools/cut_crops.py. OBTRAN 003 (no --comic) keeps the constants below.
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
     "W-what the hell Smokehouse? I've been out here for like, 3 kalpas metascanning intergalactic tumbleweed."),
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


def load_comic(cid):
    """Another comic's layout, as the same names OBTRAN 003 uses."""
    d = ROOT / "comics" / cid
    lay = json.loads((d / "layout.json").read_text())
    boxes = [(b["id"], b.get("speaker", "narrator"), *b["rect"], b["text"]) for b in lay["boxes"]]
    return dict(src=d / "source" / "page_rgb.png", out=d / "assets", grid_w=lay.get("grid_w", 1000),
                centre=tuple(lay["centre"]), boxes=boxes, panel=[tuple(p) for p in lay.get("panel", [])],
                tunnel=lay.get("tunnel", True), panel_depth=lay.get("panel_depth", PANEL_DEPTH),
                box_depth=lay.get("box_depth", BOX_DEPTH), rect_poly=True)


def main():
    cid = sys.argv[sys.argv.index("--comic") + 1] if "--comic" in sys.argv else "obtran003"
    if cid == "obtran003":
        c = dict(src=SRC, out=OUT, grid_w=GRID_W, centre=CENTRE, boxes=BOXES, panel=PANEL, tunnel=True,
                 panel_depth=PANEL_DEPTH, box_depth=BOX_DEPTH, rect_poly=False)
    else:
        c = load_comic(cid)
    SRC_, OUT_, GW, BOXES_, PANEL_ = c["src"], c["out"], c["grid_w"], c["boxes"], c["panel"]
    page = Image.open(SRC_).convert("RGB")
    W, H = page.size
    aspect = H / W
    grid_h = GW * aspect
    OUT_.mkdir(parents=True, exist_ok=True)

    # page texture
    tex = page.resize((1800, round(1800 * aspect)), Image.LANCZOS)
    tex.save(OUT_ / "page.jpg", quality=88, progressive=True, optimize=True)

    # meta
    to_uv = lambda x, y: [x / GW, y / grid_h]
    meta = {
        "aspect": aspect,
        "centre": to_uv(*c["centre"]),
        "bubbles": [
            {"id": i, "uv": to_uv(x0, y0) + to_uv(x1, y1), "speaker": s, "text": t}
            for (i, s, x0, y0, x1, y1, t) in BOXES_
        ],
        "panel": [to_uv(x, y) for (x, y) in PANEL_],
    }
    if c["rect_poly"]:
        # rectangular boxes: the outline is the rect, rounded like trace_bubbles writes it
        for b in meta["bubbles"]:
            u0, v0, u1, v1 = b["uv"]
            b["uv"] = [round(t, 5) for t in b["uv"]]
            b["poly"] = [[round(u, 5), round(v, 5)] for u, v in ((u0, v0), (u1, v0), (u1, v1), (u0, v1))]
    (OUT_ / "meta.json").write_text(json.dumps(meta))

    # depth
    dw, dh = DEPTH_W, round(DEPTH_W * aspect)
    yy, xx = np.mgrid[0:dh, 0:dw].astype(np.float32)
    u, v = (xx + 0.5) / dw, (yy + 0.5) / dh
    cu, cv = meta["centre"]
    r = np.hypot(u - cu, (v - cv) * aspect)
    if c["tunnel"]:
        pr, pd = zip(*PROFILE)
        depth = np.interp(r, pr, pd).astype(np.float32)
        # a little irregularity in the tunnel wall, strongest mid way out
        depth += fractal_noise(dh, dw) * 9.0 * np.exp(-((r - 0.3) / 0.18) ** 2)
    else:
        # no tunnel: the art sits a little behind the white gutters, with soft relief from its own light
        # (brighter recedes less), so it reads as panels set into the page
        small = np.asarray(page.resize((dw, dh), Image.BILINEAR)).astype(np.float32)
        gutter = (small.min(axis=2) > 225).astype(np.float32)
        gutter = np.asarray(Image.fromarray((gutter * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2))).astype(np.float32) / 255.0
        lum = np.asarray(Image.fromarray(small.mean(axis=2).astype(np.uint8)).filter(ImageFilter.GaussianBlur(3))).astype(np.float32) / 255.0
        art = 116 + lum * 8 + fractal_noise(dh, dw) * 3.0
        depth = (art * (1 - gutter) + 128 * gutter).astype(np.float32)

    scale = dw / GW
    panel = Image.new("L", (dw, dh), 0)
    if PANEL_:
        ImageDraw.Draw(panel).polygon([(x * scale, y * scale) for x, y in PANEL_], fill=255)
    panel = panel.filter(ImageFilter.GaussianBlur(2.0))
    pm = np.asarray(panel).astype(np.float32) / 255.0
    if c["tunnel"]:
        depth = depth * (1 - pm) + c["panel_depth"] * pm

    ids = Image.new("L", (dw, dh), 0)
    boxes = Image.new("L", (dw, dh), 0)
    di, db = ImageDraw.Draw(ids), ImageDraw.Draw(boxes)
    for n, (_, _, x0, y0, x1, y1, _) in enumerate(BOXES_):
        rect = [x0 * scale, y0 * scale, x1 * scale, y1 * scale]
        di.rectangle(rect, fill=(n + 1) * 20)
        db.rectangle(rect, fill=255)
    bm = np.asarray(boxes.filter(ImageFilter.GaussianBlur(1.5))).astype(np.float32) / 255.0
    depth = depth * (1 - bm) + c["box_depth"] * bm

    rgb = np.stack([np.clip(depth + 0.5, 0, 255).astype(np.uint8), np.asarray(ids),
                    np.asarray(panel)], axis=-1)
    Image.fromarray(rgb, "RGB").save(OUT_ / "depth.png", optimize=True)
    print(f"wrote page.jpg {tex.size}, depth.png {dw}x{dh}, meta.json to {OUT_}")
    if cid != "obtran003":
        return
    # the boxes' own outlines and widened card rects go into meta.json on top of the rects above
    import trace_bubbles
    trace_bubbles.main()

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
