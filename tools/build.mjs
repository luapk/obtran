// Build prototype/index.src.html into dist/.
//
//   node tools/build.mjs            served build (Vercel): assets and worlds as files
//   node tools/build.mjs --inline   one self contained HTML file with base64 assets (claude.ai artifact)
//   node tools/build.mjs --local    load three.js from /node_modules instead of jsDelivr (offline testing)
//
// The flags combine. tools/build.py produces the same output.
import { readFileSync, writeFileSync, mkdirSync, rmSync, copyFileSync, existsSync, readdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const SRC = join(ROOT, 'prototype', 'index.src.html');
const ASSETS = join(ROOT, 'prototype', 'assets');
const WORLDS = join(ROOT, 'worlds', 'worlds');
const DIST = join(ROOT, 'dist');

const THREE_VERSION = '0.170.0';
const THREE_CDN = `https://cdn.jsdelivr.net/npm/three@${THREE_VERSION}/build/three.module.js`;
const THREE_LOCAL = '/node_modules/three/build/three.module.js';

const args = new Set(process.argv.slice(2));
const inline = args.has('--inline');
const local = args.has('--local');

// Served with the page: splats for desktop and phones, panoramas for checking, and the list.
const isWorldFile = (f) => f === 'worlds.json' || /^[a-z0-9-]+(\.100k)?\.spz$/.test(f) || /\.pano\.(jpg|png|webp)$/.test(f);

const dataUri = (file, mime) => `data:${mime};base64,${readFileSync(join(ASSETS, file)).toString('base64')}`;

rmSync(DIST, { recursive: true, force: true });
mkdirSync(DIST, { recursive: true });

const meta = JSON.stringify(JSON.parse(readFileSync(join(ASSETS, 'meta.json'), 'utf8')));
const fill = {
  '%%THREE_URL%%': local ? THREE_LOCAL : THREE_CDN,
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
  mkdirSync(join(DIST, 'worlds'), { recursive: true });
  if (existsSync(WORLDS)) {
    for (const f of readdirSync(WORLDS).filter(isWorldFile)) { copyFileSync(join(WORLDS, f), join(DIST, 'worlds', f)); copied++; }
  }
  if (!existsSync(join(DIST, 'worlds', 'worlds.json'))) writeFileSync(join(DIST, 'worlds', 'worlds.json'), JSON.stringify({ worlds: [] }) + '\n');
}

const kb = (Buffer.byteLength(html) / 1024).toFixed(0);
console.log(`dist/index.html ${kb} KB (${inline ? 'inline' : 'files'}${local ? ', local three' : ''})${inline ? '' : `, ${copied} world files`}`);
