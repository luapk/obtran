#!/usr/bin/env node
// A local stand in for the World Labs endpoints that generate-worlds.mjs calls,
// so the pipeline can be tested without spending credits.
//
//   node mock-api.mjs 8787 &
//   WORLDLABS_BASE=http://localhost:8787 WORLDLABS_API_KEY=test WORLDLABS_POLL_MS=200 node generate-worlds.mjs --draft
//
// MOCK_FAIL=<element id> makes that element's generation fail.
// MOCK_DIE_AFTER=<n> exits the server after n operation polls, to test resuming.
import { createServer } from 'node:http';

const port = Number(process.argv[2] || 8787);
const base = `http://localhost:${port}`;
const assets = new Map();
const ops = new Map();
let polls = 0;
let n = 0;

const send = (res, code, body) => { res.writeHead(code, { 'Content-Type': 'application/json' }); res.end(JSON.stringify(body)); };
const readBody = (req) => new Promise((r) => { const c = []; req.on('data', (d) => c.push(d)); req.on('end', () => r(Buffer.concat(c))); });

createServer(async (req, res) => {
  const url = new URL(req.url, base);
  const body = await readBody(req);
  if (url.pathname.startsWith('/marble/') && req.headers['wlt-api-key'] !== 'test') return send(res, 401, { error: 'bad key' });

  if (req.method === 'POST' && url.pathname === '/marble/v1/media-assets:prepare_upload') {
    const id = `ma_${++n}`;
    const { file_name } = JSON.parse(body);
    assets.set(id, { file_name, bytes: 0 });
    return send(res, 200, { media_asset: { media_asset_id: id, file_name }, upload_info: { upload_url: `${base}/upload/${id}?sig=secret`, upload_method: 'PUT', required_headers: { 'x-mock': '1' } } });
  }
  if (req.method === 'PUT' && url.pathname.startsWith('/upload/')) {
    const a = assets.get(url.pathname.split('/')[2]);
    if (!a || req.headers['x-mock'] !== '1') return send(res, 400, {});
    a.bytes = body.length;
    res.writeHead(200); return res.end();
  }
  if (req.method === 'POST' && url.pathname === '/marble/v1/worlds:generate') {
    const b = JSON.parse(body);
    const a = assets.get(b.world_prompt?.image_prompt?.media_asset_id);
    if (!a || !a.bytes || b.world_prompt.type !== 'image' || !b.model) return send(res, 400, { error: 'bad request' });
    const id = `op_${++n}`;
    const el = a.file_name.replace(/\.[a-z]+$/, '');
    ops.set(id, { el, polls: 0, model: b.model });
    return send(res, 200, { operation_id: id, done: false });
  }
  if (req.method === 'GET' && url.pathname.startsWith('/marble/v1/operations/')) {
    const id = decodeURIComponent(url.pathname.split('/').pop());
    const op = ops.get(id);
    if (!op) return send(res, 404, { error: 'no such operation' });
    if (process.env.MOCK_DIE_AFTER && ++polls >= Number(process.env.MOCK_DIE_AFTER)) { send(res, 503, {}); setTimeout(() => process.exit(0), 50); return; }
    op.polls++;
    if (process.env.MOCK_FAIL === op.el && op.polls > 1) return send(res, 200, { operation_id: id, done: true, error: { code: 13, message: 'mock failure' } });
    if (op.polls < 3) return send(res, 200, { operation_id: id, done: false, metadata: { progress: { status: op.polls < 2 ? 'queued' : 'running' } } });
    const w = `w_${op.el}`;
    return send(res, 200, { operation_id: id, done: true, response: { world_id: w, display_name: op.el } });
  }
  if (req.method === 'GET' && url.pathname.startsWith('/marble/v1/worlds/')) {
    const w = decodeURIComponent(url.pathname.split('/').pop());
    return send(res, 200, {
      world_id: w, world_marble_url: `https://marble.worldlabs.ai/world/${w}`,
      assets: {
        caption: 'mock world',
        splats: { spz_urls: { '100k': `${base}/files/${w}-100k.spz`, '500k': `${base}/files/${w}-500k.spz`, full_res: `${base}/files/${w}-full.spz` }, semantics_metadata: { metric_scale_factor: 1.7 } },
        imagery: { pano_url: `${base}/files/${w}-pano.jpg` },
      },
    });
  }
  if (req.method === 'GET' && url.pathname.startsWith('/files/')) {
    res.writeHead(200, { 'Content-Type': 'application/octet-stream' });
    return res.end(Buffer.alloc(url.pathname.includes('100k') ? 1024 : 4096, 7));
  }
  send(res, 404, { error: `no route ${req.method} ${url.pathname}` });
}).listen(port, () => console.log(`mock World Labs API on ${base}`));
