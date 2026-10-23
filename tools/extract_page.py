"""Extract page 1 of the OBTRAN 003 PDF as an sRGB PNG.

The PDF holds one 3393x4588 CMYK JPEG at 300ppi (an InDesign export). The JPEG
uses Adobe's inverted CMYK, so a naive CMYK to RGB conversion gives a negative.
Libjpeg hands back the stored (already inverted) values, which means
R = C*K, G = M*K, B = Y*K on those values is the correct conversion.

Usage: python3 tools/extract_page.py [pdf] [out.png]
Needs: pypdf, Pillow, numpy.
"""
import io
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent.parent
PDF = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "source" / "OBTRAN_003_comic_AW.pdf"
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "source" / "page_rgb.png"


def largest_jpeg(page):
    best = None
    xobjects = page["/Resources"]["/XObject"]
    for name in xobjects:
        obj = xobjects[name].get_object()
        if obj.get("/Subtype") != "/Image":
            continue
        filters = obj.get("/Filter")
        filters = filters if isinstance(filters, list) else [filters]
        if "/DCTDecode" not in filters:
            continue
        size = int(obj["/Width"]) * int(obj["/Height"])
        if best is None or size > best[0]:
            best = (size, obj)
    if best is None:
        raise SystemExit("no JPEG image found on page 1")
    return best[1]


def main():
    reader = PdfReader(str(PDF))
    obj = largest_jpeg(reader.pages[0])
    im = Image.open(io.BytesIO(obj._data))
    print(f"image {im.size[0]}x{im.size[1]} mode {im.mode}")
    if im.mode == "CMYK":
        a = np.asarray(im).astype(np.float32) / 255.0
        c, m, y, k = a[..., 0], a[..., 1], a[..., 2], a[..., 3]
        rgb = np.stack([c * k, m * k, y * k], axis=-1)
        im = Image.fromarray(np.clip(rgb * 255.0 + 0.5, 0, 255).astype(np.uint8), "RGB")
    else:
        im = im.convert("RGB")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    im.save(OUT)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
