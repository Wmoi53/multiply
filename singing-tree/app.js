"use strict";
/* =====================================================================
   THE SINGING TREE — single-page interactive production
   Canvas 2D tree renderer · Web Audio SATB choir · agent crew board ·
   run-of-show cue engine · booking flow. No dependencies.
   ===================================================================== */
const $  = (s,r=document)=>r.querySelector(s);
const $$ = (s,r=document)=>Array.from(r.querySelectorAll(s));
const clamp=(v,a,b)=>v<a?a:v>b?b:v;
const lerp=(a,b,t)=>a+(b-a)*t;
const TAU=Math.PI*2;
const fmt=n=>Math.round(n).toLocaleString('en-US');
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const mmss=s=>{s=Math.max(0,Math.floor(s));return String(Math.floor(s/60)).padStart(2,'0')+':'+String(s%60).padStart(2,'0');};
const clone=o=>JSON.parse(JSON.stringify(o));
const store={
  get(k,d){try{const v=localStorage.getItem('singingtree:'+k);return v==null?d:JSON.parse(v);}catch(e){return d;}},
  set(k,v){try{localStorage.setItem('singingtree:'+k,JSON.stringify(v));}catch(e){}}
};
const REDUCED=matchMedia('(prefers-reduced-motion: reduce)').matches;
const SGT=new Intl.DateTimeFormat('en-GB',{timeZone:'Asia/Singapore',hour:'2-digit',minute:'2-digit',second:'2-digit',hourCycle:'h23'});
const sgtNow=()=>SGT.format(new Date());
function hash(str){let h=2166136261;for(let i=0;i<str.length;i++){h^=str.charCodeAt(i);h=Math.imul(h,16777619);}return (h>>>0)/4294967295;}
function download(name,data,type){
  const blob=data instanceof Blob?data:new Blob([data],{type});
  const u=URL.createObjectURL(blob);const a=document.createElement('a');
  a.href=u;a.download=name;document.body.appendChild(a);a.click();a.remove();
  setTimeout(()=>URL.revokeObjectURL(u),2000);
}
function hexA(h,a){const n=parseInt(h.slice(1),16);return `rgba(${n>>16&255},${n>>8&255},${n&255},${a})`;}

/* ============================ TOASTS & FEED ============================ */
function toast(title,body='',o={}){
  const el=document.createElement('div');el.className='toast';
  el.style.setProperty('--ac',o.ac||'var(--gold)');
  el.innerHTML=`<span class="ic">${o.icon||'✦'}</span><div class="tx"><b>${esc(title)}</b>${body?`<span>${esc(body)}</span>`:''}</div>${o.action?`<button class="undo">${esc(o.action)}</button>`:''}<i class="life"></i>`;
  const life=o.life||4200;
  el.querySelector('.life').animate([{width:'100%'},{width:'0%'}],{duration:life,easing:'linear',fill:'forwards'});
  let done=false;const close=()=>{if(done)return;done=true;el.classList.add('out');setTimeout(()=>el.remove(),330);};
  if(o.action)el.querySelector('.undo').addEventListener('click',()=>{o.onAction&&o.onAction();close();});
  const box=$('#toasts');box.appendChild(el);setTimeout(close,life);
  const live=$$('.toast:not(.out)',box);if(live.length>4)live[0].remove();
}
let feedN=0;
function log(who,msg,kind=''){
  const el=document.createElement('div');el.className='logline '+kind;
  el.innerHTML=`<time>${sgtNow()}</time><span class="who">${esc(who)}</span><span class="msg">${esc(msg)}</span>`;
  const f=$('#feed');f.prepend(el);while(f.children.length>80)f.lastChild.remove();
  feedN++;$('#feedCount').textContent=feedN+(feedN===1?' entry':' entries');
}

/* ============================ SETTINGS ============================ */
const PALETTES={
  classic:{name:'Classic',cols:['#FFC24B','#FF3B5C','#FFD98A','#4BE3A5','#5CD2FF']},
  ember:{name:'Ember',cols:['#FFA033','#FF3B5C','#FFC24B','#FF6E3A','#FFD98A']},
  glacier:{name:'Glacier',cols:['#5CD2FF','#F8EFE4','#B98CFF','#9FE8FF','#DDF6FF']},
  aurora:{name:'Aurora',cols:['#4BE3A5','#5CD2FF','#B98CFF','#FF5FD2','#9DFFCF']},
  candy:{name:'Candy cane',cols:['#FF3B5C','#F8EFE4','#FF5FD2','#FFFFFF','#FF3B5C']},
  gold:{name:'Pure gold',cols:['#FFC24B','#FFD98A','#FFA033','#FFE9B8','#FFB347']}
};
const DEFAULTS={lamps:2200,twinkle:85,bloom:100,star:70,chase:'wave',quality:'cinematic',palette:'classic',
  snow:45,wind:18,haze:40,zoom:100,drift:!REDUCED,blueprint:false,guides:false,choir:65,verb:55,
  sections:{S:true,A:true,T:true,B:true}};
let S=Object.assign(clone(DEFAULTS),store.get('settings',{}));
S.sections=Object.assign({S:true,A:true,T:true,B:true},S.sections||{});
if(!PALETTES[S.palette])S.palette='classic';
let saveT=0;
function saveSettings(){clearTimeout(saveT);saveT=setTimeout(()=>store.set('settings',S),250);}

/* ============================ AGENTS & ZONES ============================ */
const AGENTS=[
  {id:'AURORA-01',code:'AU',role:'Upper canopy lighting',ac:'#4BE3A5',home:'upper'},
  {id:'VESTA-02',code:'VE',role:'Power & redundancy',ac:'#FFA033',home:'power'},
  {id:'LUMEN-03',code:'LU',role:'Lower canopy lighting',ac:'#FFC24B',home:'lower'},
  {id:'CANTUS-04',code:'CA',role:'Choirmaster',ac:'#5CD2FF',home:'choir'},
  {id:'EMBER-05',code:'EM',role:'Topper beacon & cold sparks',ac:'#FF3B5C',home:'topper'},
  {id:'FLURRY-06',code:'FL',role:'Snow array & weather',ac:'#9FE8FF',home:'snow'},
  {id:'SENTINEL-07',code:'SE',role:'Crowd & cordon',ac:'#FF5FD2',home:'crowd'},
  {id:'HERALD-08',code:'HE',role:'Box office & comms',ac:'#B98CFF',home:'herald'}
];
const ZONES=[
  {id:'upper',name:'Upper canopy',meta:'19,200 lamps · 48 blocks · 21–40 m',crit:true},
  {id:'lower',name:'Lower canopy',meta:'19,200 lamps · 48 blocks · 2–21 m',crit:true},
  {id:'topper',name:'Topper & sparks',meta:'4.2 m star · 12 cold-spark fountains',crit:false},
  {id:'choir',name:'Choir ring',meta:'1,284 voices · 4 sections · 96 mics',crit:true},
  {id:'snow',name:'Snow array',meta:'6 foam-flake towers · wind-gated',crit:false},
  {id:'power',name:'Power grid',meta:'214 kW · 2 feeds · 40 kW shed plan',crit:true},
  {id:'crowd',name:'Plaza & cordon',meta:'≤ 1.4 persons/m² · 3 egress waves',crit:true},
  {id:'herald',name:'Box office & comms',meta:'3 shows nightly · PA & signage',crit:false}
];
const agentById=id=>AGENTS.find(a=>a.id===id);
const zoneById=id=>ZONES.find(z=>z.id===id);
const DEFAULT_ASSIGN={upper:null,lower:null,topper:'EMBER-05',choir:'CANTUS-04',snow:'FLURRY-06',power:'VESTA-02',crowd:'SENTINEL-07',herald:'HERALD-08'};
let assign=(()=>{const raw=store.get('assign',DEFAULT_ASSIGN)||DEFAULT_ASSIGN;const out={},seen=new Set();
  for(const z of ZONES){const a=raw[z.id];if(a&&agentById(a)&&!seen.has(a)){out[z.id]=a;seen.add(a);}else out[z.id]=null;}return out;})();
const zoneOf=aid=>ZONES.map(z=>z.id).find(z=>assign[z]===aid)||null;
function zf(z){const a=assign[z];if(!a)return 0;return agentById(a).home===z?1:.8;}
const ownedCount=()=>ZONES.filter(z=>assign[z.id]).length;
const readiness=()=>ownedCount()/ZONES.length;
const ZF={pw:1,up:1,lo:1,top:1,snow:1,choir:1};
function updateZF(){
  ZF.pw=assign.power?zf('power'):.45;
  ZF.up=(assign.upper?zf('upper'):.14)*ZF.pw; ZF.lo=(assign.lower?zf('lower'):.14)*ZF.pw; /* vacant canopy = standby glow */
  ZF.top=(assign.topper?zf('topper'):.12)*ZF.pw;
  ZF.snow=assign.snow?zf('snow'):0; ZF.choir=assign.choir?zf('choir'):0;
}

/* ============================ TREE GEOMETRY ============================ */
const TREE={R:.36,tiers:9};
let lamps=[],baubles=[];
let PX=new Float32Array(0),PY=PX,PK=PX,PB=PX,PZ=PX;
function conePoint(){
  const y=.04+.92*(1-Math.sqrt(Math.random()));
  const frac=((y-.04)/.92*TREE.tiers)%1;
  const r=(1-y)*TREE.R*(1-.2*frac)*(.9+.1*Math.random());
  const a=Math.random()*TAU;
  return {x:Math.cos(a)*r,y,z:Math.sin(a)*r,a};
}
function buildLamps(){
  const n=Math.round(S.lamps);lamps=new Array(n);
  for(let i=0;i<n;i++){const p=conePoint();p.c=(Math.random()*5)|0;p.ph=Math.random()*TAU;p.sp=.6+Math.random()*.9;lamps[i]=p;}
  PX=new Float32Array(n);PY=new Float32Array(n);PK=new Float32Array(n);PB=new Float32Array(n);PZ=new Float32Array(n);
}
function buildBaubles(){
  baubles=[];for(let i=0;i<70;i++){const p=conePoint();p.x*=1.03;p.z*=1.03;p.c=(Math.random()*5)|0;p.s=.6+Math.random()*.6;baubles.push(p);}
}
const SKY=Array.from({length:150},()=>({x:Math.random(),y:Math.random()*.62,s:Math.random()*1.2+.3,ph:Math.random()*TAU}));
const SKYLINE=(()=>{const b=[];let x=-.01;while(x<1.02){const w=.012+Math.random()*.04;const hgt=.02+Math.pow(Math.random(),2)*.15;
  b.push({x,w,h:hgt,win:Array.from({length:6},()=>[Math.random(),Math.random(),Math.random()>.55])});x+=w+Math.random()*.006;}return b;})();
const SEC_COL={S:'#4BE3A5',A:'#5CD2FF',T:'#FFC24B',B:'#FF3B5C'};
const SECTIONS=[{k:'S',name:'Soprano',n:384,col:'var(--mint)'},{k:'A',name:'Alto',n:336,col:'var(--ice)'},
  {k:'T',name:'Tenor',n:288,col:'var(--gold)'},{k:'B',name:'Bass',n:276,col:'var(--crimson)'}];

const spriteCache=new Map();
function sprite(col){
  if(spriteCache.has(col))return spriteCache.get(col);
  const c=document.createElement('canvas');c.width=c.height=64;const g=c.getContext('2d');
  const gr=g.createRadialGradient(32,32,0,32,32,32);
  gr.addColorStop(0,'rgba(255,255,255,1)');gr.addColorStop(.1,col);gr.addColorStop(.3,hexA(col,.38));gr.addColorStop(1,hexA(col,0));
  g.fillStyle=gr;g.fillRect(0,0,64,64);spriteCache.set(col,c);return c;
}

