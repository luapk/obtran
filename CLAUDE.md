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
- **GitHub workflows:** `.github/workflows/generate-worlds.yml` runs the Marble pipeline on GitHub and commits the results; `render-voices.yml` renders the voice lines the same way. Both have run. The secrets `WORLDLABS_API_KEY` and `ELEVENLABS_API_KEY` are set as Actions secrets. GitHub only offers "Run workflow" once a file is on the default branch (`main`), and Claude cannot dispatch runs (403), so runs start from a push that changes `worlds/run.json` or `voices/script.json`.
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
  assets/voice/               <beat>.mp3 and index.json, rendered by tools/render-voices.mjs
  assets/films/               Bob's films, start frames, contact sheets, index.json (cues), ot-logo.jpg
  assets/props/               slab.png, panel-back/figure/front.webp
  assets/music/               index.json (tracks, unlocks, loops); the audio files when Paul sends them
voices/
  script.json                 dialogue lines, voices and settings for render-voices.mjs
tools/
  extract_page.py             PDF to source/page_rgb.png (handles Adobe inverted CMYK)
  make_assets.py              page_rgb.png to the three files in prototype/assets; --crops recuts worlds/crops
  build.py / build.mjs        index.src.html to dist/ (same output; Vercel uses build.mjs)
                              default: assets and worlds as files; --inline: one file, base64 assets;
                              --local: three.js and Spark from /node_modules; --out <dir>: build elsewhere
  clean_worlds.py             prune each world's splats to <id>.clean.spz, and write views.json:
                              per-world ink grade (palette and thresholds from its crop) and look limits
  make_bob_head.py            Bob's head as a relief of splats from the scan, plus reliefs.json
  trace_bubbles.py            each lettering box's own outline from the scan, into meta.json (poly)
  cut_slab.py                 the slab cut from the singularity's panorama, and where its splats are
  make_panel_layers.py        Bob's panel cut into three layers for the opening space
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
.github/workflows/generate-worlds.yml, render-voices.yml, fetch-films.yml
films/sources.json            source URLs of Bob's short films, fetched into prototype/assets/films
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

