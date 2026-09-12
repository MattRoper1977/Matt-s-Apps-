/** SW2-T5R1: token inertness on the actual source mount or deployed project.
 * Compare every computed property (except custom-property definitions), geometry
 * and both pseudo-elements on the SAME loaded DOM. An emptied/disabled token
 * stylesheet is the baseline; no element is omitted because of load timing.
 * Every case plants a visible colour change, requires the comparator to fail,
 * removes it and requires the restored page to pass. No production bytes mutate.
 */
const fs=require('fs'),path=require('path'),crypto=require('crypto');
const {chromium}=require('playwright');
const ROOT=path.resolve(__dirname,'../..');
const KIND=fs.existsSync(path.join(ROOT,'resources.json'))?'lessons':'apps';
const TOKEN='01fbb17686866b97e7591781e4a78f2e9d38fb5ba35ed8acf935ce2a199643dd';
const arg=(name,fallback)=>{let i=process.argv.indexOf(name);return i<0?fallback:process.argv[i+1];};
const BASE=arg('--base',process.env.MBM_BASE_URL);
if(!BASE)throw Error('--base must name the project mount or deployed project URL');
const OUT=arg('--output','audit-output/sw2-token-inertness.json');
const routes=KIND==='lessons'?['','subject.html','subject.html?subject=science']:[''];
async function settle(page){await page.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))));await page.waitForTimeout(350);}
async function snap(page){return page.evaluate(()=>Array.from(document.querySelectorAll('*')).filter(e=>e.tagName!=='STYLE').map(e=>{let vals=[];for(const pseudo of [null,'::before','::after']){let s=getComputedStyle(e,pseudo);vals.push(Array.from(s).filter(p=>!p.startsWith('--')).map(p=>[p,s.getPropertyValue(p)]));}let r=e.getBoundingClientRect();return {tag:e.tagName,id:e.id,styles:vals,rect:[r.x,r.y,r.width,r.height]};}));}
function diffs(a,b){if(a.length!==b.length)throw Error('DOM changed during measurement');let d=[];for(let i=0;i<a.length;i++)if(JSON.stringify(a[i])!==JSON.stringify(b[i]))d.push({index:i,tag:a[i].tag,id:a[i].id});return d;}
(async()=>{const browser=await chromium.launch();let rows=[];try{
for(const route of routes)for(const width of [390,1440])for(const mode of ['light','dark','preferences']){
const ctx=await browser.newContext({viewport:{width,height:900},colorScheme:mode==='dark'?'dark':'light',reducedMotion:mode==='preferences'?'reduce':'no-preference',contrast:mode==='preferences'?'more':'no-preference'});const p=await ctx.newPage();let tokenResponse,errors=[];p.on('pageerror',e=>errors.push(String(e)));p.on('response',r=>{if(new URL(r.url()).pathname.endsWith('/assets/mbm-tokens.css'))tokenResponse=r;});
await p.goto(new URL(route,BASE.endsWith('/')?BASE:BASE+'/').href,{waitUntil:'networkidle'});await p.evaluate(()=>document.fonts.ready);await settle(p);
if(!tokenResponse||tokenResponse.status()!==200)throw Error('Token did not load '+route);if(crypto.createHash('sha256').update(await tokenResponse.body()).digest('hex')!==TOKEN)throw Error('Wrong token bytes');
const count=await p.locator('link[href$="assets/mbm-tokens.css"]').count();if(count!==1)throw Error('Expected one token link');
await p.evaluate(mode=>{document.documentElement.setAttribute('data-theme',mode==='dark'?'dark':'light');},mode);await settle(p);
const setEnabled=async yes=>{await p.evaluate(yes=>{document.querySelector('link[href$="assets/mbm-tokens.css"]').sheet.disabled=!yes;},yes);await settle(p);};
await setEnabled(false);const baseline=await snap(p);await setEnabled(true);const enabled=await snap(p);const delta=diffs(baseline,enabled);if(delta.length)throw Error('Token inertness failed '+JSON.stringify({route,width,mode,delta:delta.slice(0,5)}));
const defect=await p.addStyleTag({content:'h1 { color: rgb(255, 0, 255) !important; }'});await settle(p);const broken=await snap(p);let red=diffs(enabled,broken);if(!red.length)throw Error('Visible defect missed');await defect.evaluate(e=>e.remove());await settle(p);const restored=await snap(p);if(diffs(enabled,restored).length)throw Error('Restored failed');
rows.push({kind:KIND,route,width,mode,elements:enabled.length,pseudos:3,properties:'all non-custom computed properties plus geometry',inertness:'PASS',plantedVisibleDefect:'FAIL',changedElements:red.length,restored:'PASS',pageErrors:errors});console.log(JSON.stringify(rows.at(-1)));await ctx.close();
}
fs.mkdirSync(path.dirname(OUT),{recursive:true});fs.writeFileSync(OUT,JSON.stringify({status:'PASS',base:BASE,token:TOKEN,rows},null,2)+'\n');
}finally{await browser.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
