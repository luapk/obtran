# Prompt templates

Each worked for OBTRAN 003. Replace the parts in angle brackets; keep the rest.

## Marble world (per crop, `worlds/manifest.json`)

Style line, shared by every crop:

> Hand drawn comic ink: black ink and white chalk lines on deep black, with dusty sepia wash. High contrast,
> cross hatching and scratchy hatching for shading, no colours beyond black, off white and sepia. Keep the
> drawn line quality; do not make it photographic.

Per crop: what is in it, how it is framed, where the viewer stands. Example (`bob`):

> A small pilot in a round space helmet with a white halo of light behind his head, seated in a cockpit and
> holding a coffee cup, wearing a padded suit tangled with cables, with four round numbered control dials and
> a large lever in front of him. Seen from the front at close range, the walls of the cockpit wrapping around
> him.

## Still (Nano Banana Pro, 16:9 or 9:16, 2k, references: look, scene, brand)

> <Shot size>, photoreal live-action film still, <aspect>. The same <character> as in the first two
> reference images, <what we see>. <Props, with the brand mark exactly as in the third reference image,
> described stroke by stroke>. <Small motion cues: steam, light>. <Costume detail tied to the reference>.
> Background: <the set from the reference>, falling into deep soft bokeh. Sharp focus on <the subject>, very
> shallow depth of field, macro lens, f/1.8, cinematic low-key lighting, deep blacks, near monochrome
> desaturated grade, fine film grain, high detail. No text other than the logo, no on-screen graphics.

Make 2 to 4 and let Paul pick. The page draws its own CCTV readout, so never put graphics in the still.

## Film (Seedance 2.5, 5 s, 720p, from the still)

Acting a line:

> <Character> <the beat's action in story order, one clause per second>. <Camera: locked off, or a slow push
> in>. Photoreal, low-key lighting, deep blacks, near monochrome, fine film grain. No text, no graphics.

Seamless loop: the same still as `start_image` and `end_image`, and

> Seamless loop, locked-off <shot>, no cut, no camera move. <Small living movements>. <Background lights
> blinking softly>. The <subject> stays in the same place and in sharp focus throughout, and the shot ends in
> exactly the same pose as it begins.

Lipsync: `omni_reference` with the still as `start_image` and the line's cut as `audio_references`, and

> <Character>, exactly as in the start frame, looks straight into the camera and speaks the line in the
> audio reference, lips and jaw moving precisely in sync with every syllable: <the words, with their
> delivery>. <Eyes, brow, head>. Locked-off camera, no cut.

Then use the film's own audio for that part of the line (`tools/cut_bob_voice.py` shows how).

Higgsfield may offer a preset instead; decline it (`declined_preset_id`) so the frames are kept.

## Voice read (Eleven v4 audio tags, start of the line)

- `[calm, measured]` narrator; `[quietly]` an ending
- `[calm, insistent]` an order given without shouting; full stops, not exclamation marks
- `[stammering, incredulous]`, `[startled]`, `[nervous, under his breath]` for a character's reactions
- Spoken spellings fix pronunciation: `Caynis` for Canes, `Crypto-flahzh`, hyphens to run a name together