/* ============================ SIM STATE ============================ */
let pulse=0,starBoost=0,sparks=[],focusZone=null,focusUntil=0;
const secLevel={S:0,A:0,T:0,B:0};
const snow=Array.from({length:650},()=>({x:Math.random(),y:Math.random(),s:.6+Math.random()*1.8,v:.035+Math.random()*.09,ph:Math.random()*TAU}));
const SNOW_MAX={cinematic:650,balanced:420,performance:220};
function spark(withSound){
  const cols=PALETTES[S.palette].cols;
  sparks.push({y:0,c:cols[(Math.random()*5)|0],seed:Math.random()*TAU,v:.5+Math.random()*.25});
  if(sparks.length>30)sparks.shift();
  if(withSound)chime();
}

/* ============================ STAGE RENDERER ============================ */
class Stage{
  constructor(canvas,opts){
    this.c=canvas;this.g=canvas.getContext('2d');this.o=opts;
    this.cam={yaw:opts.yaw||0,pitch:-.1};this.lastDrag=-1e9;this.down=null;this.visible=true;
    this.w=1;this.h=1;this.dpr=1;this.resize();
    new ResizeObserver(()=>this.resize()).observe(canvas);
    new IntersectionObserver(es=>{this.visible=es[0].isIntersecting;}).observe(canvas);
    this.bind();
  }
  resize(){
    const cap={cinematic:2,balanced:1.5,performance:1}[S.quality]||1.5;
    this.dpr=Math.min(window.devicePixelRatio||1,cap);
    const r=this.c.getBoundingClientRect();this.w=Math.max(1,r.width);this.h=Math.max(1,r.height);
    this.c.width=Math.round(this.w*this.dpr);this.c.height=Math.round(this.h*this.dpr);
  }
  bind(){
    const c=this.c;
    c.addEventListener('pointerdown',e=>{this.down={x:e.clientX,y:e.clientY,yaw:this.cam.yaw,pitch:this.cam.pitch,moved:false,id:e.pointerId,type:e.pointerType};initAudio();});
    c.addEventListener('pointermove',e=>{const d=this.down;if(!d)return;const dx=e.clientX-d.x,dy=e.clientY-d.y;
      if(!d.moved&&Math.hypot(dx,dy)>6){d.moved=true;c.classList.add('dragging');try{c.setPointerCapture(d.id);}catch(_){}}
      if(d.moved){this.cam.yaw=d.yaw+dx*.008;if(d.type==='mouse')this.cam.pitch=clamp(d.pitch+dy*.002,-.35,.12);this.lastDrag=performance.now();}});
    const up=e=>{const d=this.down;if(!d)return;if(!d.moved&&e.type==='pointerup'){spark(true);}c.classList.remove('dragging');this.down=null;};
    c.addEventListener('pointerup',up);c.addEventListener('pointercancel',up);
    c.addEventListener('dblclick',()=>{this.cam.yaw=0;this.cam.pitch=-.1;this.lastDrag=performance.now();});
  }
  layout(){
    const {w,h}=this,z=S.zoom/100;
    if(this.o.hero){const wide=w>900;return wide?{cx:w*.68,cy:h*.5,U:h*.7/z}:{cx:w*.5,cy:h*.4,U:h*.5/z};}
    return {cx:w*.5,cy:h*.5,U:h*.76/z};
  }
  render(t,dt){
    const g=this.g,w=this.w,h=this.h,bp=S.blueprint;
    if(S.drift&&!this.down&&performance.now()-this.lastDrag>2500)this.cam.yaw+=dt*.14;
    g.setTransform(this.dpr,0,0,this.dpr,0,0);g.globalCompositeOperation='source-over';g.globalAlpha=1;
    const {cx,cy,U}=this.layout();
    const cY=Math.cos(this.cam.yaw),sY=Math.sin(this.cam.yaw),cP=Math.cos(this.cam.pitch),sP=Math.sin(this.cam.pitch),D=2.4;
    const P=(x,y,z)=>{const xr=x*cY-z*sY,zr=x*sY+z*cY,yy=y-.5,yr=yy*cP-zr*sP,z2=yy*sP+zr*cP,k=D/(D+z2);return {x:cx+xr*k*U,y:cy-yr*k*U,k,z:z2};};
    const Ps=(xr,y)=>{const yy=y-.5,yr=yy*cP,z2=yy*sP,k=D/(D+z2);return {x:cx+xr*k*U,y:cy-yr*k*U,k};};
    const cols=PALETTES[S.palette].cols;
    const groundY=Ps(0,0).y;

    /* --- sky --- */
    const bg=g.createLinearGradient(0,0,0,h);
    if(bp){bg.addColorStop(0,'#041a30');bg.addColorStop(1,'#020b16');}
    else{bg.addColorStop(0,'#01060a');bg.addColorStop(.55,'#04120E');bg.addColorStop(1,'#061915');}
    g.fillStyle=bg;g.fillRect(0,0,w,h);
    if(bp){
      g.strokeStyle='rgba(92,210,255,.07)';g.lineWidth=1;g.beginPath();
      for(let x=(cx%32);x<w;x+=32){g.moveTo(x,0);g.lineTo(x,h);}for(let y=(groundY%32);y<h;y+=32){g.moveTo(0,y);g.lineTo(w,y);}g.stroke();
    }else{
      g.fillStyle='#F8EFE4';
      for(const s of SKY){const a=.25+.35*Math.sin(t*1.3+s.ph);if(a<=0)continue;g.globalAlpha=a;g.fillRect(s.x*w,s.y*groundY,s.s,s.s);}
      g.globalAlpha=1;
      /* skyline */
      const sb=groundY-U*.02;
      for(const b of SKYLINE){const bx=b.x*w,bw=b.w*w,bh=b.h*U*1.4;
        g.fillStyle='#03100c';g.fillRect(bx,sb-bh,bw,bh+2);
        g.fillStyle='rgba(255,217,138,.35)';for(const [wx,wy,on] of b.win){if(on)g.fillRect(bx+wx*(bw-3),sb-bh+wy*(bh-4)+2,1.6,1.6);}}
      const gd=g.createLinearGradient(0,sb,0,h);gd.addColorStop(0,'#061915');gd.addColorStop(1,'#020806');
      g.fillStyle=gd;g.fillRect(0,sb,w,h-sb);
    }
    const top=P(0,1.0,0);

    /* --- haze & god rays --- */
    if(S.haze>0&&!bp){
      const hz=S.haze/100,lum=.35+ZF.top*.65+starBoost*.5;
      const R=Math.max(w,h)*.9;const gr=g.createRadialGradient(top.x,top.y,0,top.x,top.y,R);
      gr.addColorStop(0,`rgba(255,214,140,${.2*hz*lum})`);gr.addColorStop(.4,`rgba(255,180,120,${.05*hz*lum})`);gr.addColorStop(1,'rgba(255,214,140,0)');
      g.fillStyle=gr;g.fillRect(0,0,w,h);
      g.globalCompositeOperation='lighter';
      for(let i=0;i<9;i++){const a=Math.PI*(.16+.68*(i/8))+Math.sin(t*.2+i*1.7)*.05,sp=.035+.02*Math.sin(t*.3+i);
        g.fillStyle=`rgba(255,220,160,${.03*hz*lum})`;g.beginPath();g.moveTo(top.x,top.y);
        g.lineTo(top.x+Math.cos(a-sp)*R,top.y+Math.sin(a-sp)*R);g.lineTo(top.x+Math.cos(a+sp)*R,top.y+Math.sin(a+sp)*R);g.closePath();g.fill();}
      g.globalCompositeOperation='source-over';
    }

    /* --- ground glow --- */
    const base=Ps(0,0);
    if(!bp){g.globalCompositeOperation='lighter';
      const gg=g.createRadialGradient(base.x,base.y,0,base.x,base.y,U*.6);
      gg.addColorStop(0,hexA(cols[0],.22*(ZF.lo+.15)+pulse*.08));gg.addColorStop(1,hexA(cols[0],0));
      g.fillStyle=gg;g.beginPath();g.ellipse(base.x,base.y,U*.7,U*.16,0,0,TAU);g.fill();g.globalCompositeOperation='source-over';}

    /* --- choir ring (back half) --- */
    const ring=[];
    for(let i=0;i<96;i++){const a=i/96*TAU,sec='SATB'[(i/24)|0];const p=P(Math.cos(a)*.62,-.01,Math.sin(a)*.62);p.sec=sec;ring.push(p);}
    const drawRing=back=>{g.globalCompositeOperation='lighter';
      for(const p of ring){if((p.z>0)!==back)continue;const on=S.sections[p.sec]?1:.15;const lv=(.25+secLevel[p.sec]*.9)*on*(.25+ZF.choir*.75);
        const s=U*.05*p.k*(.6+lv);g.globalAlpha=clamp(lv,0,1)*(back?.5:1);
        if(bp){g.fillStyle='#5CD2FF';g.fillRect(p.x-1,p.y-1,2,2);}else g.drawImage(sprite(SEC_COL[p.sec]),p.x-s/2,p.y-s/2,s,s);}
      g.globalAlpha=1;g.globalCompositeOperation='source-over';};
    drawRing(true);

    /* --- lamp projection + back pass --- */
    const n=lamps.length,sz=U*.032*(S.bloom/100)*Math.pow(2200/Math.max(400,n),.3);
    const tw=Math.min(1,S.twinkle/100)*.5,tsp=.6+S.twinkle/100*2.6,pat=S.chase;
    const spr=cols.map(sprite);
    g.globalCompositeOperation='lighter';
    for(let i=0;i<n;i++){
      const l=lamps[i],zfac=l.y>.5?ZF.up:ZF.lo;
      if(zfac<=.001){PB[i]=0;continue;}
      const xr=l.x*cY-l.z*sY,zr=l.x*sY+l.z*cY,yy=l.y-.5,yr=yy*cP-zr*sP,z2=yy*sP+zr*cP,k=D/(D+z2);
      let b;
      switch(pat){
        case 'wave':b=.3+.7*(.5+.5*Math.sin(l.y*12-t*2.6));break;
        case 'chase':b=.22+.78*Math.pow(.5+.5*Math.sin(l.a*2+l.y*26-t*4.2),3);break;
        case 'sparkle':b=.22+.78*Math.pow(Math.max(0,Math.sin(t*l.sp*1.9+l.ph*7)),14);break;
        case 'candle':b=.72+.28*Math.sin(t*11*l.sp+l.ph)*Math.sin(t*6.3+l.ph*3);break;
        default:b=1;
      }
      b=(b*(1-tw*(.5+.5*Math.sin(t*tsp*l.sp+l.ph)))+pulse*.35)*zfac;
      PX[i]=cx+xr*k*U;PY[i]=cy-yr*k*U;PK[i]=k;PB[i]=b;PZ[i]=z2;
      if(z2>0){
        if(bp){g.globalAlpha=clamp(b*.4,0,1);g.fillStyle='#5CD2FF';g.fillRect(PX[i]-.6,PY[i]-.6,1.2,1.2);}
        else{const s=sz*k*.8;g.globalAlpha=clamp(b*.3,0,1);g.drawImage(spr[l.c],PX[i]-s/2,PY[i]-s/2,s,s);}
      }
    }
    g.globalAlpha=1;g.globalCompositeOperation='source-over';

    /* --- foliage --- */
    const tiers=TREE.tiers,step=.92/tiers;
    const trunkTop=Ps(0,.06),trunkBot=Ps(0,-.01);
    g.fillStyle=bp?'rgba(92,210,255,.15)':'#1a0f08';g.fillRect(trunkTop.x-U*.02,trunkTop.y,U*.04,trunkBot.y-trunkTop.y);
    for(let i=0;i<tiers;i++){
      const y0=.04+i*step,y1=Math.min(1.02,y0+step*2.15),r=(1-y0)*TREE.R*1.05;
      const apex=Ps(0,y1),bl=Ps(-r,y0),br=Ps(r,y0);
      g.beginPath();g.moveTo(apex.x,apex.y);g.lineTo(br.x,br.y);
      const seg=18,sag=r*U*.16*(-sP*2+.35);
      for(let j=1;j<seg;j++){const u=j/seg;const x=lerp(br.x,bl.x,u);
        const y=lerp(br.y,bl.y,u)+Math.sin(Math.PI*u)*sag+Math.sin(u*16+this.cam.yaw*5+i)*1.6;g.lineTo(x,y);}
      g.lineTo(bl.x,bl.y);g.closePath();
      if(bp){g.strokeStyle='rgba(92,210,255,.5)';g.lineWidth=1;g.stroke();}
      else{const fg=g.createLinearGradient(bl.x,0,br.x,0);
        fg.addColorStop(0,'#020b08');fg.addColorStop(.42,'#0b2f24');fg.addColorStop(.6,'#0e3a2c');fg.addColorStop(1,'#03100c');
        g.fillStyle=fg;g.globalAlpha=.97;g.fill();g.globalAlpha=1;}
    }
    /* light spill on foliage */
    if(!bp){g.globalCompositeOperation='lighter';
      const sp=g.createRadialGradient(cx,Ps(0,.45).y,0,cx,Ps(0,.45).y,U*.5);
      const lit=(ZF.up+ZF.lo)/2*(S.bloom/100);
      sp.addColorStop(0,hexA(cols[0],.12*lit+pulse*.05));sp.addColorStop(1,hexA(cols[0],0));
      g.fillStyle=sp;g.fillRect(cx-U*.6,Ps(0,1).y,U*1.2,base.y-Ps(0,1).y);g.globalCompositeOperation='source-over';}

    /* --- baubles --- */
    if(!bp){const avg=(ZF.up+ZF.lo)/2;
      for(const b of baubles){const p=P(b.x,b.y,b.z);if(p.z>0)continue;const r=U*.011*p.k*b.s;const col=cols[b.c];
        const bz=b.y>.5?ZF.up:ZF.lo;g.globalAlpha=.35+.6*Math.max(bz,avg*.3);
        const bg2=g.createRadialGradient(p.x-r*.35,p.y-r*.35,r*.1,p.x,p.y,r);bg2.addColorStop(0,'#fff');bg2.addColorStop(.3,col);bg2.addColorStop(1,'#120604');
        g.fillStyle=bg2;g.beginPath();g.arc(p.x,p.y,r,0,TAU);g.fill();}
      g.globalAlpha=1;}

    /* --- front lamps --- */
    g.globalCompositeOperation='lighter';
    for(let i=0;i<n;i++){
      const b=PB[i];if(b<=0||PZ[i]>0)continue;
      if(bp){g.globalAlpha=clamp(b,0,1);g.fillStyle='#9FE8FF';g.fillRect(PX[i]-.9,PY[i]-.9,1.8,1.8);continue;}
      const s=sz*PK[i]*(.75+.35*b);g.globalAlpha=clamp(b,0,1);g.drawImage(spr[lamps[i].c],PX[i]-s/2,PY[i]-s/2,s,s);
    }
    g.globalAlpha=1;

    /* --- sparks --- */
    for(const sk of sparks){
      for(let j=0;j<7;j++){const y=sk.y-j*.014;if(y<0)break;const a=y*22+sk.seed,r=(1-y)*TREE.R*.55;
        const p=P(Math.cos(a)*r,y,Math.sin(a)*r);const s=U*.07*p.k*(1-j/8);g.globalAlpha=1-j/7;
        g.drawImage(sprite(sk.c),p.x-s/2,p.y-s/2,s,s);}
    }
    g.globalAlpha=1;

    /* --- topper --- */
    const st=(S.star/100)*ZF.top+starBoost;
    if(st>.01||bp){
      const s=U*.05*top.k*(.8+.4*Math.min(1,st));
      if(!bp){const gs=s*(4+st*5);g.globalAlpha=clamp(st,0,1);g.drawImage(sprite('#FFC24B'),top.x-gs/2,top.y-gs/2,gs,gs);g.globalAlpha=1;}
      g.globalCompositeOperation='source-over';
      g.save();g.translate(top.x,top.y);g.rotate(Math.sin(t*.6)*.12);g.beginPath();
      for(let i=0;i<10;i++){const r=i%2?s*.42:s,a=-Math.PI/2+i*Math.PI/5;g.lineTo(Math.cos(a)*r,Math.sin(a)*r);}g.closePath();
      if(bp){g.strokeStyle='#9FE8FF';g.stroke();}else{g.fillStyle=st>.05?`rgba(255,${200+Math.round(40*Math.min(1,st))},120,${.35+.65*Math.min(1,st)})`:'#3a2a10';g.fill();}
      g.restore();
    }

    /* --- choir ring (front half) --- */
    drawRing(false);

    /* --- guides --- */
    const focusing=focusZone&&performance.now()<focusUntil;
    if(S.guides||bp||focusing){
      g.globalCompositeOperation='source-over';g.font='600 10px "JetBrains Mono", monospace';g.textBaseline='middle';
      const guide=(zid,y,r,label)=>{
        const on=!!assign[zid],hl=focusing&&focusZone===zid;if(focusing&&!hl&&!S.guides&&!bp)return;
        const p=Ps(0,y),rx=r*U*p.k,ry=Math.max(2,rx*Math.abs(sP)*1.6+rx*.08);
        g.strokeStyle=hl?'#5CD2FF':on?'rgba(255,217,138,.55)':'rgba(255,176,32,.9)';g.lineWidth=hl?2:1;
        g.setLineDash(on?[5,4]:[2,3]);g.beginPath();g.ellipse(p.x,p.y,rx,ry,0,0,TAU);g.stroke();g.setLineDash([]);
        const lx=p.x+rx+14;g.beginPath();g.moveTo(p.x+rx,p.y);g.lineTo(lx-4,p.y);g.stroke();
        g.fillStyle=g.strokeStyle;g.fillText(`${label} · ${on?assign[zid]:'VACANT'}`,lx,p.y);
      };
      guide('topper',1,.05,'TOPPER');guide('upper',.72,(1-.72)*TREE.R,'UPPER CANOPY');
      guide('lower',.28,(1-.28)*TREE.R,'LOWER CANOPY');guide('choir',-.01,.62,'CHOIR RING');
    }

    /* --- snow --- */
    const ns=Math.round(S.snow/100*(SNOW_MAX[S.quality]||420)*ZF.snow);
    if(ns>0){g.globalCompositeOperation='source-over';g.fillStyle=bp?'#9FE8FF':'#F8EFE4';const ss=Math.max(.8,h/760);
      for(let i=0;i<ns;i++){const p=snow[i];g.globalAlpha=.35+.45*(p.s/2.4);g.beginPath();g.arc(p.x*w,p.y*h,p.s*ss,0,TAU);g.fill();}
      g.globalAlpha=1;}

    /* --- vignette --- */
    const vg=g.createRadialGradient(w/2,h/2,Math.min(w,h)*.35,w/2,h/2,Math.max(w,h)*.75);
    vg.addColorStop(0,'rgba(0,0,0,0)');vg.addColorStop(1,'rgba(0,0,0,.55)');g.fillStyle=vg;g.fillRect(0,0,w,h);
  }
}

