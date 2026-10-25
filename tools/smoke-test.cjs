// Headless Chrome walkthrough of the built page, with screenshots.
//
//   npm i --no-save three@0.170.0 puppeteer      (or puppeteer-core plus CHROME_PATH)
//   node tools/build.mjs --local
//   python3 -m http.server 8765                  (from the repo root)
//   node tools/smoke-test.cjs shots 1280 860 desk
//   node tools/smoke-test.cjs shots 390 844 phone
//
// Env: URL (default http://localhost:8765/dist/index.html), CHROME_PATH,
// WORLD=0 to accept the drawn void when the Marble world is unavailable,
// CLASSIC=1 to walk the old flow (beats on the page, one breach) instead of the journey,
// LITE=1 to report a low memory device, so the page loads the 100k worlds (much faster here).
// Without a GPU, Chrome runs on SwiftShader, so frame rates are low; the page's
// timers use wall clock time, which is why the waits below are in seconds.
const fs = require('fs');
const path = require('path');

let puppeteer;
try { puppeteer = require('puppeteer'); } catch { puppeteer = require('puppeteer-core'); }

const [outDir = 'shots', w = '1280', h = '860', label = 'desk'] = process.argv.slice(2);
const W = Number(w), H = Number(h);
const CLASSIC = process.env.CLASSIC === '1';
const URL = (process.env.URL || 'http://localhost:8765/dist/index.html') + (CLASSIC ? '?classic=1' : '');
const phone = W < 700;
const candidates = [process.env.CHROME_PATH, '/opt/pw-browsers/chromium-1243/chrome-linux64/chrome', '/opt/pw-browsers/chromium'].filter(Boolean);
const executablePath = candidates.find((p) => { try { return fs.statSync(p).isFile(); } catch { return false; } });

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

