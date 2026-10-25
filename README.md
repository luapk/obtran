# OBTRAN 003

The OBTRAN 003 comic page from Oblivious Transfer as a browser experience: the page as drawn, with depth and parallax, the dialogue as beats, then a dive through the singularity into 3D space. No install.

- `prototype/` the engine (`index.src.html`) and OBTRAN 003's assets
- `comics/<id>/comic.json` each comic's content (beats, journey, worlds, set pieces, words); `comics/obtran003` is the first
- `.claude/skills/comic-experience/` the playbook for turning a new comic page into an experience
- `tools/` page extraction, asset making, the build and a headless smoke test
- `worlds/` the World Labs Marble pipeline that turns crops of the page into splat worlds (see `worlds/PIPELINE.md`)
- `source/` the artwork PDF

## Build

```
node tools/build.mjs            # dist/ for hosting: page, assets and worlds as files
node tools/build.mjs --inline   # one self contained HTML file, for a claude.ai artifact
node tools/build.mjs --comic <id>   # another comic (or COMIC=<id>); obtran003 by default
node tools/new_comic.mjs <id> "Title" CODE   # scaffold a new comic folder
```

Vercel runs the first one on every push (`vercel.json`).

## Test

```
npm i --no-save three@0.180.0 @sparkjsdev/spark@2.4.0 puppeteer   # in one command: a second npm i --no-save removes the first's packages
node tools/build.mjs --local
python3 -m http.server 8765
node tools/smoke-test.cjs shots 1280 860 desk
node tools/smoke-test.cjs shots 390 844 phone
```

The page opens as drawn; a tap takes you through the spaces one beat at a time. `?classic=1` keeps the earlier flow (beats on the page, then one breach).

Open `dist/index.html?world=<id>` to look at one Marble world (or `bob-head-relief`) with the ink grade on and off.

After new worlds are generated: `python3 tools/clean_worlds.py` (the workflow runs it too), and `python3 tools/make_bob_head.py` for Bob's head from the page.

`CLAUDE.md` has the full brief, state of play and task list.