/* ============================ AUDIO ============================ */
const AU={ctx:null,on:store.get('sound',true)};
function makeIR(ctx,sec){
  const len=Math.floor(ctx.sampleRate*sec),b=ctx.createBuffer(2,len,ctx.sampleRate);
  for(let ch=0;ch<2;ch++){const d=b.getChannelData(ch);for(let i=0;i<len;i++){const x=i/len;d[i]=(Math.random()*2-1)*Math.pow(1-x,3.2);}}
  return b;
}
function initAudio(){
  if(AU.ctx){if(AU.ctx.state==='suspended')AU.ctx.resume();return;}
  const AC=window.AudioContext||window.webkitAudioContext;
  if(!AC){$('#audioHint')?.remove();return;}
  let ctx;try{ctx=new AC();}catch(e){return;}
  AU.ctx=ctx;
  AU.master=ctx.createGain();AU.master.gain.value=AU.on?.9:0;
  const comp=ctx.createDynamicsCompressor();comp.threshold.value=-16;comp.ratio.value=4;
  AU.analyser=ctx.createAnalyser();AU.analyser.fftSize=128;AU.fbuf=new Uint8Array(AU.analyser.frequencyBinCount);
  AU.master.connect(comp);comp.connect(AU.analyser);AU.analyser.connect(ctx.destination);
  AU.bus=ctx.createGain();AU.dry=ctx.createGain();AU.wet=ctx.createGain();
  AU.verb=ctx.createConvolver();AU.verb.buffer=makeIR(ctx,3.4);
  AU.bus.connect(AU.dry);AU.dry.connect(AU.master);AU.bus.connect(AU.verb);AU.verb.connect(AU.wet);AU.wet.connect(AU.master);
  AU.fx=ctx.createGain();AU.fx.gain.value=.6;AU.fx.connect(AU.master);AU.fx.connect(AU.verb);
  AU.sec={};for(const s of 'SATB'){const gn=ctx.createGain();gn.connect(AU.bus);AU.sec[s]=gn;}
  if(ctx.state==='suspended')ctx.resume();
  applyAudio();$('#audioHint')?.remove();
}
function applyAudio(){
  if(!AU.ctx)return;const t=AU.ctx.currentTime;
  AU.bus.gain.setTargetAtTime(S.choir/100*.6*ZF.choir,t,.08);
  AU.wet.gain.setTargetAtTime(S.verb/100*1.1,t,.1);AU.dry.gain.setTargetAtTime(1-S.verb/100*.55,t,.1);
  for(const s of 'SATB')AU.sec[s].gain.setTargetAtTime(S.sections[s]?1:0,t,.06);
  AU.master.gain.setTargetAtTime(AU.on?.9:0,t,.05);
}
const FORMANTS={S:[800,1150,2900],A:[800,1150,2800],T:[650,1080,2650],B:[600,1040,2250]};
function sing(sec,midi,when,dur,vel=1){
  const ctx=AU.ctx;if(!ctx)return null;
  const f=440*Math.pow(2,(midi-69)/12);
  const out=ctx.createGain();out.gain.value=0;out.connect(AU.sec[sec]);
  const mix=ctx.createGain();
  FORMANTS[sec].forEach((ff,i)=>{const bp=ctx.createBiquadFilter();bp.type='bandpass';bp.frequency.value=ff;bp.Q.value=i?10:6;
    const gg=ctx.createGain();gg.gain.value=[3,1.6,.5][i];mix.connect(bp);bp.connect(gg);gg.connect(out);});
  const lfo=ctx.createOscillator();lfo.frequency.value=4.6+Math.random()*1.2;const lg=ctx.createGain();lg.gain.value=13;lfo.connect(lg);
  const oscs=[-9,0,8].map(d=>{const o=ctx.createOscillator();o.type='sawtooth';o.frequency.value=f;o.detune.value=d+Math.random()*6-3;lg.connect(o.detune);o.connect(mix);return o;});
  const a=Math.min(.16,dur*.3),r=.45,peak=.1*vel;
  out.gain.setValueAtTime(0,when);out.gain.linearRampToValueAtTime(peak,when+a);
  out.gain.setValueAtTime(peak,when+Math.max(a+.01,dur-.04));out.gain.exponentialRampToValueAtTime(.0004,when+dur+r);
  const end=when+dur+r+.05;lfo.start(when);lfo.stop(end);oscs.forEach(o=>{o.start(when);o.stop(end);});
  oscs[1].onended=()=>{try{out.disconnect();}catch(_){}};
  return out;
}
function chime(){
  const ctx=AU.ctx;if(!ctx||!AU.on)return;const t=ctx.currentTime;
  const base=[76,79,81,83,86][(Math.random()*5)|0];
  [0,12,19].forEach((o,i)=>{const os=ctx.createOscillator();os.type='sine';os.frequency.value=440*Math.pow(2,(base+o-69)/12);
    const gn=ctx.createGain();gn.gain.setValueAtTime(0,t);gn.gain.linearRampToValueAtTime([.08,.035,.015][i],t+.008);
    gn.gain.exponentialRampToValueAtTime(.0001,t+1.8);os.connect(gn);gn.connect(AU.fx);os.start(t);os.stop(t+1.9);});
}

