---
name: comic-experience
description: Turn a single page comic into an interactive browser experience like OBTRAN 003 (the page, a zoom into the caption, a walk through Gaussian splat spaces with the hand lettering as cards, character films, voices, music unlocks, a breach finale). Use when Paul brings a new comic page, asks to start a second experience, or asks how a comic is processed; also when changing comic content (beats, journey, set pieces) rather than the engine.
---

# Comic to interactive experience

This repo is an engine plus comics. The engine is `prototype/index.src.html` (and the tools); each comic is
`comics/<id>/comic.json` plus its asset folders. `tools/build.mjs --comic <id>` (or `COMIC=<id>`) embeds the
comic's content in the page. OBTRAN 003 (`comics/obtran003`) is the worked example: read `CLAUDE.md` for how
every part of it was built and why, and keep it running identically whenever the engine changes.

Working with Paul: UK English, no em dashes anywhere, plain specific words, show the work running, ask
before spending World Labs credits beyond drafts. He reviews on his phone: test at 390 x 844 first.

## The phases

Phases 1 to 3 run in order; 4 to 8 side by side once the journey is agreed; 9 to 11 close out. Stop at each
gate (G1 to G6) for Paul.

0. **Finish the split for the pipeline (first time only, before comic two).** The page engine and the
   build already take any comic. The rest still points at OBTRAN 003 and should take a comic id when the
   second comic starts (with its page in hand, since its positions have to be read anyway):
   - Workflows: `generate-worlds.yml`, `render-voices.yml` and `fetch-films.yml` read and write
     `worlds/`, `voices/script.json`, `films/sources.json` and `prototype/assets/...`. Give each a comic id
     (a file such as `comics/active`, or the path that changed) and point them at `comics/<id>/`. They run
     on pushes to `main` and spend credits: test on the branch with a dry run or the World Labs mock first.
   - Tools with OBTRAN 003 paths and content inside: `make_assets.py` (the focal point, box rects and panel
     polygon in its 1000 wide grid), `trace_bubbles.py` (`ROUGH` corners, `TRIM`), `clean_worlds.py`,
     `cut_slab.py`, `make_panel_layers.py`, `make_bob_head.py`, `cut_bob_voice.py`. Move each one's content
     into the comic folder (for example `comics/<id>/layout.json`) and give it a `--comic` argument,
     keeping OBTRAN 003's output identical. `extract_page.py` already takes input and output paths.
