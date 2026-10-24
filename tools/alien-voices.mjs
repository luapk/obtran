#!/usr/bin/env node
// Alien voice tests for Bob: voices/alien-tests.json to voices/alien-tests/*.mp3 with ElevenLabs Voice Design.
//
//   ELEVENLABS_API_KEY=... node tools/alien-voices.mjs [--force]
//
// Each test posts its description and Bob's lines to /v1/text-to-voice/design, which designs new
// voices and returns a few spoken previews (base64 MP3) with a generated_voice_id each. They are
// saved as <id>-<n>.mp3, and results.json keeps the ids, so the chosen take can be made into a voice
// (POST /v1/text-to-voice with its generated_voice_id). A test renders again only when its
// description, text or model changes. If the script's model is refused, the fallback model is tried.
// Never prints the key.
import { createHash } from 'node:crypto';
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const SCRIPT = join(ROOT, 'voices', 'alien-tests.json');
const OUT = join(ROOT, 'voices', 'alien-tests');
const RESULTS = join(OUT, 'results.json');
const force = process.argv.includes('--force');
const KEY = process.env.ELEVENLABS_API_KEY || process.env.ELEVEN_API_KEY;
const BASE = (process.env.ELEVENLABS_BASE || 'https://api.elevenlabs.io').replace(/\/$/, '');
if (!KEY) { console.error('ELEVENLABS_API_KEY is not set'); process.exit(1); }

const script = JSON.parse(readFileSync(SCRIPT, 'utf8'));
mkdirSync(OUT, { recursive: true });
const results = existsSync(RESULTS) ? JSON.parse(readFileSync(RESULTS, 'utf8')) : { tests: {} };

async function design(test, model) {
  const res = await fetch(`${BASE}/v1/text-to-voice/design`, {
    method: 'POST',
    headers: { 'xi-api-key': KEY, 'content-type': 'application/json' },
    body: JSON.stringify({ voice_description: test.description, text: test.text, model_id: model, auto_generate_text: false }),
  });
  const body = await res.text();
  if (!res.ok) return { error: `HTTP ${res.status}: ${body.slice(0, 400)}` };
  try { return { data: JSON.parse(body) }; } catch { return { error: `not JSON: ${body.slice(0, 200)}` }; }
}

let failed = false;
for (const test of script.tests) {
  const hash = createHash('sha256').update(JSON.stringify({ d: test.description, t: test.text, m: script.model })).digest('hex').slice(0, 16);
  if (!force && results.tests[test.id]?.hash === hash) { console.log(`  ${test.id.padEnd(9)} up to date`); continue; }
  let model = script.model, r = await design(test, model);
  if (r.error && script.fallback_model && /HTTP 4\d\d/.test(r.error) && !/HTTP 401/.test(r.error)) {
    console.log(`  ${test.id.padEnd(9)} ${model} refused (${r.error.slice(0, 160)}); trying ${script.fallback_model}`);
    model = script.fallback_model; r = await design(test, model);
  }
  if (r.error) {
    console.error(`  ${test.id.padEnd(9)} failed: ${r.error}`);
    failed = true;
    if (/HTTP 401/.test(r.error)) break;   // the key is refused: stop rather than repeat it
    continue;
  }
  const previews = r.data.previews || [];
  if (!previews.length) { console.error(`  ${test.id.padEnd(9)} no previews; keys: ${Object.keys(r.data).join(', ')}`); failed = true; continue; }
  const takes = previews.map((p, n) => {
    const file = `${test.id}-${n + 1}.mp3`;
    writeFileSync(join(OUT, file), Buffer.from(p.audio_base_64 || p.audio_base64 || '', 'base64'));
    return { file, generated_voice_id: p.generated_voice_id, seconds: p.duration_secs ?? null };
  });
  results.tests[test.id] = { hash, model, description: test.description, takes };
  console.log(`  ${test.id.padEnd(9)} ${takes.length} take(s) with ${model}: ${takes.map((t) => `${t.file} ${t.seconds ?? '?'}s`).join(', ')}`);
}
// save the chosen take as a voice (once), so future lines can be voiced with it
if (script.adopt && !results.adopted) {
  const [, id, n] = script.adopt.take.match(/^(.*)-(\d+)$/) || [];
  const take = results.tests[id]?.takes?.[Number(n) - 1];
  if (!take) { console.error(`adopt: no take ${script.adopt.take}`); failed = true; }
  else {
    const res = await fetch(`${BASE}/v1/text-to-voice`, {
      method: 'POST',
      headers: { 'xi-api-key': KEY, 'content-type': 'application/json' },
      body: JSON.stringify({ voice_name: script.adopt.name, voice_description: results.tests[id].description, generated_voice_id: take.generated_voice_id }),
    });
    const body = await res.text();
    if (!res.ok) { console.error(`adopt: HTTP ${res.status}: ${body.slice(0, 300)}`); failed = true; }
    else {
      const voiceId = JSON.parse(body).voice_id;
      results.adopted = { take: script.adopt.take, name: script.adopt.name, voice_id: voiceId };
      console.log(`adopted ${script.adopt.take} as "${script.adopt.name}": ${voiceId}`);
    }
  }
}
writeFileSync(RESULTS, JSON.stringify(results, null, 2) + '\n');
if (failed) process.exit(1);
