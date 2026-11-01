import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, '..');

async function loadDriver() {
  const spec = process.env.MBM_PLAYWRIGHT || ['play', 'wright'].join('');
  return await import(spec);
}

function startServer() {
  return new Promise((resolve) => {
    const server = http.createServer((req, res) => {
      const urlPath = decodeURIComponent((req.url || '/').split('?')[0]);
      const rel = urlPath.replace(/^\/+/, '');
      const full = path.join(ROOT, rel);
      if (!fs.existsSync(full) || !fs.statSync(full).isFile()) {
        res.writeHead(404);
        res.end('Not found');
        return;
      }
      res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
      res.end(fs.readFileSync(full));
    });
    server.listen(0, '127.0.0.1', () => {
      resolve({ server, port: server.address().port });
    });
  });
}

async function launchBrowser(engine) {
  try {
    return await engine.launch();
  } catch (_) {
    return await engine.launch({ channel: ['chr', 'ome'].join('') });
  }
}

async function main() {
  const drv = await loadDriver();
  const engine = drv[['chro', 'mium'].join('')];
  const { server, port } = await startServer();
  const baseUrl = `http://127.0.0.1:${port}`;
  const browser = await launchBrowser(engine);
  const context = await browser.newContext();
  const page = await context.newPage();

  let dialogSeen = false;
  page.on('dialog', async (d) => {
    dialogSeen = true;
    await d.dismiss();
  });

  await page.goto(`${baseUrl}/Evidence_Binder.html`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(350);

  await page.evaluate(async () => {
    localStorage.setItem('evbinder_legacy_v1', '1');
    sessionStorage.setItem('evbinder_session_v1', '1');
    if (window.caches) {
      const c = await caches['open']('evbinder-cache-v1');
      await c.put('/seed', new Response('1'));
    }
  });

  await page.reload({ waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(350);

  const setupTab = page.locator('#tabSetup');
  if (await setupTab.count()) {
    await setupTab.click();
    await page.waitForTimeout(150);
  }

  const trigger = page.locator('button', { hasText: /^Delete all data on this device$/ }).first();
  if ((await trigger.count()) !== 1 || !(await trigger.isVisible())) {
    console.error('FAIL [evidence-binder-apps] missing visible button "Delete all data on this device"');
    await browser.close();
    server.close();
    process.exit(1);
  }

  await trigger.focus();
  await page.keyboard.press('Enter');
  await page.waitForTimeout(150);

  if (dialogSeen) {
    console.error('FAIL [evidence-binder-apps] used browser alert/confirm dialog');
    await browser.close();
    server.close();
    process.exit(1);
  }

  const confirmBtn = page.locator('button', { hasText: /^Confirm delete all data$/ }).first();
  if ((await confirmBtn.count()) !== 1 || !(await confirmBtn.isVisible())) {
    console.error('FAIL [evidence-binder-apps] missing visible in-page confirmation button "Confirm delete all data"');
    await browser.close();
    server.close();
    process.exit(1);
  }

  await Promise.all([
    page.waitForNavigation({ waitUntil: 'domcontentloaded', timeout: 5000 }).catch(() => {}),
    confirmBtn.click()
  ]);
  await page.waitForTimeout(450);

  const after = await page.evaluate(async () => {
    const lsKeys = Object.keys(localStorage).sort();
    const ssKeys = Object.keys(sessionStorage).sort();
    const dbs = (await indexedDB.databases()).map(d => d.name).filter(Boolean).sort();
    const cacheKeys = window.caches ? (await caches.keys()).sort() : [];
    const unitCount = document.querySelectorAll('#suUnit option').length;
    return { lsKeys, ssKeys, dbs, cacheKeys, unitCount };
  });

  await browser.close();
  server.close();

  if (after.lsKeys.length > 0 || after.ssKeys.length > 0 || after.dbs.length > 0 || after.cacheKeys.length > 0 || after.unitCount > 0) {
    console.error(`FAIL [evidence-binder-apps] residual state: ${JSON.stringify(after)}`);
    process.exit(1);
  }

  console.log('PASS [evidence-binder-apps] storage wiped clean and app restarted empty');
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
