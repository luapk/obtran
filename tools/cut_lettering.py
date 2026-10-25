"""Each lettering box cut at full resolution, so the cards are sharp (Paul, 25 October: "all the text panels are
extremely low res").

The cards were drawn from assets/page.jpg, the page at 1800 px wide, so a caption box was a few hundred pixels across
and blurred when a card filled a screen. This cuts every box in meta.json from the full resolution extraction
(source/page_rgb.png: 4151 px wide for OBTRAN 001, 3393 for OBTRAN 003) over exactly its rect (the uv the card
already maps), lightly sharpened, and writes <assets>/lettering/<beat>.webp and lettering/index.json ({beat: {file,
uv}}). The page samples these instead of the page texture where they exist; the traced outline still masks them.
A hand cut image (Paul's) can replace any of them: give it in index.json with the uv it covers.
Usage: python3 tools/cut_lettering.py --comic <id>
Needs: Pillow.
"""
import hashlib
import json
import sys
from pathlib import Path

from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parent.parent


def main():
    cid = sys.argv[sys.argv.index("--comic") + 1] if "--comic" in sys.argv else "obtran003"
    if cid == "obtran003":
        assets, src = ROOT / "prototype" / "assets", ROOT / "source" / "page_rgb.png"
    else:
        assets, src = ROOT / "comics" / cid / "assets", ROOT / "comics" / cid / "source" / "page_rgb.png"
    meta = json.loads((assets / "meta.json").read_text())
    page = Image.open(src).convert("RGB")
    W, H = page.size
    out = assets / "lettering"
    out.mkdir(exist_ok=True)
    index_path = out / "index.json"
    index = json.loads(index_path.read_text()) if index_path.exists() else {}
    for b in meta["bubbles"]:
        if index.get(b["id"], {}).get("hand"):
            print(f"{b['id']:10} hand cut, left alone")
            continue
        u0, v0, u1, v1 = b["uv"]
        box = (round(u0 * W), round(v0 * H), round(u1 * W), round(v1 * H))
        im = page.crop(box).filter(ImageFilter.UnsharpMask(radius=1.2, percent=60, threshold=2))
        name = f"{b['id']}.webp"
        im.save(out / name, quality=92, method=6)
        index[b["id"]] = {"file": name, "uv": b["uv"], "v": hashlib.md5((out / name).read_bytes()).hexdigest()[:8]}
        print(f"{b['id']:10} {im.size[0]} x {im.size[1]}")
    index_path.write_text(json.dumps(index, indent=2) + "\n")


if __name__ == "__main__":
    main()
