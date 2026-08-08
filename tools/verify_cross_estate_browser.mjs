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
const results={
  sentinel:'mbm-cross-estate-unification-lessons-apps-2026-08-08',
  kind,base,widths:[],standalone:[],reducedMotion:null,errors:[],fatal:null,
};

function check(condition,message){if(!condition)results.errors.push(message)}
function sameOrigin(url){try{return new URL(url).origin===new URL(base).origin}catch{return false}}
function errorText(error){return error?.stack||error?.message||String(error)}

const browser=await chromium.launch({headless:true});
try{
  for(const width of widths){
    const context=await browser.newContext({viewport:{width,height:900},deviceScaleFactor:1});
    const page=await context.newPage();
    page.setDefaultTimeout(10000);
    const pageErrors=[];const consoleErrors=[];const failed=[];const badResponses=[];
    page.on('pageerror',error=>pageErrors.push(String(error)));
    page.on('console',message=>{if(message.type()==='error')consoleErrors.push(message.text())});
    page.on('requestfailed',request=>{if(sameOrigin(request.url()))failed.push({url:request.url(),failure:request.failure()})});
    page.on('response',response=>{if(sameOrigin(response.url())&&!response.ok())badResponses.push({url:response.url(),status:response.status()})});
    const record={width,pageErrors,consoleErrors,failed,badResponses};
    results.widths.push(record);
    try{
      const response=await page.goto(base,{waitUntil:'domcontentloaded',timeout:60000});
      record.httpStatus=response?.status()||0;
      check(response&&response.ok(),`${kind} ${width}: hub HTTP response was not successful (${record.httpStatus})`);
      await page.waitForTimeout(1200);
      const metrics=await page.evaluate((kind)=>{
        const q=selector=>document.querySelector(selector);
        const box=element=>{
          if(!element)return {width:0,height:0,visible:false,missing:true};
          const rect=element.getBoundingClientRect();
          return {width:rect.width,height:rect.height,visible:!!(rect.width&&rect.height),missing:false};
        };
        return {
          title:document.title,
          count:q('#count')?.textContent?.trim()||'',
          leadCount:q('#leadCount')?.textContent?.trim()||'',
          cards:document.querySelectorAll('.card').length,
          overflow:document.documentElement.scrollWidth-document.documentElement.clientWidth,
          active:[...document.querySelectorAll('.mbm-primary-links a[aria-current="page"]')].map(anchor=>anchor.getAttribute('href')),
          menu:box(q('#menu')),
          nav:box(q('#nav')),
          themeButtons:document.querySelectorAll('[data-mbm-theme-slot] .mbm-sw').length,
          bodyClass:document.body.className,
          readyState:document.readyState,
          kind,
        };
      },kind);
      Object.assign(record,metrics);
      check(!/^Loading/.test(metrics.count),`${kind} ${width}: catalogue remained in its loading state`);
      check(!/^Couldn't load/.test(metrics.count),`${kind} ${width}: catalogue reported '${metrics.count}'`);
      check(metrics.overflow<=1,`${kind} ${width}: horizontal page overflow ${metrics.overflow}px`);
      check(metrics.cards>0,`${kind} ${width}: no catalogue cards rendered`);
      check(metrics.active.length===1&&metrics.active[0]===(kind==='lessons'?'/Lessons/':'/Matt-s-Apps-/'),`${kind} ${width}: incorrect active navigation ${JSON.stringify(metrics.active)}`);
      check(pageErrors.length===0,`${kind} ${width}: page errors ${pageErrors.join(' | ')}`);
      check(consoleErrors.length===0,`${kind} ${width}: console errors ${consoleErrors.join(' | ')}`);
      check(failed.length===0,`${kind} ${width}: failed first-party requests ${JSON.stringify(failed)}`);
      check(badResponses.length===0,`${kind} ${width}: non-success first-party responses ${JSON.stringify(badResponses)}`);

      if(width<=900){
        check(metrics.menu.visible&&metrics.menu.width>=44&&metrics.menu.height>=44,`${kind} ${width}: mobile menu target below 44px`);
        check(!metrics.nav.visible,`${kind} ${width}: mobile navigation should begin closed`);
        if(!metrics.menu.missing){
          await page.locator('#menu').click();
          check(await page.locator('#nav').isVisible(),`${kind} ${width}: menu did not open`);
          check(await page.locator('body').evaluate(element=>element.classList.contains('mbm-nav-open')),`${kind} ${width}: scroll lock class missing`);
          const targets=await page.locator('#nav a:visible, #nav summary:visible').evaluateAll(elements=>elements.map(element=>{const rect=element.getBoundingClientRect();return {text:element.textContent.trim(),w:rect.width,h:rect.height}}));
          for(const target of targets)check(target.h>=44,`${kind} ${width}: navigation target '${target.text}' is ${target.h}px tall`);
          await page.keyboard.press('Escape');
          check(!(await page.locator('#nav').isVisible()),`${kind} ${width}: Escape did not close navigation`);
          check(await page.locator('#menu').evaluate(element=>document.activeElement===element),`${kind} ${width}: Escape did not return focus to Menu`);
        }
      }else{
        check(!metrics.menu.visible,`${kind} ${width}: desktop Menu should be hidden`);
        check(metrics.nav.visible,`${kind} ${width}: desktop navigation should be visible`);
      }

      if(width===390&&metrics.themeButtons>0){
        await page.locator('#menu').click();
        await page.locator('.mbm-nav-more>summary').click();
        check(await page.locator('.mbm-nav-more').evaluate(element=>element.open),`${kind}: More disclosure did not open`);
        await page.locator('.mbm-theme-menu>summary').click();
        await page.waitForFunction(()=>!document.querySelector('.mbm-nav-more')?.open&&document.querySelector('.mbm-theme-menu')?.open);
        check(!(await page.locator('.mbm-nav-more').evaluate(element=>element.open)),`${kind}: opening Display did not close More`);
        check(await page.locator('.mbm-theme-menu').evaluate(element=>element.open),`${kind}: Display disclosure did not open`);
        await page.locator('.mbm-sw[data-t="pink"]').click();
        check(await page.evaluate(()=>document.documentElement.getAttribute('data-theme')==='pink'&&document.body.getAttribute('data-theme')==='pink'),`${kind}: pink reading background was not applied`);
        check(await page.evaluate(()=>localStorage.getItem('mbm_reading_theme')==='pink'),`${kind}: shared reading-theme key was not persisted`);
        await page.reload({waitUntil:'domcontentloaded'});
        await page.waitForTimeout(500);
        check(await page.evaluate(()=>document.documentElement.getAttribute('data-theme')==='pink'),`${kind}: reading background did not survive reload`);
        await page.evaluate(()=>localStorage.setItem('mbm_reading_theme','cream'));
      }

      if(width===430&&metrics.cards>0){
        if(kind==='lessons'){
          await page.locator('#search').fill('bonding');
          await page.waitForTimeout(150);
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
    }catch(error){
      record.harnessError=errorText(error);
      results.errors.push(`${kind} ${width}: browser harness error: ${error?.message||String(error)}`);
      try{await page.screenshot({path:path.join(outDir,`${kind}-${width}-failure.png`),fullPage:true})}catch{}
    }finally{
      await context.close();
    }
  }

  const reduced=await browser.newContext({viewport:{width:430,height:900},reducedMotion:'reduce'});
  try{
    const page=await reduced.newPage();
    const response=await page.goto(base,{waitUntil:'domcontentloaded',timeout:60000});
    await page.waitForTimeout(500);
    const hidden=await page.locator('.mbm-reveal').evaluateAll(elements=>elements.filter(element=>getComputedStyle(element).opacity==='0').length);
    results.reducedMotion={status:response?.status()||0,hidden};
    check(response&&response.ok(),`${kind}: reduced-motion hub response failed`);
    check(hidden===0,`${kind}: reduced-motion mode left ${hidden} revealed sections hidden`);
  }catch(error){
    results.reducedMotion={error:errorText(error)};
    results.errors.push(`${kind}: reduced-motion harness error: ${error?.message||String(error)}`);
  }finally{
    await reduced.close();
  }

  const samples=kind==='lessons'?
    ['Build/Slideshows/BUILD_HUM_W1_Human_Timeline.html','Grow/Slideshows/GROW_HUM_W1_Time_Detectives.html','Launch/Slideshows/LAUNCH_HUM_W1_Source_Investigation.html','chemistry/Lesson1_Indicators-1.html']:
    ['Animation_Studio.html','Data_Manager_Studio.html','Regulation_Station.html','Whiteboard.html'];
  for(const rel of samples){
    const context=await browser.newContext({viewport:{width:390,height:844}});
    const page=await context.newPage();
    page.setDefaultTimeout(10000);
    const pageErrors=[];const consoleErrors=[];const failed=[];const badResponses=[];
    page.on('pageerror',error=>pageErrors.push(String(error)));
    page.on('console',message=>{if(message.type()==='error')consoleErrors.push(message.text())});
    page.on('requestfailed',request=>{if(sameOrigin(request.url()))failed.push({url:request.url(),failure:request.failure()})});
    page.on('response',response=>{if(sameOrigin(response.url())&&!response.ok())badResponses.push({url:response.url(),status:response.status()})});
    const record={path:rel,pageErrors,consoleErrors,failed,badResponses};
    results.standalone.push(record);
    try{
      const response=await page.goto(new URL(rel,base).href,{waitUntil:'domcontentloaded',timeout:60000});
      await page.waitForTimeout(350);
      const observation=await page.evaluate(()=>({title:document.title,bodyText:(document.body?.innerText||'').trim().slice(0,160),interactive:document.querySelectorAll('button,a,input,select,textarea,canvas,[tabindex]').length}));
      Object.assign(record,{status:response?.status()||0,...observation});
      check(response&&response.ok(),`${kind} standalone ${rel}: HTTP response failed`);
      check(observation.bodyText.length>0,`${kind} standalone ${rel}: empty body`);
      check(observation.interactive>0,`${kind} standalone ${rel}: no interactive or navigation surface found`);
      check(pageErrors.length===0,`${kind} standalone ${rel}: page errors ${pageErrors.join(' | ')}`);
      check(consoleErrors.length===0,`${kind} standalone ${rel}: console errors ${consoleErrors.join(' | ')}`);
      check(failed.length===0,`${kind} standalone ${rel}: failed first-party requests ${JSON.stringify(failed)}`);
      check(badResponses.length===0,`${kind} standalone ${rel}: non-success first-party responses ${JSON.stringify(badResponses)}`);
    }catch(error){
      record.harnessError=errorText(error);
      results.errors.push(`${kind} standalone ${rel}: harness error: ${error?.message||String(error)}`);
    }finally{
      await context.close();
    }
  }
}catch(error){
  results.fatal=errorText(error);
  results.errors.push(`${kind}: browser harness fatal error: ${error?.message||String(error)}`);
}finally{
  await browser.close();
  fs.writeFileSync(path.join(outDir,'browser-results.json'),JSON.stringify(results,null,2)+'\n');
}

if(results.errors.length){
  for(const error of results.errors)console.error('[FAIL]',error);
  process.exit(1);
}
console.log(`[PASS] ${kind} browser matrix: ${widths.length} widths, ${results.standalone.length} unchanged standalone samples`);