- `gate`, then the page as drawn (`read`, no beats on it, gentle core pulse), hint "Tap to enter". A tap zooms into the narrator's caption with no cuts (`enter`, 2.6 s; Paul, 24 October): the first card starts on the page over the drawn caption box, and the camera moves until the box sits exactly where the card rests in front of it (`cardPose`), easing its lens to the spaces' field of view while the page fades to dark around it; the card then rides the camera, and the first space unwinds out of its core behind it, with no flash and no new card. The drawn Bob panel just below the caption hands over to the floating one.
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
- **What to tap glows** (Paul, 24 October): while the page waits for "Tap to enter", a faint warm halo breathes around Bob's panel (the page shader blurs the panel mask in `depth.png`'s blue channel, `uPanelGlow`). Behind a card the reader has to act on (the hold, and QNTM CTRL) a glow follows the box's own outline (`cardGlow`, a plane behind the card using the same outline as the cut).
- **The hold powers up** (Paul: "show power up more clearly, with radial grains flying out of tap position"): grains are thrown radially out of the press (a 2D canvas, `#fx`, over the 3D), slowly at first and faster and further as it charges (70 to 590 a second, 120 to 760 px a second), with a slight swirl, paper coloured with some sepia; the ring swells 45% and glows; the card's glow builds; the world's signal jitter rises; on unlock a burst of 340 grains and a flash. Keyboard holds throw from the middle of the screen. `HOLD_DUR` is 1.4 s.
- **Bob's panel floats in the opening space** (`updatePanelFloat`, Paul: the opening illustration of Bob was unclear; "cut out the black panel he sits on and have it float in the space above the gaussian background, also slice up some elements within the panel to create a parallax effect"): `tools/make_panel_layers.py` cuts three WebP layers from the scan on one canvas: the panel (`PANEL`), Bob (halo, ring, body, arms) and the controls in front (dials, cup, stick), each filled with darkened, diffused ink behind where the layer above was cut. They sit 7, 6.4 and 5.7 units ahead, scaled to line up from the resting viewpoint, 62% of the view tall in its upper part. They follow the camera's slow wander (so they float against the world) but not the pointer or tilt, which part the layers. CRSSHKKKKK! shears them. `?panel=0` turns them off.
- **Auto advances** (Paul: no tap between Smokehouse's first two lines; none after the biometric key, timed to flow at a filmic pace): beats with `auto` in `BEATS` move on by themselves once their voice line (its decoded length) and any film on it have ended, plus that many seconds: Smokehouse's first call 1.1 s, "Holy smokes! Er, ok." 1.4 s, "Initiating QNTM CTRL..." 1.8 s, which then runs the final breach. A tap still moves on early. The smoke test waits for these steps instead of pressing.
- **Hints** (Paul, 24 October): the tap instruction shows only on the first scene, with an arrow pointing up at the card ("establish this is the narrative route"); after that only "Press and hold to unlock" is named, as a gesture nobody would guess. If a card is left 10 s with no touch, click or key, it pulses once (a 14% swell and a flash of its glow). "To be continued..." comes 8 s into the ending (5 s later than before), "Read again" at 10 s.
- **Hops** (Paul, 24 October: the enter zoom "is great. Can we use in other places as transition to orientate user to position on page?"): moving to another space, the space collapses behind the card (0.9 s), then the camera is put where the card's own box sits on the page exactly as the card did, pulls back across the page to a view of both boxes (at the page's lens), and zooms into the next box like the enter zoom (`startHop`, `updateHop`, `HOP_DUR` 3.4 s); the card swaps boxes halfway, where it looks the same as the drawing, and the next space unwinds behind it. Reduced motion keeps the old collapse.
- **CRSSHKKKKK! cuts** (Paul: "should play into next scene without animation"): its beat has `cut: 0.9`: 0.9 s in, with the static still running (2.1 s), it cuts straight to Smokehouse's space: the old world shears until the next one loads, then a hard cut, the world already open and shearing, with another burst of static (`cutTo`).
- **The final breach starts on the page:** the camera pulls back from "Initiating QNTM CTRL..." to the whole page (`startPull`, 2.2 s), then the page breaks apart and the camera dives through the drawn singularity (the classic `breach()`) into its world, so the reader sees where the story has taken them.
- Cards over films and the touch pad sit exactly where the card sits in a space. The global `canvas` rule (fixed, top 0, full height, for the 3D view) had pinned them to the top of the screen at full height, stretched; `#filmCard` and `#padCard` now reset `top` and `height`. Videos take no pointer events, so a long press reaches the pad rather than Android Chrome's video menu.
- Test hook additions: `journey`, `STEPS`, `journeyNext`, `finalBreach`, `enterSpace`, `showStep` on `window.__ot`.

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
  - **Sands of time** (a second modifier, `sandModifier`, on its own layer; Paul's idea, 24 October): the world's 100k file again, shrunk to fine grains and spread between the viewer and the world (20% to 95% of each splat's distance). Grains swirl about the line of sight towards the core, faster near the axis, are flung outward (radius 55% to 165% over a cycle) and drift towards the viewer, then fade and start again; cycles last about 25 to 65 s. Coarse cells of space (about 0.45 units) are dense (up to 93% of grains shown) or sparse (3%), so they gather in drifts. Grains are paper coloured with about a quarter sepia, opacity 1.8 (Spark gives opacity above 1 a hard edge, so they read as points), stretched along the swirl, and faded out within 0.38 units of the viewpoint so none fills the screen. Updated every frame. Over a relief only 35% of the grains show (`RELIEF_SAND`), because at full density they covered Bob's face. 30% of grains are data points (Paul: "much finer, like data points"): about a quarter the size, round and pure white. `?sand=0` or the review "Sand" toggle turns it off; reduced motion turns it off.
  - **Shards** (`updateShards`, Paul's idea, 24 October: "trace some of the angular shards to the bottom left of the comic page and have a series of them rotate out with the centrifugal force of the centre, all at different sizes and shapes"): five slabs traced by eye from the bottom left of the page (`SHARD_OUTLINES`, 1000 wide grid: the wedge, a small parallelogram, the trapezoid under the lettering, the big slab, the sliver at the foot), each cut from the page texture with a thin paper rim (edges pushed out by 2.2% of the shard). 44 copies (12 with reduced motion) spiral out of the core in the singularity only: each starts small 13 units ahead near the axis, gathers speed and flies out past the viewer to 4 units behind (Paul: "black panels should fly past camera faster") while flung out to 7 units from the axis, so it passes about 5 units to the side, faster near the axis (`0.22 + 1.5 / (1 + r)` radians a second), tumbling, over 4.5 to 8.5 s, then starts again with a new size (0.35 to 3.45 units, mostly small), stretch and spin. They fade in as the world unwinds from its core. `?shards=0` or the review "Shards" toggle turns them off.
- **Shard creaks** (Paul: "the black shards make creaking metal sounds"): every 0.7 to 2.9 s the most prominent shard (nearest for its size) groans from where it is: `sound.creak()` synthesises a train of stick-slip clicks rung through four narrow inharmonic resonances (ratios 1, 2.76, 5.4, 8.93, like a struck plate) bending down a few per cent, HRTF panned, lower and longer for bigger shards, with some reverb.
- **The nucleus** (`updateNucleus`, Paul: "can the white nucleus at the heart of the singularity be a rotating 3D object with wild flowing tendrils"; then "sit behind the other 3D shapes and track perfectly to obscure the illustrated nucleus in background", "rotate much faster than anything else, semi transparent"): a white body (an icosphere whose surface heaves with layered waves, brightest at the rim, 60% opaque) with 42 tendrils (12 with reduced motion) growing in every direction, tapered tubes 3.5 to 10 units long whose waves run from root to tip so the tips lash. It sits exactly over the drawn nucleus, measured from the world's splats: 4.2 degrees left of forward, 7.8 up, 1.38 Marble units out, brought forward 26% as the extrusion brings paper forward (`NUC_DIR`, `NUC_D`), so it moves with it as the camera drifts. The splats are drawn first (`spark.renderOrder = -10`), the nucleus over them without a depth test (order 1), then the slab (4) and shards (5). It spins at 2.6, 1.1 and 0.7 radians a second, much faster than anything else. The tendrils turn on their own group, much slower (0.45 and 0.18 radians a second), and their waves run at 0.9 (Paul: "tendrils on nucleus should move slower"). The shards now fly out of it (their group's -z points along `NUC_DIR`). `?nucleus=0` or the review toggle turns it off.
- **Ribbons** (`updateRibbons`, Paul: trace the ribbons and build them in 3D, animating in as the scene loads; then "only two 3D ribbons, one of them should come right past camera in foreground. They are cylindrical, not flat, and should sway gently in the space in accordance with camera movement"): traced from the ribbon world's own panorama (a flat view from the viewpoint, since Marble re-framed the crop and the page's positions did not line up), each point stored as yaw, pitch and the distance of the world's bright splats along that direction (`RIBBON_LINES`), so the tubes sit on the world's own ribbons. Round tubes 0.12 units thick, white with inked silhouettes. The near one (the long band from the top) dips to 16% of its distance a third of the way along, swooping about 1.8 units past the camera in the upper middle of the view; the far one is the loop on the right. A spring follows the camera's movement and turning: the tubes lag and settle, bending most at their middles, the near one twice as much. Each draws itself in from its start over 2.8 s by the clock, 0.6 s apart, with a bright tip. `?ribbons=0` or the review toggle turns them off.
- **The slab** (`updateSlab`, Paul: "cut out the big white rectangle to the left and have it float in the 3D space"): a white console-like slab Marble invented up and left of the nucleus. `tools/cut_slab.py` reprojects it from the world's panorama into a flat view, masks it to a traced outline, grades it and writes `assets/props/slab.png` and the `SLAB` constants: the card's place, and the angular box and distance range of the slab's own splats, which the ink modifier drops (`cut` uniform, on in the singularity only). The card starts exactly where the slab was and eases over 8 s into a slow drift and turn. `?slab=0` or the review toggle turns it off.
- **Ink grade:** each world's own palette and thresholds from `views.json` (`clean_worlds.py` samples ink, mid tone and paper from the world's crop and matches the crop's share of each over the front view; paper never below luminance 0.42), plus sparse warm grain in the ink and splats shrunk to 0.88 for crisper lines. Uniforms animate through `mesh.updateVersion()`.
- Look limits come from `views.json` (yaw and pitch around the forward view that holds drawn content, never under plus or minus 60 and 40 degrees) and ease back rather than stop dead.
- **Moving through a world:** the camera wanders on a slow path through the middle of the world (sideways up to 16% of its radius, 9% when extruded; up and down 4%; forward 24%, 12% when extruded), and the pointer or tilt slides it up to 2 more units. A still camera at Marble's viewpoint sees a flat panorama; moving is what shows the depth. Reliefs do not wander; they drift and take stronger pointer parallax instead.
- **Field of view in the void:** `voidFov()` widens the vertical field on portrait screens until about 70 degrees fit across (62 to 100 degrees); the breach eases into it.
- **Review mode:** `?world=<id>` skips the page and opens a world with buttons for every world and an "Ink grade" toggle, for judging worlds side by side. Ids are those in `worlds.json` plus `bob-head-relief`.
- **Reliefs:** `reliefs.json` lists worlds built from the page rather than by Marble. They are loaded the same way but not graded (they are the page's own ink), with tighter look limits and stronger viewpoint parallax, since parallax is what shows a relief's depth.

### Films of Bob (24 October, approved and live)

- **Photoreal takes (live, 24 October):** Paul asked for Bob "converted into a super high end realistic render... unmistakably Bob, but real", drinking coffee, scared at the news, dropping his coffee; then more black (black suit, dark ship panels), the OT logo on his mug (`prototype/assets/films/ot-logo.jpg`, imported as a reference) and very pale, semi-transparent skin; and black and white. Stills from Nano Banana Pro (2 credits each, with the illustration and the logo as references; candidates in `films/stills/`), animated on Seedance 2.5 from `real-wide-1` and `real-close-3`. Wide, now on "W-what the hell Smokehouse?": he sips, the transmitter erupts, the mug tips and falls, the camera pushes in on his terrified face; it plays from 1 s in so he reacts quicker (Paul), with his "W-what the hell" panel over it from the start of his line (`card: true` on the cue: the box cut from the page along its outline, drawn into a canvas where the card sits). Over every film: a super fine scan line (a dark pixel row every two) and a slow rolling band, and an alien CCTV readout drawn each frame (`drawCCTV`): corner brackets, a blinking REC, a running 3091 timestamp, rows of procedural alien glyphs (strokes, no font) that keep changing, a faint reticle, flickering signal bars and the odd glitch line. Headless screenshots here do not capture the film layer, so check films on a real browser; the overlay canvases can be exported with `toDataURL`. Close up, now on "Holy smokes! Er, ok.": fear, sweat and a tear, then he swallows. The fetch strips colour (`hue=s=0`) and the page shows films in greyscale too. The illustrated takes are kept under `previous` in `films/sources.json`. Higgsfield credits left after this: about 97.

- Paul asked for two short films of Bob from the illustration, one slightly wider and one close up, to play full screen for a moment as Bob delivers his lines, then snap back to the 3D.
- Start frames are cut from the full resolution page at 9:16 (`prototype/assets/films/bob-wide.jpg`, `bob-close.jpg`). Rendered on Higgsfield (Seedance 2.5, image to video from the start frame, 5 s, 720p, no audio, 35 credits each; Grok Imagine Lite is 5 credits if a cheaper draft is wanted). The prompts are in the Higgsfield jobs listed in `films/sources.json`. The first takes used a general prompt; Paul asked for prompts that follow the story, so the second takes (live, first takes kept in `sources.json`) act out their lines. Close up, for "W-what the hell Smokehouse?": Bob dozing on his long watch, his eyes snap open into round O shapes as the radio erupts, then a drawn mouth (not in the original art) drops open as he stammers. Wide, for "Holy smokes! Er, ok.": he flinches at the order, his hand goes to the dials, they light, and in the last second the halo becomes a swirling vortex (softer and greyer than the ink), leading into QNTM CTRL.
- This container cannot reach Higgsfield's upload host or its video CDN. Frames go up by importing them from obtran.vercel.app; clips come back through the "Fetch films" workflow, which downloads the URLs in `films/sources.json` on a push that changes it, re-encodes them (H.264, no audio, fast start) and commits `<id>.mp4` and a six-frame `<id>.sheet.jpg` to `prototype/assets/films/`.
- Playback: `prototype/assets/films/index.json` lists the clips and `cues` (beat to clip, with `at` seconds into the line, `len` to hold, `from` in the clip). The clip cuts in with a flash, holds, then snaps back with a flash and signal jitter; a tap or key cuts it short; leaving a space stops it. Portrait screens fill the frame; wide screens show the whole portrait frame with black either side. The videos live (hidden) in `#film` from the start, and the Start tap starts and stops each one inside the reader's own gesture (`primeFilms`), so phones that block a page's own playback (data saver, low power) still play them at their cue; a refused film logs `film not played` with the reason. Paul approved the second takes on 24 October ("wire in new videos"), so the cues are live: close up on "W-what the hell Smokehouse?" from the start for 3.2 s; wide on "Holy smokes! Er, ok." from 1.4 s to the end, so the press and the vortex are seen. `?films=0` turns them off.

### The biometric touch pad (24 October)

- Paul: for the press and hold, a top-down photo of an alien touch pad with glyphs and the OT logo, filmed so the screen feels alive, so the reader's own thumb completes the picture as Bob's, with a code layer that answers the touch where it lands.
- Four stills were made on Nano Banana Pro with the OT logo as reference (`films/stills/pad-*.jpg`). `pad-1` was chosen: no gloves to clash with a bare thumb, old thumbprints on the glass, the logo legible, the target at the frame's centre (0.50, 0.50). It was animated on Seedance 2.5 (5 s, 720p, 9:16, no audio, 35 credits) and fetched as film `touchpad` (clip `touchpad` in `films/index.json`, looped).
- `#pad` in `index.src.html` (`padShow`, `padHide`, `drawPad`): on the "Unlock your biometric key" beat the film fills the screen with the beat's lettering above it. Before the touch, rings breathe over the photo's target. While holding: crosshair lines to the edges with X and Y readouts, a percent figure, counter-turning segmented rings, the charge arc, a bracket that tightens as a scan line sweeps it, and streaming glyph columns, all at the touch point. On unlock the rings burst, ACCESS flashes and the pad fades after 0.9 s. Without the film the layer works over black.

### Other behaviour

- **The OT logo intro** (Paul: "a giant full screen OT logo... at the start of the experience before the comic loads"; white out of black): the label's logo redrawn as an inline SVG (four strokes measured from the image Paul sent) in the page's HTML, so it shows the moment the page opens. It flickers in (one inverted frame) under fine scan lines and a rolling band, holds until the experience has loaded and at least 1.8 s have passed, then glitches out (Paul, 24 October) over 0.75 s: sheared slices, two inverted frames, then a collapse to a bright line like a set switching off; a 10 s fallback hides it if loading fails. Behind it the gate is plain black with one sentence ("Turn your sound on and follow Bob's story through the page, exploring to unlock tracks.") and START; the comic shows only after START.
- **Music** (Paul: three tracks by QNTM CTRL from the Smokehouse Shift EP, OBTRAN003, unlocked through the story, with loops at stages; the files are to come): the tracks are Smokehouse Shift, Pulsar Forest and Preacher (Bandcamp, Juno, deejay.de). `prototype/assets/music/index.json` holds each track's file and loop names, the beat that unlocks it (Smokehouse Shift at Smokehouse's first call, Pulsar Forest when Bob unlocks his key and the Pulsar Protocol begins, Preacher at "To be continued...") and which track's loop plays in each space (`loops`, by world id, at `loopLevel`). A "QNTM CTRL 1/3" tab at the side (its panel says only "Explore to unlock tracks") (from the Start tap) flashes on each unlock with a toast; opening it lists the tracks with a play button once a track is unlocked and its file is here, and links to the EP on Bandcamp once all three are. Unlocks are kept in the browser (`ot-music`). Loops crossfade between spaces and pause while a full track plays, which goes through the master gain. The build lists the audio files present in the deployed index (`present`), so missing files are never requested; until Paul sends them the unlocks and counter work and nothing plays. Note: the tab's unlock animation class must not be `flash`, which is the white flash overlay's class (it made the tab invisible).
- **Page parallax** (Paul: "make the effect a little greater with more movement"): the camera travels 0.6 (was 0.32) with the pointer or tilt, and tilt reaches full travel at 18 degrees (was 25).

- **Audio:** a muffled cabin hum and tape hiss, a static burst on "CRSSHKKKKK!", blips on Smokehouse lines, a rising tone during the hold, then a riser, a sub-bass drop and a boom at the breach. In the void there is an HRTF-panned drone with the listener tied to the camera.
- **Reduced motion:** no parallax, and a fade to black instead of the dive.
- **Test hook:** `window.__ot = { state, breach, showBeat, BEATS, camera, worlds, look, parallax }`. Setting `state.freeze = true` stops breach time so frames can be captured at chosen points (see `tools/smoke-test.cjs`).
- **Timing:** hold, breach and ending timers use wall-clock time (capped at 0.25 s a frame), so slow devices don't stall them. Visual smoothing uses a 0.05 s cap.

### Known issues

- Fixed 24 October: lifted boxes and journey cards used to carry slivers of the art around them, because the rects are axis-aligned and the boxes slanted. `tools/trace_bubbles.py` now fits each box's own outline from the scan (rough corners by eye in `ROUGH`, refined by fitting a line to each edge: the thin white outline of a black box, the end of the white of a white box) and writes `poly` and a widened `uv` into `meta.json`; the card shader masks to the outline with a soft edge. `make_assets.py` runs it after writing `meta.json`. The page's shadow left under a lifted box (classic flow) still uses the rect. `source/bubbles_check.jpg` shows the fitted outlines.
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

**Voices (24 October):** two ElevenLabs voices play over the dialogue. `voices/script.json` holds the lines (the lettering's words; bracketed directions are `eleven_v3` audio tags), the voices and their settings. Smokehouse is `t1yzxMpe9zK42bXmI1T2` (Paul swapped it in on 24 October, replacing `SF9uvIlY93SJRMdV5jeP`), shouting, played through a walkie-talkie chain built in Web Audio at playback (band 420 to 2900 Hz with a 1.7 kHz lift, tanh overdrive, a squelch burst as the mic keys, a static bed, a click and beep as it unkeys), so it can be tuned without re-rendering. Bob is `IvUJKFyjVb5hItY9dJAT`, also over the walkie-talkie but a cleaner, wider set (300 to 3300 Hz, less lift, less drive, less static) so the two ends of the line sound different; each voice's radio settings are in the script. The narrator is `tiLGT9eftokjCKvXtgmt` (Paul's choice, 24 October, replacing `jvcMcno3QtjOzGtfpjoI`), dry with a touch of room (not on the radio), reading the caption and "To be continued...". Lines with no voice id are skipped. "3091 AD" is left as lettered; if ElevenLabs reads it as "three thousand and ninety-one", spell it out in the script. `tools/render-voices.mjs` renders only lines whose text, voice or settings changed (a hash per line in `prototype/assets/voice/index.json`); the "Render voices" workflow runs it on a push to `main` that changes `voices/script.json`, and needs the `ELEVENLABS_API_KEY` Actions secret. The key Paul uses for Hidden Camden lives in that project's Vercel environment, not on GitHub, so it has to be added to this repo separately. Lines play as each card springs up (journey) or each box lifts (classic); the next line is prefetched; leaving a space cuts the line.

All nine lines were rendered on 24 October (second run; the first failed with HTTP 401 because the key lacked the text to speech permission, and the script now stops at the first refused request rather than retrying). They run 2.2 to 12.1 s. ElevenLabs renders can end in seconds of silence (`smoke1` had 2.1 s) and vary in level (the quiet "To be continued..." sat about 7 dB under the shouted lines), so the page measures each line once when it is decoded: playback stops 0.12 s after the last sound, so the unkey beep follows the voice, and a gain before the radio chain brings each line to a similar level (clamped 0.6 to 2.2). Pronunciation (Paul, 24 October): "Spomenik Operative Bob" is the character's name and should flow as one, so the script hyphenates it ("Spomenik-Operative-Bob"); QNTM CTRL is said "quantum control"; Cryptoflage rhymes with camouflage, so the script spells it "Crypto-flahzh". "Engage Chemical Digital Cryptoflage" is a stern monotone command (Paul, 24 October): tagged `[stern, flat monotone, commanding]`, stability 0.9 and style 0 for that line, ending on a full stop. The spoken text may differ from the lettering for this; the cards always show the lettering. "3091 AD" still to check by ear. Caching: `vercel.json` lets browsers keep `/assets/` for an hour, so the page asks for each voice file with its render hash (`?v=`) and each film with its `v`, and the two index files are always rechecked; a re-render or a new take reaches people at once.

Earlier note:

Ask whether OBTRAN 003 stems can replace the synthesised sound. If so, cue the breach drop to a real track and give each region its own stem.

## Testing

- The smoke test walks the journey by default (every step, checks each step shows its world, the hold, the final breach, the ending); `CLASSIC=1` walks the old flow.
- `npm i --no-save three@0.180.0 @sparkjsdev/spark@2.4.0 puppeteer` (or `puppeteer-core` with Chrome at `CHROME_PATH`), then `node tools/build.mjs --local`, then serve the repo root on port 8765 (`python3 -m http.server 8765`) and run `node tools/smoke-test.cjs shots 1280 860 desk`, and again at 390 x 844. It walks every beat, the hold, the breach at five frozen points and the void, requires the Marble world to load after the breach (`WORLD=0` accepts the fallback), fails on any page error, and writes screenshots. To look at one world: `http://localhost:8765/dist/index.html?world=<id>`.
- Without a GPU, Chrome needs `--use-angle=swiftshader --enable-unsafe-swiftshader`. Frame rates are low, which is why timers use wall-clock time.
- To test the pipeline without spending credits, point `WORLDLABS_BASE` at a local mock that implements the four endpoints above.
- Check on a real iPhone and a mid-range Android before calling anything done. Target 60 fps on desktop and 30 or more on phones. If phones struggle, cut the 195k breach points to about 120k.
