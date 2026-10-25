// Build prototype/index.src.html into dist/.
//
//   node tools/build.mjs            served build (Vercel): assets and worlds as files
//   node tools/build.mjs --inline   one self contained HTML file with base64 assets (claude.ai artifact)
//   node tools/build.mjs --local    load three.js and Spark from /node_modules instead of jsDelivr (offline testing)
//
//   --out <dir>    write somewhere other than dist/ (relative to the repo root)
//   --comic <id>   build comics/<id>/comic.json (or set COMIC; obtran003 by default): its content is embedded in
//                  the page and its asset folders (paths in comic.json) are the ones served
// The flags combine. tools/build.py runs this.
import { readFileSync, writeFileSync, mkdirSync, rmSync, copyFileSync, existsSync, readdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const SRC = join(ROOT, 'prototype', 'index.src.html');
const comicAt = process.argv.indexOf('--comic');
const COMIC_ID = comicAt > 0 ? process.argv[comicAt + 1] : process.env.COMIC || 'obtran003';
const COMIC_FILE = join(ROOT, 'comics', COMIC_ID, 'comic.json');
if (!existsSync(COMIC_FILE)) throw new Error(`no comic ${COMIC_ID}: ${COMIC_FILE} is missing`);
const comic = JSON.parse(readFileSync(COMIC_FILE, 'utf8'));
for (const k of ['beats', 'journey', 'finalWorld', 'endBeat', 'text']) if (!comic[k]) throw new Error(`comic ${COMIC_ID}: ${k} is missing`);
// the comic's own folders, beside its comic.json unless it names others (OBTRAN 003 keeps its original ones)
const ASSETS = join(ROOT, comic.paths?.assets || join('comics', COMIC_ID, 'assets'));
const WORLDS = join(ROOT, comic.paths?.worlds || join('comics', COMIC_ID, 'worlds'));
const outAt = process.argv.indexOf('--out');
const DIST = outAt > 0 ? join(ROOT, process.argv[outAt + 1]) : join(ROOT, 'dist');

const THREE_VERSION = '0.180.0';
const THREE_CDN = `https://cdn.jsdelivr.net/npm/three@${THREE_VERSION}/build/three.module.js`;
const THREE_LOCAL = '/node_modules/three/build/three.module.js';
const THREE_ADDONS_CDN = `https://cdn.jsdelivr.net/npm/three@${THREE_VERSION}/examples/jsm/`;
const THREE_ADDONS_LOCAL = '/node_modules/three/examples/jsm/';
const SPARK_VERSION = '2.4.0';
const SPARK_CDN = `https://cdn.jsdelivr.net/npm/@sparkjsdev/spark@${SPARK_VERSION}/dist/spark.module.js`;
const SPARK_LOCAL = '/node_modules/@sparkjsdev/spark/dist/spark.module.js';

const args = new Set(process.argv.slice(2));
const inline = args.has('--inline');
const local = args.has('--local');

// Served with the page: splats (raw and cleaned, desktop and phone) and the lists.
// Panoramas stay in the repo for checking; the page never loads them.
const isWorldFile = (f) => ['worlds.json', 'views.json', 'reliefs.json'].includes(f) || /^[a-z0-9-]+(\.100k)?(\.clean)?\.spz$/.test(f);

const dataUri = (file, mime) => `data:${mime};base64,${readFileSync(join(ASSETS, file)).toString('base64')}`;

rmSync(DIST, { recursive: true, force: true });
mkdirSync(DIST, { recursive: true });

for (const f of ['page.jpg', 'depth.png', 'meta.json']) if (!existsSync(join(ASSETS, f))) throw new Error(`comic ${COMIC_ID}: ${f} is missing from ${ASSETS.slice(ROOT.length + 1)} (tools/extract_page.py, then tools/make_assets.py)`);
const meta = JSON.stringify(JSON.parse(readFileSync(join(ASSETS, 'meta.json'), 'utf8')));
// notes are for people: left out of the page
const strip = (v) => Array.isArray(v) ? v.map(strip) : v && typeof v === 'object' ? Object.fromEntries(Object.entries(v).filter(([k]) => k !== 'note').map(([k, x]) => [k, strip(x)])) : v;
const esc = (t) => String(t ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
const text = (k) => esc(comic.text[k]);
const fill = {
  '%%COMIC%%': JSON.stringify(strip(comic)).replace(/</g, '\\u003c'),
  '%%TEXT_TITLE%%': text('title'), '%%TEXT_DESCRIPTION%%': text('description'), '%%TEXT_HEADING%%': text('heading'),
  '%%TEXT_CODE%%': text('code'), '%%TEXT_LEAD%%': text('lead'), '%%TEXT_MUSICTAB%%': text('musicTab'), '%%TEXT_MUSICBUY%%': text('musicBuy'),
  '%%THREE_URL%%': local ? THREE_LOCAL : THREE_CDN,
  '%%THREE_ADDONS_URL%%': local ? THREE_ADDONS_LOCAL : THREE_ADDONS_CDN,
  '%%SPARK_URL%%': local ? SPARK_LOCAL : SPARK_CDN,
  '%%PAGE_SRC%%': inline ? dataUri('page.jpg', 'image/jpeg') : 'assets/page.jpg',
  '%%DEPTH_SRC%%': inline ? dataUri('depth.png', 'image/png') : 'assets/depth.png',
  '%%META%%': meta,
};
let html = readFileSync(SRC, 'utf8');
for (const [key, value] of Object.entries(fill)) {
  if (!html.includes(key)) throw new Error(`placeholder ${key} missing from index.src.html`);
  html = html.split(key).join(value);
}
const left = html.match(/%%[A-Z_]+%%/);
if (left) throw new Error(`unfilled placeholder ${left[0]}`);
writeFileSync(join(DIST, 'index.html'), html);

let copied = 0;
if (!inline) {
  mkdirSync(join(DIST, 'assets'), { recursive: true });
  for (const f of ['page.jpg', 'depth.png', 'meta.json']) copyFileSync(join(ASSETS, f), join(DIST, 'assets', f));
  // voice lines from tools/render-voices.mjs, when there are any
  const VOICE = join(ASSETS, 'voice');
  if (existsSync(VOICE)) {
    mkdirSync(join(DIST, 'assets', 'voice'), { recursive: true });
    for (const f of readdirSync(VOICE).filter((f) => f === 'index.json' || f.endsWith('.mp3'))) copyFileSync(join(VOICE, f), join(DIST, 'assets', 'voice', f));
  }
  // music (assets/music/index.json): the audio files present are listed in the deployed index
  // Paul's sound effects (tools/make_sfx.py)
  const SFX = join(ASSETS, 'sfx');
  if (existsSync(SFX)) {
    mkdirSync(join(DIST, 'assets', 'sfx'), { recursive: true });
    for (const f of readdirSync(SFX).filter((f) => /\.mp3$/.test(f)).sort()) copyFileSync(join(SFX, f), join(DIST, 'assets', 'sfx', f));
  }
  const MUSIC = join(ASSETS, 'music');
  if (existsSync(join(MUSIC, 'index.json'))) {
    mkdirSync(join(DIST, 'assets', 'music'), { recursive: true });
    const audio = readdirSync(MUSIC).filter((f) => /\.(mp3|m4a|ogg|wav)$/.test(f)).sort();
    for (const f of audio) copyFileSync(join(MUSIC, f), join(DIST, 'assets', 'music', f));
    const idx = JSON.parse(readFileSync(join(MUSIC, 'index.json'), 'utf8'));
    idx.present = audio;
    writeFileSync(join(DIST, 'assets', 'music', 'index.json'), JSON.stringify(idx, null, 2) + '\n');
  }
  // props cut from the worlds (tools/cut_slab.py)
  const PROPS = join(ASSETS, 'props');
  if (existsSync(PROPS)) {
    mkdirSync(join(DIST, 'assets', 'props'), { recursive: true });
    for (const f of readdirSync(PROPS).filter((f) => /\.(png|jpg|webp|json)$/.test(f))) copyFileSync(join(PROPS, f), join(DIST, 'assets', 'props', f));
  }
  // short films of Bob (films/README.md): start frames and approved clips
  const FILMS = join(ASSETS, 'films');
  if (existsSync(FILMS)) {
    mkdirSync(join(DIST, 'assets', 'films'), { recursive: true });
    for (const f of readdirSync(FILMS).filter((f) => /\.(json|jpg|mp4|webm)$/.test(f))) copyFileSync(join(FILMS, f), join(DIST, 'assets', 'films', f));
  }
  mkdirSync(join(DIST, 'assets', 'voice'), { recursive: true });
  if (!existsSync(join(DIST, 'assets', 'voice', 'index.json'))) writeFileSync(join(DIST, 'assets', 'voice', 'index.json'), JSON.stringify({ lines: {} }) + '\n');
  mkdirSync(join(DIST, 'worlds'), { recursive: true });
  if (existsSync(WORLDS)) {
    const files = readdirSync(WORLDS).filter(isWorldFile);
    // when a cleaned splat exists the page loads that, so the raw one is not deployed
    const superseded = (f) => f.endsWith('.spz') && !f.includes('.clean.') && files.includes(f.replace(/\.spz$/, '.clean.spz'));
    for (const f of files.filter((f) => !superseded(f))) { copyFileSync(join(WORLDS, f), join(DIST, 'worlds', f)); copied++; }
  }
  if (!existsSync(join(DIST, 'worlds', 'worlds.json'))) writeFileSync(join(DIST, 'worlds', 'worlds.json'), JSON.stringify({ worlds: [] }) + '\n');
}

const kb = (Buffer.byteLength(html) / 1024).toFixed(0);
console.log(`${COMIC_ID}: ${DIST.slice(ROOT.length + 1)}/index.html ${kb} KB (${inline ? 'inline' : 'files'}${local ? ', local three' : ''})${inline ? '' : `, ${copied} world files`}`);
