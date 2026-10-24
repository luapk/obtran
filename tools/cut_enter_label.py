"""Cut the start button's word and the page's enter hint out of the comic's own lettering.

  python3 tools/cut_enter_label.py

Paul, 24 October: draw the start button in the same style as the comic's black text panels, and
write "enter" in the same font as the text blocks. The lettering is hand drawn and is never retyped
in a font, so each word is assembled from letters in the black boxes: ENTER from "Engage Chemical
Digital Cryptoflage!", and TAP TO ENTER and CLICK TO ENTER from Smokehouse's first call ("TO" as it
stands in "cleared to initiate", K from "Smokehouse", C and L from "cleared", P from "pulsar").
Each letter is cut along its own ink (its connected shape, slightly grown), not as a rectangle, so
neighbours do not creep in, and the letters sit on a shared baseline. Writes white letters on a
transparent ground to prototype/assets/props/<name>.png.
"""
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as nd

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "source" / "page_rgb.png"
OUT = ROOT / "prototype" / "assets" / "props"
GAP = 0                                  # the letters' own soft edges already space them about as the boxes do
SPACE = 0.55                             # a word space, in letter heights

# each word: (box, x, y) of a point inside each letter, in pixels of that box at full resolution; None is a space
E = "engage"
S = "smoke1"
WORDS = {
    "enter": [(E, 249, 70), (E, 282, 70), (E, 294, 164), (E, 430, 70), (E, 192, 164)],
    "tap-to-enter": [(S, 770, 172), (S, 230, 172), (S, 308, 220), None, (S, 624, 172), (S, 650, 172), None,
                     (S, 300, 172), (S, 717, 172), (S, 843, 172), (S, 426, 172), (S, 266, 172)],
    "click-to-enter": [(S, 355, 172), (S, 392, 172), (S, 697, 172), (S, 718, 220), (S, 243, 78), None,
                       (S, 624, 172), (S, 650, 172), None,
                       (S, 300, 172), (S, 717, 172), (S, 843, 172), (S, 426, 172), (S, 266, 172)],
}


def main():
    page = Image.open(PAGE)
    W, H = page.size
    boxes = {b["id"]: b for b in json.load(open(ROOT / "prototype" / "assets" / "meta.json"))["bubbles"]}
    crops, labels = {}, {}
    for bid in {p[0] for w in WORDS.values() for p in w if p}:
        u0, v0, u1, v1 = boxes[bid]["uv"]
        crops[bid] = np.asarray(page.crop((int(u0 * W), int(v0 * H), int(u1 * W), int(v1 * H))).convert("L")).astype(np.float32) / 255
        labels[bid] = nd.label(crops[bid] > 0.59)[0]
    for name, spec in WORDS.items():
        cuts = []
        for p in spec:
            if p is None:
                cuts.append(None)
                continue
            bid, x, y = p
            lab, crop = labels[bid], crops[bid]
            # the letter's shape: the nearest white component to the point, grown a little for its soft edge
            ys, xs = np.nonzero(lab)
            i = np.argmin((xs - x) ** 2 + (ys - y) ** 2)
            shape = nd.binary_dilation(lab == lab[ys[i], xs[i]], iterations=2)
            sy, sx = nd.find_objects(shape.astype(int))[0]
            cuts.append(np.clip((crop[sy, sx] - 0.2) / 0.6, 0, 1) * shape[sy, sx])
        h = max(c.shape[0] for c in cuts if c is not None)
        sp = int(h * SPACE)
        w = sum(c.shape[1] if c is not None else sp for c in cuts) + GAP * (len(cuts) - 1)
        out = np.zeros((h, w), np.float32)
        x = 0
        for c in cuts:
            if c is None:
                x += sp + GAP
                continue
            out[h - c.shape[0]:, x:x + c.shape[1]] = np.maximum(out[h - c.shape[0]:, x:x + c.shape[1]], c)   # shared baseline
            x += c.shape[1] + GAP
        rgba = np.zeros((h, w, 4), np.uint8)
        rgba[..., :3] = (239, 233, 223)      # the page's paper white
        rgba[..., 3] = (out * 255).astype(np.uint8)
        OUT.mkdir(parents=True, exist_ok=True)
        Image.fromarray(rgba, "RGBA").save(OUT / f"{name}.png", optimize=True)
        print(f"{name}.png {w}x{h}")


if __name__ == "__main__":
    main()
