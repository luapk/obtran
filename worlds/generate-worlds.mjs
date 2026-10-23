#!/usr/bin/env node
// Generate one World Labs Marble world per element in manifest.json:
// upload the crop, start generation, poll until done, download the splats.
// Node 18 or later, no dependencies. See PIPELINE.md.
//
//   node generate-worlds.mjs --dry-run             plan and estimated cost, calls nothing
//   node generate-worlds.mjs --draft               marble-1.0-draft, about $0.18 a world
//   node generate-worlds.mjs                       marble-1.1, about $1.26 a world
//   --only a,b      just these element ids
//   --force         regenerate worlds that are already finished
//   --full-res      also download the full resolution splat (gitignored)
//   --concurrency n worlds in flight at once (default 2)
//
// Env: WORLDLABS_API_KEY (required unless --dry-run), WORLDLABS_BASE (default https://api.worldlabs.ai).
// State lives in worlds/worlds/state.json and is saved after every step, so a rerun resumes
// generations already in progress instead of paying for them twice.
import { readFileSync, writeFileSync, mkdirSync, existsSync, statSync, renameSync } from 'node:fs';
import { dirname, join, extname, basename } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const OUT = join(HERE, 'worlds');
const STATE_FILE = join(OUT, 'state.json');
const MODELS = { draft: { model: 'marble-1.0-draft', credits: 230 }, full: { model: 'marble-1.1', credits: 1580 } };
const CREDITS_PER_USD = 1250;
const POLL_MS = Number(process.env.WORLDLABS_POLL_MS || 10000);
const TIMEOUT_MS = 40 * 60 * 1000;
const GITHUB_LIMIT = 100 * 1024 * 1024;

// ---------- args ----------
const argv = process.argv.slice(2);
const flag = (name) => argv.includes(name);
const opt = (name) => { const i = argv.indexOf(name); return i >= 0 ? argv[i + 1] : undefined; };
const dryRun = flag('--dry-run');
const quality = flag('--draft') ? 'draft' : 'full';
const force = flag('--force');
const fullRes = flag('--full-res');
const only = opt('--only') ? new Set(opt('--only').split(',').map((s) => s.trim()).filter(Boolean)) : null;
const concurrency = Math.max(1, Number(opt('--concurrency') || 2));
const { model, credits } = MODELS[quality];
const BASE = (process.env.WORLDLABS_BASE || 'https://api.worldlabs.ai').replace(/\/$/, '');
const KEY = process.env.WORLDLABS_API_KEY;

const manifest = JSON.parse(readFileSync(join(HERE, 'manifest.json'), 'utf8'));
let elements = manifest.elements;
if (only) {
  const unknown = [...only].filter((id) => !elements.some((e) => e.id === id));
  if (unknown.length) die(`unknown element id: ${unknown.join(', ')}`);
  elements = elements.filter((e) => only.has(e.id));
}

mkdirSync(OUT, { recursive: true });
const state = existsSync(STATE_FILE) ? JSON.parse(readFileSync(STATE_FILE, 'utf8')) : {};
function saveState() {
  const tmp = STATE_FILE + '.tmp';
  writeFileSync(tmp, JSON.stringify(state, null, 2) + '\n');
  renameSync(tmp, STATE_FILE);
}

function die(msg) { console.error(`error: ${msg}`); process.exit(1); }
const log = (id, msg) => console.log(`[${new Date().toISOString().slice(11, 19)}] ${id.padEnd(17)} ${msg}`);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const usd = (c) => `$${(c / CREDITS_PER_USD).toFixed(2)}`;

const isDone = (e) => {
  const s = state[e.id];
  return s && s.status === 'done' && s.model === model && existsSync(join(OUT, `${e.id}.spz`));
};

// ---------- plan ----------
const todo = elements.filter((e) => force || !isDone(e));
const resuming = todo.filter((e) => !force && state[e.id]?.operation_id && state[e.id]?.status === 'generating' && state[e.id]?.model === model);
const newRuns = todo.length - resuming.length;
console.log(`model ${model} (${quality}), ${elements.length} element(s), ${todo.length} to run`);
for (const e of elements) {
  const why = !todo.includes(e) ? 'finished, skip' : resuming.includes(e) ? 'resume operation in progress' : 'generate';
  console.log(`  ${e.id.padEnd(17)} ${why}`);
}
console.log(`estimated cost: ${newRuns} new generation(s) x ${credits} credits = ${newRuns * credits} credits (about ${usd(newRuns * credits)})`);
if (dryRun) process.exit(0);
if (!todo.length) { writeWorldsJson(); console.log('nothing to do'); process.exit(0); }
if (!KEY) die('WORLDLABS_API_KEY is not set');

