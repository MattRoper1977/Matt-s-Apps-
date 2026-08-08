/* mbm-site-professional-design-upgrade-2026-08-07
   Progressive platform navigation and interaction layer. No content depends on
   this file: if it fails, native links, details and page content remain usable. */
(function(){
  'use strict';
  if(window.__mbmPlatform)return;
  window.__mbmPlatform=1;

  var doc=document;
  var root=doc.documentElement;
  var reduce=window.matchMedia&&window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function each(list,fn){Array.prototype.forEach.call(list||[],fn);}
  function pathOf(value){
    try{
      var u=new URL(value,location.href);
      if(u.origin!==location.origin)return '';
      var p=u.pathname.replace(/\/index\.html$/i,'/').replace(/\/{2,}/g,'/');
      return p.length>1?p.replace(/\/$/,''):p;
    }catch(e){return '';}
  }

  function setPageClass(){
    var p=location.pathname.toLowerCase();
    var name=p==='/'||/\/index\.html$/.test(p)?'home':(p.split('/').filter(Boolean)[0]||'home').replace(/[^a-z0-9-]/g,'-');
    doc.body.classList.add('mbm-platform','mbm-page-'+name);
  }

  function closeDetails(header,except){
    each(header.querySelectorAll('details[open]'),function(d){if(d!==except)d.removeAttribute('open');});
  }

  function initHeader(header){
    if(header.getAttribute('data-mbm-ready')==='1')return;
    header.setAttribute('data-mbm-ready','1');
    header.classList.add('mbm-site-header');

    var nav=header.querySelector('nav');
    if(!nav)return;
    nav.classList.add('mbm-site-nav');
    if(!nav.id)nav.id='mbmSiteNav';

    var menu=header.querySelector('.menu');
    if(!menu){
      menu=doc.createElement('button');
      menu.type='button';
      menu.className='menu';
      menu.textContent='Menu';
      var brand=header.querySelector('.brand');
      if(brand&&brand.parentNode)brand.parentNode.insertBefore(menu,nav);
      else header.insertBefore(menu,nav);
    }else{
      /* Legacy pages bind their own click handlers. Replacing the node removes
         those handlers so one click always means one state change. */
      var clean=menu.cloneNode(true);
      menu.parentNode.replaceChild(clean,menu);
      menu=clean;
    }
    menu.setAttribute('aria-controls',nav.id);
    menu.setAttribute('aria-expanded','false');

    var isOpen=false;
    function setOpen(open,returnFocus){
      isOpen=!!open;
      nav.classList.toggle('open',isOpen);
      menu.setAttribute('aria-expanded',isOpen?'true':'false');
      doc.body.classList.toggle('mbm-nav-open',isOpen&&window.innerWidth<=900);
      if(!isOpen){closeDetails(header);if(returnFocus)try{menu.focus();}catch(e){}}
    }
    menu.addEventListener('click',function(){setOpen(!isOpen,false);});
    nav.addEventListener('click',function(e){
      var a=e.target&&e.target.closest?e.target.closest('a'):null;
      if(a&&window.innerWidth<=900)setOpen(false,false);
    });
    doc.addEventListener('keydown',function(e){if(e.key==='Escape'&&(isOpen||header.querySelector('details[open]')))setOpen(false,true);});
    doc.addEventListener('pointerdown',function(e){
      if(!header.contains(e.target)){if(isOpen)setOpen(false,false);else closeDetails(header);}
    },{passive:true});
    each(header.querySelectorAll('details'),function(d){
      d.addEventListener('toggle',function(){if(d.open)closeDetails(header,d);});
    });
    window.addEventListener('resize',function(){if(window.innerWidth>900&&isOpen)setOpen(false,false);},{passive:true});

    var here=pathOf(location.href);
    each(nav.querySelectorAll('a[href]'),function(a){
      if(a.hasAttribute('aria-current'))return;
      var p=pathOf(a.href);
      if(p&&p===here)a.setAttribute('aria-current','page');
    });

    function sizeHeader(){root.style.setProperty('--mbm-header-height',Math.ceil(header.getBoundingClientRect().height)+'px');}
    sizeHeader();
    window.addEventListener('resize',sizeHeader,{passive:true});
    if('ResizeObserver' in window)new ResizeObserver(sizeHeader).observe(header);

    function reflectScroll(){header.classList.toggle('is-scrolled',window.scrollY>12);}
    reflectScroll();
    window.addEventListener('scroll',reflectScroll,{passive:true});
  }

  function initRails(){
    each(doc.querySelectorAll('.rail,.dx-chips,.rx-chiprow'),function(rail){
      if(rail.scrollWidth<=rail.clientWidth+4)return;
      if(!rail.hasAttribute('tabindex'))rail.tabIndex=0;
      rail.addEventListener('keydown',function(e){
        if(e.key!=='ArrowLeft'&&e.key!=='ArrowRight')return;
        e.preventDefault();
        var amount=Math.max(180,Math.round(rail.clientWidth*.72));
        rail.scrollBy({left:e.key==='ArrowRight'?amount:-amount,behavior:reduce?'auto':'smooth'});
      });
    });
  }

  function initReveals(){
    var els=doc.querySelectorAll('main>section:not(:first-child),main+.frommatt,.dx-contact');
    if(reduce||!('IntersectionObserver' in window)){
      each(els,function(el){el.classList.add('mbm-reveal','is-visible');});
      return;
    }
    root.classList.add('mbm-platform-ready');
    var io=new IntersectionObserver(function(entries){
      each(entries,function(entry){if(entry.isIntersecting){entry.target.classList.add('is-visible');io.unobserve(entry.target);}});
    },{rootMargin:'0px 0px -7% 0px',threshold:.04});
    each(els,function(el){el.classList.add('mbm-reveal');io.observe(el);});
  }

  function initBackToTop(){
    if(doc.documentElement.scrollHeight<window.innerHeight*2.2)return;
    var b=doc.createElement('button');
    b.type='button';b.className='mbm-backtop';b.textContent='↑';b.setAttribute('aria-label','Back to top');
    doc.body.appendChild(b);
    function reflect(){b.classList.toggle('is-visible',window.scrollY>Math.max(720,window.innerHeight*.85));}
    b.addEventListener('click',function(){window.scrollTo({top:0,behavior:reduce?'auto':'smooth'});});
    reflect();window.addEventListener('scroll',reflect,{passive:true});
  }

  function init(){
    if(!doc.body)return;
    setPageClass();
    each(doc.querySelectorAll('header.header'),initHeader);
    initRails();
    initReveals();
    initBackToTop();
  }

  if(doc.readyState==='loading')doc.addEventListener('DOMContentLoaded',init,{once:true});
  else init();
})();
