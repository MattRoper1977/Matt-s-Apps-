/* mbm-cross-estate-unification-lessons-apps-2026-08-08
   Browser matrix for one Lessons or Apps hub. */
import { chromium } from 'playwright';
import fs from 'node:fs';
import path from 'node:path';

const base=(process.env.MBM_BASE_URL||process.argv[2]||'http://127.0.0.1:4173/').replace(/\/?$/,'/');
const root=process.cwd();
const kind=fs.existsSync(path.join(root,'resources.json'))?'lessons':fs.existsSync(path.join(root,'apps.json'))?'apps':null;
if(!kind)throw new Error('Could not detect repository kind');
const widths=[320,360,390,430,768,1024,1280,1440];
const outDir=path.join(root,'audit-output');
fs.mkdirSync(outDir,{recursive:true});
const results={sentinel:'mbm-cross-estate-unification-lessons-apps-2026-08-08',kind,base,widths:[],standalone:[],errors:[]};

function check(condition,message){if(!condition)results.errors.push(message)}
function sameOrigin(url){try{return new URL(url).origin===new URL(base).origin}catch{return false}}

const browser=await chromium.launch({headless:true});
try{
  for(const width of widths){
    const context=await browser.newContext({viewport:{width,height:900},deviceScaleFactor:1});
    const page=await context.newPage();
    const pageErrors=[];const consoleErrors=[];const failed=[];
    page.on('pageerror',err=>pageErrors.push(String(err)));
    page.on('console',msg=>{if(msg.type()==='error')consoleErrors.push(msg.text())});
    page.on('requestfailed',req=>{if(sameOrigin(req.url()))failed.push({url:req.url(),failure:req.failure()})});
    const response=await page.goto(base,{waitUntil:'networkidle',timeout:60000});
    check(response&&response.ok(),`${kind} ${width}: hub HTTP response was not successful`);
    await page.waitForFunction(()=>{const el=document.querySelector('#count');return el&&!/Loading|Couldn't load/.test(el.textContent||'')},{timeout:30000});
    const metrics=await page.evaluate((kind)=>{
      const q=s=>document.querySelector(s);
      const box=el=>{const r=el.getBoundingClientRect();return {width:r.width,height:r.height,visible:!!(r.width&&r.height)}};
      return {
        title:document.title,
        count:q('#count')?.textContent?.trim()||'',
        leadCount:q('#leadCount')?.textContent?.trim()||'',
        cards:document.querySelectorAll('.card').length,
        overflow:document.documentElement.scrollWidth-document.documentElement.clientWidth,
        active:[...document.querySelectorAll('.mbm-primary-links a[aria-current="page"]')].map(a=>a.getAttribute('href')),
        menu:box(q('#menu')),
        nav:box(q('#nav')),
        themeButtons:document.querySelectorAll('[data-mbm-theme-slot] .mbm-sw').length,
        bodyClass:document.body.className,
        kind,
      };
    },kind);
    check(metrics.overflow<=1,`${kind} ${width}: horizontal page overflow ${metrics.overflow}px`);
    check(metrics.cards>0,`${kind} ${width}: no catalogue cards rendered`);
    check(metrics.active.length===1&&metrics.active[0]===(kind==='lessons'?'/Lessons/':'/Matt-s-Apps-/'),`${kind} ${width}: incorrect active navigation ${JSON.stringify(metrics.active)}`);
    check(pageErrors.length===0,`${kind} ${width}: page errors ${pageErrors.join(' | ')}`);
    check(consoleErrors.length===0,`${kind} ${width}: console errors ${consoleErrors.join(' | ')}`);
    check(failed.length===0,`${kind} ${width}: failed first-party requests ${JSON.stringify(failed)}`);

    if(width<=900){
      check(metrics.menu.visible&&metrics.menu.width>=44&&metrics.menu.height>=44,`${kind} ${width}: mobile menu target below 44px`);
      check(!metrics.nav.visible,`${kind} ${width}: mobile navigation should begin closed`);
      await page.locator('#menu').click();
      check(await page.locator('#nav').isVisible(),`${kind} ${width}: menu did not open`);
      check(await page.locator('body').evaluate(el=>el.classList.contains('mbm-nav-open')),`${kind} ${width}: scroll lock class missing`);
      const targets=await page.locator('#nav a:visible, #nav summary:visible').evaluateAll(els=>els.map(el=>{const r=el.getBoundingClientRect();return {text:el.textContent.trim(),w:r.width,h:r.height}}));
      for(const t of targets)check(t.h>=44,`${kind} ${width}: navigation target '${t.text}' is ${t.h}px tall`);
      await page.keyboard.press('Escape');
      check(!(await page.locator('#nav').isVisible()),`${kind} ${width}: Escape did not close navigation`);
      check(await page.locator('#menu').evaluate(el=>document.activeElement===el),`${kind} ${width}: Escape did not return focus to Menu`);
    }else{
      check(!metrics.menu.visible,`${kind} ${width}: desktop Menu should be hidden`);
      check(metrics.nav.visible,`${kind} ${width}: desktop navigation should be visible`);
    }

    if(width===390){
      await page.locator('#menu').click();
      await page.locator('.mbm-nav-more>summary').click();
      check(await page.locator('.mbm-nav-more').evaluate(el=>el.open),`${kind}: More disclosure did not open`);
      await page.locator('.mbm-theme-menu>summary').click();
      check(!(await page.locator('.mbm-nav-more').evaluate(el=>el.open)),`${kind}: opening Display did not close More`);
      check(await page.locator('.mbm-theme-menu').evaluate(el=>el.open),`${kind}: Display disclosure did not open`);
      await page.locator('.mbm-sw[data-t="pink"]').click();
      check(await page.evaluate(()=>document.documentElement.getAttribute('data-theme')==='pink'&&document.body.getAttribute('data-theme')==='pink'),`${kind}: pink reading background was not applied`);
      check(await page.evaluate(()=>localStorage.getItem('mbm_reading_theme')==='pink'),`${kind}: shared reading-theme key was not persisted`);
      await page.reload({waitUntil:'networkidle'});
      check(await page.evaluate(()=>document.documentElement.getAttribute('data-theme')==='pink'),`${kind}: reading background did not survive reload`);
      await page.evaluate(()=>localStorage.setItem('mbm_reading_theme','cream'));
    }

    if(width===430){
      if(kind==='lessons'){
        await page.locator('#search').fill('bonding');
        await page.waitForTimeout(120);
        check((await page.locator('#status').innerText()).includes('Showing'),`lessons: filtered result announcement missing`);
        await page.locator('[data-clear-filters]').click();
        check((await page.locator('#search').inputValue())==='',`lessons: clear filters did not reset search`);
      }else{
        check(metrics.leadCount==='Thirty-one',`apps: manifest-derived lead count was '${metrics.leadCount}'`);
        await page.locator('.seg[data-aud="t"]').click();
        check((await page.locator('#status').innerText()).includes('Showing'),`apps: filtered result announcement missing`);
        await page.locator('[data-clear-filters]').click();
        check(await page.locator('.seg[data-aud=""]').getAttribute('aria-pressed')==='true',`apps: clear filters did not restore All audience`);
      }
    }

    await page.screenshot({path:path.join(outDir,`${kind}-${width}.png`),fullPage:true});
    results.widths.push({width,...metrics,pageErrors,consoleErrors,failed});
    await context.close();
  }

  const reduced=await browser.newContext({viewport:{width:430,height:900},reducedMotion:'reduce'});
  const rp=await reduced.newPage();
  await rp.goto(base,{waitUntil:'networkidle'});
  await rp.waitForFunction(()=>document.body.classList.contains('mbm-platform'));
  const hidden=await rp.locator('.mbm-reveal').evaluateAll(els=>els.filter(el=>getComputedStyle(el).opacity==='0').length);
  check(hidden===0,`${kind}: reduced-motion mode left ${hidden} revealed sections hidden`);
  await reduced.close();

  const samples=kind==='lessons'?
    ['Build/Slideshows/BUILD_HUM_W1_Human_Timeline.html','Grow/Slideshows/GROW_HUM_W1_Time_Detectives.html','Launch/Slideshows/LAUNCH_HUM_W1_Source_Investigation.html','chemistry/Lesson1_Indicators-1.html']:
    ['Animation_Studio.html','Data_Manager_Studio.html','Regulation_Station.html','Whiteboard.html'];
  for(const rel of samples){
    const context=await browser.newContext({viewport:{width:390,height:844}});
    const page=await context.newPage();
    const pageErrors=[];const consoleErrors=[];const failed=[];
    page.on('pageerror',err=>pageErrors.push(String(err)));
    page.on('console',msg=>{if(msg.type()==='error')consoleErrors.push(msg.text())});
    page.on('requestfailed',req=>{if(sameOrigin(req.url()))failed.push({url:req.url(),failure:req.failure()})});
    const response=await page.goto(new URL(rel,base).href,{waitUntil:'domcontentloaded',timeout:60000});
    await page.waitForTimeout(350);
    const observation=await page.evaluate(()=>({title:document.title,bodyText:(document.body?.innerText||'').trim().slice(0,160),interactive:document.querySelectorAll('button,a,input,select,textarea,canvas,[tabindex]').length}));
    check(response&&response.ok(),`${kind} standalone ${rel}: HTTP response failed`);
    check(observation.bodyText.length>0,`${kind} standalone ${rel}: empty body`);
    check(observation.interactive>0,`${kind} standalone ${rel}: no interactive or navigation surface found`);
    check(pageErrors.length===0,`${kind} standalone ${rel}: page errors ${pageErrors.join(' | ')}`);
    check(consoleErrors.length===0,`${kind} standalone ${rel}: console errors ${consoleErrors.join(' | ')}`);
    check(failed.length===0,`${kind} standalone ${rel}: failed first-party requests ${JSON.stringify(failed)}`);
    results.standalone.push({path:rel,status:response?.status()||0,...observation,pageErrors,consoleErrors,failed});
    await context.close();
  }
} finally {
  await browser.close();
}

fs.writeFileSync(path.join(outDir,'browser-results.json'),JSON.stringify(results,null,2)+'\n');
if(results.errors.length){
  for(const error of results.errors)console.error('[FAIL]',error);
  process.exit(1);
}
console.log(`[PASS] ${kind} browser matrix: ${widths.length} widths, ${results.standalone.length} unchanged standalone samples`);