// ---------- api ----------
async function api(method, path, body) {
  for (let attempt = 0; ; attempt++) {
    let res;
    try {
      res = await fetch(BASE + path, {
        method,
        headers: { 'WLT-Api-Key': KEY, ...(body ? { 'Content-Type': 'application/json' } : {}) },
        body: body ? JSON.stringify(body) : undefined,
      });
    } catch (err) {
      if (attempt < 4) { await sleep(2000 * 2 ** attempt); continue; }
      throw new Error(`${method} ${path}: ${err.message}`);
    }
    const text = await res.text();
    if ((res.status === 429 || res.status >= 500) && attempt < 4) { await sleep(2000 * 2 ** attempt); continue; }
    if (!res.ok) throw new Error(`${method} ${path}: HTTP ${res.status} ${text.slice(0, 400)}`);
    try { return text ? JSON.parse(text) : {}; } catch { throw new Error(`${method} ${path}: response is not JSON`); }
  }
}

// Describe a response by its keys only, so errors never echo URLs with tokens.
const shape = (o, d = 0) => (o && typeof o === 'object' && d < 3
  ? `{${Object.keys(o).map((k) => `${k}${o[k] && typeof o[k] === 'object' ? ':' + shape(o[k], d + 1) : ''}`).join(',')}}` : '');
const pick = (o, ...paths) => {
  for (const p of paths) {
    const v = p.split('.').reduce((a, k) => (a == null ? a : a[k]), o);
    if (v != null && v !== '') return v;
  }
  return undefined;
};

async function upload(e) {
  const file = join(HERE, e.crop);
  const ext = extname(file).slice(1).toLowerCase();
  const prep = await api('POST', '/marble/v1/media-assets:prepare_upload', { file_name: basename(file), kind: 'image', extension: ext });
  const assetId = pick(prep, 'media_asset.media_asset_id', 'media_asset.id', 'media_asset_id', 'id');
  const info = prep.upload_info || {};
  if (!assetId || !info.upload_url) throw new Error(`unexpected prepare_upload response ${shape(prep)}`);
  const data = readFileSync(file);
  const res = await fetch(info.upload_url, {
    method: info.upload_method || 'PUT',
    headers: { ...(info.required_headers || {}) },
    body: data,
  });
  if (!res.ok) throw new Error(`upload PUT: HTTP ${res.status}`);
  return assetId;
}

async function generate(e, assetId) {
  const body = {
    display_name: `OBTRAN 003 ${e.title}`,
    model,
    world_prompt: {
      type: 'image',
      image_prompt: { source: 'media_asset', media_asset_id: assetId },
      text_prompt: `${e.prompt} ${manifest.style}`,
      is_pano: 'auto',
    },
  };
  const op = await api('POST', '/marble/v1/worlds:generate', body);
  const opId = pick(op, 'operation_id', 'id', 'name');
  if (!opId) throw new Error(`unexpected worlds:generate response ${shape(op)}`);
  return String(opId).replace(/^operations\//, '');
}

async function poll(e, opId) {
  const started = Date.now();
  let last = '';
  while (Date.now() - started < TIMEOUT_MS) {
    const op = await api('GET', `/marble/v1/operations/${encodeURIComponent(opId)}`);
    if (op.error) state[e.id].status = 'failed';
    if (op.error) throw new Error(`generation failed: ${typeof op.error === 'string' ? op.error : JSON.stringify(op.error).slice(0, 400)}`);
    if (op.done) return op;
    const progress = pick(op, 'metadata.progress.status', 'metadata.progress', 'metadata.status', 'status');
    const note = typeof progress === 'object' ? JSON.stringify(progress) : String(progress ?? 'running');
    if (note !== last) { log(e.id, `generating: ${note}`); last = note; }
    await sleep(POLL_MS);
  }
  throw new Error(`timed out after ${TIMEOUT_MS / 60000} minutes; rerun to keep polling operation ${opId}`);
}

async function worldFrom(op) {
  let world = pick(op, 'response.world', 'response');
  const worldId = pick(world || {}, 'world_id', 'id') || pick(op, 'metadata.world_id');
  if (!world?.assets && worldId) {
    const res = await api('GET', `/marble/v1/worlds/${encodeURIComponent(worldId)}`);
    world = res.world || res;
  }
  if (!world?.assets) throw new Error(`no assets in finished operation ${shape(op)}`);
  return { world, worldId: worldId || pick(world, 'world_id', 'id') };
}

async function download(url, dest) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`download ${basename(dest)}: HTTP ${res.status}`);
  const buf = Buffer.from(await res.arrayBuffer());
  writeFileSync(dest + '.part', buf);
  renameSync(dest + '.part', dest);
  return buf.length;
}

