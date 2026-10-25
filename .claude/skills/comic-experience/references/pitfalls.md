# Pitfalls from OBTRAN 003, and the default that avoids each

| Area | What happened | Default |
| --- | --- | --- |
| Artwork | Adobe's inverted CMYK turned the page into a negative | Extract with `tools/extract_page.py`; compare with the PDF first |
| Worlds | Framed art came back as a picture in an invented room; every world was a shallow shell; full quality was sharper, not deeper | Judge drafts first; take depth from page-cut layers, reliefs and set pieces |
| Worlds | Phones loaded the 100k files, too coarse to read | 500k unless the device reports under 4 GB |
| Camera | Portrait screens had a landscape lens; hops double bounced on phones (lens and distance pulling against each other) | Widen the lens on portrait; keep a zoom moving one way at a time (`updateHop` works distance out from the view height and the lens); test at 390 x 844 first |
| Cards | Rectangles carried slivers of art; long one-line boxes ran wider than the rest | Traced outlines; `cardAspect` |
| Films | Headless Chrome cannot play H.264 or screenshot the film layer | Test on WebM copies; export overlay canvases with `toDataURL`; check on a phone |
| Lipsync | Seedance re-performed the line about 0.2 s off, so lips missed the original voice | Use the film's own audio for the spoken part; `sync` on the cue |
| Sound | No browser plays sound before the first tap (iPhones never, Chrome only on sites used before) | Anything that must be heard comes after a tap; Paul chose to leave the gate's decrypt sound as "where allowed" |
| Levels | The master compressor swallowed the music; the volume slider sat before a limiter and was linear | Music on its own limiter, then the dip, then the volume on a decibel scale; measure in an OfflineAudioContext over whole loops |
| Finale | The final world loaded at the climax and froze the glyphs on screen | `prepareWorld` a beat or two early; must-not-freeze effects on CSS layers (`#glyphVeil`) |
| Opening | Sand over the full-screen hand video made it look transparent | Thin the sand (`BACKDROP_SAND`) over any full-screen film |
| Layout | The global `canvas` rule pinned overlay canvases to the top; a tab class named `flash` hid the tab | Reset `top` on every new canvas overlay; never reuse the `flash` class |
| Phones | The controls covered the page | Slim icon row at the top right below 600 px |
| Caching | Browsers kept old voice files and films | A version in every asset address (`?v=` render hash or take id) |
| Tooling | `npm i --no-save <one package>` removed the other unsaved packages | Install three, Spark and puppeteer-core in one command |
| Build | `--out` paths are relative to the repo root | Build to `dist/` (gitignored) for local tests |
| Process | Two sessions worked on `main` at once and solved the same problem twice | One session per comic; merge `main` before every push |
| Headless | SwiftShader renders a frame every few seconds, so frame-based timers stretch | Time anything tied to sound by the clock; judge timing on a phone |
| Worlds | World Labs refused a bonfire crop twice as violence (spears, figures in the flames, a body by the fire); refusals cost nothing | Keep weapons, figures in fire and bodies out of crops; cut tighter and let a film carry the people |
| Worlds | Painted colour art came back deep (OBTRAN 001: medians up to 7) and the wander, scaled to the median, drove the camera into the scenery | `clean_worlds.py` writes `clear`; the wander stays within 1.2 times it |
| Grade | A colour comic needs its own grade; a strong palette pull posterises | `"grade": {"mode": "palette"}` in the manifest; gentle `pull`, partial `transfer` |
| Engine | The page shader assumed ten lettering boxes | `BOX_MAX`; load a new comic in review mode early to find assumptions like this |
| Assets | Paul's 3D model came as a Maya binary scene and he has no Maya | `tools/mb_to_glb.py` reads the meshes, UVs and transforms out of the .mb |
