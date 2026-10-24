"""Build prototype/index.src.html into dist/. Same output and flags as tools/build.mjs.

  python3 tools/build.py            served build: assets and worlds as files
  python3 tools/build.py --inline   one self contained HTML file with base64 assets
  python3 tools/build.py --local    load three.js and Spark from /node_modules instead of jsDelivr
  python3 tools/build.py --out dir  write somewhere other than dist/ (relative to the repo root)
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
DIST = ROOT / (sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else "dist")

THREE_VERSION = "0.180.0"
THREE_CDN = f"https://cdn.jsdelivr.net/npm/three@{THREE_VERSION}/build/three.module.js"
THREE_LOCAL = "/node_modules/three/build/three.module.js"
THREE_ADDONS_CDN = f"https://cdn.jsdelivr.net/npm/three@{THREE_VERSION}/examples/jsm/"
THREE_ADDONS_LOCAL = "/node_modules/three/examples/jsm/"
SPARK_VERSION = "2.4.0"
SPARK_CDN = f"https://cdn.jsdelivr.net/npm/@sparkjsdev/spark@{SPARK_VERSION}/dist/spark.module.js"
SPARK_LOCAL = "/node_modules/@sparkjsdev/spark/dist/spark.module.js"

# panoramas stay in the repo for checking; the page never loads them
WORLD_FILE = re.compile(r"^(worlds\.json|views\.json|reliefs\.json|[a-z0-9-]+(\.100k)?(\.clean)?\.spz)$")


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
        "%%THREE_ADDONS_URL%%": THREE_ADDONS_LOCAL if local else THREE_ADDONS_CDN,
        "%%SPARK_URL%%": SPARK_LOCAL if local else SPARK_CDN,
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
        # voice lines from tools/render-voices.mjs, when there are any
        voice = ASSETS / "voice"
        if voice.exists():
            (DIST / "assets" / "voice").mkdir()
            for f in sorted(voice.iterdir()):
                if f.name == "index.json" or f.suffix == ".mp3":
                    shutil.copyfile(f, DIST / "assets" / "voice" / f.name)
        # Paul's sound effects (tools/make_sfx.py)
        sfx = ASSETS / "sfx"
        if sfx.exists():
            (DIST / "assets" / "sfx").mkdir()
            for f in sorted(sfx.iterdir()):
                if f.suffix == ".mp3":
                    shutil.copyfile(f, DIST / "assets" / "sfx" / f.name)
        # music (assets/music/index.json): the audio files present are listed in the deployed index
        music = ASSETS / "music"
        if (music / "index.json").exists():
            (DIST / "assets" / "music").mkdir()
            audio = sorted(f.name for f in music.iterdir() if f.suffix in (".mp3", ".m4a", ".ogg", ".wav"))
            for name in audio:
                shutil.copyfile(music / name, DIST / "assets" / "music" / name)
            idx = json.loads((music / "index.json").read_text())
            idx["present"] = audio
            (DIST / "assets" / "music" / "index.json").write_text(json.dumps(idx, indent=2, ensure_ascii=False) + "\n")
        # props cut from the worlds (tools/cut_slab.py)
        props = ASSETS / "props"
        if props.exists():
            (DIST / "assets" / "props").mkdir()
            for f in sorted(props.iterdir()):
                if f.suffix in (".png", ".jpg", ".webp", ".json"):
                    shutil.copyfile(f, DIST / "assets" / "props" / f.name)
        # short films of Bob (films/README.md): start frames and approved clips
        films = ASSETS / "films"
        if films.exists():
            (DIST / "assets" / "films").mkdir()
            for f in sorted(films.iterdir()):
                if f.suffix in (".json", ".jpg", ".mp4", ".webm"):
                    shutil.copyfile(f, DIST / "assets" / "films" / f.name)
        (DIST / "assets" / "voice").mkdir(exist_ok=True)
        if not (DIST / "assets" / "voice" / "index.json").exists():
            (DIST / "assets" / "voice" / "index.json").write_text(json.dumps({"lines": {}}, separators=(",", ":")) + "\n")
        (DIST / "worlds").mkdir()
        if WORLDS.exists():
            names = sorted(f.name for f in WORLDS.iterdir() if WORLD_FILE.match(f.name))
            # when a cleaned splat exists the page loads that, so the raw one is not deployed
            superseded = lambda n: n.endswith(".spz") and ".clean." not in n and n[:-4] + ".clean.spz" in names
            for n in names:
                if not superseded(n):
                    shutil.copyfile(WORLDS / n, DIST / "worlds" / n)
                    copied += 1
        if not (DIST / "worlds" / "worlds.json").exists():
            (DIST / "worlds" / "worlds.json").write_text(json.dumps({"worlds": []}, separators=(",", ":")) + "\n")

    kb = round(len(html.encode()) / 1024)
    mode = ("inline" if inline else "files") + (", local three" if local else "")
    extra = "" if inline else f", {copied} world files"
    print(f"{DIST.relative_to(ROOT)}/index.html {kb} KB ({mode}){extra}")


if __name__ == "__main__":
    main()
