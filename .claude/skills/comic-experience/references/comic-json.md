# comic.json, field by field

The engine (`prototype/index.src.html`) reads these through `COMIC`, embedded at build time by
`tools/build.mjs`. Keys named `note` anywhere are for people and are left out of the page. Values below are
OBTRAN 003's (`comics/obtran003/comic.json`).

## Top level

| Field | What it does | OBTRAN 003 |
| --- | --- | --- |
| `id` | The folder name under `comics/`; `--comic <id>` | `obtran003` |
| `paths.assets` | Folder with `page.jpg`, `depth.png`, `meta.json`, `voice/`, `films/`, `music/`, `sfx/`, `props/`. Default `comics/<id>/assets` | `prototype/assets` |
| `paths.worlds` | Folder with `worlds.json`, `views.json`, `reliefs.json` and the splats. Default `comics/<id>/worlds` | `worlds/worlds` |
| `beats` | One entry per lettering box, in story order (below) | 9 beats |
| `journey` | Spaces in order: `{ world, beats: [indexes into beats] }` | 6 spaces |
| `finalWorld` | The world the finale breaches into; the shards, nucleus, slab, strobe and zoom out live there | `singularity-core` |
| `endBeat` | The beat id of the ending's lettering, which becomes the way back to the start | `tbc` |
| `cardAspect` | Widest box shape (width over height) a card's width is worked out for; longer boxes stand shorter | `3.9` |
| `speakerGain` | Gain per speaker id from `voices/script.json` | `{ "smokehouse": 0.75 }` |

## Beats

Each beat: `{ "b": "<id>" , ...flags }`. The id is the lettering box's id in `meta.json` and the voice
line's `beat` in `voices/script.json`.

| Flag | Meaning |
| --- | --- |
| `fx` | `static` (a static burst) or `blip` (a radio blip) as the card comes up |
| `cut` | Cut straight to the next space this many seconds in, on the static (CRSSHKKKKK!) |
| `auto` | Move on by itself this many seconds after the line and any film end |
| `hold` | A press and hold unlocks it (the biometric pad shows) |
| `trigger` | Tapping the card itself runs the finale |
| `filmOnly` | Its card shows only over its film |
| `invert` | Its card flashes negative while its line plays |

## Text

| Field | Where it shows |
| --- | --- |
| `title`, `description` | Browser tab and page description |
| `heading` | Hidden heading for screen readers |
| `code` | The word that decrypts on the gate (`OBTRAN003`) |
| `lead` | The gate's one sentence |
| `musicTab`, `musicBuy` | The track counter's label and the buy link's words |
| `triggerHint` | Classic flow hint on the trigger beat |
| `breachPage`, `breachSpace` | Screen reader words for the finale (classic and journey) |
| `cctvDate` | The date on the films' CCTV readout |

## Set pieces (all optional: leave one out and it is not built)

| Piece | Fields | Notes |
| --- | --- | --- |
| `panel` | `world`, `on`, `uv` (the layers' canvas on the page), `layers` ([file, distance]) | Page-cut layers floating in a space (`tools/make_panel_layers.py`, `props/panel-<file>.webp`). `?panel=1` forces it on |
| `shards` | `outlines` (polygons in the 1000 wide page grid) | Slabs cut from the page, flung out of the final world's core |
| `ribbons` | `world`, `lines` ([{ path: [[yaw, pitch, dist]...], near?, sway }]), `return` (points closing the ring) | 3D tubes traced from a world's panorama |
| `nucleus` | `yaw`, `pitch` (degrees), `dist` (Marble units) | The spinning body over the drawn centre of the final world; the shards fly out of it |
| `slab` | `card`, `hide` (from `tools/cut_slab.py`) | A Marble artefact cut out of the final world; its floating card is off unless `?slab=1` |

## Elsewhere (not in comic.json yet)

Films (`films/index.json`, `films/sources.json`), music (`assets/music/index.json`), voices
(`voices/script.json`) and worlds (`worlds/manifest.json`, `run.json`) keep their own files. The OT logo
intro and the touch pad film are the label's and shared by every comic for now.
