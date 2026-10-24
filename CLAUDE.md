# OBTRAN 003: interactive comic page

Handoff from a claude.ai session on 23 October 2026, brought into this repo the same day. This file is the brief, the state of play and the task list. Read it in full before changing anything.

## What this is

Paul runs Oblivious Transfer, an electronic vinyl label. OBTRAN 003 has a one-page comic: Spomenik Operative Bob gets a transmission from Smokehouse Shift, initiates QNTM CTRL, and the page ends "To be continued...". The goal is a browser experience: the reader starts on the page as drawn, gets subtle depth and parallax, reads the dialogue as beats, then breaks through the central singularity into explorable 3D space. No app install.

The original brief (written with Gemini) belongs at `source/original-brief.md`, but it was not uploaded with the other files and is not in the repo yet; ask Paul for it if it is needed. Parts of its stack and code were wrong; the corrections are under "Verified facts" below. Where this file and the brief disagree, this file wins.

## Working with Paul

- UK English. No em dashes anywhere: copy, code, comments, docs.
- Plain, specific language. No marketing hype or prestige labels in any copy.
- He is a creative director and builds tools himself; treat him as a build partner. Show the work running rather than describing it.
- Ask before spending his World Labs credits beyond a draft run.

## Current state

- **Prototype, published as a private claude.ai artifact:** https://claude.ai/artifact/EPqcW5oA6DNdHPtyCYzFwH. It is `prototype/index.src.html` built by `tools/build.mjs --inline`.
- **Recovered into the repo (23 October):** the first upload held only the PDF, the crops and the pipeline README. The page source and its three assets were recovered from the published artifact (the script and markup are identical to it; the only change since is an inline favicon), and the tools, manifest, pipeline script, mock, workflow and Vercel config were rewritten to this brief. `make_assets.py` reproduces `meta.json` exactly and `depth.png` to within about one level on average; the committed `depth.png` is the original.
- **Marble pipeline:** `worlds/` holds crops, prompts and a script that generates splat worlds through the World Labs API. Tested against `worlds/mock-api.mjs` (happy path, failure, resume after a dropped connection, vanished operation), not yet against the real API. The request and response field names follow "Verified facts" below; the docs host could not be reached from the session that wrote the script, so the script reads responses defensively and reports the shape of anything unexpected.
- **GitHub workflow:** `voices/script.json            dialogue lines, voices and settings for render-voices.mjs
.github/workflows/generate-worlds.yml, render-voices.yml` runs the pipeline on GitHub and commits the results. Not yet run. Paul has added `WORLDLABS_API_KEY` as an Actions secret. GitHub only offers "Run workflow" once the file is on the default branch (`main`).
- **Vercel:** project `obtran` in the team "Paul's projects", already linked to `luapk/obtran`; production follows `main` (https://obtran.vercel.app). The build now serves the page texture, depth map and worlds as files. Every push builds; branch pushes get a preview URL behind Vercel login.
- **First draft run (23 October, marble-1.0-draft, all seven):** succeeded in under 3 minutes. Each world is a valid SPZ v2 file of 497,664 splats (about 5 MB) plus a 99,846 splat file (about 1 MB), positions within about plus or minus 1.2 units of the origin, OpenCV axes (x right, y down, z forward). The panorama (`assets.imagery.pano_url`, a 2304x1152 PNG of about 5 MB) was missing from the response when generation finished but present a few minutes later; a free `--refresh` run fetched all seven. Draft worlds have an empty `semantics_metadata`, so there is no `metric_scale_factor`; scale them by eye, or check whether marble-1.1 provides it. The full world response shape is recorded in `state.json` (`response_shape`); it also offers collider and HQ meshes. Marble links are in `worlds/worlds/worlds.json`.
- **What the drafts look like** (`worlds/previews/`, made by `tools/preview_splats.py`: 360 view from the origin, source crop, forward view):
  - Marble treats each crop as the forward view and builds a world around it. Where the art has a strong frame (the cockpit's hexagon, Bob's helmet ring, the tunnel mouth) it reads the frame as a window or screen, so the drawing becomes a flat picture inside an invented room.
  - `bob-cockpit` and `bob-head`: invented, symmetrical sci-fi interiors in a cleaner engraved style with a blue-grey and brown cast; Bob stays a flat image. Not his ink. The head world also invents a line of fake lettering under the porthole.
  - `bob`: Bob and his cockpit kept, re-drawn as a tidier line illustration inside a lit oval, black void around it.
  - `singularity-core`: the tunnel and starburst kept, set in a ring in a grey void.
  - `hull-machinery`, `ribbon-loops`, `monolith-slabs`: the forms come back as real 3D objects in space and the white ribbons hold up well, but black turns to sepia-brown haze and the line detail softens.
  - So: the colour grade (task 4) is needed everywhere, the three object regions are the most promising Marble worlds, and Bob is the clearest case for building from the page itself (task 6).
- **Ink pass (task 4, 23 October):** the void after the breach is now the singularity Marble world, rendered by Spark and graded to the page's tones; the procedural void is the fallback if Spark or the world fails. Paul reviewed a Gemini-written "splat stylization guide" first; its ideas were right but its code was not (no Spark CLI exists, `onBeforeCompile` does not reach Spark's shaders, OrbitControls puts the camera outside a world made to be seen from inside). What was built instead is below under "The prototype, as built".
- **Bob's head from the page (task 6, started):** Paul has no layered PSD or ink scans, so `tools/make_bob_head.py` builds a relief from the scan: face ellipse fitted to the ink outline, halo, helmet ring, surroundings fading to ink. It is `?world=bob-head-relief` for now; it gets its place in the story with the portals (task 5).
- **Paul's phone test (24 October):** the worlds looked flat, zoomed in and all alike. Three causes, all fixed: phones loaded the 100k files (too coarse to read; now 500k unless `navigator.deviceMemory` is under 4), the camera only turned at Marble's viewpoint (now it wanders slowly through the middle of the world, and pointer or tilt slides it further), and portrait used a landscape lens (now the vertical field widens until about 70 degrees fit across, capped at 100). The deeper cause is the assets: in every draft world almost all forward splats sit between 0.8 and 1.8 units from the viewpoint, nothing nearer, so a draft world is a thick shell around you, closer to a panorama with relief than a space with things in it. Paul approved one marble-1.1 test (ribbon loops, 24 October, about 1,580 credits): it is not deeper. Forward splats spread 1.39 times from nearest to furthest (p5 to p95), against 1.49 for the draft; both are the same shell. It is sharper, with a truer black ground and crisper ribbons, much closer to the crop, and it comes with `metric_scale_factor` (0.49) and a 13 MB panorama. So depth will not come from paying for quality; it has to come from structure (page-cut layers in front of a Marble backdrop, the way Bob's head is built). Paul then approved full quality for the singularity, hull machinery and monolith slabs too (24 October, about 4,740 credits), so those four are marble-1.1 (scale factors 0.55, 1.38, 0.49, 0.73) and the three Bob worlds are drafts. marble-1.1 splats are much flatter than the draft's (median longest to shortest axis 123 to 1, against 58), so they break up faster away from the viewpoint.
- **Extrusion (24 October, Paul's idea: "extrude the splatter algorithmically in space... lean into the glitches"):** see "The worlds layer". It turns the shell into layers that separate as the camera wanders. Tuned against the full-quality worlds: at first it buried the singularity in needles off-centre, so the pull, streak count and camera travel were all reduced until the dense line worlds stayed legible along the whole path.
- **The journey (24 October, Paul: "walk through each space one at a time with the dialogue and copy boxes leading you through it"):** the default flow is now a walk through the spaces, one beat at a time; the old flow (beats on the page, one breach) is `?classic=1`. See "The journey" below. This replaces the portal idea for task 5: the transitions are collapses into each world's core, not Spark portals.

### Paul's feedback on the prototype (the reason for the next phase)

1. **"Why does the Gaussian splat not match the image?"** There are no real splats in the prototype. The page relief and the breach particles are sampled from the page. Everything after the breach (slabs, rings, ribbons, starburst) is procedural geometry invented in code, so the 3D world does not look like his drawing. This is the main thing to fix.
2. **"I want the individual panel to have separate experiences each."** Confirmed by Paul on 23 October: each region of the art becomes its own world you enter (Bob's cockpit, the singularity, the hull machinery, the ribbon loops, the monolith slabs), and so does Bob himself, with his head the most important. `worlds/manifest.json` now has seven elements, including `bob` (the figure) and `bob-head` (head, halo and helmet ring).
3. **He wants the generation automated through GitHub and Vercel.** Design below.

## Repo map

```
CLAUDE.md                     this file
README.md                     short overview, build and test commands
package.json                  npm scripts only, no dependencies (Vercel installs nothing)
source/
  OBTRAN_003_comic_AW.pdf     the artwork (2 pages; page 1 is the comic, page 2 is blank)
  original-brief.md           the Gemini-era handoff (not uploaded yet)
  page_rgb.png                full resolution page from extract_page.py (gitignored)
prototype/
  index.src.html              the experience (single file, placeholders filled at build)
  assets/page.jpg             page texture, 1800x2434, sRGB
  assets/depth.png            depth map 512x692 (R = depth, G = lettering box index x 20, B = Bob's panel mask)
  assets/meta.json            page aspect, singularity centre, bubble rects, panel polygon (all in page UV, origin top left)
tools/
  extract_page.py             PDF to source/page_rgb.png (handles Adobe inverted CMYK)
  make_assets.py              page_rgb.png to the three files in prototype/assets; --crops recuts worlds/crops
  build.py / build.mjs        index.src.html to dist/ (same output; Vercel uses build.mjs)
                              default: assets and worlds as files; --inline: one file, base64 assets;
                              --local: three.js and Spark from /node_modules; --out <dir>: build elsewhere
  clean_worlds.py             prune each world's splats to <id>.clean.spz, and write views.json:
                              per-world ink grade (palette and thresholds from its crop) and look limits
  make_bob_head.py            Bob's head as a relief of splats from the scan, plus reliefs.json
  render-voices.mjs           voices/script.json to prototype/assets/voice/*.mp3 with ElevenLabs
  preview_splats.py           quick 360 and forward renders of a world beside its crop
  smoke-test.cjs              headless Chrome walkthrough with screenshots
worlds/
  manifest.json               element ids, crops and their pixel rects on the page, prompts, shared style line
  crops/*.jpg                 seven crops from the page, cut clear of lettering
  previews/*.jpg              the first draft's renders from preview_splats.py
  run.json                    settings for the next workflow run; changing it on main starts one
  generate-worlds.mjs         upload, generate, poll, download (Node 18+, no dependencies)
  mock-api.mjs                local stand in for the four World Labs endpoints
  PIPELINE.md                 how to run it locally, on GitHub, and against the mock
  worlds/                     output: <id>.spz (500k), <id>.100k.spz, <id>.pano.png, state.json, worlds.json;
                              from tools: <id>(.100k).clean.spz, views.json, bob-head-relief(.100k).spz, reliefs.json
.github/workflows/generate-worlds.yml
vercel.json                   build command and output directory
```

## Source artwork facts

- The PDF page is an InDesign export holding one 3393x4588 CMYK JPEG at 300ppi with a soft mask. No layers, no live text, no vector lettering. The black frame around the page comes from InDesign, not the image.
- The JPEG uses Adobe's inverted CMYK. Naive conversion gives a negative. `extract_page.py` does it correctly: R = C*K, G = M*K, B = Y*K on the stored values.
- Positions in `tools/make_assets.py` are authored in a 1000-wide grid over the page (1000 x 1352). Singularity centre: (455, 575). Bob's panel polygon and the ten lettering boxes are listed there.
- Lettering is hand drawn. Keep it as image cut-outs, never retype it in a font. Hidden DOM text exists for screen readers.
- Better source files would change the approach. If Paul has the layered PSD or separate ink scans, ask for them: clean cut-outs and hand-made depth replace the estimated depth map.

## The prototype, as built

Stack: three.js 0.180.0 and Spark 2.4.0 (`@sparkjsdev/spark`), both from jsDelivr, on WebGL2; custom ShaderMaterials for the page; Web Audio synthesised in code. No GSAP, no WebGPU. Spark 2.4 needs three 0.180 or later, and imports `three/addons/`, so the import map carries that entry too (without it Spark fails to load).

### The journey (the default flow)

- `gate`, then the page as drawn (`read`, no beats on it, gentle core pulse), hint "Tap to enter". A tap dives the camera into the middle of Bob's panel (`enter`, 1.8 s, page fades, flash) and the first space unwinds out of its core.
- `JOURNEY` in `index.src.html` maps spaces to beats; edit it to reorder:
  | Space | Beats |
  |---|---|
  | `bob-cockpit` | caption, "CRSSHKKKKK!" (static burst, flash, the world shears) |
  | `hull-machinery` | "Smokehouse Shift for Bob..." |
  | `ribbon-loops` | "Engage Chemical Digital Cryptoflage!" |
  | `bob-head-relief` | "W-what the hell Smokehouse?..." |
  | `monolith-slabs` | "This is not a drill, Bob... Spomenik Transfer Protocol" (spomenik: monument) |
  | `bob` | "Unlock your biometric key" (press and hold), "Holy smokes! Er, ok.", "Initiating QNTM CTRL..." (tap the card itself) |
  | `singularity-core` | the final breach (the full breach sound), then "To be continued..." and "Read again" |
- In a space (`state.stage === 'void'`, `journey.phase === 'space'`): the beat's lettering is one card cut from the page (the same shader as the lifted boxes), carried low in front of the camera, sized to the screen, springing up with a flicker and a small tilt. Drag or tilt to look; a tap (not a drag), Space, Enter or the right arrow moves on.
- Moving to another world: the space collapses into its core (suction to 1 over 0.9 s, the camera pushes forward, jitter rises), the next world loads (its files were prefetched when the previous step began), then it unwinds out of its core (suction back to 0 at 0.55 a second) and the next card comes up. Beats in the same space just swap the card.
- The final breach collapses Bob's space over 3.5 s in time with the breach sound's drop, then the singularity unwinds slowly; the transmitter's random crackles start only then.
- Test hook additions: `journey`, `STEPS`, `journeyNext`, `finalBreach`, `enterSpace` on `window.__ot`.

### Stages (the `state.stage` values; the classic flow, `?classic=1`)

1. **`gate`:** Start button. One tap starts audio and asks for iOS motion permission.
2. **`read`:** the page is a displaced plane, 320 x 433 segments. Depth comes from `depth.png`: a radial tunnel that recedes at the singularity, with Bob's panel and the boxes raised flat. Pointer or tilt moves the camera for parallax.
   - Beats lift one box at a time, with a scanline flicker and a shadow left in the base. The box jumps on a spring (slight overshoot) 1.6 units towards the reader and grows 12% with a small random tilt, held over its place on the page so edge boxes stay on screen (Paul asked for more jump, 24 October). Reduced motion keeps the old small lift.
   - "Unlock your biometric key" needs a 1.4 s press and hold (or holding Space).
   - The breach starts only when the reader taps the "INITIATING QNTM CTRL..." box itself.
   - The core pulses and inflow particles spiral in harder with each beat (`uAgit`).
3. **`breach`:** 4.8 s. The page swaps to 195k points sampled from the same texture and depth. They release from the centre outward, swirl, and fade dark points first.
   - The camera reaches the page plane at u = 0.42, then flies to `VOID_Z = -26`.
   - The FOV widens mid-flight and there is a small roll.
   - Fog density falls from 0.6 to 0.034.
4. **`void`:** you are inside the singularity Marble world (see "The worlds layer"). Drag to look, the pointer or tilt slides the viewpoint slightly, an idle sweep after 4 s stays within the world's look limits. "To be continued..." arrives as the original lettering on a card attached to the camera, then a "Read again" button. If the world cannot load, the procedural void (ink slabs, rings, ribbons, starburst) is used.

### The worlds layer (Spark)

- The story world (`singularity-core`) starts loading on the Start tap. During the breach the drawn rings carry the dive; at the flash (u = 0.72) the world replaces them.
- Worlds are `SplatMesh` objects from `views.json` file paths (the cleaned splats; 500k everywhere, 100k only when `navigator.deviceMemory` is under 4), turned from Marble's OpenCV axes with `quaternion.set(1, 0, 0, 0)`, scaled by `WORLD_SCALE = 12` and centred on `P0`, so the camera sits at Marble's viewpoint. Draft worlds have no `metric_scale_factor`.
- One Spark `objectModifier` (a raw GLSL dyno node, `inkModifier`) does four things per splat, and a sand layer adds a fifth:
  - **Suction:** swirl and pull towards the core straight ahead. It runs from 1 during the breach and unwinds after arrival, so the world opens out of the singularity.
  - **Jitter:** banded horizontal shear like a bad transmission. The transmitter "crackles" every 9 to 17 s in the void, with a static burst, echoing "CRSSHKKKKK!".
  - **Extrusion** (`extrude` uniform, on by default, `?extrude=0` or the review toggle turns it off; reliefs never): each splat moves along its line of sight from the viewpoint. Paper lines come forward (26%), mid tones a little (10%); the shell is cut into angular blocks (about 6 by 8 degrees) and half of them slip back towards the viewer (up to 16%); a few blocks jump to a new depth on a slow clock (up to 24% either way). Each splat shrinks by the factor it moves, so from the viewpoint the drawing looks exactly as before and the layers only open up as the camera moves. 2.2% of splats become streaks along the line of sight, half of them ink smears, at 70% opacity. Two echo layers (the 100k file again at 80% and 64% depth, 14% and 7% opacity, paper only) add ghost depth. The modifier refreshes about ten times a second while extruding.
  - **Sands of time** (a second modifier, `sandModifier`, on its own layer; Paul's idea, 24 October): the world's 100k file again, shrunk to fine grains and spread between the viewer and the world (20% to 95% of each splat's distance). Grains swirl about the line of sight towards the core, faster near the axis, are flung outward (radius 55% to 165% over a cycle) and drift towards the viewer, then fade and start again; cycles last about 25 to 65 s. Coarse cells of space (about 0.45 units) are dense (up to 93% of grains shown) or sparse (3%), so they gather in drifts. Grains are paper coloured with about a quarter sepia, opacity 1.8 (Spark gives opacity above 1 a hard edge, so they read as points), stretched along the swirl, and faded out within 0.38 units of the viewpoint so none fills the screen. Updated every frame. `?sand=0` or the review "Sand" toggle turns it off; reduced motion turns it off.
  - **Ink grade:** each world's own palette and thresholds from `views.json` (`clean_worlds.py` samples ink, mid tone and paper from the world's crop and matches the crop's share of each over the front view; paper never below luminance 0.42), plus sparse warm grain in the ink and splats shrunk to 0.88 for crisper lines. Uniforms animate through `mesh.updateVersion()`.
- Look limits come from `views.json` (yaw and pitch around the forward view that holds drawn content, never under plus or minus 60 and 40 degrees) and ease back rather than stop dead.
- **Moving through a world:** the camera wanders on a slow path through the middle of the world (sideways up to 16% of its radius, 9% when extruded; up and down 4%; forward 24%, 12% when extruded), and the pointer or tilt slides it up to 2 more units. A still camera at Marble's viewpoint sees a flat panorama; moving is what shows the depth. Reliefs do not wander; they drift and take stronger pointer parallax instead.
- **Field of view in the void:** `voidFov()` widens the vertical field on portrait screens until about 70 degrees fit across (62 to 100 degrees); the breach eases into it.
- **Review mode:** `?world=<id>` skips the page and opens a world with buttons for every world and an "Ink grade" toggle, for judging worlds side by side. Ids are those in `worlds.json` plus `bob-head-relief`.
- **Reliefs:** `reliefs.json` lists worlds built from the page rather than by Marble. They are loaded the same way but not graded (they are the page's own ink), with tighter look limits and stronger viewpoint parallax, since parallax is what shows a relief's depth.

### Other behaviour

- **Audio:** a muffled cabin hum and tape hiss, a static burst on "CRSSHKKKKK!", blips on Smokehouse lines, a rising tone during the hold, then a riser, a sub-bass drop and a boom at the breach. In the void there is an HRTF-panned drone with the listener tied to the camera.
- **Reduced motion:** no parallax, and a fade to black instead of the dive.
- **Test hook:** `window.__ot = { state, breach, showBeat, BEATS, camera, worlds, look, parallax }`. Setting `state.freeze = true` stops breach time so frames can be captured at chosen points (see `tools/smoke-test.cjs`).
- **Timing:** hold, breach and ending timers use wall-clock time (capped at 0.25 s a frame), so slow devices don't stall them. Visual smoothing uses a 0.05 s cap.

### Known issues

- Lifted boxes carry a sliver of the surrounding art, because rects are axis-aligned and the boxes are slanted. Clean cut-outs fix this.
- The depth map is a heuristic. It reads well head-on and stretches at hard edges at large parallax.
- The procedural void is generic. It is now only the fallback, and the breach's first 70%.
- Marble worlds of framed art (cockpit, Bob's head) are a picture in an invented room; the grade cannot fix that. `monolith-slabs` is the weakest of the object worlds: Marble's bright brown haze between the slabs still grades pale where the crop has dark ground.
- Draft worlds are shallow shells (see "Paul's phone test" above); moving the camera shows what depth there is, but it is modest.
- Under SwiftShader (no GPU) 500k splats render at a frame every few seconds, so a full desktop walkthrough takes 15 to 30 minutes. Not representative of real devices, but not yet measured on one either.
- Inside a claude.ai artifact, device motion is blocked, so tilt only works when self-hosted.
- The whole page is one 2 MB HTML file with base64 assets. That is fine for an artifact, but on Vercel the assets should be served as files.

## Verified facts (checked 23 October 2026; re-check anything version-sensitive)

- **Spark** (sparkjs.dev, by World Labs) is a 3D Gaussian splat renderer for THREE.js.
  - It runs on WebGL2, not WebGPU, and targets over 98% of devices.
  - The package is `@sparkjsdev/spark`, not `@worldlabs/spark` as the brief says.
  - Usage: create `THREE.WebGLRenderer`, then `new SparkRenderer({ renderer })` added to the scene, and `SplatMesh` objects for the splats.
  - It sorts splats in a worker. It supports per-splat colour editing and displacement through its dyno shader graph, and procedural splats through `SplatGenerator`.
  - Spark 2.0 adds level-of-detail trees, virtual paging and the .RAD format.
  - Read the current docs before coding against its API; the brief's `SplatMesh.load()` call is wrong.
- **three.js native splats:** three.js merged a native WebGPU and TSL splat renderer (`GaussianSplatMesh`, `SPZLoader`) for r186. At the time it was on the dev branch and young. Spark is the safer choice.
- **WebGPU support:**
  - Chrome and Edge from 113; Android Chrome from 121 on Android 12+ with Qualcomm or ARM GPUs.
  - Firefox 141 on Windows and 145 on Apple Silicon Macs.
  - Safari 26 on macOS, iOS and iPadOS.
  - Not a reason to switch. WebGL2 reaches more people.
- **World Labs API:**
  - Base `https://api.worldlabs.ai`, auth header `WLT-Api-Key`.
  - Upload: `POST /marble/v1/media-assets:prepare_upload`, then PUT the file to `upload_info.upload_url` with `required_headers`.
  - Generate: `POST /marble/v1/worlds:generate` with `world_prompt: { type: "image", image_prompt: { source: "media_asset", media_asset_id }, text_prompt, is_pano: "auto" }`.
  - Poll `GET /marble/v1/operations/{operation_id}` until `done`. The result is in `response`, or `GET /marble/v1/worlds/{world_id}`.
  - Splats are at `assets.splats.spz_urls` with keys `100k`, `500k` and `full_res`; also `assets.imagery.pano_url` and `assets.splats.semantics_metadata.metric_scale_factor`.
  - Generation takes about 5 minutes.
  - Costs: `marble-1.0-draft` image input is 230 credits (about $0.18); `marble-1.1` is 1,580 (about $1.26). 1,250 credits = $1. PLY export is free; HQ mesh export is 3,500 credits.
  - API credits are bought at platform.worldlabs.ai and are separate from Marble app credits.
  - Commercial terms need checking before release.
- **This session's limits:** the claude.ai workspace could not reach api.worldlabs.ai, and a claude.ai artifact cannot call it either (CSP). The pipeline therefore runs on Paul's machine or in GitHub Actions.

## Tasks, in order

### 1. Confirm the panel structure with Paul

Done: one world per region of the art, plus Bob and Bob's head (see feedback point 2). Full-quality worlds still wait until Paul has seen a draft run.

Marble makes explorable scenes from an image, so a close crop of a character may come back as a room with Bob flattened into it rather than a figure you can look at from around him. Judge `bob` and `bob-head` from the draft panoramas. If Marble loses him, build Bob's head from the page itself (task 6): a relief splat or layered cut-out from the scan, with hand-made depth for the face, halo and helmet ring.

### 2. Set up GitHub and run a draft generation

- Done: the repo exists and Paul has added `WORLDLABS_API_KEY` as an Actions secret. Never put the key in code, logs or commits.
- The workflow has to be on `main` before it can be run. It starts from "Run workflow" or from a push to `main` that changes `worlds/run.json` (quality, only, force). Claude's GitHub access cannot dispatch workflows (403), so Claude starts runs by editing `run.json`.
- Run "Generate worlds" with quality = draft: seven worlds, about 1,610 credits (about $1.29).
- The workflow commits `worlds/worlds/` back, including on failure, so `state.json` lets a rerun resume in-progress operations.
- Check the 500k `.spz` sizes. GitHub rejects files over 100 MB, and full-res files are gitignored.
- Look at the panoramas with Paul. The question is how much of his ink Marble keeps.

### 3. Deploy on Vercel

- Done: the Vercel project is connected, and `dist/` gets the splats (only the cleaned ones when they exist), `worlds.json`, `views.json` and `reliefs.json`, with the page loading its texture and depth as files. Panoramas stay in the repo only.
- Every push, including the workflow's commits, then redeploys.
- Device tilt works here, because the self-hosted page isn't sandboxed. Test on an iPhone: `DeviceOrientationEvent.requestPermission` has to be called from the Start tap, which it already is.

### 4. Load Marble worlds with Spark

Done for the story world and review mode (see "The worlds layer"). Remaining: measure frame rates on a real iPhone and mid-range Android; if phones struggle with 100k splats plus the page, try Spark's LoD (`lod` / `enableLod` options) before cutting splats. The original notes follow.

- Keep the page stage as it is, since it already matches the art.
- Add `SparkRenderer` and load each world listed in `worlds.json`: the 100k file on phones (`pointer: coarse` or a GPU check), 500k on desktop.
- Grade every splat to the page's three tones with a dyno colour edit: threshold luminance to ink black (#050403), paper (#efe9df) and sepia (#8a6a4a), with a little noise for grit. Compare against the panorama and the crop side by side, and tune until the ink reads.
- Scale with `metric_scale_factor`, then position each world beyond the singularity.
- Spark and the existing custom ShaderMaterials share one WebGLRenderer. Check that depth sorting with the page points and the void geometry is correct.

### 5. Build the per-region experiences (next)

Spark 2.4 has `SparkPortals`: paired disks that render one splat world through another and move the camera across when it passes through. That is close to "tap a region and dive into its world" out of the box; check its options in `dist/types/SparkPortals.d.ts` before building.

Working design, for each region:

- On the page, the region is a tap target. The camera dives into it, the way the breach dives into the core.
- It opens its own world, interaction and sound, with a way back to the page.
- Suggested starting points, to agree with Paul:
  - **Bob's cockpit:** sit in his seat and look around his instruments.
  - **Bob, and his head:** the one Paul cares about most. Come face to face with him inside the helmet, the halo behind his head; the figure world shows him in the seat with the coffee cup and the four numbered dials.
  - **The singularity:** the existing breach.
  - **Hull machinery:** drift between fragments.
  - **Ribbon loops:** follow a ribbon.
  - **Monolith slabs:** slow orbit.
- The dialogue beats still run on the page first. Decide with Paul whether regions unlock in story order or are free to explore after QNTM CTRL.

### 6. Fidelity fallback

Started for Bob's head: `tools/make_bob_head.py` (no source layers exist; Paul confirmed). The face ellipse is fitted to the ink outline (centre 250, 330 in the crop; 152 x 81 px at minus 70 degrees), the helmet ring to its white arc. Depths are constants at the top of the script; tune them there. Same approach applies to any region Marble loses.

If Marble's worlds lose too much of the ink, build regions from the page itself:

- Cut each drawn element (hull blocks, ribbons, the panel) from the scan.
- Place them in 3D as cards or relief splats, sampled from the texture with depth, the way the breach points already are.
- Mixing per region is fine, for example a Marble cockpit with cut-out hull blocks.

### 7. Audio

**Voices (24 October):** two ElevenLabs voices play over the dialogue. `voices/script.json` holds the lines (the lettering's words; bracketed directions are `eleven_v3` audio tags), the voices and their settings. Smokehouse is `SF9uvIlY93SJRMdV5jeP`, shouting, played through a walkie-talkie chain built in Web Audio at playback (band 420 to 2900 Hz with a 1.7 kHz lift, tanh overdrive, a squelch burst as the mic keys, a static bed, a click and beep as it unkeys), so it can be tuned without re-rendering. Bob is `IvUJKFyjVb5hItY9dJAT`, also over the walkie-talkie but a cleaner, wider set (300 to 3300 Hz, less lift, less drive, less static) so the two ends of the line sound different; each voice's radio settings are in the script. Whether the narrator lines (caption, "To be continued...") are voiced is still open; lines with no voice id are skipped. `tools/render-voices.mjs` renders only lines whose text, voice or settings changed (a hash per line in `prototype/assets/voice/index.json`); the "Render voices" workflow runs it on a push to `main` that changes `voices/script.json`, and needs the `ELEVENLABS_API_KEY` Actions secret. The key Paul uses for Hidden Camden lives in that project's Vercel environment, not on GitHub, so it has to be added to this repo separately. Lines play as each card springs up (journey) or each box lifts (classic); the next line is prefetched; leaving a space cuts the line.

Earlier note:

Ask whether OBTRAN 003 stems can replace the synthesised sound. If so, cue the breach drop to a real track and give each region its own stem.

## Testing

- The smoke test walks the journey by default (every step, checks each step shows its world, the hold, the final breach, the ending); `CLASSIC=1` walks the old flow.
- `npm i --no-save three@0.180.0 @sparkjsdev/spark@2.4.0 puppeteer` (or `puppeteer-core` with Chrome at `CHROME_PATH`), then `node tools/build.mjs --local`, then serve the repo root on port 8765 (`python3 -m http.server 8765`) and run `node tools/smoke-test.cjs shots 1280 860 desk`, and again at 390 x 844. It walks every beat, the hold, the breach at five frozen points and the void, requires the Marble world to load after the breach (`WORLD=0` accepts the fallback), fails on any page error, and writes screenshots. To look at one world: `http://localhost:8765/dist/index.html?world=<id>`.
- Without a GPU, Chrome needs `--use-angle=swiftshader --enable-unsafe-swiftshader`. Frame rates are low, which is why timers use wall-clock time.
- To test the pipeline without spending credits, point `WORLDLABS_BASE` at a local mock that implements the four endpoints above.
- Check on a real iPhone and a mid-range Android before calling anything done. Target 60 fps on desktop and 30 or more on phones. If phones struggle, cut the 195k breach points to about 120k.