/* ============================ CAROLS ============================ */
const CHORD={I:[0,[0,4,7]],ii:[2,[0,3,7]],iii:[4,[0,3,7]],IV:[5,[0,4,7]],V:[7,[0,4,7]],V7:[7,[0,4,7,10]],vi:[9,[0,3,7]],'V/V':[2,[0,4,7]]};
const CAROLS=[
  {id:'silent',title:'Silent Night',key:'B♭ major',tonic:58,bpm:150,step:3,meter:'6/8',
   prog:'I:6 I:6 V7:6 I:6 IV:6 I:6 IV:6 I:6 V7:6 V7:6 I:6 I:6 I:3 V7:3 I:6 V7:6 I:12'},
  {id:'faithful',title:'O Come, All Ye Faithful',key:'G major',tonic:55,bpm:96,step:1,meter:'4/4',
   prog:'I:2 V:2 I:2 IV:2 I:2 V:2 vi:1 ii:1 V:2 I:2 V:2 vi:2 iii:2 IV:2 V:2 I:4 IV:2 I:2 V:4 I:2 IV:2 I:2 V7:2 I:4'},
  {id:'joy',title:'Joy to the World',key:'D major',tonic:50,bpm:112,step:1,meter:'2/4',
   prog:'I:4 IV:2 V:2 I:4 V:2 I:2 I:2 IV:2 V7:2 I:2 I:4 V:4 V7:4 I:4 IV:2 I:2 V7:2 I:2 I:4 IV:2 V:2 I:6'},
  {id:'hark',title:'Hark! The Herald Angels Sing',key:'F major',tonic:53,bpm:108,step:1,meter:'4/4',
   prog:'I:2 I:2 V:2 I:2 I:2 IV:2 V7:2 I:2 I:2 vi:2 V:2 I:2 V/V:2 V:2 V7:4 I:2 IV:2 I:2 V:2 vi:2 ii:2 V7:2 I:4'},
  {id:'deck',title:'Deck the Halls',key:'C major',tonic:48,bpm:132,step:1,meter:'4/4',
   prog:'I:4 V:2 I:2 IV:2 I:2 V:2 I:2 ii:2 V:2 I:4 IV:2 V:2 I:4 vi:2 ii:2 V7:4 I:4 IV:2 I:2 V7:2 I:2 I:6'},
  {id:'holy',title:'O Holy Night',key:'C major',tonic:48,bpm:138,step:3,meter:'12/8',
   prog:'I:12 IV:6 I:6 V7:6 I:6 vi:6 iii:6 IV:12 I:6 V7:6 I:12 vi:6 ii:6 V7:12 I:12'}
];
const RANGE={S:[60,79],A:[53,72],T:[48,67],B:[38,60]};
function arrange(c){
  const pc0=c.tonic%12,spb=60/c.bpm,ev=[];let tt=0,prev={S:67,A:62,T:55,B:43};
  const chords=c.prog.trim().split(/\s+/).map(x=>{const [s,b]=x.split(':');return {sym:s,beats:+b};});
  chords.forEach((ch,ci)=>{
    const [root,ints]=CHORD[ch.sym];const pcs=ints.map(i=>(pc0+root+i)%12);const rootPc=(pc0+root)%12;
    const used=new Set();
    const pick=(sec,ok,upper)=>{const [lo,hi]=RANGE[sec];let best=prev[sec],bs=1e9;
      for(let m=lo;m<=hi;m++){if(!ok(m))continue;let s=Math.abs(m-prev[sec]);if(upper!=null&&m>=upper)s+=30;if(used.has(m%12))s+=2.5;if(s<bs){bs=s;best=m;}}return best;};
    const v={};
    v.B=pick('B',m=>m%12===rootPc,null);
    v.S=pick('S',m=>pcs.includes(m%12),null);used.add(v.S%12);
    v.A=pick('A',m=>pcs.includes(m%12),v.S);used.add(v.A%12);
    v.T=pick('T',m=>pcs.includes(m%12),v.A);
    const dur=ch.beats*spb;
    ev.push({t:tt,type:'chord',dur});
    for(const s of 'ATB')ev.push({t:tt,sec:s,m:v[s],dur:dur*.97});
    /* soprano re-articulates every `step` beats with a seeded chord-tone walk */
    let cur=v.S;const n=Math.max(1,Math.round(ch.beats/c.step));
    for(let k=0;k<n;k++){
      if(k>0){const dir=hash(c.id+ci+':'+k)>.5?1:-1;let best=cur,bs=1e9;
        for(let m=RANGE.S[0];m<=RANGE.S[1];m++){if(!pcs.includes(m%12)||m===cur||Math.abs(m-cur)>5)continue;
          const s=Math.abs(m-cur)+Math.abs(m-69)*.18+(Math.sign(m-cur)!==dir?2:0);if(s<bs){bs=s;best=m;}}cur=best;}
      const d=Math.min(c.step,ch.beats-k*c.step)*spb;
      ev.push({t:tt+k*c.step*spb,sec:'S',m:cur,dur:d*.94});
    }
    prev={...v,S:cur};tt+=dur;
  });
  ev.sort((a,b)=>a.t-b.t);
  return {events:ev,dur:tt+.8};
}
CAROLS.forEach(c=>{c.arr=arrange(c);});

let song=null;
function playCarol(id){
  if(!assign.choir){
    toast('The choir ring has no owner','Put CANTUS-04 back on the choir ring and the ring will sing.',{ac:'var(--warn)',icon:'!',action:'Assign',onAction:()=>place('CANTUS-04','choir'),life:6000});
    return false;
  }
  initAudio();stopCarol(true);
  const c=CAROLS.find(x=>x.id===id);if(!c)return false;
  song={c,start:performance.now(),ai:0,vi:0,nodes:[]};
  renderRepertoire();$('#npLabel').textContent='NOW SINGING · '+c.title.toUpperCase();
  log(assign.choir,`Downbeat · ${c.title} · ${c.key} · ${c.meter}`,'ok');
  if(AU.ctx&&!AU.on)toast('Sound is muted','Unmute in the top bar to hear the choir.',{icon:'♪'});
  return true;
}
function stopCarol(silent){
  if(!song)return;
  if(AU.ctx){const t=AU.ctx.currentTime;for(const n of song.nodes){try{n.gain.cancelScheduledValues(t);n.gain.setValueAtTime(n.gain.value,t);n.gain.linearRampToValueAtTime(0,t+.25);}catch(_){}}}
  song=null;$('#npFill').style.width='0%';$('#npLabel').textContent='STANDBY';renderRepertoire();
}
function songTick(){
  if(!song)return;const now=(performance.now()-song.start)/1000,ev=song.c.arr.events;
  if(AU.ctx){
    if(AU.ctx.state==='running'){
      while(song.ai<ev.length&&ev[song.ai].t<now+.3){const e=ev[song.ai++];
        if(e.sec&&e.t>now-.4){const n=sing(e.sec,e.m,AU.ctx.currentTime+Math.max(0,e.t-now),e.dur,e.sec==='S'?1.05:e.sec==='B'?1:.85);if(n)song.nodes.push(n);}}
      if(song.nodes.length>160)song.nodes.splice(0,80);
    }
  }else{while(song.ai<ev.length&&ev[song.ai].t<now)song.ai++;}
  while(song.vi<ev.length&&ev[song.vi].t<=now){const e=ev[song.vi++];
    if(e.type==='chord')pulse=Math.min(1,pulse+.55);else if(S.sections[e.sec]&&ZF.choir>0)secLevel[e.sec]=1;}
  $('#npFill').style.width=Math.min(100,now/song.c.arr.dur*100)+'%';
  if(now>song.c.arr.dur){const c=song.c;stopCarol(true);log(assign.choir||'CANTUS-04',`Release · ${c.title} — ring holds`,'');}
}
setInterval(songTick,40);
function hum(){
  initAudio();if(!AU.ctx||!assign.choir)return;const t=AU.ctx.currentTime+.05;
  [['B',46],['T',53],['A',58],['S',62]].forEach(([s,m])=>sing(s,m,t,3.2,.8));
  for(const s of 'SATB')if(S.sections[s])secLevel[s]=1;pulse=.6;
}

