#!/usr/bin/env node
import { chromium } from 'playwright';
import fs from 'node:fs';
import path from 'node:path';

const argv=process.argv.slice(2);
const value=(k,d='')=>{const i=argv.indexOf(k);return i>=0?argv[i+1]:d};
const baseArg=value('--base',process.env.LUNDYLOOP_BASE_URL||'');
if(!baseArg){console.error('usage: node verify_lundyloop_browser.mjs --base <Apps-base-url> [--artifacts dir]');process.exit(2)}
const base=new URL(baseArg.endsWith('/')?baseArg:`${baseArg}/`);
const artifacts=value('--artifacts',process.env.LUNDYLOOP_ARTIFACTS||'audit-output/lundyloop');
fs.mkdirSync(artifacts,{recursive:true});
const result={base:base.href,status:'PASS',checks:[],errors:[],externalRequests:[]};
const check=(name,ok,detail='')=>{result.checks.push({name,ok,detail});if(!ok)result.errors.push(`${name}: ${detail}`)};
const launchOptions={headless:true};
if(process.env.LUNDYLOOP_CHROMIUM_EXECUTABLE) launchOptions.executablePath=process.env.LUNDYLOOP_CHROMIUM_EXECUTABLE;
const browser=await chromium.launch(launchOptions);
try{
 for(const vp of [{name:'desktop',width:1440,height:900},{name:'tablet',width:768,height:1024},{name:'mobile',width:390,height:844}]){
  const ctx=await browser.newContext({viewport:{width:vp.width,height:vp.height}});const page=await ctx.newPage();const ce=[],pe=[];
  page.on('console',m=>{if(m.type()==='error')ce.push(m.text())});page.on('pageerror',e=>pe.push(String(e)));
  page.on('request',req=>{const u=new URL(req.url());if(!['data:','blob:'].includes(u.protocol)&&u.origin!==base.origin)result.externalRequests.push({surface:vp.name,url:req.url(),type:req.resourceType()})});
  let response=await page.goto(new URL('LundyLoop_Professional_OS.html',base).href,{waitUntil:'networkidle'});
  check(`${vp.name}: root flagship HTTP`,!!response&&response.ok(),response?String(response.status()):'no response');
  check(`${vp.name}: root flagship title`,(await page.title()).includes('LundyLoop Pro'),await page.title());
  check(`${vp.name}: Apps return`,await page.locator('a[href="./"]').count()>=1);
  check(`${vp.name}: suite route`,await page.locator('a[href="LundyLoop_Professional_OS/"]').count()>=1);
  let overflow=await page.evaluate(()=>document.documentElement.scrollWidth-document.documentElement.clientWidth);
  check(`${vp.name}: root no horizontal overflow`,overflow<=1,`overflow=${overflow}`);
  await page.locator('#demoTopBtn').click();const confirm=page.getByRole('button',{name:'Replace with demo'});await confirm.waitFor({state:'visible'});await confirm.click();
  await page.waitForFunction(()=>Number(document.querySelector('#navOpenCount')?.textContent||0)>0,null,{timeout:10000});
  check(`${vp.name}: demo workflow`,Number(await page.locator('#navOpenCount').textContent())>0);
  await page.locator('#shieldBtn').click();check(`${vp.name}: privacy shield`,await page.locator('#shield').evaluate(el=>getComputedStyle(el).display!=='none'));await page.locator('#unshieldBtn').click();
  await page.locator('[data-view="capture"]').click();check(`${vp.name}: pupil capture opens`,await page.locator('#view-capture').evaluate(el=>el.classList.contains('active')));
  check(`${vp.name}: console clean`,ce.length===0,ce.join(' | '));check(`${vp.name}: page errors clean`,pe.length===0,pe.join(' | '));
  await page.screenshot({path:path.join(artifacts,`${vp.name}-flagship.png`),fullPage:true});
  response=await page.goto(new URL('LundyLoop_Professional_OS/',base).href,{waitUntil:'networkidle'});
  check(`${vp.name}: suite launcher HTTP`,!!response&&response.ok(),response?String(response.status()):'no response');
  check(`${vp.name}: launcher flagship link`,await page.locator('a[href="LundyLoop_PRO_Participation_Operating_System.html"]').count()===1);
  overflow=await page.evaluate(()=>document.documentElement.scrollWidth-document.documentElement.clientWidth);check(`${vp.name}: launcher no overflow`,overflow<=1,`overflow=${overflow}`);
  await ctx.close();
 }
 const ctx=await browser.newContext({viewport:{width:768,height:1024}});const page=await ctx.newPage();
 const files=['01_LundyLoop_Pupil_Explainer_PRO.html','02_LundyLoop_Tokenism_Detective.html','03_LundyLoop_Live_Class_Board.html','04_LundyLoop_Influence_Receipt_Maker.html'];
 for(const f of files){const errors=[];const handler=e=>errors.push(String(e));page.on('pageerror',handler);const r=await page.goto(new URL(`LundyLoop_Professional_OS/pupil_tools/${f}`,base).href,{waitUntil:'networkidle'});check(`${f}: HTTP`,!!r&&r.ok(),r?String(r.status()):'no response');check(`${f}: suite return`,await page.locator('a.suite-return[href="../index.html"]').count()===1);check(`${f}: page clean`,errors.length===0,errors.join(' | '));page.off('pageerror',handler)}
 await ctx.close();
 // Hub card: present only when testing the repository root, and required for deployment acceptance.
 const hub=await browser.newPage();const ce=[];hub.on('console',m=>{if(m.type()==='error')ce.push(m.text())});
 const hr=await hub.goto(base.href,{waitUntil:'networkidle'});check('Apps hub HTTP',!!hr&&hr.ok(),hr?String(hr.status()):'no response');
 const card=hub.locator('.card',{has:hub.getByRole('heading',{name:'LundyLoop Professional OS'})});
 check('Apps card appears exactly once',await card.count()===1,`count=${await card.count()}`);
 if(await card.count()===1){check('Apps card is Teacher Admin',await card.locator('.aud-t').count()===1);const href=await card.locator('a.open').getAttribute('href');check('Apps card route',href==='LundyLoop_Professional_OS.html',String(href));}
 check('Apps hub console clean',ce.length===0,ce.join(' | '));await hub.close();
 check('no external runtime requests',result.externalRequests.length===0,JSON.stringify(result.externalRequests));
}finally{await browser.close()}
result.status=result.errors.length?'FAIL':'PASS';fs.writeFileSync(path.join(artifacts,'browser-results.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result,null,2));process.exit(result.errors.length?1:0);
