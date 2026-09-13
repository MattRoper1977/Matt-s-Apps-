/** SW2 Part T: token loading and authored-body inertness on source or publication.
 * Compare every computed property (except custom-property definitions), geometry
 * and both pseudo-elements on the SAME loaded DOM. An emptied/disabled token
 * stylesheet is the baseline; no element is omitted because of load timing.
 * Published shared navigation and signoff now intentionally consume tokens; only
 * those exact marked components are excluded from the body-inertness comparison.
 * The source comparison still covers every element. Publication chrome has its
 * own 31-surface token, contrast, keyboard and mutation checks in the Site gate.
 * Every case plants a visible body colour change, requires the comparator to fail,
 * removes it and requires the restored page to pass. No production bytes mutate.
 */
const fs=require('fs'),path=require('path'),crypto=require('crypto');
const {chromium}=require('playwright');
const ROOT=path.resolve(__dirname,'../..');
const KIND=fs.existsSync(path.join(ROOT,'resources.json'))?'lessons':'apps';
const TOKEN='2e78ad7348ee7beaafda1f33ff5b112e7fd121654d7a9d39fc1ec681dee00019';
const arg=(name,fallback)=>{let i=process.argv.indexOf(name);return i<0?fallback:process.argv[i+1];};
const BASE=arg('--base',process.env.MBM_BASE_URL);
if(!BASE)throw Error('--base must name the project mount or deployed project URL');
const OUT=arg('--output','audit-output/sw2-token-inertness.json');
// Actual unchanged pinned-builder output measurements, not raw-source digests.
const PUBLISHED={"apps":{"":"0dee121f685c7fe7e61d95870da1ce9d12c3968bd3a6920ecacc0b2a0d175b19"},"lessons":{"":"5da2c06375c9a088b01a94facb82f9b7c69c388adf01745b917cc34efc8c089c","subject.html":"45a79c3fe7f709df105c87959d12ab79d9a883cdc8947ff35b1de6c7617ad141"}};
const published=process.argv.includes('--published');
const routes=KIND==='lessons'?['','subject.html','subject.html?subject=science']:[''];
async function waitForPublished(){
  if(!published)return;
  const wanted={...PUBLISHED[KIND],'/assets/mbm-tokens.css':TOKEN};
  let last=[];
  for(let attempt=0;attempt<60;attempt++){
    last=[];
    for(const [route,digest] of Object.entries(wanted)){
      try{
        const url=new URL(route,BASE.endsWith('/')?BASE:BASE+'/');
        url.searchParams.set('sw2-proof',Date.now()+'-'+attempt);
        const response=await fetch(url,{headers:{'Cache-Control':'no-cache, no-store','Pragma':'no-cache'},signal:AbortSignal.timeout(10000)});
        const actual=crypto.createHash('sha256').update(Buffer.from(await response.arrayBuffer())).digest('hex');
        if(response.status!==200||actual!==digest)last.push({route,status:response.status,actual});
      }catch(error){last.push({route,error:String(error)});}
    }
    if(!last.length){console.log('Exact published HTML and token bytes are ready');return;}
    if(attempt<59)await new Promise(resolve=>setTimeout(resolve,5000));
  }
  throw Error('Expected admitted publication did not become ready: '+JSON.stringify(last));
}

