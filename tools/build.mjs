// Build prototype/index.src.html into dist/.
//
//   node tools/build.mjs            served build (Vercel): assets and worlds as files
//   node tools/build.mjs --inline   one self contained HTML file with base64 assets (claude.ai artifact)
//   node tools/build.mjs --local    load three.js and Spark from /node_modules instead of jsDelivr (offline testing)
//
//   --out <dir>    write somewhere other than dist/ (relative to the repo root)
// The flags combine. tools/build.py produces the same output.
import { readFileSync, writeFileSync, mkdirSync, rmSync, copyFileSync, existsSync, readdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const SRC = join(ROOT, 'prototype', 'index.src.html');
const ASSETS = join(ROOT, 'prototype', 'assets');
const WORLDS = join(ROOT, 'worlds', 'worlds');
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

const meta = JSON.stringify(JSON.parse(readFileSync(join(ASSETS, 'meta.json'), 'utf8')));
const fill = {
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
console.log(`${DIST.slice(ROOT.length + 1)}/index.html ${kb} KB (${inline ? 'inline' : 'files'}${local ? ', local three' : ''})${inline ? '' : `, ${copied} world files`}`);
