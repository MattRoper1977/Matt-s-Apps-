/* mbm-site-professional-design-upgrade-2026-08-07
   mbm-accounts-members-mailing-2026-08-08
   mbm-homepage-audience-routing-2026-08-09
   Progressive platform navigation and interaction layer. No public content
   depends on this file: if it fails, native links and page content remain usable. */
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
    each(header.querySelectorAll('details'),function(d){d.addEventListener('toggle',function(){if(d.open)closeDetails(header,d);});});
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

  /* Account discovery is part of the platform shell, not copied into hundreds
     of games/lessons. It always points at a real route. When Supabase is not
     configured the route explains that safely; it never creates a local
     password as a fallback. */
  /* Fail-closed, and deliberately so. This used to read !=='off', which meant
     every page in the estate got the account and mailing affordances unless it
     remembered to opt out - and exactly one page ever did. A page that forgot
     the marker got a sign-in link in front of whoever was reading it, silently,
     with nothing failing anywhere.

     The default is now the other way round. Only 'on' allows them; absent,
     misspelt, mangled by a renderer or simply forgotten all read as no. The
     cost of a mistake becomes a missing link on an adult page, which somebody
     reports, instead of a sign-in link on a child's page, which nobody sees.

     Which pages may say 'on' is declared in data/adult-surfaces.json and
     asserted against the tree by verify_adult_surfaces.py. It is not read here:
     this file must work from file:// with no fetch, and a page cannot be
     trusted to describe itself anyway - the gate is what makes the marker
     honest. Note this is the same attribute the estate already had, with its
     default inverted, not a new marker convention. */
  function adultFeaturesAllowed(){
    return !!doc.body&&doc.body.getAttribute('data-mbm-adult-features')==='on';
  }
  function accountTargets(){
    var links=[];
    if(!adultFeaturesAllowed())return links;
    each(doc.querySelectorAll('header.header nav'),function(nav){
      var existing=nav.querySelector('a[href="/account/"],a[href="https://madebymatt.uk/account/"]');
      if(existing){existing.setAttribute('data-mbm-account-nav','1');links.push(existing);return;}
      var panel=nav.querySelector('.mbm-nav-panel');
      if(!panel)return;
      var a=doc.createElement('a');a.href='/account/';a.textContent='Account';a.setAttribute('data-mbm-account-nav','1');
      var members=panel.querySelector('a[href="/members/"],a[href$="/members/"]');
      if(members)panel.insertBefore(a,members);else panel.appendChild(a);
      links.push(a);
    });
    return links;
  }
  function ensureSecondaryLink(href,text,attr){
    if(!adultFeaturesAllowed())return;
    each(doc.querySelectorAll('header.header nav .mbm-nav-panel'),function(panel){
      if(panel.querySelector('a['+attr+']'))return;
      var a=doc.createElement('a');a.href=href;a.textContent=text;a.setAttribute(attr,'1');
      var privacy=panel.querySelector('a[href="/privacy/"],a[href$="/privacy/"]');
      if(privacy)panel.insertBefore(a,privacy);else panel.appendChild(a);
    });
  }
  function removeSecondary(attr){each(doc.querySelectorAll('a['+attr+']'),function(a){if(a.parentNode)a.parentNode.removeChild(a);});}
  function ensurePlatformExtrasStyle(){
    if(doc.getElementById('mbmPlatformExtrasStyle'))return;
    var style=doc.createElement('style');style.id='mbmPlatformExtrasStyle';
    style.textContent='.mbm-mailing-cta{display:inline-flex;align-items:center;justify-content:center;min-height:44px;padding:.55rem .9rem;border-radius:999px;background:#F2A24A;color:#161D3D!important;font-size:.8rem;font-weight:850;text-decoration:none;box-shadow:0 2px 0 #C97F2E}.mbm-mailing-cta:focus-visible{outline:3px solid #F2A24A;outline-offset:3px;box-shadow:0 0 0 6px rgba(22,29,61,.7)}';
    doc.head.appendChild(style);
  }
  function reflectMailingFooter(enabled){
    if(!adultFeaturesAllowed()||doc.body.getAttribute('data-mbm-mailing-footer')==='off')enabled=false;
    each(doc.querySelectorAll('footer.footer'),function(footer){
      var existing=footer.querySelector('[data-mbm-mailing-cta]');
      if(!enabled||footer.getAttribute('data-mbm-mailing-cta')==='off'){if(existing&&existing.parentNode)existing.parentNode.removeChild(existing);return;}
      if(existing)return;
      ensurePlatformExtrasStyle();
      var a=doc.createElement('a');a.href='/mailing-list/';a.textContent='Join mailing list';a.className='mbm-mailing-cta';a.setAttribute('data-mbm-mailing-cta','1');
      var bar=footer.querySelector('.bar')||footer;bar.appendChild(a);
    });
  }
  function reflectAccountNav(s){
    each(doc.querySelectorAll('[data-mbm-account-nav]'),function(a){
      var current=a.getAttribute('aria-current')==='page';
      a.textContent=current?'Account':(s.configured?(s.user?'Account':'Log in'):'Account');
      a.setAttribute('aria-label',s.configured?(s.user?'Account settings':'Log in to Made by Matt'):'Made by Matt account');
    });
    if(s.configured&&!s.user)ensureSecondaryLink('/account/?mode=register','Create account','data-mbm-register-nav');else removeSecondary('data-mbm-register-nav');
    var mailing=s.config&&s.config.mailing;
    var mailingOn=!!(mailing&&mailing.enabled===true);
    if(mailingOn)ensureSecondaryLink('/mailing-list/','Mailing list','data-mbm-mailing-nav');else removeSecondary('data-mbm-mailing-nav');
    reflectMailingFooter(mailingOn);
  }
  function retireLegacyTeacherList(){
    /* The homepage used to post marketing opt-ins through FormSubmit. Keep the
       contact form untouched, but make the teacher-updates block point at the
       single managed mailing route instead. This also removes stale local-only
       account wording without rewriting unrelated homepage content. */
    var box=doc.querySelector('.dx-teach');
    if(!box||box.getAttribute('data-mbm-mailing-replaced')==='1')return;
    var form=box.querySelector('form.dx-tform[action^="https://formsubmit.co/"]');
    if(!form)return;
    box.setAttribute('data-mbm-mailing-replaced','1');
    var notes=box.querySelectorAll('.dx-cnote');
    if(notes[1])notes[1].innerHTML='<b>This is separate from an account.</b> Creating an account never joins the mailing list, and joining the mailing list never creates an account. Subscriptions use the dedicated Made by Matt mailing service and keep unsubscribe separate.';
    var link=doc.createElement('a');
    link.href='/mailing-list/';
    link.className='mbm-mailing-cta';
    link.setAttribute('data-mbm-home-mailing','1');
    link.textContent='Join the mailing list';
    ensurePlatformExtrasStyle();
    form.replaceWith(link);
  }

  function initAccountNav(){
    if(!adultFeaturesAllowed()){
      removeSecondary('data-mbm-account-nav');
      removeSecondary('data-mbm-register-nav');
      removeSecondary('data-mbm-mailing-nav');
      reflectMailingFooter(false);
      return;
    }
    accountTargets();
    retireLegacyTeacherList();
    function attach(){
      if(!window.MBMAccount)return false;
      window.MBMAccount.subscribe(reflectAccountNav);
      return true;
    }
    if(attach())return;
    if(doc.querySelector('script[data-mbm-account-client]'))return;
    var s=doc.createElement('script');s.src='/assets/mbm-account.js';s.defer=true;s.setAttribute('data-mbm-account-client','1');s.onload=attach;s.onerror=function(){reflectAccountNav({configured:false,user:null,config:null});};
    doc.head.appendChild(s);
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
    initAccountNav();
    initRails();
    initReveals();
    initBackToTop();
  }

  if(doc.readyState==='loading')doc.addEventListener('DOMContentLoaded',init,{once:true});
  else init();
})();
