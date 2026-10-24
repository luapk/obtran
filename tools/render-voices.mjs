#!/usr/bin/env node
// Render the dialogue's voice lines with ElevenLabs, from voices/script.json.
// Node 18 or later, no dependencies. The Render voices workflow runs this on GitHub.
//
//   ELEVENLABS_API_KEY=... node tools/render-voices.mjs        render lines that are missing or changed
//   node tools/render-voices.mjs --dry-run                     list what would render, call nothing
//   --force       render every line with a voice again
//   --only a,b    just these beats (ids from the script, e.g. smoke1,drill)
//
// Writes prototype/assets/voice/<beat>.mp3 and prototype/assets/voice/index.json, which
// records each line's speaker, whether it plays through the radio, and a hash of what was
// rendered (text, voice, model, settings), so a line only renders again when one changes.
// Env: ELEVENLABS_API_KEY (or ELEVEN_API_KEY), ELEVENLABS_BASE (default https://api.elevenlabs.io).
import { readFileSync, writeFileSync, mkdirSync, existsSync, renameSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const SCRIPT = join(ROOT, 'voices', 'script.json');
const OUT = join(ROOT, 'prototype', 'assets', 'voice');
const INDEX = join(OUT, 'index.json');

const argv = process.argv.slice(2);
const dryRun = argv.includes('--dry-run');
const force = argv.includes('--force');
const onlyAt = argv.indexOf('--only');
const only = onlyAt >= 0 ? new Set(argv[onlyAt + 1].split(',').map((s) => s.trim())) : null;
const KEY = process.env.ELEVENLABS_API_KEY || process.env.ELEVEN_API_KEY;
const BASE = (process.env.ELEVENLABS_BASE || 'https://api.elevenlabs.io').replace(/\/$/, '');

const script = JSON.parse(readFileSync(SCRIPT, 'utf8'));
mkdirSync(OUT, { recursive: true });
const index = existsSync(INDEX) ? JSON.parse(readFileSync(INDEX, 'utf8')) : { lines: {} };

const plan = [];
for (const line of script.lines) {
  if (only && !only.has(line.beat)) continue;
  const voice = script.voices[line.speaker];
  if (!voice) throw new Error(`line ${line.beat}: no voice "${line.speaker}" in the script`);
  if (!voice.id) { console.log(`  ${line.beat.padEnd(8)} skip: no voice id for ${line.speaker} yet`); continue; }
  const body = { text: line.text, model_id: line.model || script.model, voice_settings: { ...voice.settings, ...(line.settings || {}) } };
  const hash = createHash('sha256').update(JSON.stringify({ body, voice: voice.id, format: script.output_format })).digest('hex').slice(0, 16);
  const file = `${line.beat}.mp3`;
  const current = index.lines[line.beat]?.hash === hash && existsSync(join(OUT, file));
  if (current && !force) { console.log(`  ${line.beat.padEnd(8)} up to date`); continue; }
  plan.push({ line, voice, body, hash, file });
}
const chars = plan.reduce((n, p) => n + p.line.text.length, 0);
console.log(`${plan.length} line(s) to render, ${chars} characters`);
for (const p of plan) console.log(`  ${p.line.beat.padEnd(8)} ${p.line.speaker}: ${p.line.text}`);
if (dryRun || !plan.length) { writeIndex(); process.exit(0); }
if (!KEY) { console.error('error: ELEVENLABS_API_KEY is not set'); process.exit(1); }

function writeIndex() {
  // the page reads this: which lines exist, who speaks them, and which play through the radio
  for (const line of script.lines) {
    const entry = index.lines[line.beat];
    // radio is false, or the walkie-talkie settings for that voice (band, mid lift, drive, static)
    if (entry) Object.assign(entry, { speaker: line.speaker, radio: script.voices[line.speaker]?.radio || false });
  }
  const tmp = INDEX + '.tmp';
  writeFileSync(tmp, JSON.stringify(index, null, 2) + '\n');
  renameSync(tmp, INDEX);
}

let failed = 0;
for (const p of plan) {
  let done = false;
  for (let attempt = 1; attempt <= 3 && !done; attempt++) {
    try {
      const url = `${BASE}/v1/text-to-speech/${encodeURIComponent(p.voice.id)}?output_format=${encodeURIComponent(script.output_format)}`;
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'xi-api-key': KEY, 'Content-Type': 'application/json', Accept: 'audio/mpeg' },
        body: JSON.stringify(p.body),
      });
      if (!res.ok) {
        const err = (await res.text().catch(() => '')).slice(0, 300);
        if ((res.status === 429 || res.status >= 500) && attempt < 3) { console.log(`  ${p.line.beat} HTTP ${res.status}, retrying`); await new Promise((r) => setTimeout(r, 3000 * attempt)); continue; }
        throw new Error(`HTTP ${res.status} ${err}`);
      }
      const buf = Buffer.from(await res.arrayBuffer());
      writeFileSync(join(OUT, p.file) + '.part', buf);
      renameSync(join(OUT, p.file) + '.part', join(OUT, p.file));
      index.lines[p.line.beat] = { file: p.file, hash: p.hash, bytes: buf.length };
      writeIndex();
      console.log(`  ${p.line.beat.padEnd(8)} ${(buf.length / 1024).toFixed(0)} KB`);
      done = true;
    } catch (e) {
      if (attempt === 3) { console.error(`  ${p.line.beat} FAILED: ${e.message}`); failed++; }
      else await new Promise((r) => setTimeout(r, 3000 * attempt));
    }
  }
  await new Promise((r) => setTimeout(r, 600));
}
writeIndex();
if (failed) { console.error(`${failed} line(s) failed`); process.exit(1); }