const mb = (n) => `${(n / 1048576).toFixed(1)} MB`;

async function run(e) {
  const s = (state[e.id] = force && state[e.id]?.status === 'done' ? {} : state[e.id] || {});
  try {
    if (!(s.status === 'generating' && s.operation_id && s.model === model)) {
      log(e.id, `uploading ${e.crop}`);
      const assetId = await upload(e);
      const opId = await generate(e, assetId);
      Object.assign(s, { status: 'generating', model, media_asset_id: assetId, operation_id: opId, started_at: new Date().toISOString(), error: undefined });
      saveState();
      log(e.id, `started operation ${opId}`);
    } else log(e.id, `resuming operation ${s.operation_id}`);

    const op = await poll(e, s.operation_id);
    const { world, worldId } = await worldFrom(op);
    const spz = world.assets.splats?.spz_urls || {};
    const pano = world.assets.imagery?.pano_url;
    if (!spz['500k'] && !spz.full_res) throw new Error(`no splat urls in world ${shape(world.assets)}`);

    const files = {};
    const get = async (url, name) => {
      if (!url) return;
      const n = await download(url, join(OUT, name));
      files[name] = n;
      log(e.id, `downloaded ${name} ${mb(n)}${n > GITHUB_LIMIT ? '  (over GitHub\'s 100 MB limit)' : ''}`);
    };
    await get(spz['500k'] || spz.full_res, `${e.id}.spz`);
    await get(spz['100k'], `${e.id}.100k.spz`);
    await get(pano, `${e.id}.pano${extname(new URL(pano || 'https://x/a.jpg').pathname) || '.jpg'}`);
    if (fullRes) await get(spz.full_res, `${e.id}.full.spz`);

    Object.assign(s, {
      status: 'done', world_id: worldId, finished_at: new Date().toISOString(),
      marble_url: world.world_marble_url || world.marble_url || null,
      metric_scale_factor: world.assets.splats?.semantics_metadata?.metric_scale_factor ?? null,
      caption: world.assets.caption || null,
      files,
    });
    delete s.error;
    saveState();
    log(e.id, 'done');
  } catch (err) {
    s.error = err.message;
    // an operation the API no longer knows about cannot be resumed; the next run starts a new one
    if (s.status !== 'generating' || /operations\/.*HTTP 404/.test(err.message)) s.status = 'failed';
    saveState();
    log(e.id, `FAILED: ${err.message}`);
    throw err;
  }
}

function writeWorldsJson() {
  const [pw, ph] = manifest.page_px;
  const worlds = manifest.elements
    .filter((e) => state[e.id]?.status === 'done' && existsSync(join(OUT, `${e.id}.spz`)))
    .map((e) => {
      const s = state[e.id];
      const [x, y, w, h] = e.crop_px;
      const rel = (f) => (existsSync(join(OUT, f)) ? `worlds/${f}` : null);
      const pano = Object.keys(s.files || {}).find((f) => f.startsWith(`${e.id}.pano`));
      return {
        id: e.id, title: e.title, model: s.model, world_id: s.world_id, marble_url: s.marble_url,
        splats: { '500k': rel(`${e.id}.spz`), '100k': rel(`${e.id}.100k.spz`) },
        pano: pano ? rel(pano) : null,
        metric_scale_factor: s.metric_scale_factor,
        crop_uv: [x / pw, y / ph, (x + w) / pw, (y + h) / ph],
      };
    });
  writeFileSync(join(OUT, 'worlds.json'), JSON.stringify({ updated: new Date().toISOString(), worlds }, null, 2) + '\n');
  return worlds.length;
}

// ---------- main ----------
const queue = [...todo];
const failures = [];
await Promise.all(Array.from({ length: Math.min(concurrency, queue.length) }, async () => {
  while (queue.length) {
    const e = queue.shift();
    try { await run(e); } catch { failures.push(e.id); }
  }
}));
const n = writeWorldsJson();
console.log(`worlds.json lists ${n} world(s)`);
for (const e of elements) {
  const f = join(OUT, `${e.id}.spz`);
  if (existsSync(f) && statSync(f).size > GITHUB_LIMIT) console.warn(`warning: ${e.id}.spz is ${mb(statSync(f).size)}, over GitHub's limit; commit the 100k file only`);
}
if (failures.length) { console.error(`failed: ${failures.join(', ')} (rerun the same command to retry or resume)`); process.exit(1); }
