#!/usr/bin/env node
/* Origin drive for the two v2.3 standalones: the person-shaped checks, on the
 * real pages. For each page — splash exactly once with its own title, Skip at
 * the 44px touch target and actually dismissing, the estate back chip mounted
 * from /hud.js, zero console errors. The B4 matrix proves the import protocol;
 * this proves the front door a pupil walks through.
 *
 *   node tools/wave_ohm_live_drive.mjs --base https://madebymatt.uk/Matt-s-Apps-/
 */
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const pw = (() => {
  for (const p of ['playwright', '/opt/node22/lib/node_modules/playwright/index.js']) {
    try { return require(p); } catch (_) {}
  }
  console.error('[FAIL] playwright not found'); process.exit(2);
})();
const { chromium } = pw;

const argv = process.argv.slice(2);
const val = (n) => { const i = argv.indexOf(n); return i > -1 ? argv[i + 1] : null; };
const BASE = (val('--base') || process.env.MBM_BASE_URL || '').replace(/\/?$/, '/');
if (!BASE) { console.error('usage: --base <url>'); process.exit(2); }

const PAGES = [
  ['wave-interference-iridescence-engine-v2-3.html', 'WAVE & IRIDESCENCE'],
  ['ohms-law-fault-finder-v2-3.html', "OHM'S LAW FAULT-FINDER"],
];

const results = [];
const check = (limb, ok, detail) => {
  results.push(ok);
  console.log(`  ${ok ? 'PASS' : 'FAIL'}  ${String(limb).padEnd(46)} ${detail}`);
};

const browser = await chromium.launch({
  args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'],
});
const ctx = await browser.newContext({ viewport: { width: 1280, height: 1000 } });

for (const [file, title] of PAGES) {
  console.log(`\n${file}`);
  const page = await ctx.newPage();
  const errs = [];
  page.on('console', (m) => { if (m.type() === 'error') errs.push(m.text()); });
  page.on('pageerror', (e) => errs.push('pageerror: ' + e.message));
  await page.goto(new URL(file, BASE).href, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(1500);
  const n = await page.evaluate(() => document.querySelectorAll('.mbm-splash').length);
  check('splash exactly once', n === 1, `count ${n}`);
  const t = await page.evaluate(() => (document.querySelector('.mbm-splash') || {}).textContent || '');
  check('splash carries the page title', t.includes(title), JSON.stringify(t.trim().slice(0, 44)));
  const skip = page.locator('.mbm-splash .mbm-skip');
  const box = await skip.boundingBox().catch(() => null);
  check('Skip visible and >=44px tall', !!box && box.height >= 44, box ? `${Math.round(box.width)}x${Math.round(box.height)}` : 'no box');
  await skip.click().catch(() => {});
  await page.waitForTimeout(700);
  const gone = await page.evaluate(() => document.querySelectorAll('.mbm-splash').length);
  check('Skip dismisses it', gone === 0, `count after ${gone}`);
  const chip = page.locator('#mbmhud-back, #mbmhud-home, #mbmhud-pill').first();
  const cb = await chip.boundingBox().catch(() => null);
  check('estate back chip mounted', !!cb && cb.width > 0 && cb.height > 0, cb ? `${Math.round(cb.width)}x${Math.round(cb.height)}` : 'no box');
  check('zero console errors', errs.length === 0, errs.length ? errs.slice(0, 2).join(' | ') : 'clean');
  await page.close();
}

await browser.close();
const bad = results.filter((r) => !r).length;
console.log(`\n${bad ? '[FAIL]' : '[PASS]'} wave/ohm origin drive: ${results.length - bad}/${results.length} limbs`);
process.exit(bad ? 1 : 0);