1. **Intake.** Ask for the files and decisions in "What to ask Paul" below. Inspect the file (pages, size,
   ppi, colour mode, layers). Extract the page at full resolution (`tools/extract_page.py`; check for
   Adobe's inverted CMYK, which comes out as a negative) and compare it with the PDF by eye. Scaffold the
   comic: `node tools/new_comic.mjs <id>`.
2. **Read the page.** Beats (one per lettering box, plus sound-only beats), reading order, panel map.
   Trace each box's outline (`tools/trace_bubbles.py`), build the depth map and masks and `meta.json`
   (`tools/make_assets.py`; positions authored in a 1000 wide grid), cut the world crops clear of
   lettering (`--crops`) into the comic's manifest. **G1: beat list agreed.**
3. **Shape the journey.** Fill `beats` and `journey` in `comic.json`: which space each beat is in, which
   cut, hop, auto advance, wait for a tap, press and hold, or trigger the finale. Plan films, backdrops,
   set pieces and the finale. Show Paul a one page storyboard. **G2: storyboard signed off. No credits
   are spent before this.**
4. **Worlds.** A Marble prompt per crop with the shared style line (`references/prompts.md`). Drafts first
   (230 credits each), previews (`tools/preview_splats.py`) beside the crops. **G3: drafts reviewed;
   Paul picks which earn full quality (1,580 each).** Clean and grade (`tools/clean_worlds.py`). Expect
   framed art to come back as a picture in an invented room, and every world to be a shell 0.8 to 1.8
   units out: depth comes from page-cut layers (`tools/make_panel_layers.py`), reliefs
   (`tools/make_bob_head.py`), the extrusion and sand, and traced set pieces, not from paying for quality.
5. **Cards and camera.** Cards come from the traced outlines; set `cardAspect` to the widest normal box.
   Tune the enter zoom and the hops on a phone first (the spaces' lens is far wider there).
6. **Films.** Stills on Nano Banana Pro (about 2 credits; 2 to 4 per shot) from the character's look
   reference, the drawing and brand references. **G4: Paul picks the stills.** Animate on Seedance 2.5
   (35 credits per 5 s, 720p): portrait first, 16:9 where it matters; the same still as start and end frame
   for a loop. Lipsync: give the line's audio as a reference (deploy the cut so Higgsfield can import it
   from a URL), then use the film's own audio for that part of the line and `sync` the cue. List films in
   `films/sources.json` (the Fetch films workflow brings them in black and white, silent, with a contact
   sheet) and cue them in `films/index.json`.
7. **Voices.** `voices/script.json`: lines, speakers, voice ids, reads as audio tags, spoken spellings
   for pronunciation (cards always show the lettering). Eleven v4 takes only stability and similarity, so
   the read comes from tags and punctuation (full stops for calm; exclamation marks push to shouting).
   **G5: first render checked by ear.**
8. **Music and sound.** Loops from Paul's excerpts (`tools/make_music.py`), effects (`tools/make_sfx.py`),
   unlocks and loop cues in `assets/music/index.json`. Measure levels by rendering through the page's own
   chain in an OfflineAudioContext over whole loops (voices about -16 dB RMS).
9. **Interactions and finale.** Special gestures and their feedback; the finale's world prepared a beat
   or two early (`prepareWorld`); anything full screen that must not freeze on a CSS layer.
10. **Deploy.** Vercel project per comic (or `COMIC` set in its environment); Actions secrets
    `WORLDLABS_API_KEY`, `ELEVENLABS_API_KEY`. Claude cannot dispatch workflows: runs start from a push that
    changes their inputs.
11. **Test.** `tools/smoke-test.cjs` at 1280 x 860 and 390 x 844 (see CLAUDE.md "Testing"); WebM copies of
    films (headless cannot play H.264); simulate the sound block (headless ignores autoplay rules); real
    iPhone and Android. Accessibility: at most 3 flashes a second, reduced motion, screen reader text.
    **G6: Paul's phone check and sign off.**

## What to ask Paul

- Artwork: layered PSD or ink scans with the lettering on its own layer (best), else the print PDF or a 300
  ppi TIFF. Layers remove the outline tracing and the estimated depth map.
- The dialogue in reading order, who says each line, any spoken changes.
- A look reference per character who appears on film.
- ElevenLabs voice ids and a read per speaker (or descriptions to design from).
- Music: 25 to 35 s excerpts per track to unlock, and the full tracks; effects; logo and release links.
- A credit cap per service (World Labs API, Higgsfield, ElevenLabs).
- Decisions: which regions become spaces and in what order; which characters get films and lipsync; which
  gestures; the finale; one repo per comic or a folder per comic.

## The comic file

`comics/<id>/comic.json` holds everything comic-specific. Field by field, with OBTRAN 003's values as
examples: `references/comic-json.md`. A starter: `templates/comic.json` (copied by `tools/new_comic.mjs`).

Assets the engine expects in the comic's `paths.assets` folder: `page.jpg`, `depth.png`, `meta.json`,
`voice/`, `films/` (with `index.json`), `music/index.json`, `sfx/`, `props/`; worlds in `paths.worlds`
(`worlds.json`, `views.json`, `reliefs.json`, the `.spz` files).

## Rules that came from mistakes

See `references/pitfalls.md`; read it before phase 4 and again before testing.

## Costs (OBTRAN 003, for scale)

10 boxes, 7 spaces, 3 characters on film: about 4 to 6 working days. World Labs about 8,000 credits (7
drafts, 4 full quality); Higgsfield about 480 (about 30 stills, 12 films); ElevenLabs about 1,000
characters per full script render. The shareable write-up with the same method:
https://claude.ai/artifact/XDLjNg5GxZfCRWAH11vZMm
