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
- **GitHub workflow:** `.github/workflows/generate-worlds.yml` runs the pipeline on GitHub and commits the results. Not yet run. Paul has added `WORLDLABS_API_KEY` as an Actions secret. GitHub only offers "Run workflow" once the file is on the default branch (`main`).
- **Vercel:** project `obtran` in the team "Paul's projects", already linked to `luapk/obtran`; production follows `main` (https://obtran.vercel.app). The build now serves the page texture, depth map and worlds as files. Every push builds; branch pushes get a preview URL behind Vercel login.
- **Not started:** loading Marble worlds into the experience (Spark) and per-panel experiences.

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
                              default: assets and worlds as files; --inline: one file, base64 assets; --local: three.js from /node_modules
  smoke-test.cjs              headless Chrome walkthrough with screenshots
worlds/
  manifest.json               element ids, crops and their pixel rects on the page, prompts, shared style line
  crops/*.jpg                 five crops from the page, cut clear of lettering
  generate-worlds.mjs         upload, generate, poll, download (Node 18+, no dependencies)
  mock-api.mjs                local stand in for the four World Labs endpoints
  PIPELINE.md                 how to run it locally, on GitHub, and against the mock
  worlds/                     output: <id>.spz (500k), <id>.100k.spz, <id>.pano.jpg, state.json, worlds.json
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

Stack: three.js 0.170.0 from jsDelivr on WebGL2, custom ShaderMaterials, Web Audio synthesised in code. No GSAP, no Spark, no WebGPU.

### Stages (the `state.stage` values)

1. **`gate`:** Start button. One tap starts audio and asks for iOS motion permission.
2. **`read`:** the page is a displaced plane, 320 x 433 segments. Depth comes from `depth.png`: a radial tunnel that recedes at the singularity, with Bob's panel and the boxes raised flat. Pointer or tilt moves the camera for parallax.
   - Beats lift one box at a time, with a scanline flicker and a shadow left in the base.
   - "Unlock your biometric key" needs a 1.4 s press and hold (or holding Space).
   - The breach starts only when the reader taps the "INITIATING QNTM CTRL..." box itself.
   - The core pulses and inflow particles spiral in harder with each beat (`uAgit`).
3. **`breach`:** 4.8 s. The page swaps to 195k points sampled from the same texture and depth. They release from the centre outward, swirl, and fade dark points first.
   - The camera reaches the page plane at u = 0.42, then flies to `VOID_Z = -26`.
   - The FOV widens mid-flight and there is a small roll.
   - Fog density falls from 0.6 to 0.034.
4. **`void`:** drag to look, slow drift, an idle auto-rotate after 4 s. "To be continued..." arrives as the original lettering on a card attached to the camera, then a "Read again" button.

### Other behaviour

- **Audio:** a muffled cabin hum and tape hiss, a static burst on "CRSSHKKKKK!", blips on Smokehouse lines, a rising tone during the hold, then a riser, a sub-bass drop and a boom at the breach. In the void there is an HRTF-panned drone with the listener tied to the camera.
- **Reduced motion:** no parallax, and a fade to black instead of the dive.
- **Test hook:** `window.__ot = { state, breach, showBeat, BEATS, camera }`. Setting `state.freeze = true` stops breach time so frames can be captured at chosen points (see `tools/smoke-test.cjs`).
- **Timing:** hold, breach and ending timers use wall-clock time (capped at 0.25 s a frame), so slow devices don't stall them. Visual smoothing uses a 0.05 s cap.

### Known issues

- Lifted boxes carry a sliver of the surrounding art, because rects are axis-aligned and the boxes are slanted. Clean cut-outs fix this.
- The depth map is a heuristic. It reads well head-on and stretches at hard edges at large parallax.
- The procedural void is generic. It should be replaced or reduced once real worlds exist.
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
- The workflow has to be on `main` before it can be run.
- Run "Generate worlds" with quality = draft: seven worlds, about 1,610 credits (about $1.29).
- The workflow commits `worlds/worlds/` back, including on failure, so `state.json` lets a rerun resume in-progress operations.
- Check the 500k `.spz` sizes. GitHub rejects files over 100 MB, and full-res files are gitignored.
- Look at the panoramas with Paul. The question is how much of his ink Marble keeps.

### 3. Deploy on Vercel

- Done: the Vercel project is connected, and `dist/` gets `worlds/worlds/*.spz`, the panoramas and `worlds.json` (an empty list until worlds exist), with the page loading its texture and depth as files.
- Every push, including the workflow's commits, then redeploys.
- Device tilt works here, because the self-hosted page isn't sandboxed. Test on an iPhone: `DeviceOrientationEvent.requestPermission` has to be called from the Start tap, which it already is.

### 4. Load Marble worlds with Spark

- Keep the page stage as it is, since it already matches the art.
- Add `SparkRenderer` and load each world listed in `worlds.json`: the 100k file on phones (`pointer: coarse` or a GPU check), 500k on desktop.
- Grade every splat to the page's three tones with a dyno colour edit: threshold luminance to ink black (#050403), paper (#efe9df) and sepia (#8a6a4a), with a little noise for grit. Compare against the panorama and the crop side by side, and tune until the ink reads.
- Scale with `metric_scale_factor`, then position each world beyond the singularity.
- Spark and the existing custom ShaderMaterials share one WebGLRenderer. Check that depth sorting with the page points and the void geometry is correct.

### 5. Build the per-region experiences (once task 1 is confirmed)

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

If Marble's worlds lose too much of the ink, build regions from the page itself:

- Cut each drawn element (hull blocks, ribbons, the panel) from the scan.
- Place them in 3D as cards or relief splats, sampled from the texture with depth, the way the breach points already are.
- Mixing per region is fine, for example a Marble cockpit with cut-out hull blocks.

### 7. Audio

Ask whether OBTRAN 003 stems can replace the synthesised sound. If so, cue the breach drop to a real track and give each region its own stem.

## Testing

- `npm i --no-save three@0.170.0 puppeteer` (or `puppeteer-core` with Chrome at `CHROME_PATH`), then `node tools/build.mjs --local`, then serve the repo root on port 8765 (`python3 -m http.server 8765`) and run `node tools/smoke-test.cjs shots 1280 860 desk`, and again at 390 x 844. It walks every beat, the hold, the breach at five frozen points and the void, fails on any page error, and writes screenshots.
- Without a GPU, Chrome needs `--use-angle=swiftshader --enable-unsafe-swiftshader`. Frame rates are low, which is why timers use wall-clock time.
- To test the pipeline without spending credits, point `WORLDLABS_BASE` at a local mock that implements the four endpoints above.
- Check on a real iPhone and a mid-range Android before calling anything done. Target 60 fps on desktop and 30 or more on phones. If phones struggle, cut the 195k breach points to about 120k.
