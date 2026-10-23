# OBTRAN 003

The OBTRAN 003 comic page from Oblivious Transfer as a browser experience: the page as drawn, with depth and parallax, the dialogue as beats, then a dive through the singularity into 3D space. No install.

- `prototype/` the page (`index.src.html`) and its assets
- `tools/` page extraction, asset making, the build and a headless smoke test
- `worlds/` the World Labs Marble pipeline that turns crops of the page into splat worlds (see `worlds/PIPELINE.md`)
- `source/` the artwork PDF

## Build

```
node tools/build.mjs            # dist/ for hosting: page, assets and worlds as files
node tools/build.mjs --inline   # one self contained HTML file, for a claude.ai artifact
```

Vercel runs the first one on every push (`vercel.json`).

## Test

```
npm i --no-save three@0.170.0 puppeteer
node tools/build.mjs --local
python3 -m http.server 8765
node tools/smoke-test.cjs shots 1280 860 desk
node tools/smoke-test.cjs shots 390 844 phone
```

`CLAUDE.md` has the full brief, state of play and task list.
