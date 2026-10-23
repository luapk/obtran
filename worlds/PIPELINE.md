# OBTRAN 003 worlds

Turns crops of the OBTRAN 003 page into World Labs Marble splat worlds in one command: upload, generate, wait, download.

## What's here

- `crops/` seven elements cut from the page at full resolution: Bob's cockpit, Bob, Bob's head, the singularity, hull machinery, ribbon loops, monolith slabs
- `manifest.json` one entry per element: crop, its pixel rectangle on the page (`crop_px`, x y w h), title and scene prompt, plus a shared style line that holds the black, white and sepia ink look
- `generate-worlds.mjs` the pipeline (Node 18 or later, nothing to install)
- `mock-api.mjs` a local stand in for the World Labs endpoints, for testing without credits

## Run it

1. Create an API key at platform.worldlabs.ai and buy API credits there. App credits from a Marble subscription don't work with the API.
2. In this folder:

```
export WORLDLABS_API_KEY=your-key
node generate-worlds.mjs --dry-run      # plan and estimated cost, calls nothing
node generate-worlds.mjs --draft        # test pass, about $0.18 a world
node generate-worlds.mjs                # full quality, about $1.26 a world
```

Each world takes about five minutes; two run at once. Results land in `worlds/` (this folder's `worlds/` subfolder), alongside `state.json`, which records each element's operation and status:

- `<id>.spz` 500k splats, for desktop
- `<id>.100k.spz` 100k splats, for phones
- `<id>.pano.jpg` Marble's panorama, useful for checking the look quickly
- `worlds.json` the list the experience loads, with each world's Marble link

Add `--refresh` to re-read finished worlds without generating anything (free): it records each response's shape in `state.json` and downloads anything missing, such as a panorama. `python3 tools/preview_splats.py` (from the repo root) renders a quick look at each world into `shots/worlds/`; the first draft's are in `previews/`.

Add `--full-res` to also download the full resolution splat (`<id>.full.spz`, gitignored because GitHub rejects files over 100 MB).

## Run it on GitHub

The "Generate worlds" workflow (`.github/workflows/generate-worlds.yml`) runs the same script on GitHub Actions and commits `worlds/worlds/` back to the branch it ran on, including when the run fails, so the next run can resume. Each commit redeploys the site on Vercel.

1. Add the API key as a repository secret named `WORLDLABS_API_KEY` (Settings, Secrets and variables, Actions).
2. Actions tab, "Generate worlds", "Run workflow". Pick `draft` or `full`, optionally a comma separated list of ids.

GitHub only lists a manually run workflow once the file is on the default branch.

The other way to start it is to change `run.json` (this folder) and push to `main`. Its `quality` (`draft` or `full`), `only` (a list of ids, empty for all), `force` and `refresh` fields stand in for the inputs, and the file keeps a record of what was asked for. This is how Claude starts runs, since its GitHub access can push but cannot press "Run workflow".

## Test without credits

```
node mock-api.mjs 8787 &
WORLDLABS_BASE=http://localhost:8787 WORLDLABS_API_KEY=test WORLDLABS_POLL_MS=200 node generate-worlds.mjs --draft
```

Run this in a copy of the folder, or delete `worlds/` afterwards, so the fake files don't get committed. `MOCK_FAIL=<id>` on the mock makes one generation fail; `MOCK_DIE_AFTER=<n>` stops the mock after n polls, to test resuming.

## Recutting the crops

`python3 tools/make_assets.py --crops` (from the repo root, after `tools/extract_page.py`) recuts every crop from the full resolution page using `crop_px`.

## Rerunning

- Finished worlds are skipped. Use `--force` to regenerate them.
- If a run stops (credits, network, closed laptop), run the same command again. It picks up generations already in progress instead of paying for them twice.
- `--only bob-cockpit,singularity-core` runs just those elements.

## Changing what gets generated

Edit `manifest.json`. To add an element, add an entry with a new `id` and its `crop_px` rectangle (x, y, width, height on the 3393 x 4588 page), then run `python3 tools/make_assets.py --crops` from the repo root to cut the crop, or add the crop to `crops/` yourself. Keep crops clear of lettering. Prompts describe the scene; the shared `style` line is appended to every prompt.

## Commercial use

Check World Labs' terms for API output before this ships with the release.