async function settle(page){await page.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))));await page.waitForTimeout(350);}
// Fingerprint every observed style value before transport; retain all elements, pseudos and geometry.
// Independent full-observation transport comparison verifies the same SHA-256 values.
async function snap(page){return page.evaluate(async published=>Promise.all(Array.from(document.querySelectorAll('*')).filter(e=>e.tagName!=='STYLE'&&(!published||!e.closest('[data-mbm-navigation="education"],[data-mbm-chrome="signoff"]'))).map(async e=>{let vals=[];for(const pseudo of [null,'::before','::after']){let s=getComputedStyle(e,pseudo);vals.push(Array.from(s).filter(p=>!p.startsWith('--')).map(p=>[p,s.getPropertyValue(p)]));}let r=e.getBoundingClientRect();const record={tag:e.tagName,id:e.id,styles:vals,rect:[r.x,r.y,r.width,r.height]};const bytes=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(JSON.stringify(record.styles)));record.styles=Array.from(new Uint8Array(bytes),b=>b.toString(16).padStart(2,'0')).join('');return record;})),published);}
function diffs(a,b){if(a.length!==b.length)throw Error('DOM changed during measurement');let d=[];for(let i=0;i<a.length;i++)if(JSON.stringify(a[i])!==JSON.stringify(b[i]))d.push({index:i,tag:a[i].tag,id:a[i].id});return d;}
(async()=>{await waitForPublished();const browser=await chromium.launch();let rows=[];try{
for(const route of routes)for(const width of [390,1440])for(const mode of ['light','dark','preferences']){
const ctx=await browser.newContext({extraHTTPHeaders:{'Cache-Control':'no-cache, no-store','Pragma':'no-cache'},viewport:{width,height:900},colorScheme:mode==='dark'?'dark':'light',reducedMotion:mode==='preferences'?'reduce':'no-preference',contrast:mode==='preferences'?'more':'no-preference'});const p=await ctx.newPage();let tokenResponse,errors=[];p.on('pageerror',e=>errors.push(String(e)));p.on('response',r=>{if(new URL(r.url()).pathname.endsWith('/assets/mbm-tokens.css'))tokenResponse=r;});
const response=await p.goto(new URL(route,BASE.endsWith('/')?BASE:BASE+'/').href,{waitUntil:'networkidle'});
if(published){const expected=PUBLISHED[KIND][route.split('?')[0]];if(!expected||response.status()!==200||crypto.createHash('sha256').update(await response.body()).digest('hex')!==expected)throw Error('Published HTML differs from admitted builder output: '+route);}await p.evaluate(()=>document.fonts.ready);await settle(p);
if(!tokenResponse||tokenResponse.status()!==200)throw Error('Token did not load '+route);if(crypto.createHash('sha256').update(await tokenResponse.body()).digest('hex')!==TOKEN)throw Error('Wrong token bytes');
const count=await p.locator('link[href$="assets/mbm-tokens.css"]').count();if(count!==1)throw Error('Expected one token link');
if(await p.locator('link[href$="assets/mbm-tokens.css"]').getAttribute('href')!=='/assets/mbm-tokens.css')throw Error('Expected origin-root token URL');
await p.evaluate(mode=>{document.documentElement.setAttribute('data-theme',mode==='dark'?'dark':'light');},mode);await settle(p);
const setEnabled=async yes=>{await p.evaluate(yes=>{document.querySelector('link[href$="assets/mbm-tokens.css"]').sheet.disabled=!yes;},yes);await settle(p);};
await setEnabled(false);const baseline=await snap(p);await setEnabled(true);const enabled=await snap(p);const delta=diffs(baseline,enabled);if(delta.length)throw Error('Token inertness failed '+JSON.stringify({route,width,mode,delta:delta.slice(0,5)}));
const defect=await p.addStyleTag({content:'h1 { color: rgb(255, 0, 255) !important; }'});await settle(p);const broken=await snap(p);let red=diffs(enabled,broken);if(!red.length)throw Error('Visible defect missed');await defect.evaluate(e=>e.remove());await settle(p);const restored=await snap(p);if(diffs(enabled,restored).length)throw Error('Restored failed');
rows.push({kind:KIND,route,width,mode,elements:enabled.length,pseudos:3,properties:'all non-custom computed properties plus geometry',scope:published?'authored body outside explicitly marked shared navigation/signoff':'every source element',inertness:'PASS',plantedVisibleDefect:'FAIL',changedElements:red.length,restored:'PASS',pageErrors:errors});console.log(JSON.stringify(rows.at(-1)));await ctx.close();
}
fs.mkdirSync(path.dirname(OUT),{recursive:true});fs.writeFileSync(OUT,JSON.stringify({status:'PASS',base:BASE,publishedBytesChecked:published,token:TOKEN,rows},null,2)+'\n');
}finally{await browser.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
