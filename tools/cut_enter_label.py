"""Cut the word ENTER for the start button out of the comic's own lettering.

  python3 tools/cut_enter_label.py

Paul, 24 October: draw the start button in the same style as the comic's black text panels.
The lettering is hand drawn and is never retyped in a font, so the word is assembled from
letters in the black "Engage Chemical Digital Cryptoflage!" box: E and N from ENGAGE, T from
CRYPTOFLAGE, the second E from ENGAGE, R from CRYPTOFLAGE. Each letter is cut along its own
ink (its connected shape, slightly grown), not as a rectangle, so neighbours do not creep in,
and the letters sit on a shared baseline with the box's own spacing. Writes
prototype/assets/props/enter.png: white letters on a transparent ground.
"""
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as nd

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "source" / "page_rgb.png"
OUT = ROOT / "prototype" / "assets" / "props" / "enter.png"
# (x, y) of a point inside each letter, in pixels of the Engage box at full resolution
LETTERS = [(249, 70), (282, 70), (294, 164), (430, 70), (192, 164)]
GAP = 0                                  # the letters' own soft edges already space them about as the box does


def main():
    page = Image.open(PAGE)
    W, H = page.size
    box = {b["id"]: b for b in json.load(open(ROOT / "prototype" / "assets" / "meta.json"))["bubbles"]}["engage"]
    u0, v0, u1, v1 = box["uv"]
    crop = np.asarray(page.crop((int(u0 * W), int(v0 * H), int(u1 * W), int(v1 * H))).convert("L")).astype(np.float32) / 255
    lab, _ = nd.label(crop > 0.59)
    cuts = []
    for x, y in LETTERS:
        # the letter's shape: the nearest white component to the point, grown a little for its soft edge
        ys, xs = np.nonzero(lab)
        k = lab[ys[np.argmin((xs - x) ** 2 + (ys - y) ** 2)], xs[np.argmin((xs - x) ** 2 + (ys - y) ** 2)]]
        shape = nd.binary_dilation(lab == k, iterations=2)
        sy, sx = nd.find_objects(shape.astype(int))[0]
        alpha = np.clip((crop[sy, sx] - 0.2) / 0.6, 0, 1) * shape[sy, sx]
        cuts.append(alpha)
    h = max(c.shape[0] for c in cuts)
    w = sum(c.shape[1] for c in cuts) + GAP * (len(cuts) - 1)
    out = np.zeros((h, w), np.float32)
    x = 0
    for c in cuts:
        out[h - c.shape[0]:, x:x + c.shape[1]] = np.maximum(out[h - c.shape[0]:, x:x + c.shape[1]], c)   # shared baseline
        x += c.shape[1] + GAP
    rgba = np.zeros((h, w, 4), np.uint8)
    rgba[..., :3] = (239, 233, 223)      # the page's paper white
    rgba[..., 3] = (out * 255).astype(np.uint8)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(rgba, "RGBA").save(OUT, optimize=True)
    print(f"{OUT.relative_to(ROOT)} {w}x{h}")


if __name__ == "__main__":
    main()
