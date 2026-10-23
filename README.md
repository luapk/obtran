# OBTRAN 003 worlds

Turns crops of the OBTRAN 003 page into World Labs Marble splat worlds in one command: upload, generate, wait, download.

## What's here

- `crops/` five elements cut from the page at full resolution: Bob's cockpit, the singularity, hull machinery, ribbon loops, monolith slabs
- `manifest.json` one entry per element: crop, title and scene prompt, plus a shared style line that holds the black, white and sepia ink look
- `generate-worlds.mjs` the pipeline (Node 18 or later, nothing to install)

## Run it

1. Create an API key at platform.worldlabs.ai and buy API credits there. App credits from a Marble subscription don't work with the API.
2. In this folder:

```
export WORLDLABS_API_KEY=your-key
node generate-worlds.mjs --dry-run      # plan and estimated cost, calls nothing
node generate-worlds.mjs --draft        # test pass, about $0.18 a world
node generate-worlds.mjs                # full quality, about $1.26 a world
```

Each world takes about five minutes; two run at once. Results land in `worlds/`:

- `<id>.spz` 500k splats, for desktop
- `<id>.100k.spz` 100k splats, for phones
- `<id>.pano.jpg` Marble's panorama, useful for checking the look quickly
- `worlds.json` the list the experience loads, with each world's Marble link

Add `--full-res` to also download the full resolution splat.

## Rerunning

- Finished worlds are skipped. Use `--force` to regenerate them.
- If a run stops (credits, network, closed laptop), run the same command again. It picks up generations already in progress instead of paying for them twice.
- `--only bob-cockpit,singularity-core` runs just those elements.

## Changing what gets generated

Edit `manifest.json`. To add an element, add a crop to `crops/` and an entry with a new `id`. Prompts describe the scene; the shared `style` line is appended to every prompt.

## Commercial use

Check World Labs' terms for API output before this ships with the release.