(async () => {
  fs.mkdirSync(outDir, { recursive: true });
  const browser = await puppeteer.launch({
    headless: true,
    executablePath,
    // software rendering can take minutes for one frame of a 500k splat world
    protocolTimeout: 20 * 60 * 1000,
    args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--autoplay-policy=no-user-gesture-required', '--no-sandbox'],
  });
  const page = await browser.newPage();
  await page.setViewport({ width: W, height: H, deviceScaleFactor: 1, isMobile: phone, hasTouch: phone });
  if (process.env.LITE === '1') await page.evaluateOnNewDocument(() => Object.defineProperty(navigator, 'deviceMemory', { get: () => 2 }));
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
  // a browser abandons a video's download when it is paused (ERR_ABORTED): not a failure
  page.on('requestfailed', (r) => { if (/\.mp4/.test(r.url()) && /ABORTED/.test(r.failure()?.errorText || '')) return; errors.push(`request failed ${r.url()} ${r.failure()?.errorText || ''}`); });

  let n = 0;
  const shot = async (name) => {
    const f = path.join(outDir, `${label}-${String(++n).padStart(2, '0')}-${name}.png`);
    await page.screenshot({ path: f });
    console.log('  ', f);
  };

  await page.goto(URL, { waitUntil: 'networkidle0', timeout: 120000 });
  await page.waitForFunction(() => window.__ot, { timeout: 120000 });
  await sleep(1500);
  await shot('gate');

  await page.waitForSelector('#gate.ready', { timeout: 120000 });   // Enter comes in after OBTRAN003 decrypts
  await page.click('#start');
  await sleep(1500);
  await page.mouse.move(W * 0.8, H * 0.3);
  await sleep(1500);

  if (!CLASSIC) {
    // the journey: tap into Bob's panel, then each beat in its own space
    await shot('page');
    await page.keyboard.press('ArrowRight');
    // ready = in its space; or already gone on (a beat that advances by itself, such as the one before the finale, can
// leave its space between two polls when a frame takes seconds under SwiftShader)
    const spaceReady = (step) => page.waitForFunction((s) => { const J = window.__ot.journey; return (J.step === s && J.phase === 'space' && window.__ot.worlds.ok) || J.step > s || (J.step === s && (J.phase === 'out' || J.phase === 'load' || J.done)); }, { timeout: 600000, polling: 500 }, step);
    const steps = await page.evaluate(() => window.__ot.STEPS);
    const beats = await page.evaluate(() => window.__ot.BEATS);
    for (let i = 0; i < steps.length; i++) {
      if (beats[steps[i].beat].cut) {
        // this beat cuts into the next space by itself within a second: just see it pass
        await page.waitForFunction((s) => window.__ot.journey.step > s, { timeout: 600000, polling: 200 }, i).catch(() => { throw new Error(`step ${i} did not cut to the next space`); });
        continue;
      }
      await spaceReady(i).catch(() => { throw new Error(`step ${i} (${steps[i].world}) never became ready`); });
      const world = await page.evaluate(() => window.__ot.worlds.id);
      if (world !== steps[i].world) throw new Error(`step ${i} shows ${world}, expected ${steps[i].world}`);
      await sleep(2500);
      await shot(`step${i}-${steps[i].world}`);
      // a key during one of Bob's films only cuts the film, so let it finish first
      await page.waitForFunction(() => !window.__ot.films?.on || window.__ot.films.looping, { timeout: 60000, polling: 200 });   // a looping film waits for the key below, which also moves on
      const beat = await page.evaluate((b) => window.__ot.BEATS[b], steps[i].beat);
      if (beat.auto) {
        // this beat moves on by itself once its line (and film) end: wait for it rather than pressing
        const moved = beat.trigger ? () => window.__ot.journey.phase !== 'space' : (s) => window.__ot.journey.step !== s;
        await page.waitForFunction(moved, { timeout: 120000, polling: 200 }, i).catch(() => { throw new Error(`step ${i} did not move on by itself`); });
      } else if (beat.hold) {
        await page.keyboard.down('Space');
        // at most 0.25 s of hold counts per frame, and a 500k world can take tens of seconds a frame here
        await page.waitForFunction((s) => window.__ot.journey.step === s + 1, { timeout: 600000, polling: 200 }, i)
          .catch(() => { throw new Error('hold did not unlock the next beat'); });
        await page.keyboard.up('Space');
      } else if (beat.trigger) {
        await page.keyboard.press('Enter');
      } else {
        await page.keyboard.press('ArrowRight');
      }
    }
    await page.waitForFunction(() => window.__ot.journey.done && window.__ot.worlds.id === 'singularity-core', { timeout: 600000, polling: 500 })
      .catch(() => { throw new Error('the final breach did not reach the singularity'); });
    await page.waitForFunction(() => window.__ot.endReady(), { timeout: 600000 });
    await sleep(1500);
    await shot('end');
    const st = await page.evaluate(() => ({ stage: window.__ot.state.stage, again: true, world: window.__ot.worlds.id, splats: window.__ot.worlds.mesh?.numSplats ?? null }));
    await browser.close();
    console.log(JSON.stringify(st));
    if (errors.length) { console.error('page errors:\n' + errors.join('\n')); process.exit(1); }
    console.log('ok');
    return;
  }

  await shot('beat-caption');

  const beat = () => page.evaluate(() => window.__ot.state.beat);
  // advance until the hold beat
  while (true) {
    const b = await page.evaluate(() => window.__ot.BEATS[window.__ot.state.beat]);
    if (b.hold || b.trigger) break;
    await page.keyboard.press('ArrowRight');
    await sleep(900);
    await shot(`beat-${await page.evaluate(() => window.__ot.BEATS[window.__ot.state.beat].b)}`);
  }

  // press and hold to unlock
  const before = await beat();
  await page.keyboard.down('Space');
  await sleep(700);
  await shot('hold');
  // the hold timer counts at most 0.25 s a frame, so on slow software rendering it takes longer
  await page.waitForFunction((b) => window.__ot.state.beat === b + 1, { timeout: 30000, polling: 100 }, before)
    .catch(() => { throw new Error('hold did not unlock the next beat'); });
  await page.keyboard.up('Space');
  await sleep(400);
  await shot('beat-after-hold');

  await page.keyboard.press('ArrowRight');
  await sleep(1200);
  await shot('beat-qntm');

  // breach, frozen at chosen points
  await page.keyboard.press('Enter');
  await page.evaluate(() => { window.__ot.state.freeze = true; });
  for (const u of [0.15, 0.35, 0.5, 0.7, 0.9]) {
    await page.evaluate((u) => { window.__ot.state.breachT = u * 4.8; }, u);
    await sleep(2500);
    await shot(`breach-${Math.round(u * 100)}`);
  }
  await page.evaluate(() => { window.__ot.state.freeze = false; window.__ot.state.breachT = 4.8; });
  await page.waitForFunction(() => window.__ot.state.stage === 'void', { timeout: 120000 });
  // the Marble world should replace the drawn void (set WORLD=0 to accept the fallback)
  if (process.env.WORLD !== '0') {
    await page.waitForFunction(() => window.__ot.worlds.ok && window.__ot.worlds.mesh && window.__ot.worlds.mesh.visible, { timeout: 120000 })
      .catch(() => { throw new Error('the Marble world did not load after the breach'); });
  }
  // the ending runs on wall clock time at no more than 0.25 s a frame, so wait for it rather than sleep
  await page.waitForFunction(() => window.__ot.endReady(), { timeout: 600000 });
  await sleep(1500);
  await shot('void-end');
  await page.mouse.move(W / 2, H / 2);
  await page.mouse.down();
  await page.mouse.move(W / 2 - 200, H / 2 + 40, { steps: 8 });
  await page.mouse.up();
  await sleep(1200);
  await shot('void-look');

  const st = await page.evaluate(() => ({ stage: window.__ot.state.stage, again: window.__ot.endReady(), world: window.__ot.worlds.id, splats: window.__ot.worlds.mesh?.numSplats ?? null }));
  await browser.close();
  console.log(JSON.stringify(st));
  if (errors.length) { console.error('page errors:\n' + errors.join('\n')); process.exit(1); }
  if (st.stage !== 'void' || !st.again) { console.error('did not reach the ending'); process.exit(1); }
  console.log('ok');
})().catch((e) => { console.error(e); process.exit(1); });
