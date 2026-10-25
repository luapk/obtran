"""Paul's hand cut lettering placed on the page, so the cards use it (Paul, 25 October: "use these ones i manually
cut out. much sharper"; images/ in the repo, screenshots from the PDF zoomed in).

Each image is matched to its box: for every box in meta.json, the image is scaled to the page's full resolution
extraction over a range of sizes and slid over the box and a margin round it (normalised cross correlation on grey,
cv2.matchTemplate); the best match names the box and gives the page rect the image covers. It is copied to
<assets>/lettering/<beat>.png and listed in lettering/index.json with that rect and "hand": true, so
tools/cut_lettering.py leaves it alone. The traced outline still masks it on the card.
Usage: python3 tools/place_lettering.py --comic <id> [images dir, default images]
Needs: numpy, opencv-python, Pillow.
"""
import hashlib
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent


def grey(im):
    return cv2.cvtColor(np.asarray(im.convert("RGB")), cv2.COLOR_RGB2GRAY).astype(np.float32)


def main():
    cid = sys.argv[sys.argv.index("--comic") + 1]
    rest = [a for a in sys.argv[1:] if a not in ("--comic", cid)]
    src_dir = ROOT / (rest[0] if rest else "images")
    assets = ROOT / "comics" / cid / "assets"
    meta = json.loads((assets / "meta.json").read_text())
    page = Image.open(ROOT / "comics" / cid / "source" / "page_rgb.png")
    W, H = page.size
    pg = grey(page)
    out = assets / "lettering"
    out.mkdir(exist_ok=True)
    index_path = out / "index.json"
    index = json.loads(index_path.read_text()) if index_path.exists() else {}
    for f in sorted(src_dir.glob("*.png")) + sorted(src_dir.glob("*.jpg")):
        im = Image.open(f)
        g = grey(im)
        best = None
        for b in meta["bubbles"]:
            u0, v0, u1, v1 = b["uv"]
            bw, bh = (u1 - u0) * W, (v1 - v0) * H
            # the image's aspect has to be near the box's to be it
            if not 0.6 < (im.width / im.height) / (bw / bh) < 1.6:
                continue
            m = 0.12
            x0, y0 = max(0, int((u0 - m * (u1 - u0)) * W)), max(0, int((v0 - m * (v1 - v0)) * H))
            x1, y1 = min(W, int((u1 + m * (u1 - u0)) * W)), min(H, int((v1 + m * (v1 - v0)) * H))
            region = pg[y0:y1, x0:x1]
            for s in np.linspace(0.78, 1.12, 24):
                tw = int(bw * s)
                th = int(tw * im.height / im.width)
                if tw < 20 or th < 10 or tw >= region.shape[1] or th >= region.shape[0]:
                    continue
                t = cv2.resize(g, (tw, th), interpolation=cv2.INTER_AREA)
                r = cv2.matchTemplate(region, t, cv2.TM_CCOEFF_NORMED)
                _, score, _, loc = cv2.minMaxLoc(r)
                if best is None or score > best[0]:
                    best = (score, b["id"], ((x0 + loc[0]) / W, (y0 + loc[1]) / H, (x0 + loc[0] + tw) / W, (y0 + loc[1] + th) / H))
        if not best or best[0] < 0.5:
            print(f"{f.name}: no box matched ({best and round(best[0], 2)})")
            continue
        score, bid, uv = best
        name = f"{bid}.png"
        im.convert("RGB").save(out / name, optimize=True)
        index[bid] = {"file": name, "uv": [round(v, 5) for v in uv], "hand": True, "from": f.name, "match": round(score, 3),
                      "v": hashlib.md5((out / name).read_bytes()).hexdigest()[:8]}
        print(f"{f.name}: {bid} (match {score:.3f}), {im.width} x {im.height}")
    index_path.write_text(json.dumps(index, indent=2) + "\n")


if __name__ == "__main__":
    main()
