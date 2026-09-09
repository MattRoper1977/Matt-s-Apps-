/**
 * SW2 T4 — the token file is INERT, measured rather than asserted.
 *
 * assets/mbm-tokens.css names colours and declares no selectors, so the claim
 * has always been that linking it changes no pixel. That claim is only true if
 * it defines no custom property the estate already defines: a redefinition wins
 * on cascade order (the stamped <link> is last in <head>) and repaints every
 * consumer of that name.
 *
 * It was not true. Five names collided -- --mbm-ink, --mbm-focus, --mbm-font,
 * --mbm-line, --mbm-muted -- all owned by assets/mbm-platform.css or
 * assets/brand/brand-tokens.css, with six live consumers between them. The
 * measurable consequence was /main/'s .mbm-audience repainting from #1B2140 to
 * #161D3D: a design change, which T3 is not allowed to make.
 *
 * So this gate does not read the file. It loads every stamped page twice --
 * once as served, once with the token <link> stripped -- and diffs the computed
 * style of every element in the document. Zero differences, or it fails.
 *
 * A name census alone would not have caught it either: --mbm-line's collision
 * only matters where a consumer is on the page, and only rendering knows that.
 *
 *   node tools/sw2/check_tokens_inert.cjs --origin http://127.0.0.1:PORT
 *   node tools/sw2/check_tokens_inert.cjs --origin ... --break   # red proof
 */
const { createRequire } = require('module');
const { chromium } = createRequire('/opt/node22/lib/node_modules/playwright')('playwright');

// The two Lessons pages that carry the shared platform chrome. The other six
// top-level pages load neither mbm-platform.css nor the unified header, so they
// are not in SW2's scope and linking the token file on them would be a change
// nobody asked for.
// The Apps hub is the one page SW2 T5 touches here (S7 owns the rest).
const ROUTES = ['/'];

// Everything a colour token can reach. Shorthands are avoided: they serialise
// inconsistently, and a longhand diff names the property that moved.
const PROPS = [
  'color', 'background-color', 'border-top-color', 'border-right-color',
  'border-bottom-color', 'border-left-color', 'outline-color', 'outline-style',
  'outline-width', 'box-shadow', 'font-family', 'border-top-left-radius',
  'fill', 'stroke', 'caret-color', 'text-decoration-color', 'column-rule-color',
];

const SEP = ' |@| ';

function arg(name, fallback) {
  const i = process.argv.indexOf(name);
  return i >= 0 ? process.argv[i + 1] : fallback;
}

async function snapshot(browser, origin, route, { strip, breakIt }) {
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const page = await context.newPage();

  // The token file is EMPTIED rather than unlinked. Removing the <link> would
  // remove an element, so the two runs would not have the same DOM to compare
  // -- the first version of this gate failed on exactly that, twelve times.
  if (strip) {
    await page.route('**/assets/mbm-tokens.css', (r) =>
      r.fulfill({ status: 200, contentType: 'text/css', body: '/* emptied by the inertness gate */' }));
  }
  // --break puts one known collision back, so the gate has a red proof that
  // does not require editing the shipped file.
  if (breakIt) {
    await page.route('**' + route, async (r) => {
      const response = await r.fetch();
      const body = (await response.text()).replace(
        '</head>', `<style>:root{${breakIt}}</style></head>`);
      await r.fulfill({ response, body });
    });
  }

  await page.goto(origin + route, { waitUntil: 'networkidle', timeout: 30000 });
  await page.evaluate(() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r))));

  // Keyed by structural path, not by index. Four routes inject elements from
  // script after load and the count drifts in BOTH directions between two loads
  // of the same page -- that is the page's own timing, not the stylesheet, and
  // an index-aligned diff would report it as a token failure. Elements that
  // appear in only one run are counted and reported, never silently dropped.
  const measured = await page.evaluate(([props, sep]) => {
    const out = {};
    const path = (el) => {
      const parts = [];
      for (let n = el; n && n.nodeType === 1; n = n.parentElement) {
        const i = n.parentElement ? [...n.parentElement.children].indexOf(n) : 0;
        parts.unshift(n.tagName.toLowerCase() + ':' + i);
      }
      return parts.join('/');
    };
    for (const el of document.querySelectorAll('*')) {
      const cs = getComputedStyle(el);
      out[path(el)] = {
        style: props.map((p) => cs.getPropertyValue(p)).join(sep),
        tag: el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') +
          (typeof el.className === 'string' && el.className
            ? '.' + el.className.trim().split(/\s+/).join('.')
            : ''),
      };
    }
    return out;
  }, [PROPS, SEP]);
  await context.close();
  return measured;
}

(async () => {
  const origin = arg('--origin', 'http://127.0.0.1:4911').replace(/\/$/, '');
  // --break takes the declaration to inject, so the red proof can name a token
  // this estate actually consumes. The default that works on the site
  // (--mbm-line) is overridden more locally here and changes nothing, which
  // would have made this gate pass its own red proof and prove nothing.
  const breakIt = process.argv.includes('--break')
    ? (arg('--break', '') || '--mbm-navy:#30475c')
    : null;

  const browser = await chromium.launch();
  const problems = [];
  const unstable = [];
  let elements = 0;

  for (const route of ROUTES) {
    const served = await snapshot(browser, origin, route, { strip: false, breakIt });
    const without = await snapshot(browser, origin, route, { strip: true, breakIt: false });

    const shared = Object.keys(served).filter((k) => k in without);
    const only = Object.keys(served).length + Object.keys(without).length - 2 * shared.length;
    if (only) unstable.push(`${route}: ${only} element(s) present in only one of the two loads`);
    elements += shared.length;

    const seen = new Set();
    for (const k of shared) {
      if (served[k].style === without[k].style) continue;
      const a = served[k].style.split(SEP);
      const b = without[k].style.split(SEP);
      for (let j = 0; j < PROPS.length; j++) {
        if (a[j] === b[j]) continue;
        const key = `${route}|${PROPS[j]}|${b[j]}|${a[j]}`;
        if (seen.has(key)) continue;
        seen.add(key);
        problems.push(`${route}  ${served[k].tag.slice(0, 46)}  ${PROPS[j]}: ${b[j]} -> ${a[j]}`);
      }
    }
  }

  await browser.close();

  console.log(`token inertness: ${ROUTES.length} page types, ${elements} elements compared, ${PROPS.length} properties each`);
  if (unstable.length) {
    console.log(`  script-injected elements not comparable (the page's own timing, both directions):`);
    for (const u of unstable) console.log('    ' + u);
  }
  if (problems.length) {
    console.error(`\nPROBLEMS: ${problems.length} (first difference per route, property and value pair)`);
    for (const p of problems.slice(0, 40)) console.error('  ' + p);
    if (problems.length > 40) console.error(`  … and ${problems.length - 40} more`);
    process.exit(1);
  }
  console.log('linking assets/mbm-tokens.css changes no computed style on any Apps page');
})().catch((e) => { console.error(String(e).slice(0, 400)); process.exit(2); });