/* ============================ RUN OF SHOW ============================ */
const SHOW_LEN=56;
const CUES=[
  {t:0,name:'House to half',desc:'Plaza dims, the cordon closes around the choir ring, the canopy drops to candle glow.',zones:['crowd'],set:{bloom:45,star:12,snow:0,haze:70,twinkle:25,chase:'candle'}},
  {t:6,name:'Choir walk-on',desc:'1,284 singers take the ring; CANTUS-04 gives the tuning chord.',zones:['choir'],set:{choir:70,verb:60},fx:'hum'},
  {t:12,name:'Canopy ignition',desc:'Lower canopy first, upper canopy on the swell — a vertical wave to the crown.',zones:['lower','upper'],set:{bloom:115,twinkle:85,chase:'wave',star:40}},
  {t:22,name:'First snowfall',desc:'Foam-flake towers open into the breeze; the haze lifts for the god rays.',zones:['snow'],set:{snow:72,wind:-14,haze:48}},
  {t:30,name:'Full choir · Joy to the World',desc:'All four sections on the bus; the canopy chases every downbeat.',zones:['choir'],set:{choir:82,chase:'chase',twinkle:120,bloom:130},fx:'carol'},
  {t:44,name:'Topper & cold sparks',desc:'Beacon to full, twelve cold-spark fountains, sparkle pops across 38,400 lamps.',zones:['topper'],set:{star:100,bloom:155,chase:'sparkle'},fx:'sparks'},
  {t:52,name:'Curtain & egress',desc:'Canopy settles to a steady burn; the house is released in three waves.',zones:['herald','crowd'],set:{bloom:95,snow:35,chase:'steady',twinkle:60,star:75}}
];
const show={state:'idle',t:0,cue:-1,pre:null,dropped:new Set()};
let tweens={};
function tween(set,dur){for(const k in set){if(typeof set[k]==='number')tweens[k]={from:S[k],to:set[k],t:0,dur};else S[k]=set[k];}syncUI();}
let uiT=0;
function tweenUpdate(dt){
  let any=false;
  for(const k in tweens){const tw=tweens[k];tw.t+=dt;const p=Math.min(1,tw.t/tw.dur);const e=p<.5?2*p*p:1-Math.pow(-2*p+2,2)/2;
    S[k]=lerp(tw.from,tw.to,e);if(p>=1)delete tweens[k];any=true;}
  if(any){uiT+=dt;if(uiT>.08||!Object.keys(tweens).length){uiT=0;syncUI();applyAudio();}}
}
function cueOwned(c){return c.zones.some(z=>assign[z]);}
function applyCumulative(upto){
  if(show.pre)applySettings(show.pre);
  for(let j=0;j<=upto;j++){if(cueOwned(CUES[j]))Object.assign(S,CUES[j].set);}
  syncUI();applyAudio();
}
function showRun(){
  initAudio();
  if(show.state==='run')return;
  if(show.state==='idle'||show.state==='done'){
    if(show.state==='done'&&show.pre)applySettings(show.pre);
    if(readiness()<1){const vac=ZONES.filter(z=>!assign[z.id]).map(z=>z.name);
      toast('Running with vacant zones',`${vac.join(', ')} will drop their cues.`,{ac:'var(--warn)',icon:'!',action:'Auto-assign',onAction:autoAssign,life:6500});}
    show.pre=show.pre||clone(S);show.t=0;show.cue=-1;show.dropped=new Set();
    log('STAGE','Show started · 7 cues · 56 s','ok');
  }else log('STAGE',`Resumed at ${mmss(show.t)}`,'');
  show.state='run';syncTransport();renderTimeline();
}
function showPause(){if(show.state!=='run')return;show.state='pause';log('STAGE',`Paused at ${mmss(show.t)}`,'warn');syncTransport();}
function showReset(){
  tweens={};if(show.pre)applySettings(show.pre);
  show.state='idle';show.t=0;show.cue=-1;show.pre=null;show.dropped=new Set();
  stopCarol(true);syncTransport();renderTimeline();$('#hudCue').textContent='STANDBY · house open, agents on station';
  log('STAGE','Show reset · console restored','');
}
function fireCue(i){
  show.cue=i;const c=CUES[i];const vac=c.zones.filter(z=>!assign[z]);
  if(vac.length===c.zones.length){show.dropped.add(i);
    log('STAGE',`CUE ${i+1} DROPPED — ${vac.map(z=>zoneById(z).name).join(' & ')} has no owner`,'bad');}
  else{
    tween(c.set,1.8);log(assign[c.zones.find(z=>assign[z])],`CUE ${i+1} · ${c.name}`,'ok');
    if(vac.length)log('STAGE',`${vac.map(z=>zoneById(z).name).join(' & ')} unowned — part of the cue stays dark`,'warn');
    if(c.fx==='carol')playCarol('joy');
    if(c.fx==='hum')hum();
    if(c.fx==='sparks'){starBoost=1;for(let k=0;k<10;k++)setTimeout(()=>spark(k%3===0),k*200);}
  }
  renderTimeline();$('#hudCue').textContent=`CUE ${i+1}/7 · ${c.name.toUpperCase()}`;
}
function showUpdate(dt){
  if(show.state!=='run')return;show.t+=dt;
  while(show.cue+1<CUES.length&&CUES[show.cue+1].t<=show.t)fireCue(show.cue+1);
  if(show.t>=SHOW_LEN){show.t=SHOW_LEN;show.state='done';log('STAGE','Curtain · house released in three waves','ok');
    toast('Curtain',show.dropped.size?`${show.dropped.size} cue(s) dropped for want of an owner.`:'Seven cues, no dead air.',{ac:'var(--mint)',icon:'★'});
    $('#hudCue').textContent='CURTAIN · house released';syncTransport();renderTimeline();}
}
function seek(t,{andRun=false}={}){
  t=clamp(t,0,SHOW_LEN);tweens={};
  if(show.state==='idle'||show.state==='done'){if(show.state==='done'&&show.pre)applySettings(show.pre);show.pre=show.pre||clone(S);}
  let idx=-1;for(let i=0;i<CUES.length;i++)if(CUES[i].t<=t)idx=i;
  if(andRun){applyCumulative(idx-1);show.cue=idx-1;show.t=Math.max(0,CUES[idx]?.t??t)-.001;}
  else{applyCumulative(idx);show.cue=idx;show.t=t;if(idx>=0)$('#hudCue').textContent=`CUE ${idx+1}/7 · ${CUES[idx].name.toUpperCase()}`;}
  show.state=andRun?'run':'pause';
  if(andRun)initAudio();
  syncTransport();renderTimeline();
}
function syncTransport(){
  const st=show.state;
  for(const n of ['2','3']){$('#runBtn'+n).disabled=st==='run';$('#pauseBtn'+n).disabled=st!=='run';$('#stopBtn'+n).disabled=st==='idle';}
  $('#runBtn2').textContent=st==='pause'?'Resume':st==='done'?'Run again':'Run the show';
  $('#runBtn3').textContent=st==='pause'?'▶ Resume':st==='done'?'▶ Again':'▶ Run';
  const map={idle:['HOLD','var(--warn)'],run:['RUNNING','var(--mint)'],pause:['PAUSED','var(--gold-2)'],done:['CURTAIN','var(--ice)']}[st];
  const el=$('#transportStatus');el.style.color=map[1];el.innerHTML=`<span class="dot${st==='run'?' live':''}"></span> ${map[0]}`;
}
function renderTimeline(){
  $('#timeline').innerHTML=CUES.map((c,i)=>{
    const st=show.state!=='idle'&&i===show.cue?'now':(show.state!=='idle'&&i<show.cue?'done':'');
    const drop=show.dropped.has(i)?' dropped':'';
    const own=c.zones.map(z=>{const a=assign[z]&&agentById(assign[z]);
      return a?`<span style="color:${a.ac}">● ${a.id}</span>`:`<span style="color:var(--warn)">○ ${zoneById(z).name.toUpperCase()} · VACANT</span>`;}).join('');
    return `<button class="cue ${st}${drop}" data-cue="${i}" aria-label="Jump to cue ${i+1}: ${esc(c.name)}"><span class="t">${mmss(c.t)}</span><span class="body"><b>${esc(c.name)}</b><span>${esc(c.desc)}</span></span><span class="own">${own}</span><i class="prog"></i></button>`;
  }).join('');
}
function updateShowUI(){
  const p=show.t/SHOW_LEN*100;
  $('#scrubFill').style.width=p+'%';$('#scrubHead').style.left=p+'%';
  $('#opsTime').textContent=mmss(show.t);$('#transportTime').textContent=`${mmss(show.t)} / ${mmss(SHOW_LEN)}`;
  $('#scrub').setAttribute('aria-valuenow',Math.round(show.t));
  if(show.cue>=0){const c=CUES[show.cue],end=CUES[show.cue+1]?.t??SHOW_LEN;const el=$(`.cue[data-cue="${show.cue}"] .prog`);
    if(el)el.style.width=clamp((show.t-c.t)/(end-c.t),0,1)*100+'%';}
}

/* ============================ CONSOLE UI ============================ */
const SLIDERS=[
  ['cLamps','lamps',v=>fmt(v)],['cTwinkle','twinkle',v=>(v/100).toFixed(2)+'×'],['cBloom','bloom',v=>Math.round(v)+'%'],
  ['cStar','star',v=>Math.round(v)+'%'],['cSnow','snow',v=>Math.round(v)+'%'],['cWind','wind',v=>(v>0?'+':'')+Math.round(v)],
  ['cHaze','haze',v=>Math.round(v)+'%'],['cZoom','zoom',v=>(v/100).toFixed(2)+'×'],['cChoir','choir',v=>Math.round(v)+'%'],
  ['cVerb','verb',v=>Math.round(v)+'%']
];
function setP(el){el.style.setProperty('--p',((el.value-el.min)/(el.max-el.min)*100)+'%');}
function syncUI(){
  for(const [id,key,f] of SLIDERS){const el=$('#'+id);el.value=S[key];setP(el);$('#v'+id.slice(1)).textContent=f(S[key]);}
  $('#cChase').value=S.chase;$('#cQuality').value=S.quality;
  $$('#palSeg button').forEach(b=>b.setAttribute('aria-pressed',b.dataset.pal===S.palette));
  $('#vPalette').textContent=PALETTES[S.palette].name;$('#monPal').textContent=PALETTES[S.palette].name.toUpperCase();
  $('#tDrift').setAttribute('aria-checked',S.drift);$('#tBlueprint').setAttribute('aria-checked',S.blueprint);$('#tGuides').setAttribute('aria-checked',S.guides);
  $$('#voiceChips button').forEach(b=>b.setAttribute('aria-pressed',!!S.sections[b.dataset.sec]));
  const on='SATB'.split('').filter(s=>S.sections[s]).join('');$('#vSections').textContent=on||'—';
}
function applySettings(o){
  const prevQ=S.quality;
  S=Object.assign(clone(DEFAULTS),clone(o));
  if(Math.round(S.lamps)!==lamps.length)buildLamps();
  if(prevQ!==S.quality)stages.forEach(s=>s.resize());
  syncUI();applyAudio();
}
function initConsole(){
  $('#palSeg').innerHTML=Object.entries(PALETTES).map(([k,p])=>`<button data-pal="${k}" aria-pressed="false"><span class="sw">${p.cols.slice(0,3).map(c=>`<i style="background:${c}"></i>`).join('')}</span>${p.name}</button>`).join('');
  for(const [id,key,f] of SLIDERS){const el=$('#'+id);
    el.addEventListener('input',()=>{S[key]=+el.value;delete tweens[key];setP(el);$('#v'+id.slice(1)).textContent=f(S[key]);
      if(key==='lamps')buildLamps();if(key==='choir'||key==='verb')applyAudio();saveSettings();});}
  $('#cChase').addEventListener('change',e=>{S.chase=e.target.value;saveSettings();});
  $('#cQuality').addEventListener('change',e=>{S.quality=e.target.value;stages.forEach(s=>s.resize());saveSettings();toast('Render quality',`${e.target.selectedOptions[0].text} — pixel ratio and snow count adjusted.`);});
  $('#palSeg').addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;S.palette=b.dataset.pal;syncUI();saveSettings();pulse=.8;});
  const tg=(id,key)=>$('#'+id).addEventListener('click',()=>{S[key]=!S[key];syncUI();saveSettings();});
  tg('tDrift','drift');tg('tBlueprint','blueprint');tg('tGuides','guides');
  $('#voiceChips').addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;const s=b.dataset.sec;S.sections[s]=!S.sections[s];syncUI();applyAudio();saveSettings();
    log(assign.choir||'STAGE',`${SECTIONS.find(x=>x.k===s).name} ${S.sections[s]?'back on':'pulled from'} the bus`,S.sections[s]?'':'warn');});
  $('#btnTestChoir').addEventListener('click',()=>{if(!assign.choir){toast('The choir ring has no owner','Assign an agent to the choir ring first.',{ac:'var(--warn)',icon:'!'});return;}hum();toast('Tuning chord','B♭ major, all enabled sections, through the cathedral reverb.',{icon:'♪',ac:'var(--ice)'});});
  $('#btnReset').addEventListener('click',()=>{const prev=clone(S);tweens={};applySettings(DEFAULTS);saveSettings();
    toast('Console reset','Defaults restored.',{action:'Undo',onAction:()=>{applySettings(prev);saveSettings();}});});
  $('#btnRandom').addEventListener('click',()=>{const keys=Object.keys(PALETTES),ch=['wave','chase','sparkle','candle','steady'],r=(a,b)=>Math.round(a+Math.random()*(b-a));
    Object.assign(S,{palette:keys[r(0,keys.length-1)],chase:ch[r(0,4)],twinkle:r(20,180),bloom:r(70,160),star:r(40,100),snow:r(0,90),wind:r(-60,60),haze:r(10,80)});
    tweens={};syncUI();saveSettings();pulse=1;starBoost=.6;log('STAGE',`New look · ${PALETTES[S.palette].name} · ${$('#cChase').selectedOptions[0].text}`,'');});
  $('#btnPng').addEventListener('click',exportPNG);
  $('#btnJson').addEventListener('click',exportJSON);
  syncUI();
}
function exportPNG(){
  const m=stages[1];m.render(performance.now()/1000,0);
  m.c.toBlob(b=>{if(!b){toast('Export failed','The browser refused to encode the frame.',{ac:'var(--danger)'});return;}
    download(`singing-tree-frame-${Date.now()}.png`,b,'image/png');toast('Frame exported',`${m.c.width}×${m.c.height} PNG from CAM 01.`,{icon:'⤓'});},'image/png');
}
function cueSheet(){
  return JSON.stringify({production:'The Singing Tree · Marina Bay 2026',exported:new Date().toISOString(),timezone:'Asia/Singapore',
    console:S,palette:PALETTES[S.palette],
    crew:ZONES.map(z=>({zone:z.name,agent:assign[z.id],specialist:assign[z.id]?agentById(assign[z.id]).home===z.id:null})),
    readiness:Math.round(readiness()*100)+'%',
    runOfShow:CUES.map((c,i)=>({cue:i+1,at:mmss(c.t),name:c.name,description:c.desc,owners:c.zones.map(z=>assign[z]||'VACANT'),settings:c.set})),
    repertoire:CAROLS.map(c=>({title:c.title,key:c.key,meter:c.meter,seconds:+c.arr.dur.toFixed(1)}))},null,2);
}
function exportJSON(){download('singing-tree-cue-sheet.json',cueSheet(),'application/json');toast('Cue sheet exported','Console, crew and all seven cues as JSON.',{icon:'⤓'});}

