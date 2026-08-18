// Re-run the Maker Lab acceptance test against the published origin.
//
// v2.1 exists because v2.0.0's opaque-origin sandbox made every studio report
// "browser storage unavailable" and split saves into two stores (M1), and
// because any window that could post into the Shell could overwrite a
// Passport (M2). Both fixes are about how a real browser treats a real origin,
// so proving them on a served copy is not the same as proving them where
// pupils and teachers actually open the suite.
import { chromium } from 'playwright';

const base = process.argv[2];
if (!base) throw new Error('usage: verify_live_acceptance.mjs <published Apps root>');
const suite = new URL('Teesside_Maker_Lab_PRO/', base).href;
const MARKER = `LIVE-ACCEPTANCE-${process.env.GITHUB_SHA?.slice(0, 12) ?? 'local'}`;

const results = [];
const check = (name, pass, detail = '') => {
  results.push({ name, pass, detail });
  console.log(`${pass ? 'PASS' : 'FAIL'}  ${name}${detail ? '  — ' + detail : ''}`);
};

// Honour an explicit browser path the way the LundyLoop verifier does, so this
// can be run outside CI against a served copy before it is trusted on production.
const executablePath = process.env.MAKERLAB_CHROMIUM_EXECUTABLE || undefined;
const browser = await chromium.launch(executablePath ? { executablePath } : {});
const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });

// The hub card must reach the suite landing page, not some other route.
{
  const page = await context.newPage();
  await page.goto(base, { waitUntil: 'networkidle' });
  const href = await page.evaluate(() => {
    const link = [...document.querySelectorAll('a')]
      .find(a => /Teesside Cross-Curricular Maker Lab PRO/.test(a.closest('.card')?.textContent ?? ''));
    return link?.href ?? null;
  });
  check('hub card resolves to the suite landing page',
    !!href && href.endsWith('Teesside_Maker_Lab_PRO/index.html'), href ?? 'card not found');
  if (href) {
    const response = await page.goto(href, { waitUntil: 'domcontentloaded' });
    check('suite landing page serves 200', response?.status() === 200, String(response?.status()));
  }
  await page.close();
}

// M1: one save route. Typing in the embedded studio must persist, and the same
// state must be there when the studio is opened directly.
const page = await context.newPage();
const consoleErrors = [];
page.on('pageerror', error => consoleErrors.push(String(error)));
await page.goto(`${suite}STUDIO_SHELL.html?app=1`, { waitUntil: 'networkidle' });
await page.waitForSelector('#appFrame');
const frame = await (await page.$('#appFrame')).contentFrame();
await frame.waitForLoadState('domcontentloaded');
await page.waitForTimeout(1500);

await frame.evaluate(marker => {
  const field = document.querySelector('#proLearner');
  field.value = marker;
  field.dispatchEvent(new Event('input', { bubbles: true }));
}, MARKER);
await page.waitForTimeout(2000);

const chip = await frame.locator('#autosave').textContent();
check('autosave chip reports a save, not unavailable storage',
  /saved \d{2}:\d{2}/.test(chip ?? '') && !/unavailable/i.test(chip ?? ''), chip ?? 'no chip');

const stored = await page.evaluate(() => localStorage.getItem('MBM_MAKER_PRO_V2_shadow_rig_pro_v2'));
check('the studio wrote its state under the shared key', !!stored && stored.includes(MARKER));

// M2: only the framed studio may sync. A forged message from any other window
// must not reach the Passport.
const before = await page.evaluate(() => localStorage.getItem('MBM_MAKER_STUDIO_SHELL_V2'));
await page.evaluate(() => window.postMessage({
  channel: 'MBM_MAKER_PRO_SHELL_V2', app: 'shadow_rig_pro_v2', type: 'SYNC_APP',
  payload: { project: { app: 'shadow_rig_pro_v2', evidence: [{ forged: true }] } },
}, '*'));
await page.waitForTimeout(1000);
const afterForged = await page.evaluate(() => localStorage.getItem('MBM_MAKER_STUDIO_SHELL_V2'));
check('a forged sync from another window is refused',
  !(afterForged ?? '').includes('"forged":true') && before === afterForged);

const framed = await (await page.$('#appFrame')).contentFrame();
await framed.evaluate(() => parent.postMessage({
  channel: 'MBM_MAKER_PRO_SHELL_V2', app: 'shadow_rig_pro_v2', type: 'SYNC_APP',
  payload: { project: { app: 'shadow_rig_pro_v2', evidence: [{ genuine: 'LIVE-GENUINE' }] } },
}, '*'));
await page.waitForTimeout(1000);
const afterGenuine = await page.evaluate(() => localStorage.getItem('MBM_MAKER_STUDIO_SHELL_V2'));
check('a genuine sync from the framed studio still lands',
  (afterGenuine ?? '').includes('LIVE-GENUINE'));

// Same browser context, so the studio opened directly sees the same storage.
const direct = await context.newPage();
await direct.goto(`${suite}01_Anamorphic_Shadow_Rig_Studio_PRO_v2.html`, { waitUntil: 'networkidle' });
await direct.waitForTimeout(1500);
const restored = await direct.evaluate(marker => {
  const state = localStorage.getItem('MBM_MAKER_PRO_V2_shadow_rig_pro_v2');
  const field = [...document.querySelectorAll('input,textarea')].find(i => i.value?.includes(marker));
  return { inState: !!state?.includes(marker), inField: field?.id ?? null };
}, MARKER);
check('the directly opened studio reads the same saved state',
  restored.inState && restored.inField === 'proLearner', JSON.stringify(restored));

check('no uncaught page errors', consoleErrors.length === 0, consoleErrors.join(' | '));

await browser.close();
const failed = results.filter(r => !r.pass);
console.log(`\n${results.length - failed.length}/${results.length} live acceptance checks passed`);
process.exit(failed.length ? 1 : 0);
