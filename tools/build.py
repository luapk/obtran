"""Build prototype/index.src.html into dist/. Same output and flags as tools/build.mjs.

  python3 tools/build.py            served build: assets and worlds as files
  python3 tools/build.py --inline   one self contained HTML file with base64 assets
  python3 tools/build.py --local    load three.js from /node_modules instead of jsDelivr
"""
import base64
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "prototype" / "index.src.html"
ASSETS = ROOT / "prototype" / "assets"
WORLDS = ROOT / "worlds" / "worlds"
DIST = ROOT / "dist"

THREE_VERSION = "0.170.0"
THREE_CDN = f"https://cdn.jsdelivr.net/npm/three@{THREE_VERSION}/build/three.module.js"
THREE_LOCAL = "/node_modules/three/build/three.module.js"

WORLD_FILE = re.compile(r"^(worlds\.json|[a-z0-9-]+(\.100k)?\.spz|.+\.pano\.(jpg|png|webp))$")


def js_numbers(x):
    # match JSON.stringify, which writes 0.0 as 0
    if isinstance(x, float) and x.is_integer():
        return int(x)
    if isinstance(x, list):
        return [js_numbers(v) for v in x]
    if isinstance(x, dict):
        return {k: js_numbers(v) for k, v in x.items()}
    return x


def data_uri(name, mime):
    return f"data:{mime};base64," + base64.b64encode((ASSETS / name).read_bytes()).decode()


def main():
    args = set(sys.argv[1:])
    inline, local = "--inline" in args, "--local" in args
    shutil.rmtree(DIST, ignore_errors=True)
    DIST.mkdir(parents=True)

    meta = json.loads((ASSETS / "meta.json").read_text())
    meta = json.dumps(js_numbers(meta), separators=(",", ":"), ensure_ascii=False)
    fill = {
        "%%THREE_URL%%": THREE_LOCAL if local else THREE_CDN,
        "%%PAGE_SRC%%": data_uri("page.jpg", "image/jpeg") if inline else "assets/page.jpg",
        "%%DEPTH_SRC%%": data_uri("depth.png", "image/png") if inline else "assets/depth.png",
        "%%META%%": meta,
    }
    html = SRC.read_text()
    for key, value in fill.items():
        if key not in html:
            raise SystemExit(f"placeholder {key} missing from index.src.html")
        html = html.replace(key, value)
    left = re.search(r"%%[A-Z_]+%%", html)
    if left:
        raise SystemExit(f"unfilled placeholder {left.group(0)}")
    (DIST / "index.html").write_text(html)

    copied = 0
    if not inline:
        (DIST / "assets").mkdir()
        for name in ("page.jpg", "depth.png", "meta.json"):
            shutil.copyfile(ASSETS / name, DIST / "assets" / name)
        (DIST / "worlds").mkdir()
        if WORLDS.exists():
            for f in sorted(WORLDS.iterdir()):
                if WORLD_FILE.match(f.name):
                    shutil.copyfile(f, DIST / "worlds" / f.name)
                    copied += 1
        if not (DIST / "worlds" / "worlds.json").exists():
            (DIST / "worlds" / "worlds.json").write_text(json.dumps({"worlds": []}, separators=(",", ":")) + "\n")

    kb = round(len(html.encode()) / 1024)
    mode = ("inline" if inline else "files") + (", local three" if local else "")
    extra = "" if inline else f", {copied} world files"
    print(f"dist/index.html {kb} KB ({mode}){extra}")


if __name__ == "__main__":
    main()