/* ============================ AGENT BOARD ============================ */
let selAgent=null,boardWasFull=false;
function renderBoard(){
  $('#roster').innerHTML=AGENTS.map(a=>{const z=zoneOf(a.id);
    const st=z?`ON STATION · ${zoneById(z).name.toUpperCase()}${a.home!==z?' · 80%':''}`:'IDLE · AWAITING A ZONE';
    const load=z?(a.home===z?Math.round(62+hash(a.id)*28):96):6;
    return `<button class="agent${selAgent===a.id?' sel':''}${z?'':' idle'}" draggable="true" data-agent="${a.id}" style="--ac:${a.ac}" aria-pressed="${selAgent===a.id}"><span class="av">${a.code}</span><span class="info"><b>${a.id}</b><span>${a.role}</span><small>${st}</small></span><span class="load" title="Load ${load}%"><i style="width:${load}%"></i></span></button>`;}).join('');
  $('#zones').innerHTML=ZONES.map(z=>{const aid=assign[z.id],a=aid&&agentById(aid);
    return `<div class="zone${a?'':' vacant'}${selAgent?' target':''}${focusZone===z.id&&performance.now()<focusUntil?' focused':''}" data-zone="${z.id}" tabindex="0" role="button" aria-label="${z.name}: ${a?'owned by '+a.id:'vacant'}${selAgent?'. Place '+selAgent+' here':''}">${z.crit?'<span class="crit">CRITICAL</span>':''}<h4>${z.name}</h4><p class="meta">${z.meta}</p><div class="slot${a?' filled':''}"${a?` style="--ac:${a.ac}"`:''}>${a?`<span class="dot" style="color:${a.ac}"></span><div><b>${a.id}</b><small>${a.home===z.id?'Specialist · 100%':'Covering · 80% throughput'}</small></div><button class="x" data-unassign="${z.id}" aria-label="Remove ${a.id} from ${z.name}">×</button>`:'<span class="empty">◌ VACANT — DROP AN AGENT</span>'}</div></div>`;}).join('');
  updateReadiness();
}
function updateReadiness(){
  const r=readiness(),pct=Math.round(r*100),vac=ZONES.filter(z=>!assign[z.id]),idle=AGENTS.filter(a=>!zoneOf(a.id));
  $('#readyRing').setAttribute('stroke-dashoffset',(213.6*(1-r)).toFixed(1));$('#readyPct').textContent=pct+'%';
  const words=['Zero','One','Two','Three','Four','Five','Six','Seven','Eight'];
  if(!vac.length){$('#readyTitle').textContent='All eight zones owned — ready for curtain';
    $('#readySub').textContent=ZONES.every(z=>agentById(assign[z.id]).home===z.id)?'Every agent is on its specialist station.':'Some agents are covering outside their specialty at 80% throughput.';}
  else{$('#readyTitle').textContent=`${words[vac.length]} zone${vac.length>1?'s':''} unowned — the show is on hold`;
    const names=vac.map(z=>z.name.toLowerCase());const list=names.length>1?names.slice(0,-1).join(', ')+' and '+names.slice(-1):names[0];
    $('#readySub').textContent=`${list[0].toUpperCase()+list.slice(1)} ${vac.length>1?'are':'is'} dark. ${idle.length?`Place the ${idle.length===1?'idle agent':words[idle.length].toLowerCase()+' idle agents'}, or let the scheduler do it.`:'Let the scheduler do it.'}`;}
  const ba=$('#btnAuto');ba.disabled=!vac.length;ba.classList.toggle('pulse',!!vac.length);
  $('#btnClear').disabled=!ownedCount();
}
function commitBoard(){
  store.set('assign',assign);updateZF();renderBoard();renderTimeline();applyAudio();
  const full=readiness()===1;
  if(full&&!boardWasFull)toast('All eight zones owned','The tree is fully crewed — ready for curtain.',{ac:'var(--mint)',icon:'✓'});
  boardWasFull=full;
}
function place(aid,zid){
  if(!aid||!zid)return;
  const from=zoneOf(aid),prev=assign[zid];
  if(prev===aid){selAgent=null;renderBoard();return;}
  assign[zid]=aid;if(from)assign[from]=null;
  if(prev&&from){assign[from]=prev;log(prev,`Swapped to ${zoneById(from).name}`,'');}
  else if(prev)log(prev,`Relieved from ${zoneById(zid).name} · now idle`,'warn');
  const a=agentById(aid);
  log(aid,`On station · ${zoneById(zid).name}${a.home!==zid?' · outside specialty, 80% throughput':''}`,a.home===zid?'ok':'warn');
  selAgent=null;focusZone=zid;focusUntil=performance.now()+2200;commitBoard();
}
function unassign(zid){
  const aid=assign[zid];if(!aid)return;assign[zid]=null;log(aid,`Stood down from ${zoneById(zid).name}`,'warn');commitBoard();
  toast(`${aid} stood down`,`${zoneById(zid).name} is now vacant.`,{ac:'var(--warn)',action:'Undo',onAction:()=>{if(!assign[zid]&&!zoneOf(aid)){assign[zid]=aid;log(aid,`Back on ${zoneById(zid).name}`,'ok');commitBoard();}}});
}
function autoAssign(){
  const vac=ZONES.filter(z=>!assign[z.id]);if(!vac.length)return;
  let n=0;
  for(const z of vac){const idle=AGENTS.filter(a=>!zoneOf(a.id));if(!idle.length)break;
    const a=idle.find(x=>x.home===z.id)||idle[0];assign[z.id]=a.id;n++;
    log(a.id,`Scheduler · on station · ${z.name}${a.home!==z.id?' · covering':''}`,'ok');}
  selAgent=null;commitBoard();if(n&&readiness()<1)toast('Crew auto-assigned',`${n} zone(s) filled.`,{ac:'var(--mint)',icon:'⚡'});
}
function initBoard(){
  const roster=$('#roster'),zones=$('#zones');
  roster.addEventListener('click',e=>{const b=e.target.closest('.agent');if(!b)return;selAgent=selAgent===b.dataset.agent?null:b.dataset.agent;renderBoard();
    if(selAgent){const z=$(`.agent[data-agent="${selAgent}"]`);z&&z.focus({preventScroll:true});}});
  roster.addEventListener('dragstart',e=>{const b=e.target.closest('.agent');if(!b)return;e.dataTransfer.setData('text/plain',b.dataset.agent);e.dataTransfer.effectAllowed='move';
    b.classList.add('drag');$$('.zone',zones).forEach(z=>z.classList.add('target'));});
  roster.addEventListener('dragend',()=>{$$('.agent').forEach(a=>a.classList.remove('drag'));$$('.zone').forEach(z=>z.classList.remove('target','over'));});
  zones.addEventListener('dragover',e=>{const z=e.target.closest('.zone');if(!z)return;e.preventDefault();e.dataTransfer.dropEffect='move';
    $$('.zone.over',zones).forEach(x=>x!==z&&x.classList.remove('over'));z.classList.add('over');});
  zones.addEventListener('dragleave',e=>{const z=e.target.closest('.zone');if(z&&!z.contains(e.relatedTarget))z.classList.remove('over');});
  zones.addEventListener('drop',e=>{const z=e.target.closest('.zone');if(!z)return;e.preventDefault();place(e.dataTransfer.getData('text/plain'),z.dataset.zone);});
  const act=z=>{if(selAgent)place(selAgent,z.dataset.zone);else{focusZone=z.dataset.zone;focusUntil=performance.now()+2600;renderBoard();
    const a=assign[focusZone];toast(zoneById(focusZone).name,a?`Owned by ${a} — highlighted on the stage monitor.`:'Vacant — select an agent, then tap here.',{ac:a?'var(--ice)':'var(--warn)',life:2600});}};
  zones.addEventListener('click',e=>{const x=e.target.closest('[data-unassign]');if(x){e.stopPropagation();unassign(x.dataset.unassign);return;}const z=e.target.closest('.zone');if(z)act(z);});
  zones.addEventListener('keydown',e=>{if(e.target.classList.contains('zone')&&(e.key==='Enter'||e.key===' ')){e.preventDefault();act(e.target);}});
  document.addEventListener('keydown',e=>{if(e.key==='Escape'&&selAgent){selAgent=null;renderBoard();}});
  $('#btnAuto').addEventListener('click',autoAssign);
  $('#btnClear').addEventListener('click',()=>{const prev={...assign};for(const k in assign)assign[k]=null;log('STAGE','Board cleared · all agents stood down','bad');commitBoard();
    toast('Board cleared','Every zone is vacant; the tree is dark.',{ac:'var(--danger)',action:'Undo',life:6500,onAction:()=>{assign=prev;log('STAGE','Crew restored','ok');commitBoard();}});});
  boardWasFull=readiness()===1;renderBoard();
}
const CHATTER={
  upper:()=>`Upper canopy · 48/48 blocks · ${(96+Math.random()*3.8).toFixed(1)}% lamp health`,
  lower:()=>`Lower canopy · block ${(Math.random()*48|0)+1} re-addressed · 0 dark lamps`,
  topper:()=>`Topper · gimbal ${(Math.random()*2).toFixed(1)}° · spark fountains armed 12/12`,
  choir:()=>`Ring pitch A = ${(440+Math.random()*.8-.4).toFixed(1)} Hz · ${Math.round(28+Math.random()*2)} °C on stage`,
  snow:()=>`Gusts ${Math.round(Math.abs(S.wind)*.3+Math.random()*3)} km/h · foam reserve ${Math.round(60+Math.random()*35)}%`,
  power:()=>`Feed A ${Math.round(100+Math.random()*12)} kW · Feed B ${Math.round(98+Math.random()*12)} kW · shed plan idle`,
  crowd:()=>`Plaza density ${(0.6+Math.random()*.7).toFixed(2)} p/m² · all egress routes clear`,
  herald:()=>`Box office · ${Math.round(40+Math.random()*120)} reservations in the last hour`
};
setInterval(()=>{if(document.hidden)return;const owned=ZONES.filter(z=>assign[z.id]);if(!owned.length)return;
  const z=owned[(Math.random()*owned.length)|0];log(assign[z.id],CHATTER[z.id](),'');},9000);

