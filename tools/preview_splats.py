"""Render quick previews of Marble .spz worlds, to judge how much of the ink survives.

For each world it writes a 360 degree panorama seen from the origin (where Marble
puts the input view) and a forward view, with the source crop alongside.
Splats are drawn as depth sorted discs of their base colour, so this is a rough
look, not what Spark will render.

Usage: python3 tools/preview_splats.py [out_dir] [ids...]
Needs: Pillow, numpy.
"""
import gzip
import json
import struct
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
WORLDS = ROOT / "worlds" / "worlds"
SH_C0 = 0.28209479177387814


def read_spz(path):
    raw = path.read_bytes()
    d = gzip.decompress(raw) if raw[:2] == b"\x1f\x8b" else raw
    magic, version, n, sh_degree, frac_bits, flags, _ = struct.unpack("<IIIBBBB", d[:16])
    if magic != 0x5053474E:
        raise ValueError(f"{path.name} is not an spz file")
    o = 16
    if version < 2:
        raise ValueError("spz version 1 (float16 positions) is not handled")
    p = np.frombuffer(d, np.uint8, n * 9, o).reshape(n, 3, 3).astype(np.int32)
    o += n * 9
    v = p[..., 0] | (p[..., 1] << 8) | (p[..., 2] << 16)
    v = np.where(v & 0x800000, v - 0x1000000, v)
    pos = v.astype(np.float32) / (1 << frac_bits)
    alpha = np.frombuffer(d, np.uint8, n, o).astype(np.float32) / 255.0
    o += n
    col = np.frombuffer(d, np.uint8, n * 3, o).reshape(n, 3).astype(np.float32)
    o += n * 3
    scale = np.frombuffer(d, np.uint8, n * 3, o).reshape(n, 3).astype(np.float32)
    o += n * 3
    rgb = np.clip(0.5 + SH_C0 * ((col / 255.0 - 0.5) / 0.15), 0, 1)
    radius = np.exp(scale / 16.0 - 10.0).max(axis=1)
    return pos, rgb, alpha, radius


def splat(img_w, img_h, x, y, depth, rgb, alpha, rad_px):
    """Draw opaque discs far to near, so the nearest splat wins each pixel."""
    out = np.full((img_h, img_w, 3), 0.02, np.float32)
    keep = alpha > 0.2
    x, y, depth, rgb, rad_px = x[keep], y[keep], depth[keep], rgb[keep], rad_px[keep]
    order = np.argsort(-depth)
    x, y, rgb = x[order], y[order], rgb[order]
    r = np.clip(np.round(rad_px[order]), 0, 3)
    for dy in range(-3, 4):
        for dx in range(-3, 4):
            d2 = dx * dx + dy * dy
            m = r * r >= d2
            xx = np.clip(np.round(x[m]) + dx, 0, img_w - 1).astype(int)
            yy = np.clip(np.round(y[m]) + dy, 0, img_h - 1).astype(int)
            out[yy, xx] = rgb[m]
    return Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8))


def panorama(pos, rgb, alpha, radius, w=1600, h=800):
    # OpenCV convention as Marble exports: x right, y down, z forward
    x, y, z = pos[:, 0], pos[:, 1], pos[:, 2]
    dist = np.sqrt(x * x + y * y + z * z) + 1e-6
    lon = np.arctan2(x, z)
    lat = np.arcsin(np.clip(-y / dist, -1, 1))
    px = (lon / (2 * np.pi) + 0.5) * w
    py = (0.5 - lat / np.pi) * h
    rad = radius / dist * (w / (2 * np.pi))
    return splat(w, h, px, py, dist, rgb, alpha, rad + 0.6)


def forward(pos, rgb, alpha, radius, w=900, h=900, fov=80):
    x, y, z = pos[:, 0], pos[:, 1], pos[:, 2]
    m = z > 0.05
    f = (w / 2) / np.tan(np.radians(fov / 2))
    px = x[m] / z[m] * f + w / 2
    py = y[m] / z[m] * f + h / 2
    inside = (px >= 0) & (px < w) & (py >= 0) & (py < h)
    sel = np.where(m)[0][inside]
    rad = radius[sel] / z[sel] * f
    return splat(w, h, px[inside], py[inside], z[sel], rgb[sel], alpha[sel], rad + 0.6)


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "shots" / "worlds"
    ids = sys.argv[2:]
    out.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((ROOT / "worlds" / "manifest.json").read_text())
    for el in manifest["elements"]:
        if ids and el["id"] not in ids:
            continue
        f = WORLDS / f"{el['id']}.spz"
        if not f.exists():
            continue
        pos, rgb, alpha, radius = read_spz(f)
        pano = panorama(pos, rgb, alpha, radius)
        fwd = forward(pos, rgb, alpha, radius)
        crop = Image.open(ROOT / "worlds" / el["crop"]).convert("RGB")
        crop.thumbnail((900, 900))
        sheet = Image.new("RGB", (1600, 800 + 920), (20, 18, 16))
        sheet.paste(pano, (0, 0))
        sheet.paste(crop, (0, 810))
        sheet.paste(fwd, (1600 - 900, 810))
        dr = ImageDraw.Draw(sheet)
        dr.text((8, 8), f"{el['id']}  360 from origin", fill=(255, 220, 120))
        dr.text((8, 818), "source crop", fill=(255, 220, 120))
        dr.text((708, 818), "splats, forward view", fill=(255, 220, 120))
        dest = out / f"{el['id']}.jpg"
        sheet.save(dest, quality=88)
        print(f"{dest}  {len(pos)} splats, extent {np.percentile(np.abs(pos), 95, axis=0).round(2)}")


if __name__ == "__main__":
    main()
