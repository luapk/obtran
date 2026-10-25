// Scaffold a new comic for the engine: comics/<id>/comic.json from the comic skill's template, and the
// asset and world folders the engine expects, with empty index files so it builds and loads.
//
//   node tools/new_comic.mjs <id> ["Title"] [CODE]
//
// Then: extract the page (tools/extract_page.py), make page.jpg, depth.png and meta.json into
// comics/<id>/assets (tools/make_assets.py), fill comic.json phase by phase, and build with
// node tools/build.mjs --comic <id>. See .claude/skills/comic-experience/SKILL.md.
import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const [id, title = id, code = (id || '').toUpperCase()] = process.argv.slice(2);
if (!id || !/^[a-z0-9-]+$/.test(id)) { console.error('usage: node tools/new_comic.mjs <id: lowercase letters, digits, hyphens> ["Title"] [CODE]'); process.exit(1); }
const dir = join(ROOT, 'comics', id);
if (existsSync(join(dir, 'comic.json'))) { console.error(`comics/${id}/comic.json already exists`); process.exit(1); }

const template = readFileSync(join(ROOT, '.claude', 'skills', 'comic-experience', 'templates', 'comic.json'), 'utf8');
const fill = (s) => s.split('__ID__').join(id).split('__TITLE__').join(title).split('__CODE__').join(code);
const files = {
  'comic.json': fill(template),
  'assets/voice/index.json': JSON.stringify({ lines: {} }, null, 2) + '\n',
  'assets/films/index.json': JSON.stringify({ note: 'Films for this comic: clips, cues and backdrops (see comics/obtran003 via prototype/assets/films/index.json for every option).', clips: {}, cues: {}, backdrops: {} }, null, 2) + '\n',
  'assets/music/index.json': JSON.stringify({ note: 'Tracks to unlock, loops per space and the start beat (see prototype/assets/music/index.json).', tracks: [], loops: {}, loopLevel: 2.4 }, null, 2) + '\n',
  'worlds/manifest.json': JSON.stringify({ page: '', page_px: [0, 0], style: '', elements: [] }, null, 2) + '\n',
  'worlds/worlds/worlds.json': JSON.stringify({ worlds: [] }, null, 2) + '\n',
};
for (const sub of ['assets/sfx', 'assets/props']) mkdirSync(join(dir, sub), { recursive: true });
for (const [path, body] of Object.entries(files)) {
  mkdirSync(dirname(join(dir, path)), { recursive: true });
  writeFileSync(join(dir, path), body);
}
console.log(`comics/${id}: comic.json, assets/ (voice, films, music, sfx, props), worlds/`);
console.log('next: page.jpg, depth.png and meta.json into assets/ (tools/extract_page.py, tools/make_assets.py), then fill comic.json');