/* ============================ CHOIR SECTION ============================ */
function initChoir(){
  $('#secBars').innerHTML=SECTIONS.map(s=>`<div class="sec-row"><b style="color:${s.col}">${s.name.toUpperCase()}</b><div class="bar"><i style="background:${s.col}" data-w="${s.n/384*100}"></i><u data-sec="${s.k}"></u></div><span>${s.n}</span></div>`).join('');
  renderRepertoire();
  $('#repertoire').addEventListener('click',e=>{const b=e.target.closest('.carol');if(!b)return;if(song&&song.c.id===b.dataset.id){stopCarol();log(assign.choir||'STAGE','Cut-off · ring released','');}else playCarol(b.dataset.id);});
  $('#npStop').addEventListener('click',()=>{if(song){stopCarol();log(assign.choir||'STAGE','Cut-off · ring released','');}});
}
function renderRepertoire(){
  const PLAY='<svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true"><path d="M3 1.5v9l7.5-4.5z" fill="currentColor"/></svg>';
  const STOP='<svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true"><rect x="2.5" y="2.5" width="7" height="7" rx="1" fill="currentColor"/></svg>';
  $('#repertoire').innerHTML=CAROLS.map((c,i)=>{const on=song&&song.c.id===c.id;
    return `<button class="carol${on?' playing':''}" data-id="${c.id}" aria-pressed="${!!on}"><span class="no">${String(i+1).padStart(2,'0')}</span><span class="ttl"><b>${c.title}</b><span>${c.key.toUpperCase()} · ${c.meter} · SATB · ARR. CANTUS-04</span></span><span class="dur">${mmss(c.arr.dur)}</span><span class="playicon">${on?STOP:PLAY}</span></button>`;}).join('');
}

/* ============================ BOOKING ============================ */
const DATES=(()=>{const out=[],d0=Date.UTC(2026,11,12);for(let i=0;i<24;i++){const x=new Date(d0+i*864e5),iso=x.toISOString().slice(0,10);
  out.push({iso,dark:iso==='2026-12-15'||iso==='2026-12-22',label:x.toLocaleDateString('en-GB',{weekday:'short',day:'numeric',month:'short',timeZone:'UTC'})});}return out;})();
const TIERS=[
  {id:'free',name:'Promenade',desc:'Free standing on the waterfront',price:0,cap:2400,ac:'var(--ice)',plan:'plan-free'},
  {id:'canopy',name:'Canopy Circle',desc:'Seated under the lower boughs',price:28,cap:420,ac:'var(--gold)',plan:'plan-canopy'},
  {id:'loft',name:'Choir Loft',desc:'Standing beside the choir ring',price:58,cap:120,ac:'var(--mint)',plan:'plan-loft'}
];
const QUIET=['2026-12-13','2026-12-20'];
const todayIso=new Date().toISOString().slice(0,10);
const bk={date:(DATES.find(d=>!d.dark&&d.iso>=todayIso)||DATES.find(d=>!d.dark)).iso,time:'19:30',tier:'canopy',qty:2};
const timesFor=iso=>iso==='2026-12-31'?['19:30','20:30','21:30','23:45']:['19:30','20:30','21:30'];
const bookings=()=>store.get('bookings',[]);
function remaining(){
  const tier=TIERS.find(t=>t.id===bk.tier);let left=Math.round(tier.cap*(.05+.6*hash(bk.date+bk.time+bk.tier)));
  left-=bookings().filter(b=>b.date===bk.date&&b.time===bk.time&&b.tier===bk.tier).reduce((s,b)=>s+b.qty,0);return Math.max(0,left);
}
function highlightPlan(tid){const plan=tid&&TIERS.find(t=>t.id===tid).plan;TIERS.forEach(t=>document.getElementById(t.plan)?.classList.toggle('dim',!!plan&&t.plan!==plan));}
function renderBooking(){
  $('#dateChips').innerHTML=DATES.map(d=>{const sm=d.dark?'DARK':d.iso==='2026-12-31'?'+ COUNTDOWN':QUIET.includes(d.iso)?'QUIET 19:30':'3 SHOWS';
    return `<button data-date="${d.iso}" aria-pressed="${bk.date===d.iso}"${d.dark?' disabled':''}>${d.label}<small>${sm}</small></button>`;}).join('');
  if(!timesFor(bk.date).includes(bk.time))bk.time='19:30';
  $('#timeChips').innerHTML=timesFor(bk.date).map(t=>{const sm=t==='23:45'?'COUNTDOWN':(t==='19:30'&&QUIET.includes(bk.date))?'QUIET SHOW':'60 MIN';
    return `<button data-time="${t}" aria-pressed="${bk.time===t}">${t}<small>${sm}</small></button>`;}).join('');
  $('#tiers').innerHTML=TIERS.map(t=>`<button class="tier" data-tier="${t.id}" style="--ac:${t.ac}" aria-pressed="${bk.tier===t.id}"><span class="rad"></span><span><b>${t.name}</b><span>${t.desc}</span></span><span class="price">${t.price?'S$'+t.price:'Free'}</span></button>`).join('');
  updateTotal();highlightPlan(bk.tier);
}
function updateTotal(){
  const tier=TIERS.find(t=>t.id===bk.tier),left=remaining(),tot=tier.price*bk.qty;
  $('#qtyVal').textContent=bk.qty;$('#totalNote').textContent=`${bk.qty} GUEST${bk.qty>1?'S':''}`;
  $('#totalVal').textContent=tot?'S$'+fmt(tot):'Free';
  const an=$('#availNote');
  if(left<bk.qty){an.textContent=left?`ONLY ${left} LEFT`:'SOLD OUT';an.style.color='var(--danger)';}
  else{an.textContent=`${fmt(left)} ${tier.id==='canopy'?'SEATS':'PLACES'} LEFT`;an.style.color=left<30?'var(--warn)':'var(--mint)';}
  $('#btnConfirm').disabled=left<bk.qty;
}
const EMAIL_RE=/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
function renderDone(b){
  const tier=TIERS.find(t=>t.id===b.tier),d=DATES.find(x=>x.iso===b.date);
  $('#bookingForm').hidden=true;const el=$('#bookingDone');el.hidden=false;
  el.innerHTML=`<div class="confirm"><div class="seal"><svg width="34" height="34" viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12.5l4.2 4.2L19 7" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/></svg></div>
    <h3>You’re under the tree</h3><p style="color:var(--muted);font-size:13.5px">HERALD-08 has held your place. Show this reference at the Bayfront gate.</p>
    <div class="refbox">${esc(b.ref)}</div>
    <div class="recap"><div><span>Night</span><b>${esc(d?d.label:b.date)}</b></div><div><span>Showtime</span><b>${esc(b.time)} SGT</b></div>
    <div><span>Tier</span><b>${esc(tier.name)}</b></div><div><span>Guests</span><b>${b.qty}</b></div>
    <div><span>Lead guest</span><b>${esc(b.name)}</b></div><div><span>Total</span><b>${b.total?'S$'+fmt(b.total):'Free'}</b></div></div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px"><button class="btn btn-sm btn-primary" id="btnPass">⤓ Download pass</button><button class="btn btn-sm" id="btnAnother">Book another</button></div></div>`;
  $('#btnPass').addEventListener('click',()=>{download(`singing-tree-pass-${b.ref}.txt`,
    `THE SINGING TREE · MARINA BAY 2026\n==================================\nReference : ${b.ref}\nNight     : ${d?d.label:b.date} (${b.date})\nShowtime  : ${b.time} SGT\nTier      : ${tier.name}\nGuests    : ${b.qty}\nLead guest: ${b.name}\nTotal     : ${b.total?'S$'+b.total:'Free'}\n\nBayfront Promenade, Marina Bay, Singapore 018956\nEnter via Bayfront MRT Exit B. Held until 20 minutes past the half-hour call.\n\nA fictional production — demonstration pass, no payment taken.\n`,'text/plain');});
  $('#btnAnother').addEventListener('click',()=>{el.hidden=true;$('#bookingForm').hidden=false;renderBooking();});
}
function initBooking(){
  renderBooking();
  $('#dateChips').addEventListener('click',e=>{const b=e.target.closest('button');if(!b||b.disabled)return;bk.date=b.dataset.date;renderBooking();});
  $('#timeChips').addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;bk.time=b.dataset.time;renderBooking();});
  const tiers=$('#tiers');
  tiers.addEventListener('click',e=>{const b=e.target.closest('.tier');if(!b)return;bk.tier=b.dataset.tier;renderBooking();});
  tiers.addEventListener('mouseover',e=>{const b=e.target.closest('.tier');if(b)highlightPlan(b.dataset.tier);});
  tiers.addEventListener('mouseleave',()=>highlightPlan(bk.tier));
  $('#qtyMinus').addEventListener('click',()=>{bk.qty=Math.max(1,bk.qty-1);updateTotal();});
  $('#qtyPlus').addEventListener('click',()=>{if(bk.qty>=8){toast('Eight guests per reservation','Make a second reservation for larger groups.',{icon:'i'});return;}bk.qty++;updateTotal();});
  const nm=$('#bkName'),em=$('#bkEmail');
  nm.addEventListener('input',()=>{nm.classList.remove('err');$('#errName').classList.remove('show');});
  em.addEventListener('input',()=>{em.classList.remove('err');$('#errEmail').classList.remove('show');});
  $('#btnConfirm').addEventListener('click',()=>{
    const name=nm.value.trim(),email=em.value.trim();let ok=true;
    if(name.length<2){nm.classList.add('err');$('#errName').classList.add('show');ok=false;}
    if(!EMAIL_RE.test(email)){em.classList.add('err');$('#errEmail').classList.add('show');ok=false;}
    if(!ok){(name.length<2?nm:em).focus();return;}
    if(remaining()<bk.qty){updateTotal();return;}
    const tier=TIERS.find(t=>t.id===bk.tier);
    const ref='ST-'+bk.date.slice(5).replace('-','')+'-'+Math.random().toString(36).slice(2,6).toUpperCase();
    const b={ref,date:bk.date,time:bk.time,tier:bk.tier,qty:bk.qty,name,email,total:tier.price*bk.qty,at:new Date().toISOString()};
    const list=bookings();list.push(b);store.set('bookings',list.slice(-20));
    log(assign.herald||'STAGE',`Reservation ${ref} · ${b.qty} × ${tier.name} · ${b.time}`,'ok');
    if(!assign.herald)log('STAGE','Box office unowned — confirmation queued until HERALD is back','warn');
    toast('Reservation confirmed',`${ref} · ${b.qty} × ${tier.name}`,{ac:'var(--mint)',icon:'✓'});
    nm.value='';em.value='';renderDone(b);
  });
  const last=bookings().slice(-1)[0];if(last&&TIERS.some(t=>t.id===last.tier))renderDone(last);
}

