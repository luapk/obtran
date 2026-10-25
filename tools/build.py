"""Build the experience into dist/: runs tools/build.mjs with the same flags (--inline, --local, --out, --comic).

  python3 tools/build.py [flags]

It used to be a line-for-line copy of build.mjs; since the comic content moved into comics/<id>/comic.json
there is one build, so the two cannot drift apart. Needs Node 18 or later.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.exit(subprocess.call(["node", str(ROOT / "tools" / "build.mjs"), *sys.argv[1:]]))
