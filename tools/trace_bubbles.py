"""Fit each lettering box's own outline from the scan and add it to meta.json.

  python3 tools/trace_bubbles.py            update prototype/assets/meta.json
  python3 tools/trace_bubbles.py --sheet    also write a check sheet to source/bubbles_check.jpg

The boxes are drawn slanted, with some corners cut, so the axis-aligned rects in
make_assets.py carry slivers of the art around them and clip some box corners.
ROUGH below gives each box's corners by eye, in the 1000 wide page grid, to within
a few units. For each side, the fit scans across the edge at many points: on a
black box it finds the thin white outline, on a white box the end of the white.
A straight line is fitted through those points, dropping outliers (ribbons that
touch the box, letters near the edge), and the corners are where neighbouring
lines meet. For each bubble it writes:
  poly   the outline, in page UV (origin top left), padded to keep the outline
  uv     the rect the card cuts from the page, widened to hold the whole outline
The card shader masks each card to its poly.
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "source" / "page_rgb.png"
META = ROOT / "prototype" / "assets" / "meta.json"
PAD = 0.004          # extra page width kept around the outline when cutting the card

# Corners by eye, clockwise from the top left, in the 1000 wide grid; and the box kind.
ROUGH = {
    "caption": ("black", [(37, 16.5), (319, 16), (309.5, 109.5), (29, 108.5)]),
    "crsh": ("black", [(514, 136), (733, 135.5), (710, 176.5), (498, 177), (499, 152.5)]),
    "smoke1": ("black", [(601, 178.5), (922, 178), (910, 251.5), (584, 252)]),
    "engage": ("black", [(780, 270.5), (940, 271), (932, 316.5), (907, 330.5), (746, 330.5), (750, 294)]),
    "bob1": ("white", [(368.5, 329), (670.5, 329), (667.5, 402.5), (642, 420.5), (356.5, 420.5)]),
    "drill": ("black", [(713, 685.5), (950, 688.5), (941, 751.5), (905, 774.5), (707, 775.5)]),
    "unlock": ("black", [(590, 831), (904, 829.5), (895, 864.5), (582.5, 865)]),
    "holy": ("white", [(149.5, 900), (379.5, 900), (369, 935.5), (143.5, 935.5)]),
    "qntm": ("white", [(181.5, 951.5), (446, 952.5), (432.5, 994), (173.5, 994)]),
    "tbc": ("black", [(736, 1301), (926.5, 1300), (923, 1334), (733, 1334)]),
}
SEARCH = 6.0         # how far either side of a rough edge to look, in grid units
OUTLINE_PAD = 5      # pixels kept outside a black box's outline line (its half width and a little)
WHITE_PAD = 2        # pixels kept outside a white box's edge


def edge_points(lum, a, b, kind, s):
    """Points on the real edge near the rough edge a to b (full resolution pixels)."""
    a, b = np.array(a) * s, np.array(b) * s
    t_hat = (b - a) / np.linalg.norm(b - a)
    n = np.array([t_hat[1], -t_hat[0]])          # outward for a clockwise outline (y down)
    r = int(SEARCH * s)
    offs = np.arange(-r, r + 1)
    pts = []
    for t in np.linspace(0.08, 0.92, 60):
        c = a + (b - a) * t
        xy = c[None, :] + offs[:, None] * n[None, :]
        xi, yi = np.round(xy[:, 0]).astype(int), np.round(xy[:, 1]).astype(int)
        if xi.min() < 0 or yi.min() < 0 or xi.max() >= lum.shape[1] or yi.max() >= lum.shape[0]:
            continue
        prof = lum[yi, xi]
        prof = np.convolve(prof, np.ones(3) / 3, mode="same")
        if kind == "black":
            # the thin white outline: bright samples, the run nearest the rough edge
            bright = prof > 0.55
            if not bright.any():
                continue
            idx = np.nonzero(bright)[0]
            runs = np.split(idx, np.nonzero(np.diff(idx) > 1)[0] + 1)
            run = min(runs, key=lambda q: abs(q.mean() - r))
            if len(run) > 0.4 * s * 3:        # wider than an outline: a ribbon, not the line
                continue
            d = run.mean() - r + OUTLINE_PAD
        else:
            # a white box: walk outward from inside while it stays white
            if prof[: r // 2].mean() < 0.6:
                continue
            dark = prof < 0.45
            k = r // 2
            while k < len(prof) - 4 and not dark[k:k + 4].all():
                k += 1
            if k >= len(prof) - 4:
                continue
            d = k - r + WHITE_PAD
        pts.append(c + d * n)
    return np.array(pts)


def fit_line(pts):
    """Total least squares, dropping points more than 2.5 px off, three times."""
    keep = np.ones(len(pts), bool)
    for _ in range(3):
        p = pts[keep]
        if len(p) < 6:
            return None
        m = p.mean(0)
        u, sv, vt = np.linalg.svd(p - m)
        d = vt[0]
        nrm = np.array([-d[1], d[0]])
        res = np.abs((pts - m) @ nrm)
        keep = res < max(2.5, np.median(res[keep]) * 2)
    return m, d, keep.sum()


def intersect(l1, l2):
    (p, d), (q, e) = l1, l2
    A = np.array([d, -e]).T
    if abs(np.linalg.det(A)) < 1e-6:
        return (p + q) / 2
    t = np.linalg.solve(A, q - p)
    return p + d * t[0]


def main():
    page = Image.open(PAGE).convert("L")
    W, H = page.size
    s = W / 1000
    lum = np.asarray(page).astype(np.float32) / 255
    meta = json.loads(META.read_text())
    rgb = Image.open(PAGE).convert("RGB") if "--sheet" in sys.argv else None
    sheet = []
    for b in meta["bubbles"]:
        kind, rough = ROUGH[b["id"]]
        lines, fitted = [], 0
        for i in range(len(rough)):
            a, c = rough[i], rough[(i + 1) % len(rough)]
            pts = edge_points(lum, a, c, kind, s)
            f = fit_line(pts) if len(pts) >= 6 else None
            if f is None:
                # too few clean points on this side (a short cut corner): keep the rough edge, padded
                pa, pc = np.array(a) * s, np.array(c) * s
                t_hat = (pc - pa) / np.linalg.norm(pc - pa)
                n = np.array([t_hat[1], -t_hat[0]])
                lines.append((pa + n * (OUTLINE_PAD if kind == "black" else WHITE_PAD), t_hat))
            else:
                lines.append((f[0], f[1]))
                fitted += 1
        corners = [intersect(lines[i - 1], lines[i]) for i in range(len(lines))]
        # a corner far from its rough position means a bad fit: fall back to the rough corner
        for i, c in enumerate(corners):
            if np.linalg.norm(c - np.array(rough[i]) * s) > SEARCH * s * 1.5:
                corners[i] = np.array(rough[i]) * s
        pu = [[round(float(x) / W, 5), round(float(y) / H, 5)] for x, y in corners]
        b["poly"] = pu
        us, vs = [p[0] for p in pu], [p[1] for p in pu]
        b["uv"] = [round(max(0, min(us) - PAD), 5), round(max(0, min(vs) - PAD * W / H), 5),
                   round(min(1, max(us) + PAD), 5), round(min(1, max(vs) + PAD * W / H), 5)]
        print(f"  {b['id']:8} {kind}  {fitted} of {len(rough)} sides fitted")
        if rgb is not None:
            xs, ys = [c[0] for c in corners], [c[1] for c in corners]
            m = 20 * s
            box = (int(min(xs) - m), int(min(ys) - m), int(max(xs) + m), int(max(ys) + m))
            crop = rgb.crop(box)
            d = ImageDraw.Draw(crop)
            d.polygon([(x - box[0], y - box[1]) for x, y in corners], outline=(255, 40, 40), width=4)
            crop.thumbnail((520, 230))
            sheet.append(crop)
    META.write_text(json.dumps(meta))   # one line, as make_assets.py writes it
    if sheet:
        out = Image.new("RGB", (1060, 240 * ((len(sheet) + 1) // 2)), "grey")
        for k, t in enumerate(sheet):
            out.paste(t, ((k % 2) * 530, (k // 2) * 240))
        out.save(ROOT / "source" / "bubbles_check.jpg", quality=88)


if __name__ == "__main__":
    main()