/* ============================ PAGE CHROME ============================ */
function initChrome(){
  const items=['42 m Douglas fir · 38,400 addressable lamps','1,284 voices across four sections','Eight agents · eight zones · zero dead air',
    'Shows nightly 19:30 · 20:30 · 21:30 SGT','Countdown show 23:45 · 31 December','Bayfront MRT Exit B · 4 min walk',
    'Snow by FLURRY-06 · biodegradable foam flakes','Power by VESTA-02 · 214 kW on two feeds','Free promenade standing every night'];
  $('#tickerTrack').innerHTML=[...items,...items].map(s=>`<span>${s}</span>`).join('');
  $('#meter').innerHTML='<i></i>'.repeat(18);
  const burger=$('#burger'),links=$('#navLinks');
  burger.addEventListener('click',()=>{const o=burger.getAttribute('aria-expanded')!=='true';burger.setAttribute('aria-expanded',o);links.classList.toggle('open',o);});
  links.addEventListener('click',e=>{if(e.target.closest('a')){burger.setAttribute('aria-expanded','false');links.classList.remove('open');}});
  const navMap=new Map($$('.nav-links a').map(a=>[a.getAttribute('href').slice(1),a]));
  const io=new IntersectionObserver(es=>{for(const e of es)if(e.isIntersecting){$$('.nav-links a').forEach(a=>a.classList.remove('active'));navMap.get(e.target.id)?.classList.add('active');}},{rootMargin:'-45% 0px -50% 0px'});
  $$('main section[id]').forEach(s=>io.observe(s));
  const prog=$('#progress'),top=$('#toTop');
  const onScroll=()=>{const h=document.documentElement;const p=h.scrollTop/Math.max(1,h.scrollHeight-h.clientHeight);prog.style.width=(p*100)+'%';top.classList.toggle('show',h.scrollTop>innerHeight*.9);};
  addEventListener('scroll',onScroll,{passive:true});onScroll();
  top.addEventListener('click',()=>scrollTo({top:0,behavior:REDUCED?'auto':'smooth'}));
  const rv=new IntersectionObserver(es=>{for(const e of es)if(e.isIntersecting){e.target.classList.add('in');rv.unobserve(e.target);
    if(e.target.id==='statsBand')countUp();$$('.bar i[data-w]',e.target).forEach(i=>i.style.width=i.dataset.w+'%');}},{threshold:.12});
  $$('.reveal').forEach(el=>rv.observe(el));
  const sb=$('#soundBtn');
  const syncSound=()=>{sb.classList.toggle('off',!AU.on);sb.setAttribute('aria-pressed',AU.on);$('#soundLbl').textContent=AU.on?'Sound on':'Sound off';};
  sb.addEventListener('click',e=>{e.stopPropagation();AU.on=!AU.on;store.set('sound',AU.on);initAudio();applyAudio();syncSound();});
  syncSound();
  const wake=()=>{initAudio();removeEventListener('pointerdown',wake);removeEventListener('keydown',wake);};
  addEventListener('pointerdown',wake);addEventListener('keydown',wake);
  const tickClock=()=>{const t=sgtNow();$('#clock').textContent=t;$('#footClock').textContent=t.slice(0,5);};tickClock();setInterval(tickClock,1000);
  $('#heroRun').addEventListener('click',()=>{initAudio();const before=ownedCount();autoAssign();
    if(ownedCount()>before)log('STAGE','Briefing · scheduler filled every vacant zone','ok');
    if(show.state==='run'){toast('Show already running','Open the console to take over.',{icon:'▶'});return;}
    if(show.state!=='idle')showReset();showRun();
    toast('Agents briefed — show running','All eight zones owned. Open the console to take over mid-show.',{ac:'var(--mint)',icon:'▶',action:'Console',onAction:()=>$('#console').scrollIntoView({behavior:REDUCED?'auto':'smooth'})});});
  for(const n of ['2','3']){$('#runBtn'+n).addEventListener('click',showRun);$('#pauseBtn'+n).addEventListener('click',showPause);$('#stopBtn'+n).addEventListener('click',showReset);}
  $('#timeline').addEventListener('click',e=>{const b=e.target.closest('.cue');if(b)seek(CUES[+b.dataset.cue].t,{andRun:true});});
  $('#scrubMarks').innerHTML=CUES.map(c=>`<i style="left:${c.t/SHOW_LEN*100}%"></i>`).join('');
  const scrub=$('#scrub');let scrubbing=false;
  const at=e=>{const r=scrub.getBoundingClientRect();return clamp((e.clientX-r.left)/r.width,0,1)*SHOW_LEN;};
  scrub.addEventListener('pointerdown',e=>{scrubbing=true;try{scrub.setPointerCapture(e.pointerId);}catch(_){}seek(at(e));});
  scrub.addEventListener('pointermove',e=>{if(scrubbing)seek(at(e));});
  scrub.addEventListener('pointerup',()=>{scrubbing=false;});scrub.addEventListener('pointercancel',()=>{scrubbing=false;});
  scrub.addEventListener('keydown',e=>{const d={ArrowRight:2,ArrowUp:2,ArrowLeft:-2,ArrowDown:-2}[e.key];if(d){e.preventDefault();seek(show.t+d);}
    if(e.key==='Home'){e.preventDefault();seek(0);}if(e.key==='End'){e.preventDefault();seek(SHOW_LEN-.01);}});
  $('#footCue').addEventListener('click',exportJSON);
  $('#footPress').addEventListener('click',()=>download('singing-tree-press-kit.txt',
`THE SINGING TREE · MARINA BAY 2026 — PRESS KIT
===============================================
Season    : 12 December 2026 – 4 January 2027 (dark 15 & 22 Dec)
Venue     : Bayfront Promenade, Marina Bay, Singapore 018956
Shows     : 19:30 · 20:30 · 21:30 SGT nightly; countdown show 23:45 on 31 Dec

THE TREE  : 42 m Douglas fir · 38,400 addressable lamps in 96 blocks · 1,912 ornaments
THE CHOIR : 1,284 voices — Soprano 384 · Alto 336 · Tenor 288 · Bass 276
THE CREW  : eight autonomous agents, one per production zone
${AGENTS.map(a=>`  ${a.id.padEnd(12)} ${a.role}`).join('\n')}

RUN OF SHOW (compressed 56 s demo)
${CUES.map((c,i)=>`  ${String(i+1).padStart(2)}. ${mmss(c.t)}  ${c.name}`).join('\n')}

A fictional production built as an interactive front-end.
`,'text/plain'));
  const nf=$('#newsForm');nf.addEventListener('submit',e=>{e.preventDefault();const v=$('#newsEmail').value.trim();
    if(!EMAIL_RE.test(v)){$('#errNews').classList.add('show');$('#newsEmail').classList.add('err');return;}
    $('#errNews').classList.remove('show');$('#newsEmail').classList.remove('err');store.set('news',true);
    $('#newsOk').style.display='block';$('#newsEmail').value='';log(assign.herald||'STAGE','New subscriber on the curtain-call list','ok');});
  if(store.get('news',false))$('#newsOk').style.display='block';
}
function countUp(){
  $$('#statsBand b[data-count]').forEach(b=>{const to=+b.dataset.count,suf=b.dataset.suffix||'',t0=performance.now(),d=REDUCED?1:1400;
    const step=now=>{const p=Math.min(1,(now-t0)/d),e=1-Math.pow(1-p,3);b.textContent=fmt(to*e)+suf;if(p<1)requestAnimationFrame(step);};requestAnimationFrame(step);});
}

/* ============================ HUD & LOOP ============================ */
function updateHUD(fps){
  const lit=(assign.upper?19200:0)+(assign.lower?19200:0);
  const voices=ZF.choir&&S.choir>0?SECTIONS.filter(s=>S.sections[s.k]).reduce((a,s)=>a+s.n,0):0;
  const load=Math.round(28+lit/38400*150*(S.bloom/100)*(assign.power?1:.45)+S.snow*.25+S.haze*.1);
  $('#hudLamps').textContent=fmt(lit);$('#hudVoices').textContent=fmt(voices);$('#hudLoad').textContent=load;
  $('#hudWind').textContent=Math.round(Math.abs(S.wind)*.3);$('#hudAgents').textContent=`${ownedCount()}/8`;
  $('#hudReady').textContent=Math.round(readiness()*100)+'%';$('#hudFps').textContent=Math.round(fps)+' FPS';
  const ms=$('#monState');
  const dark=ZONES.filter(z=>['upper','lower','power'].includes(z.id)&&!assign[z.id]).map(z=>z.name.toUpperCase());
  if(dark.length){ms.textContent=dark.join(' · ')+' DARK';ms.className='chip warn';}else{ms.textContent=fmt(lit)+' LAMPS';ms.className='chip';}
}
function updateMeter(){
  const bars=$('#meter').children;let data=null;
  if(AU.ctx&&AU.analyser&&AU.on){AU.analyser.getByteFrequencyData(AU.fbuf);data=AU.fbuf;}
  for(let i=0;i<bars.length;i++){let v;
    if(data){v=data[Math.min(data.length-1,2+i*2)]/255;}else v=pulse*.6*Math.abs(Math.sin(i*1.7+performance.now()/300))+.05;
    bars[i].style.height=Math.max(2,v*24)+'px';}
  for(const s of SECTIONS){const u=$(`.bar u[data-sec="${s.k}"]`);if(u)u.style.width=(s.n/384*100*secLevel[s.k])+'%';}
}
let stages=[],last=performance.now(),fpsAcc=0,fpsN=0,fps=60,hudT=0;
function frame(now){
  const raw=Math.min(.25,(now-last)/1000),dt=Math.min(.05,raw);last=now;const t=now/1000;
  pulse*=Math.exp(-dt*3.2);starBoost*=Math.exp(-dt*1.4);
  for(const s of 'SATB')secLevel[s]*=Math.exp(-dt*2);
  tweenUpdate(raw);showUpdate(raw);
  const wind=S.wind/100,ns=Math.round(S.snow/100*(SNOW_MAX[S.quality]||420)*ZF.snow);
  for(let i=0;i<ns;i++){const p=snow[i];p.y+=p.v*dt;p.x+=(wind*.09+Math.sin(t*.8+p.ph)*.012)*dt*(p.v*10);
    if(p.y>1.02){p.y=-.02;p.x=Math.random();}if(p.x>1.02)p.x-=1.04;else if(p.x<-.02)p.x+=1.04;}
  for(let i=sparks.length-1;i>=0;i--){const s=sparks[i];s.y+=s.v*dt;if(s.y>=1){sparks.splice(i,1);starBoost=Math.min(1.4,starBoost+.7);pulse=Math.min(1,pulse+.4);}}
  for(const st of stages)if(st.visible)st.render(t,dt);
  fpsAcc+=dt;fpsN++;hudT+=dt;
  if(hudT>.25){fps=fpsN/fpsAcc;fpsAcc=0;fpsN=0;hudT=0;updateHUD(fps);}
  updateMeter();if(show.state!=='idle'||$('#scrubFill').style.width!=='0%')updateShowUI();
  requestAnimationFrame(frame);
}

/* ============================ BOOT ============================ */
updateZF();buildLamps();buildBaubles();
stages=[new Stage($('#heroCanvas'),{hero:true,yaw:.4}),new Stage($('#monitorCanvas'),{hero:false})];
initConsole();initBoard();initChoir();renderTimeline();syncTransport();initBooking();initChrome();
log('STAGE','Ops feed online · season 2026 · Bayfront Promenade','ok');
ZONES.forEach(z=>{if(assign[z.id])log(assign[z.id],`On station · ${z.name}`,'');});
ZONES.filter(z=>!assign[z.id]).forEach(z=>log('STAGE',`${z.name} has no owner — zone dark`,'warn'));
requestAnimationFrame(frame);
