"""Cut the world crops a comic's manifest lists from its full resolution page.

Each element's crop_px is [x, y, w, h] in page pixels; the crop is written to its crop path (relative to
the manifest) as a JPEG. Any comic: OBTRAN 003's crops come from make_assets.py --crops instead.

Usage: python3 tools/cut_crops.py comics/<id>/worlds/manifest.json source/page_rgb.png [--recut]
"""
import json
import sys
from pathlib import Path

from PIL import Image


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 2:
        sys.exit(__doc__)
    manifest_path, page_path = Path(args[0]), Path(args[1])
    manifest = json.loads(manifest_path.read_text())
    page = Image.open(page_path).convert("RGB")
    if list(page.size) != list(manifest["page_px"]):
        sys.exit(f"page is {page.size[0]}x{page.size[1]}, manifest says {manifest['page_px']}")
    for e in manifest["elements"]:
        dest = manifest_path.parent / e["crop"]
        if dest.exists() and "--recut" not in sys.argv:
            continue
        x, y, w, h = e["crop_px"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        page.crop((x, y, x + w, y + h)).save(dest, quality=92)
        print(f"{e['id']:18} {w}x{h} -> {dest}")


if __name__ == "__main__":
    main()
