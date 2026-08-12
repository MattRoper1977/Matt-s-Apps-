/* GENERATED from madebymatt.github.io/theme.js — edit there, run tools/sync_theme.py. Hand edits will be reverted. */
/* Made by Matt — shared reading-theme engine.
   Applies the stored reading background (mbm_reading_theme) and injects the
   swatch control into whatever nav/header the host page provides.
   Defensive by design: any failure leaves the page exactly as it was. */
(function(){
if(window.__mbmTheme)return; window.__mbmTheme=1;
try{
var K='mbm_reading_theme';
var NAME={cream:'Warm',pink:'Pink',blue:'Blue',light:'Light',dark:'Dark',highlumen:'High lumen'};
/* High lumen is pure white, and so is Light's swatch. The two are told apart
   by the ring the swatch already draws around every dot, plus the label and
   the title - not by the fill, which cannot distinguish them. */
var DOT={cream:'#F6F1E4',pink:'#F4C9D4',blue:'#BFD6EE',light:'#FFFFFF',dark:'#161D3D',highlumen:'#FFFFFF'};
var ORDER=['cream','pink','blue','light','dark','highlumen'];
var cur='cream';
try{cur=localStorage.getItem(K)||'cream'}catch(e){}
if(!NAME[cur])cur='cream';

function setAttr(t){
  var els=[document.documentElement,document.body],i;
  for(i=0;i<els.length;i++){
    if(!els[i])continue;
    if(t==='cream')els[i].removeAttribute('data-theme');
    else els[i].setAttribute('data-theme',t);
  }
}

function boot(){
  var st=document.createElement('style');
  st.id='mbmSwStyles';
  st.textContent='.mbm-sw-wrap{display:flex;align-items:center;gap:.1rem;flex-wrap:wrap}'
  +'.mbm-swl{display:none;width:100%;margin:.5rem 0 .1rem;font-size:.7rem;font-weight:800;letter-spacing:.16em;text-transform:uppercase}'
  +'.mbm-sw-wrap.on-dark .mbm-swl{color:#C9D1E2}'
  +'.mbm-sw-wrap.on-light .mbm-swl{color:#47506B}'
  +'.mbm-sw{display:inline-flex;align-items:center;justify-content:center;width:44px;height:44px;padding:0;background:transparent;border:0;border-radius:50%;cursor:pointer}'
  +'.mbm-sw i{display:block;width:18px;height:18px;border-radius:50%;border:1.5px solid #FFFFFF66;box-shadow:0 0 0 1.5px #16204055;transition:transform .15s ease}'
  +'.mbm-sw:hover i{transform:scale(1.2);border-color:#FFF}'
  +'.mbm-sw[aria-pressed="true"] i{border-color:#FFF;box-shadow:0 0 0 3px #F2A24A,0 0 0 4.5px #16204055}'
  +'.mbm-sw:focus-visible{outline:3px solid #F2A24A;outline-offset:2px}'
  +'@media(max-width:680px){.mbm-swl{display:block}.mbm-sw-wrap{width:100%;gap:.35rem;margin-top:.5rem;padding-top:.2rem;border-top:1px solid transparent}'
  +'.mbm-sw-wrap.on-dark{border-top-color:#B9E6CD2C}.mbm-sw-wrap.on-light{border-top-color:#16204022}}'
  +'@media(prefers-reduced-motion:reduce){.mbm-sw i{transition:none}.mbm-sw:hover i{transform:none}}'
  +'@media print{.mbm-sw-wrap{display:none!important}}';
  document.head.appendChild(st);

  var mount=document.querySelector('[data-mbm-theme-slot]')
        ||document.querySelector('nav#nav')
        ||document.querySelector('nav.xnav')
        ||document.querySelector('header nav')
        ||document.querySelector('nav')
        ||document.querySelector('header .bar')
        ||document.querySelector('header');
  if(!mount)return;

  // A link inside the same bar is legible against that bar by definition, so
  // borrow its colour rather than guessing the background. Falls back to a
  // luminance walk, then to on-dark (every mount but primary's is navy).
  function linkColour(el){
    var a=el.querySelector('a');
    if(!a)return '';
    var c='';try{c=getComputedStyle(a).color||''}catch(e){}
    return /rgba?\(/.test(c)&&!/rgba\([^)]*,\s*0\s*\)/.test(c)?c:'';
  }
  function groundIsDark(el){
    var n=el;
    while(n&&n.nodeType===1){
      var bg='';
      try{bg=getComputedStyle(n).backgroundColor||''}catch(e){}
      var m=bg.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*([\d.]+))?\)/);
      if(m&&(m[4]===undefined||parseFloat(m[4])>0.2)){
        return (0.2126*+m[1]+0.7152*+m[2]+0.0722*+m[3])/255 < 0.5;
      }
      n=n.parentNode;
    }
    return true;
  }
  var wrap=document.createElement('div');
  wrap.className='mbm-sw-wrap '+(groundIsDark(mount)?'on-dark':'on-light');
  wrap.setAttribute('role','group');
  wrap.setAttribute('aria-label','Reading background');
  var lab=document.createElement('span');
  lab.className='mbm-swl'; lab.textContent='Reading background';
  var lc=linkColour(mount);
  if(lc){lab.style.color=lc;lab.style.opacity='.8';}
  wrap.appendChild(lab);

  var btns=[];
  function apply(t,save){
    cur=t; setAttr(t);
    for(var i=0;i<btns.length;i++){
      btns[i].setAttribute('aria-pressed',btns[i].getAttribute('data-t')===t?'true':'false');
    }
    if(save){try{localStorage.setItem(K,t)}catch(e){}}
  }
  for(var i=0;i<ORDER.length;i++){
    (function(t){
      var b=document.createElement('button');
      b.type='button'; b.className='mbm-sw';
      b.setAttribute('data-t',t);
      b.setAttribute('aria-pressed',t===cur?'true':'false');
      b.title=NAME[t];
      b.setAttribute('aria-label',NAME[t]+' reading background');
      var dot=document.createElement('i');
      dot.style.background=DOT[t];
      if(t==='dark')dot.style.borderColor='#B9E6CD99';
      /* A white dot on a white mount is invisible without this; the shared
         rule's translucent border is not enough at maximum brightness. */
      if(t==='highlumen'){dot.style.borderColor='#FFFFFF';dot.style.boxShadow='0 0 0 2px #0B1020';}
      b.appendChild(dot);
      b.addEventListener('click',function(){apply(t,true)});
      wrap.appendChild(b); btns.push(b);
    })(ORDER[i]);
  }
  mount.appendChild(wrap);
  window.__mbmApplyTheme=apply;
  apply(cur,false);
}

setAttr(cur);
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);
else boot();
}catch(e){}
})();
