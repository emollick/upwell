import {
  ROOMS,
  PROPS,
  CARRIED,
  FEEDS,
  STOPS,
  TRAFFIC,
  travel,
  shipTimeAtRideSeconds, rideSecondsAtShipTime, shipRateAtRideSeconds,
  kmText,
  altitudeText, RIDE_SECONDS,
  clamp,
  freshState,
  restore,
  save as storePassage,
  visibleProp,
  actionLabel,
  roomAt,
} from './journey.js';
import { CabinAudio } from './audio.js';
import { CabinViews } from './cabin-views.js';
import { SWITCHES, PAGES } from './control-catalog.js';
import {adjacentMoment,linkedObservation,loadMoments,passageTime} from './passage-moments.js';
import {GraphicsDialog} from './graphics.js';
import {PhotoJournal} from './photo-journal.js';
import {handrailLoad,loadLabel} from './flight-physics.js';

const $ = (id) => document.getElementById(id);
const hoverPoint = { x: 0, y: 0 };
const html = (name, cls = '', text = '') => {
  const el = document.createElement(name);
  if (cls) el.className = cls;
  if (text) el.textContent = text;
  return el;
};
const audio = new CabinAudio();
let s = restore(),
  aboard = false,
  mode = 'walk',
  world = null,
  worldTask = null,
  time = 0,
  previous = 0,
  nextUi = 0,
  nextSave = 0;
let modal = '',
  selected = '',
  target = '',
  hoverId = null,
  pointer = null,
  equalizing = false,
  presenting = false,
  monitor = null,
  radio = null,
  toastTimer = 0,
  lastTraffic = '',
  lastEncounter = '';
let rememberedFocus = null,
  boarding = false,
  resetPending = false;
let passageMoments=[],momentOrigin=null,momentFixture=false,momentInspection=null;
let realShipClock=null,stargazingSeconds=0,stargazingFence=null;
let warmupFrames=0;
function releaseStargazingFrame(){
  if(stargazingFence)world.r.getContext().deleteSync(stargazingFence);
  stargazingFence=null;
}
function aboardClock(seconds){
  const whole=Math.max(0,Math.floor(seconds+.000001));
  return [Math.floor(whole/3600),Math.floor(whole/60)%60,whole%60].map(n=>String(n).padStart(2,'0')).join(':');
}
function clockRate(rate){
  return Number(rate.toFixed(rate<.1?2:rate<2?2:rate<10?1:0)).toLocaleString('en-US')+'×';
}
function setPace(real){
  releaseStargazingFrame();
  stargazingSeconds=0;
  s.realShipTime=real;realShipClock=real?shipTimeAtRideSeconds(s.progress*RIDE_SECONDS):null;
  nextUi=0;save(s);
}
function paceControl(body){
  const label=html('label','passage-pace','Passage time'),select=$('boardingPace').cloneNode(true);
  select.removeAttribute('id');select.setAttribute('aria-describedby','inFlightClockHint');select.value=s.realShipTime?'real':'guided';
  select.addEventListener('change',()=>setPace(select.value==='real'));
  const hint=html('p','panel-copy','Guided time speeds up the long climb and slows for close passes. At 1×, one second aboard takes one second. Your hands and loose objects always move in real time.');
  hint.id='inFlightClockHint';label.append(select);body.append(label,hint);
}
const linkedMomentId=new URLSearchParams(location.search).get('moment');
document.addEventListener('visibilitychange',()=>{previous=0;warmupFrames=2;});
const linkedStop=linkedMomentId?linkedObservation(linkedMomentId).catch(()=>null):null;
if(linkedStop)linkedStop.then(linked=>{
  if(linked&&!boarding&&!aboard)$('boardingState').textContent=linked.name+' · '+passageTime(linked.start)+' into the guided ride';
}).catch(()=>{});
const plate=new CabinViews($('station'),selectView,()=>world.deckLoad<=handrailLoad?pushOff():enterAisle());
const graphics=new GraphicsDialog($('graphicsDialog'),()=>world,()=>{
  world.clearKeys();cancelCabinGrip();pointer=null;turning=null;
});
const journal=new PhotoJournal($('photoDialog'),notify,()=>{
  world.clearKeys();cancelCabinGrip();pointer=null;turning=null;
});
$('photoShutter').onclick=()=>journal.request();
$('photoReview').onclick=()=>journal.open();
function enterAisle(){
  const origin=momentOrigin;momentOrigin=null;momentFixture=false;
  const seated=mode==='cabin'&&world.deckLoad<=handrailLoad?world.passengerPose(s.progress*RIDE_SECONDS):null;
  if(origin)s.room=origin.room;
  mode='walk';viewMode();
  if(origin?.free)world.resumePassenger(origin,s,s.progress*RIDE_SECONDS);
  else if(seated&&!origin){world.position.fromArray(seated.position);world.yaw=seated.yaw;world.pitch=seated.pitch;world.flight.reset(world.position.y);world.updateCamera(0);}
  s.room=roomAt(world.position.z);
  sync();
}
function freePassenger(){
  if(mode!=='walk'||world.restId)return false;
  if(modal==='moments'&&momentInspection)return !!momentInspection.angle;
  return modal!=='inspect'||!!world.inspection;
}
function save(state){
  if(aboard&&world){
    state.passenger=freePassenger()?{room:roomAt(world.position.z),...world.passengerPose(state.progress*RIDE_SECONDS)}:
      momentOrigin?.free?momentOrigin:null;
  }
  storePassage(state);
}
function pushOff(direction='away'){
  if(!world||world.deckLoad>handrailLoad)return;
  if(mode==='cabin')enterAisle();
  if(world.restId)stand();
  if(world.pushPassenger(direction)){
    audio.play('handhold');$('scene').focus({preventScroll:true});
  }else notify(direction==='down'&&world.position.y<=world.flight.deckY+.015?'At the deck. Push off to rise.':'Coasting between handholds.');
}
function dockNotice(){
  if(world?.inspection)return 'Docked at Aster Reach · microgravity. Let go to release the item.';
  return matchMedia('(pointer:coarse)').matches?'Docked at Aster Reach · tap Push off.':'Docked at Aster Reach · Space to push off.';
}
const dispatch=[
  'Equatorial anchor. Bridge retracting. Stand clear of the guide bay.',
  'The upper gantry is clear. The ocean platform is below the carriage.',
  'Entering the marine cloud field. Direct sunlight will be intermittent.',
  'We are clearing the high cloud tops.',
  'Stratosphere sector. The atmosphere is thinning.',
  'Passing one hundred kilometres. The bright edge below the window is the atmosphere.',
  'Earth limb sector. The lower camera is tracking the surface.',
  'High orbit. The Earth camera is available at the window seat.',
  'Aster Reach has the carriage. The drive is braking for the receiving vault.',
  'Receiving bay. The capture arms are standing by.',
  'Terminal collar aligned. The service handwheel can seat the transfer clamp.'
];
function selectView(id){
  if(id==='valley'&&s.progress<1){notify('The valley gallery relay connects at the dock.');return;}
  if(id==='floor'&&s.room!=='observation'){notify('The floor port is in the observation saloon.');return;}
  if(id==='shaded'&&s.room!=='observation'){notify('The shaded side window is in the observation saloon.');return;}
  momentOrigin=null;momentFixture=false;
  const change=mode!=='cabin';mode='cabin';if(change){closePanel(false);world.seat(s.room);}
  world.setView(id);plate.update(true,id,s.room);document.body.classList.remove('walking');
  $('hints').hidden=true;$('reticle').hidden=id!=='window';$('target').hidden=true;
  $('stand').hidden=true;hoverId=null;audio.play('click');
}
function notify(msg) {
  clearTimeout(toastTimer);
  $('toast').textContent = msg;
  $('toast').classList.add('shown');
  toastTimer = setTimeout(() => $('toast').classList.remove('shown'), 3400);
}
function syncSound() {
  $('soundButton')
    .querySelector('use')
    .setAttribute('href', audio.enabled ? '#sound' : '#silent');
  $('soundButton').setAttribute(
    'aria-label',
    audio.enabled ? 'Mute cabin sound' : 'Enable cabin sound',
  );
  $('soundButton').setAttribute('aria-pressed', String(audio.enabled));
}
function loadWorld() {
  if (worldTask) return worldTask;
  worldTask = (async () => {
    const { World } = await import('./world.js');
    const w = new World($('scene'));
    const [,moments]=await Promise.all([w.init((n) => {
      if (boarding) $('boardingState').textContent = 'Opening compartments · ' + n + ' / 3';
    }),loadMoments()]);
    passageMoments=moments;
    w.switchboard.receiving=()=>Boolean(radio&&!radio.paused&&!radio.ended&&radio.readyState>=2);
    w.onStep=weight=>audio.play(weight>.20?'step':'handhold');
    w.onFittingStop=(id,cardInTray)=>{
      if(id==='locker_drawer'&&world&&Math.abs(world.position.z)<2.15){
        audio.play('drawerStop');if(cardInTray)audio.play('cardTap');
      }
    };
    w.looseItems.hitSound=(id,force,point)=>audio.impact(id,force,point);
    w.fracture.onSound=(kind,force)=>{
      if(w.position.distanceTo(w.fracture.root.position)>4)return;
      if(kind==='fractureChip')audio.chip(force);else audio.play(kind);
    };
    world = w;
    return w;
  })().catch((e) => {
    console.warn('Carriage startup:', e.message);worldTask=null; $('scene').replaceChildren();
    return null;
  });
  return worldTask;
}
function viewMode(){
  const walk=mode==='walk';$('scene').hidden=false;document.body.classList.toggle('walking',walk);
  if(walk)world.go(s.room);else world.seat(s.room);
  world.setView('window');world.resize();plate.update(!walk,'window',s.room);
  $('reticle').hidden=false;$('target').hidden=true;$('hints').hidden=!walk||!!sessionStorageSafe('upwell.hints');
  $('stand').hidden=true;hoverId=null;target='';
}
function sessionStorageSafe(k, value) {
  try {
    if (value) sessionStorage.setItem(k, value);
    return sessionStorage.getItem(k);
  } catch {
    return null;
  }
}
async function board(seat=false,resume=false) {
  if (boarding) return;

  boarding = true;
  const b = $('board');
  b.disabled = true;
  $('seatBoard').disabled = true;
  b.querySelector('span').textContent = 'Boarding…';
  $('boardingState').textContent = 'Opening the observation saloon';
  audio.start().catch(() => {});
  if(!await loadWorld()){
    boarding=false;b.disabled=false;$('seatBoard').disabled=false;b.querySelector('span').textContent='Try boarding again';
    $('boardingState').textContent='The 3D carriage could not start. Enable WebGL 2 or use the Windows player.';return;
  }
  if(!resume){s=freshState();s.realShipTime=$('boardingPace').value==='real';}
  realShipClock=null;stargazingSeconds=0;
  const savedPose=resume?s.passenger:null;
  if(savedPose)s.room=savedPose.room;
  mode=seat?'cabin':'walk';
  aboard = true;
  boarding = false;
  warmupFrames=2;
  time = 0;
  previous = 0;
  document.body.classList.add('aboard');
  for (const id of ['hud', 'menuButton', 'inventoryButton','graphicsButton','photoTools']) $(id).hidden = false;
  $('landing').hidden = true;
  viewMode();
  if(resume){
    const now=s.progress*RIDE_SECONDS;
    if(savedPose)world.resumePassenger(savedPose,s,now);
    else if(travel(s.progress).forces.gravityG<=handrailLoad)world.resumePassenger(world.passengerPose(0),s,now);
    s.room=roomAt(world.position.z);
  }
  sync();
  if(!resume&&linkedMomentId){
    const linked=await linkedStop;
    const index=passageMoments.findIndex(m=>m.id===linkedMomentId);
    if(index<0&&linked){
      visitObservation(linked);
    }else if(index>=0){
      if(seat){setPassageTime(passageMoments[index].start/RIDE_SECONDS);world.setView('window');notify(passageMoments[index].name);}
      else visitMoment(index);
    }
  }
  if (mode === 'walk') $('scene').focus({ preventScroll: true });
  else $('menuButton').focus({ preventScroll: true });
  setTimeout(() => {
    $('hints').hidden = true;
  }, 20000);
  requestAnimationFrame(frame);
}
function sync() {
  $('networkLabel').textContent = ROOMS[s.room];
  $('bagCount').textContent = s.items.length || '';
  const m = travel(s.progress);
  $('alt').textContent = m.km<1?Math.round(m.km*1000).toLocaleString('en-US'):m.km<20?m.km.toFixed(1):kmText(m.km);
  $('altUnit').textContent=m.km<1?'m':'km';
  $('phase').textContent = m.name;
  $('scaleFill').style.width = s.progress * 100 + '%';
  plate.update(mode==='cabin',world?.view||'window',s.room);
  $('stand').hidden = mode==='cabin'||!world?.restId;
  save(s);
}
function go(room) {
  if (room === 'service' && !s.hatch) {
    audio.play('no');
    notify(
      s.unlocked
        ? 'Open the service hatch from the sleeper.'
        : 'The service hatch needs a crew credential.',
    );
    return;
  }
  if (s.room === 'service' && room !== 'service' && !s.hatch) {
    notify('Open the service hatch to return to the sleeper.');
    return;
  }
  momentOrigin=null;momentFixture=false;
  s.room = room;
  world?.go(room);
  closePanel(false);
  if(mode==='cabin')world.seat(s.room);
  sync();
  notify(ROOMS[room]);
}
function stand() {
  if (world?.restId) world.stand();
  $('stand').hidden = true;
  audio.play('click');
  notify('Back in the aisle.');
}
function takePosition(id) {
  momentOrigin=null;momentFixture=false;
  closePanel(false);
  if(mode==='cabin'){mode='walk';viewMode();}
  world?.rest(id);
  $('hints').hidden=true;$('target').hidden=true;$('reticle').hidden=true;
  $('stand').hidden = false;
  const msg = {
    window: 'At the forward glazing.',
    field_glasses: 'Stabilized optics engaged.',
    lounge_seat: 'Seated at the observation window.',
    bunk: 'Berth restraints fastened.',
    grab_handle: 'Braced at the transfer rail.',
  };
  notify(msg[id]);
  audio.play('click');
}
function closePanel(focus = true) {
  const previousInspection=focus&&modal==='moments'?momentInspection:null;
  momentInspection=null;
  hoverId = null;
  momentFixture=false;
  const aimOnReturn=focus&&modal==='inspect'&&(['accel_test','capillary_primer','fracture_press','fracture_reload'].includes(selected)||selected?.startsWith('loom_service_'))?selected:null;
  cancelCabinGrip();
  $('backdrop').style.cursor='';
  for (const el of [$('scene'), $('station'), $('hud'), document.querySelector('header')]) {
    el.inert = false;
  }
  $('panel').hidden = true;
  $('backdrop').hidden = true;
  monitor = null;
  world?.hideModel();document.body.classList.remove('handling','fitting');$('handlingHint').hidden=true;
  if(aimOnReturn)world.aimFitting(aimOnReturn);
  modal = '';
  selected = '';
  resetPending = false;
  if(previousInspection){restoreInspection(previousInspection);return;}
  if (focus) {
    if (rememberedFocus?.isConnected && rememberedFocus.offsetParent)
      rememberedFocus.focus({ preventScroll: true });
    else $('scene').focus({ preventScroll: true });
  }
}
function openPanel(tag, title, type, id = '') {
  hoverId = null;
  if(type!=='inspect'||id!=='capillary_cell')momentFixture=false;
  if(modal!==type||selected!==id){
    clearTimeout(toastTimer);$('toast').classList.remove('shown');$('toast').textContent='';
  }
  cancelCabinGrip();
  for (const el of [$('scene'), $('station'), $('hud'), document.querySelector('header')]) {
    el.inert = true;
  }
  if (!modal) rememberedFocus = document.activeElement;
  world?.clearKeys();
  world?.hideModel();document.body.classList.remove('handling','fitting');$('handlingHint').hidden=true;
  pointer = null;
  monitor = null;
  modal = type;
  selected = id;
  $('panelTag').textContent = tag;
  $('panelTitle').textContent = title;
  $('panel').dataset.fitting=id;
  $('inspectionMoments').hidden=type!=='inspect';
  $('panelBody').replaceChildren();
  $('panel').hidden = false;
  $('backdrop').hidden = false;
  $('panel').scrollTop = 0;
  $('panelClose').focus({ preventScroll: true });
  return $('panelBody');
}
function button(label, cb, cls = 'quiet') {
  const b = html('button', cls, label);
  b.type = 'button';
  b.addEventListener('click', cb);
  return b;
}
function fixtureButton(label,id){
  let pressed=false,releasedAt=-Infinity;
  const b=button(label,()=>{if(!pressed&&performance.now()-releasedAt>180)operateFixture(id);},'primary');
  const down=()=>{
    if(pressed)return;
    pressed=true;b.classList.add('physically-held');operateFixture(id,true);
  };
  const up=()=>{
    if(!pressed)return;
    pressed=false;releasedAt=performance.now();b.classList.remove('physically-held');
    if(id==='fracture_press')world?.fracture?.release();else world?.fixtures?.release();
  };
  b.addEventListener('pointerdown',e=>{if(e.button===0){b.setPointerCapture(e.pointerId);down();}});
  if(id==='fracture_press')b.addEventListener('contextmenu',e=>e.preventDefault());
  b.addEventListener('keydown',e=>{if(e.key===' '||e.key==='Enter'){e.preventDefault();if(!e.repeat)down();}});
  b.addEventListener('keyup',e=>{if(e.key===' '||e.key==='Enter'){e.preventDefault();up();}});
  for(const event of ['pointerup','pointercancel','lostpointercapture','blur'])b.addEventListener(event,up);
  return b;
}
function row(label, meta, cb) {
  const b = button('', cb, 'row');
  b.append(html('span', '', label), html('small', '', meta));
  return b;
}
function section(body, title) {
  body.append(html('h3', 'sect', title));
}
function stat(body, label, value, key) {
  const a = html('div', 'stat'),
    b = html('b', '', value);
  if (key) b.dataset.live = key;
  a.append(html('span', '', label), b);
  body.append(a);
}
function operateHand(){
  const item=world?.inspection;if(!item?.joint||!world.operateHeld())return;
  const sounds={field_glasses:'focus',mug:'valve',logbook:'folio',tool_roll:'keeper'};
  audio.play(sounds[item.id]);
  const state=s.deviceStops[item.id],label=$('panelBody').querySelector('[data-mechanism]');
  if(label)label.textContent=handLabel(item,state);
  save(s);
}
function handLabel(item,stop){
  if(item.id==='field_glasses')return 'Focus drum · '+(stop+1)+' / 6';
  if(item.id==='mug')return 'Press drinking valve';
  if(item.id==='logbook')return stop?'Close flight log':'Open flight log';
  return stop?'Latch tool keeper':'Release tool keeper';
}
function releaseHand(){
  const item=world?.inspection;
  if(!item||item.tap)return;
  world.looseItems.release(item,s);closePanel();sync();
  notify(PROPS[item.id].name+' released.');
}
function gripHint(moving=false){
  const hand=world?.inspection;
  $('handlingHint').textContent=hand?.carrying?'Drag to look · Use the arrows to move':moving?'Drag the object and release your grip':
    matchMedia('(pointer:coarse)').matches?'Drag to turn · Walk with item to carry it':'Drag to turn · Right-drag to look · WASD to carry · G to let go';
}
function carryPad(actions,hand){
  if(mode!=='walk'||!matchMedia('(pointer:coarse)').matches)return;
  const pad=html('div','carry-pad');pad.hidden=true;pad.setAttribute('aria-label','Carry item');
  const toggle=button('Walk with item',e=>{
    hand.carrying=!hand.carrying;hand.moveMode=false;world.clearKeys();gripHint();
    pad.hidden=!hand.carrying;e.currentTarget.setAttribute('aria-pressed',String(hand.carrying));
    e.currentTarget.textContent=hand.carrying?'Handle item':'Walk with item';
  });
  for(const [key,symbol,label] of [['a','←','left'],['w','↑','forward'],['s','↓','back'],['d','→','right']]){
    const b=button(symbol,()=>{});b.setAttribute('aria-label','Carry '+label);
    b.onpointerdown=e=>{b.setPointerCapture(e.pointerId);world.keys.add(key);e.preventDefault();};
    b.onpointerup=b.onpointercancel=b.onlostpointercapture=()=>world.keys.delete(key);pad.append(b);
  }
  if(world.deckLoad<=handrailLoad)pad.append(button('Push off',()=>pushOff()),button('Down',()=>pushOff('down')));
  actions.append(toggle,pad);
}
function pressValve(down){
  const item=world?.inspection;
  if(item?.id!=='mug'||item.valveHeld===down)return;
  item.holdValve(down);
  if(down)audio.play('valve');
}
function drinkingValveButton(label){
  const b=button(label,e=>{if(e.detail===0&&!b.dataset.pressed)operateHand();},'quiet mechanism-control');
  b.addEventListener('pointerdown',e=>{if(e.button===0){b.setPointerCapture(e.pointerId);pressValve(true);}});
  b.addEventListener('keydown',e=>{if(e.key===' '||e.key==='Enter'){e.preventDefault();b.dataset.pressed='1';pressValve(true);}});
  b.addEventListener('keyup',e=>{if(e.key===' '||e.key==='Enter'){e.preventDefault();delete b.dataset.pressed;pressValve(false);}});
  for(const type of ['pointerup','pointercancel','lostpointercapture','blur'])b.addEventListener(type,()=>pressValve(false));
  return b;
}
function returnVessel(){
  const hand=world.inspection;
  if(!hand||hand.id!=='mug')return;
  if(!world.vesselCradle.park(hand,point=>{
    audio.contactSound('VesselImpact',point,.30);audio.play('keeper');
    notify('Flask secured in the galley cradle.');
  })){notify('Carry the flask to the counter in the crew sleeper.');return;}
  s.items=s.items.filter(id=>id!=='mug');
  delete s.loose.mug;
  closePanel();sync();
}
function scope(body) {
  const el = html('div', 'scope-monitor');
  monitor=html('canvas');el.append(monitor);
  const t = html(
    'b',
    '',
    String(s.feed + 1).padStart(2, '0') + ' / ' + FEEDS[s.feed].toUpperCase(),
  );
  t.dataset.live = 'feed';
  el.append(t);
  body.append(el);
}
function inspect(id) {
  const prop = PROPS[id];
  if (!prop) return;
  const fracture=id.startsWith('fracture_');
  if(fracture&&s.room!=='service')return;
  if(CARRIED.includes(id)&&!s.items.includes(id)){use(id);return;}
  const same=modal==='inspect'&&selected===id,previousLean=!!world.lean;
  const instrument=fracture||['accelerometer','accel_test','capillary_cell','capillary_primer'].includes(id);
  const body = openPanel(prop.tag + '  /  ' + ROOMS[CARRIED.includes(id)?s.room:prop.room], prop.name, 'inspect', id);
  const carried = s.items.includes(id);
  const handheld=CARRIED.includes(id);
  if(handheld){
    document.body.classList.add('handling');gripHint();$('handlingHint').hidden=false;world.hold(id,$('panel'));
  }else{
    const assembly=fracture?'fracture_cell':({accel_test:'accelerometer',capillary_primer:'capillary_cell'}[id]||id);
    document.body.classList.add('fitting');world.setView('window');world.aimFitting(assembly);
    world.leanTo(assembly,same?previousLean:instrument);
    if(id==='ascent_lever'||id==='nav_screen')scope(body);
  }
  const description=html('p','panel-copy',fracture?fractureDescription():prop.description);
  if(fracture)description.dataset.live='ceramicDescription';
  body.append(description);
  if(id==='capillary_cell'&&momentFixture){
    const next=button('Next · Docked at Aster Reach',()=>stepMoment(1),'row');
    next.setAttribute('aria-label','Next moment');body.prepend(next);
  }
  if(id==='accelerometer'||id==='accel_test'){
    stat(body,'Vertical load',signedLoad(travel(s.progress).forces.down/9.80665),'signedLoad');
    stat(body,'Mechanical pointer',signedLoad(world.fixtures?.physics.proof.x??0),'proofLoad');
  }
  if(id==='capillary_cell'||id==='capillary_primer'){
    stat(body,'Sealed charge','77% liquid  /  23% gas');
  }
  if(fracture){
    stat(body,'Applied load',Math.round(world.fracture.load)+' N','ceramicLoad');
    stat(body,'Peak witness',Math.round(world.fracture.peak)+' N','ceramicPeak');
    stat(body,'Chamber',fractureStatus(),'ceramicState');
  }
  if (id === 'locker_drawer' && s.drawer && !s.items.includes('access_card')&&!s.loose.access_card)
    body.append(row('Service keycard', 'In tray  ↗', () => inspect('access_card')));
  if (id === 'card_reader' || id === 'pressure_gauge' || id === 'pressure_hatch')
    stat(
      body,
      'Seal differential',
      equalizing ? 'Equalizing' : s.hatch ? '0.00 kPa' : '0.02 kPa',
      'pressure',
    );
  if (id === 'docking_wheel') {
    const collar=world.exterior.terminals.bays.aster.coupling;
    stat(body, 'Handwheel', s.clamp + ' / 3 detents', 'clamp');
    stat(body, 'Follower travel', (18*collar.travel).toFixed(1)+' mm', 'follower');
    stat(body, 'Transfer sleeve', sleeveReading(collar), 'sleeve');
  }
  if (id === 'nav_screen' || id === 'ascent_lever') {
    stat(body, 'Automatic drive', travel(s.progress).speed + ' km/h', 'speed');
    stat(body, 'Altitude', kmText(travel(s.progress).km) + ' km', 'km');
  }
  const actions = html('div', 'btnline');
  if(id==='panel_gain'||id==='camera_focus'){
    actions.append(button('Turn left',()=>use(id,true,-1)),button('Turn right',()=>use(id,true,1),'primary'));
  }else if(id==='accelerometer'||id==='accel_test'){
    actions.append(fixtureButton('Apply test load','accel_test'));
    actions.append(button('Show load on flight display',()=>use('key_load')));
  }else if(id==='capillary_cell'||id==='capillary_primer'){
    actions.append(fixtureButton('Stroke primer','capillary_primer'));
  }else if(fracture){
    const lever=fixtureButton('Hold test lever','fracture_press');
    const feed=button('Index next coupon',()=>use('fracture_reload',true));
    lever.dataset.cartridge='press';feed.dataset.cartridge='index';
    lever.disabled=world.fracture.broken||world.fracture.index>=0;
    feed.disabled=!world.fracture.broken||world.fracture.index>=0;
    const operations=html('div','btnline cartridge-ops');
    operations.append(lever,feed);body.prepend(operations);
  }else if (!carried) actions.append(button(actionLabel(id, s), () => use(id, true), 'primary'));
  const softAction={bunk:['quilt','Press quilt'],privacy_curtain:['curtain','Brush hem'],service_cabinet:['service','Pluck service loop']}[id];
  if(softAction&&(id!=='service_cabinet'||s.cabinet)){
    actions.append(button(softAction[1],()=>{
      const [kind]=softAction;
      if(!world.aimFabric?.(kind)||!world.touchFabric?.(kind)){notify(kind==='quilt'?'Draw back the berth screen to reach the quilt.':'This fitting is out of reach.');return;}
      audio.play(kind==='service'?'pluck':'brush');
    }));
  }
  if(id.startsWith('loom_service_')){
    const test=id.endsWith('power')?'test_power':'test_fiber';
    actions.append(button(test==='test_power'?'Run load test':'Run loopback test',()=>use(test)));
  }
  if(!handheld&&world.layout.props[id]&&!['window','lounge_seat','bunk'].includes(id)){
    const lean=button(world.lean?'Step back':'Lean closer',e=>{
      const assembly=fracture?'fracture_cell':({accel_test:'accelerometer',capillary_primer:'capillary_cell'}[id]||id);
      world.leanTo(assembly,!world.lean);e.currentTarget.textContent=world.lean?'Step back':'Lean closer';
    });actions.append(lean);
  }
  if (carried && id === 'field_glasses')
    actions.append(button('Use optics', () => takePosition(id), 'primary'));
  if (carried && id === 'access_card')
    actions.append(
      button(
        'Present at reader',
        () => {
          if (s.room !== 'berth') {
            notify('The reader is on the sleeper side of the service hatch.');
            return;
          }
          if (world && mode === 'walk') world.aimFitting('card_reader');
          use('card_reader', true);
        },
        'primary',
      ),
    );
  if(handheld){
    const item=world.inspection;
    if(item?.joint){const label=handLabel(item,s.deviceStops[id]);const control=id==='mug'?drinkingValveButton(label):button(label,operateHand,'quiet mechanism-control');control.dataset.mechanism=id;actions.append(control);}
    if(carried)actions.append(button('Stow',()=>closePanel(),'primary'),button('Let go',releaseHand));
    if(carried&&id==='mug')actions.append(button('Fit in galley cradle',returnVessel));
    if(carried)carryPad(actions,item);
    actions.append(button('Move & release',e=>{
      item.moveMode=!item.moveMode;item.previousDrag=0;item.mouseImpulse.set(0,0,0);item.eventAt=0;
      e.currentTarget.setAttribute('aria-pressed',String(item.moveMode));gripHint(item.moveMode);
      $('backdrop').style.cursor=item.moveMode?'grabbing':'grab';
    }));
    actions.append(button('Turn over',()=>world.inspection?.flip()),button('Look closer',()=>world.inspection?.magnify(1.24)));
    const lamp=button('Inspection light',e=>{if(!world.inspection)return;world.inspection.workLamp=!world.inspection.workLamp;
      e.currentTarget.setAttribute('aria-pressed',String(world.inspection.workLamp));audio.play('click');});
    lamp.setAttribute('aria-pressed','true');actions.append(lamp);
  }
  actions.append(button('Graphics',()=>graphics.open()));body.append(actions);
  if(!handheld)world.fittingPanel=$('panel');
}
function inventory() {
  const body = openPanel('CAR 07  /  PERSONAL EFFECTS', 'Inventory', 'inventory');
  if (!s.items.length)
    body.append(
      html('p', 'panel-copy', 'Your pockets are empty. Pick up a loose item to keep it here.'),
    );
  else
    for (const id of s.items)
      body.append(row(PROPS[id].name, PROPS[id].tag + '  ↗', () => inspect(id)));
}
function guide() {
  const body = openPanel('CAR 07  /  PASSENGER ACCESS', 'Carriage guide', 'guide');
  body.append(row('Graphics','F2',()=>graphics.open()));
  for (const [id, name] of Object.entries(ROOMS))
    body.append(
      row(
        name,
        id === s.room ? 'Here' : id === 'service' && !s.hatch ? 'Hatch secured' : 'Enter  →',
        () => go(id),
      ),
    );
  section(body, 'Within reach');
  const ids = Object.keys(PROPS).filter(id=>(s.loose[id]?roomAt(s.loose[id].p[2]):PROPS[id].room)===s.room&&visibleProp(id,s));
  if (s.room === 'berth') for(const id of ['pressure_hatch','card_reader'])if(!ids.includes(id))ids.push(id);
  for (const id of ids)
    body.append(
      row(PROPS[id].name, 'Inspect  ↗', () => {
        if (mode === 'walk') world.aimFitting(id);
        inspect(id);
      }),
    );
  section(body, 'Passage');
  body.append(
    row('Passage moments','Open  ↗',momentsPanel),
    row('Timetable', 'Open  ↗', route),
    row('Inventory', s.items.length + ' items', inventory),
  );
  section(body, 'View & controls');
  if (world)
    body.append(
      row(mode === 'walk' ? 'Take a window seat' : 'Enter the aisle', 'Switch', () => {
        closePanel(false);
        if(mode==='cabin'){enterAisle();return;}
        mode='cabin';momentOrigin=null;momentFixture=false;
        viewMode();
        sync();
      }),
    );
  body.append(
    html(
      'p',
      'guide-keys',
      (world.deckLoad<=handrailLoad?'Space pushes off the deck or ceiling. X or Ctrl pushes toward the deck. Aim and use WASD at a handhold, then release to coast. ':'WASD to walk. ')+
      'Drag to look. E operates a fitting. F inspects it. I opens inventory. M lists passage moments. [ and ] step between moments. N and P skip timetable stops. R opens the timetable.',
    ),
  );
  const native = html('a', 'row', 'Open the Unity player ↗');
  native.href = 'https://upwell-tetherline.netlify.app/unity/';
  native.style.textDecoration = 'none';
  body.append(native);
  const reset = button('Start a new passage', (e) => {
    if (!resetPending) {
      resetPending = true;
      e.currentTarget.textContent = 'Restart from the launch bay?';
      return;
    }
    newPassage();
  });
  body.append(reset);
}
function route() {
  const body = openPanel('EQUATORIAL LINE  /  UPBOUND', 'Passage timetable', 'route');
  body.append(
    html(
      'p',
      'panel-copy',
      'A car normally leaves each end every eight ship hours. On the upbound ride you meet one about every four hours. This passage has five passenger cars, nine freight carriers and two cable tenders, including the extra supply run F04.',
    ),
  );
  paceControl(body);
  const stops = html('div', 'route-stops');
  body.append(button('Passage moments',momentsPanel));
  for (const [p, km, name] of STOPS) {
    const e=button('',()=>skip(p,name),'route-stop'+(p<=s.progress?' on':''));e.setAttribute('aria-label','Watch '+name);
    e.dataset.at = p;
    e.append(html('span', '', name), html('small','',altitudeText(km)));
    stops.append(e);
  }
  body.append(stops);
  const stats = html('div', 'stats');
  stat(stats, 'Climb speed', travel(s.progress).speed + ' km/h', 'speed');
  stat(stats, 'Time aboard', elapsed(), 'hours');
  stat(stats,'Apparent weight',travel(s.progress).forces.gravityG.toFixed(3)+' g','load');
  stat(stats,'Atmospheric region',travel(s.progress).atmosphere,'air');
  body.append(stats);
  const a = html('div', 'btnline');
  if (s.progress < 1)
    a.append(
      button(
        'Next waypoint',
        () => {
          const next = STOPS.find((x) => x[0] > s.progress + 0.001);
          skip(next?.[0] ?? 1, 'Waypoint reached');
        },
        'primary',
      ),
    );
  const car = TRAFFIC.find((x) => x.approachAt > s.progress+.00001);
  if (car)
    a.append(
      button('Watch '+car.car+' · '+car.type, () => {
        skip(Math.max(s.progress,car.approachAt-.0011), 'Counterline approach · '+car.car);
        mode='cabin';s.room='observation';viewMode();selectView('counter');
      }),
    );
  if (s.progress === 1 && s.clamp < 3)
    body.append(
      html(
        'p',
        'panel-copy',
        'The nonrotating hub is alongside. The service handwheel seats the transfer clamp.',
      ),
    );
  if (s.clamp === 3)
    body.append(
      html(
        'p',
        'panel-copy',
        'Car 07 is secured to the hub. The habitat turns beyond the bearing.',
      ),
    );
  body.append(a);
}
function setPassageTime(p){
  releaseStargazingFrame();
  const from=s.progress*RIDE_SECONDS;
  s.progress=clamp(p);if(s.progress<1)s.clamp=0;
  if(s.progress<1&&world?.view==='valley'){
    world.setView('colony');plate.update(mode==='cabin','colony',s.room);
  }
  realShipClock=null;stargazingSeconds=0;
  const to=s.progress*RIDE_SECONDS;
  if(momentOrigin?.free&&to<from)world.rewindPassengerBookmark(momentOrigin,s,from,to,time);
  if(world&&Math.abs(to-from)>.00001)world.seekPassage(s,from,to,time,freePassenger());
  world?.instruments.resetTrace();
  lastTraffic='';lastEncounter='';radio?.pause();previous=0;nextUi=0;
}
function skip(p, message) {
  const keepHand=modal==='inspect'&&!!world.inspection;
  setPassageTime(p);
  if(!keepHand)closePanel(false);
  if(s.progress===1&&s.followMomentView&&freePassenger()&&!world.inspection&&!world.trackedSeek)world.faceDock(true);
  sync();
  updateUI(travel(s.progress));
  audio.play('alert');
  const phase=travel(s.progress).name;
  notify(s.progress===1?dockNotice():message===phase?phase:message+' · '+phase);
}
function stepStop(direction){
  const seconds=s.progress*RIDE_SECONDS;
  const stop=direction>0?STOPS.find(([p])=>p*RIDE_SECONDS>seconds+.6):STOPS.findLast(([p])=>p*RIDE_SECONDS<seconds-.9);
  if(stop)skip(stop[0],stop[2]);
}
function updateMomentButtons(){
  for(const [id,dir] of [['momentPrev',-1],['momentNext',1]]){
    const index=momentIndex(dir),b=$(id);
    b.disabled=index<0;
    if(index>=0)b.title=(dir<0?'Previous':'Next')+' · '+passageMoments[index].name;
  }
}
function momentsPanel(){
  if(modal!=='moments'){
    const held=world.inspection;
    momentInspection=modal==='inspect'?{id:selected,...world.passengerPose(s.progress*RIDE_SECONDS),
      lean:world.lean,angle:held?.angle.slice(),zoom:held?.zoom,light:held?.workLamp,offset:held?.handOffset.toArray()}:null;
  }
  const body=openPanel('EQUATORIAL LINE','Passage moments','moments');
  paceControl(body);
  const optics=html('div','btnline');
  for(const [id,title] of [['harbor','Harbor optics'],['tender','Cable tender T03']]){
    optics.append(button(title,async()=>visitObservation(await linkedObservation(id))));
  }
  body.append(optics);
  const links=html('div','btnline');
  for(const [id,title] of [['valley','Valley gallery'],['stargazing','Stargazing window']])
    links.append(button(title,async()=>visitObservation(await linkedObservation(id))));
  body.append(links);
  const label=html('label','moment-follow'),follow=document.createElement('input');
  follow.type='checkbox';follow.checked=s.followMomentView;
  follow.onchange=()=>{s.followMomentView=follow.checked;save(s);};
  label.append(follow,document.createTextNode('Use suggested view'));body.append(label);
  const list=html('div','moment-list');
  for(const [i,m] of passageMoments.entries()){
    const b=button('',()=>visitMoment(i),'moment-row');
    b.setAttribute('aria-label','Watch '+m.name);
    const details=html('span');details.append(html('b','',m.name),html('small','',m.detail));
    b.append(details,html('time','',passageTime(m.start)));list.append(b);
  }
  body.append(list);
}
function visitObservation(m){
  if(!m)return;
  closePanel(false);setPassageTime(m.start/RIDE_SECONDS);s.room='observation';selectView(m.view);
  if(m.id==='stargazing'){
    if(!s.realShipTime)stargazingSeconds=20;
    warmupFrames=2;
    world.seat('observation');world.setView('window');
    if(s.lamps)world.switchboard.operate('cabin_lights',s);
    if(s.panelGain!==0){s.panelGain=0;world.switchboard.trigger('panel_gain');}
    if(s.shade)world.switchboard.operate('solar_film',s);
    sync();
    updateUI(travel(s.progress));
  }
  notify(m.detail);
}
function restoreInspection(bookmark){
  inspect(bookmark.id);
  if(bookmark.angle)world.resumePassenger(bookmark,s,s.progress*RIDE_SECONDS);
  else {world.position.fromArray(bookmark.position);world.yaw=bookmark.yaw;world.pitch=bookmark.pitch;}
  world.lean=bookmark.lean;
  const held=world.inspection;
  if(held&&bookmark.angle){
    held.angle=bookmark.angle.slice();held.turntable.rotation.set(...held.angle,'YXZ');held.zoom=held.easedZoom=bookmark.zoom;
    held.workLamp=bookmark.light;held.handOffset.fromArray(bookmark.offset);held.appearance=1;
    const control=[...$('panelBody').querySelectorAll('button')].find(b=>b.textContent==='Inspection light');
    control?.setAttribute('aria-pressed',String(held.workLamp));
  }
  world.updateCamera(0);
}
function visitMoment(index){
  const moment=passageMoments[index];if(!moment)return;
  const restoreView=modal==='moments'&&(!s.followMomentView||momentInspection?.angle)?momentInspection:null;
  const manualInspection=modal==='inspect'&&!momentFixture;
  const follow=s.followMomentView&&!manualInspection&&!restoreView;
  const freeAtDock=moment.id==='dock'&&(momentOrigin?momentOrigin.free:freePassenger());
  if(follow&&!momentOrigin&&!freeAtDock){
    momentOrigin={room:s.room,free:freePassenger(),rest:world.restId,...world.passengerPose(s.progress*RIDE_SECONDS)};
  }
  if(!manualInspection)closePanel(false);
  setPassageTime(moment.start/RIDE_SECONDS);
  if(follow&&freeAtDock){
    if(momentOrigin)enterAisle();
    else {world.setView('window');s.room=roomAt(world.position.z);}
    if(!world.trackedSeek)world.faceDock();
  }else if(follow&&moment.id==='dock'&&momentOrigin){
    // An intentionally seated/braced traveller keeps their own compartment
    // when the suggested exterior camera gives way to the docked cabin.
    const anchor=momentOrigin;momentOrigin=null;momentFixture=false;
    mode=anchor.rest?'walk':'cabin';s.room=anchor.room;viewMode();
    if(anchor.rest)world.rest(anchor.rest);
  }else if(follow){
    world.stand();world.clearKeys();momentFixture=false;
    if(moment.view==='cell'){
      mode='walk';s.room='berth';viewMode();momentFixture=true;inspect('capillary_cell');
    }else{
      mode='cabin';s.room='observation';viewMode();
      world.setView(moment.view);plate.update(true,moment.view,s.room);
    }
  }
  if(restoreView)restoreInspection(restoreView);
  if(!modal)$('scene').focus({preventScroll:true});
  sync();updateUI(travel(s.progress));audio.play('click');
  notify(moment.id==='dock'?dockNotice():moment.name);
}
function momentIndex(direction){
  const next=adjacentMoment(passageMoments,s.progress*RIDE_SECONDS,direction);
  // The galley event plays right up to 6:00. Choosing the final cabin view
  // must still work after the clock stops, even when no time remains to skip.
  if(next<0&&direction>0&&s.followMomentView&&(momentFixture||momentOrigin))return passageMoments.length-1;
  return next;
}
function stepMoment(direction){
  visitMoment(momentIndex(direction));
}
function elapsed() {
  const h = shipTimeAtRideSeconds(s.progress*RIDE_SECONDS)/3600;
  return Math.floor(h) + ' h ' + String(Math.floor((h % 1) * 60)).padStart(2, '0') + ' m';
}
function systems() {
  const body = openPanel('AV / 101  ·  LIVE', 'Systems console', 'systems');
  scope(body);
  const stats = html('div', 'stats');
  stat(stats, 'Automatic drive', travel(s.progress).speed + ' km/h', 'speed');
  stat(stats, 'Altitude', kmText(travel(s.progress).km) + ' km', 'km');
  stat(stats, 'Guide circuits', 'A + B  /  Nominal');
  stat(stats,'Apparent weight',travel(s.progress).forces.gravityG.toFixed(3)+' g','load');
  stat(stats,'Drive acceleration',travel(s.progress).forces.driveAcceleration.toFixed(2)+' m/s²','accel');
  stat(stats,'Atmospheric region',travel(s.progress).atmosphere,'air');
  stat(stats, 'Service hatch', s.hatch ? 'Open' : 'Sealed', 'hatch');
  stat(stats, 'Terminal clamp', s.clamp + ' / 3 detents', 'clamp');
  body.append(stats);
  const a = html('div', 'btnline');
  a.append(
    button('Change camera', () => use('ascent_lever', false)),
    button('Passage timetable', route),
  );
  body.append(a);
}
function access(fromPanel) {
  if (!s.items.includes('access_card')) {
    world.switchboard.trigger('card_reader','denied');
    audio.play('no');
    notify('Credential required. The crew drawer holds the spare.');
    return;
  }
  if (equalizing||presenting) {
    notify('Pressure interlock is equalizing.');
    return;
  }
  if (s.unlocked) {
    world.switchboard.trigger('card_reader','granted');
    audio.play('click');
    notify('Credential accepted. Service access is enabled.');
    return;
  }
  presenting=true;world.presentKey(()=>{
  presenting=false;equalizing = true;
  world.switchboard.trigger('card_reader','reading');
  audio.play('equalize');
  notify('Credential accepted · equalizing the two bays.');
  setTimeout(() => {
    if (!equalizing) return;
    equalizing = false;
    s.unlocked = true;
    s.hatch = true;
    world.switchboard.trigger('card_reader','granted');
    audio.play('hatch');
    sync();
    if (modal === 'inspect' && ['card_reader', 'pressure_hatch'].includes(selected))
      inspect(selected);
    notify('Pressure matched. The service hatch is opening.');
  }, 1250);},()=>{presenting=false;});
}
function signedLoad(value){
  const v=Math.abs(value)<.0005?0:value;
  return (v>0?'+':'')+v.toFixed(3)+' g';
}
function fractureStatus(){
  const f=world.fracture;
  return f.index>=0?'Indexing':f.broken?'Five fragments':f.load>1?'Under load':'Coupon seated';
}
function fractureDescription(){
  const f=world.fracture;
  if(f.index>=0)return 'The magazine draws the shutters across the guard while a fresh strip moves onto the rollers.';
  if(f.broken)return 'The ceramic pieces are loose behind the guard. The red witness holds the breaking load until the magazine seats another strip.';
  return PROPS[selected]?.description??'';
}
function operateFixture(id,held=false){
  if(id==='fracture_press'){
    if(s.room!=='service')return;
    if(held)world.fracture.press();else if(!modal)inspect(id);
    return;
  }
  if(!world.fixtures?.operate(id,held))return;
  audio.play(id==='accel_test'?'proof':'prime');
  if(!modal)notify(id==='accel_test'?'Proof mass under test · +0.10 g':'Galley return primed.');
}
function cancelCabinGrip(){
  if(pointer?.pressTimer)clearTimeout(pointer.pressTimer);
  if(world)world.drawingCurtain=false;
  world?.fixtures?.release();world?.fracture?.release();world?.releaseFabric?.();
}
function use(id, fromPanel = false, direction = 1) {
  if (!id) return;
  if(id.startsWith('fracture_')){
    if(s.room!=='service')return;
    if(id==='fracture_reload'){
      if(!world.fracture.reload()&&!fromPanel)notify('Unload the lever before indexing a spent coupon.');
    }else inspect(id);
    return;
  }
  if(id.startsWith('loom_service_')){
    if(fromPanel)world.aimFabric(id);
    const hit=fromPanel?null:world.fabricUnderAim;
    if(!world.touchFabric(id,hit?.id===id?hit.point:undefined)){notify('Reach the cable through the open inspection cover.');return;}
    audio.play('pluck');if(!fromPanel)notify(PROPS[id].name+' released.');return;
  }
  if(id==='accelerometer'||id==='capillary_cell'){inspect(id);return;}
  if(id==='accel_test'||id==='capillary_primer'){operateFixture(id);return;}
  if(SWITCHES[id]){
    const effect=world.switchboard.operate(id,s,direction);
    if(!effect)return;audio.play(effect.sound);notify(effect.message);
    if(effect.dispatch)use('intercom');
    sync();if(fromPanel&&modal==='inspect')inspect(id);return;
  }
  if (CARRIED.includes(id)) {
    if(id==='mug'&&world.vesselCradle.moving)return;
    if (s.items.includes(id)) {
      inspect(id);
      return;
    }
    if (id === 'access_card' && !s.drawer&&!s.loose[id]) {
      notify('Open the crew drawer to reach the card.');
      return;
    }
    const body=world.looseItems.bodies.get(id);
    const pose=body?{p:body.root.position.clone(),q:body.root.quaternion.clone(),v:body.vel.clone(),w:body.spin.clone()}:null;
    const flex=body?world.dynamics.flexState(world.dynamics.loose.get(id)):[];
    delete s.loose[id];if(body)world.looseItems.remove(id);
    s.items.push(id);
    audio.play(id==='tool_roll'?'keeper':id==='logbook'?'folio':id==='field_glasses'?'focus':'click');
    notify(PROPS[id].name + ' in hand.');
    sync();
    inspect(id);
    if(pose&&world.inspection){world.inspection.fromPose=pose;world.dynamics.restoreFlex(world.dynamics.held,flex);}
    return;
  }
  switch (id) {
    case 'pilot_console':
      audio.play('click');
      systems();
      return;
    case 'ascent_lever':
      s.feed = (s.feed + direction + 3) % 3;
      s.screen = 1;
      audio.play('detent');
      notify('Exterior camera 0' + (s.feed + 1) + ' · ' + FEEDS[s.feed]);
      break;
    case 'nav_screen':
      s.screen = (s.screen + 1) % PAGES.length;
      audio.play('click');
      notify(PAGES[s.screen]);
      break;
    case 'window':
    case 'lounge_seat':
    case 'bunk':
    case 'grab_handle':
      takePosition(id);
      return;
    case 'nadir_port':
      closePanel(false);selectView('floor');return;
    case 'roller_shade':
      s.shade = !s.shade;
      audio.play('shade');
      notify(s.shade ? 'Solar film descending.' : 'Solar film retracting.');
      break;
    case 'lamp':
      s.lamps = !s.lamps;
      audio.play('click');
      notify('Saloon lights ' + (s.lamps ? 'on.' : 'off.'));
      break;
    case 'reading_lamp':
      s.berthLight = !s.berthLight;
      audio.play('click');
      notify('Berth light ' + (s.berthLight ? 'on.' : 'off.'));
      break;
    case 'privacy_curtain':
      s.curtain = Number(s.curtain)<.5;
      audio.play('slide');
      notify(s.curtain ? 'Berth screen drawn.' : 'Screen stowed.');
      break;
    case 'locker_drawer':
      s.drawer = !s.drawer;
      audio.play('runner');
      notify(
        s.drawer
          ? s.items.includes('access_card')||s.loose.access_card
            ? 'Crew tray extended.'
            : 'Crew tray extended · a keycard is inside.'
          : 'Drawer latched.',
      );
      break;
    case 'card_reader':
      access(fromPanel);
      return;
    case 'pressure_hatch':
      if (!s.unlocked) {
        if (s.items.includes('access_card')) access(fromPanel);
        else {
          audio.play('no');
          notify('Hatch interlock engaged. Present a keycard at the reader.');
        }
        return;
      }
      if (s.hatch && mode === 'walk' && !world.safeToShut()) {
        notify('Step clear of the hatch track.');
        return;
      }
      s.hatch = !s.hatch;
      audio.play('hatch');
      notify(s.hatch ? 'Service hatch opening.' : 'Pressure leaf closing.');
      break;
    case 'service_cabinet':
      s.cabinet = !s.cabinet;
      audio.play('slide');
      notify(
        s.cabinet ? 'Panel released · power and fiber looms exposed.' : 'Cable panel latched.',
      );
      break;
    case 'breaker':
      s.bayLight = !s.bayLight;
      audio.play('detent');
      notify(s.bayLight ? 'Cable inspection light on.' : 'Cable inspection light off.');
      break;
    case 'pressure_gauge':
      audio.play('click');
      notify(
        equalizing
          ? 'Differential falling.'
          : s.hatch
            ? 'Differential 0.00 kPa · bays connected.'
            : 'Differential 0.02 kPa · seals holding.',
      );
      break;
    case 'intercom': {
      world.switchboard.trigger('intercom');
      const i = travel(s.progress).index;
      audio.play('alert');
      radio?.pause();
      radio = new Audio('./assets/audio/Dispatch' + i + '.wav');
      radio.volume=.66;radio.muted=!audio.enabled;
      radio.play().catch(()=>{});
      notify(dispatch[i]);
      break;
    }
    case 'docking_wheel':
      if (s.progress < 1) {
        audio.play('clamp');
        notify('Travel stop holds. The wheel releases at the terminal collar.');
        break;
      }
      if (s.clamp === 3) {
        audio.play('click');
        notify(world.exterior.terminals.bays.aster.coupling.status);
        break;
      }
      s.clamp++;
      audio.dockTurn(s.clamp);
      notify(
        [
          '',
          'Centering the capture jaws.',
          'Drawing the collar against its stops.',
          'Locking the collar. The transfer sleeve will extend.',
        ][s.clamp],
      );
      break;
  }
  if(world?.instruments)world.instruments.last=-Infinity;
  sync();
  if (fromPanel && modal === 'inspect') inspect(id);
}
function newPassage() {
  momentOrigin=null;momentFixture=false;
  equalizing = false;presenting=false;
  s = freshState();
  if (radio) {
    radio.pause();
    radio = null;
  }
  lastTraffic = '';
  lastEncounter = '';
  time = 0;
  nextUi = 0;
  nextSave = 0;
  previous = 0;
  world?.instruments.resetTrace();
  closePanel(false);
  if (mode === 'walk') world.go('observation');
  else world.seat(s.room);
  sync();
  notify('Equatorial anchor · bridge release.');
}
function sleeveReading(collar) {
  if(collar.sleeve>=1)return 'Seated';
  if(collar.sleeve<=0)return 'Withdrawn';
  return (2.42*collar.bridgeClearance).toFixed(2)+' m to contact';
}
function live(m) {
  const f=world.fracture;
  const collar=world.exterior.terminals.bays.aster.coupling;
  const data = {
    ceramicLoad:Math.round(f.load)+' N',ceramicPeak:Math.round(f.peak)+' N',ceramicState:fractureStatus(),ceramicDescription:fractureDescription(),
    signedLoad:signedLoad(m.forces.down/9.80665),proofLoad:signedLoad(world.fixtures?.physics.proof.x??0),
    km: altitudeText(m.km),
    speed: m.speed + ' km/h',
    hours: elapsed(),
    load:m.forces.gravityG.toFixed(3)+' g',accel:m.forces.driveAcceleration.toFixed(2)+' m/s²',air:m.atmosphere,
    clamp: s.clamp + ' / 3 detents',
    follower:(18*collar.travel).toFixed(1)+' mm',sleeve:sleeveReading(collar),
    hatch: s.hatch ? 'Open' : 'Sealed',
    pressure: equalizing ? 'Equalizing' : s.hatch ? '0.00 kPa' : '0.02 kPa',
    feed: '0' + (s.feed + 1) + ' / ' + FEEDS[s.feed].toUpperCase(),
  };
  $('panelBody')
    .querySelectorAll('[data-live]')
    .forEach((n) => {
      const value=data[n.dataset.live];
      if(n.textContent!==value)n.textContent=value;
    });
  $('panelBody')
    .querySelectorAll('.route-stop')
    .forEach((n) => n.classList.toggle('on', Number(n.dataset.at) <= s.progress));
  for(const b of $('panelBody').querySelectorAll('[data-cartridge]')){
    // A disabled button can drop pointer capture before the operator lets go.
    b.disabled=b.dataset.cartridge==='press'?(f.broken&&!f.held)||f.index>=0:!f.broken||f.held||f.stroke>.10||f.index>=0;
  }
}
function updateUI(m) {
  graphics.refresh();
  updateMomentButtons();
  plate.setDocked(s.progress>=1);
  const lightLoad=m.forces.gravityG<=handrailLoad;
  plate.setLowLoad(lightLoad);
  $('cabinLoad').textContent=loadLabel(m.forces);
  const aboard=aboardClock(m.seconds<=9?m.seconds:m.forces.shipSeconds+9);
  const pace=m.seconds>=RIDE_SECONDS?'Docked':s.realShipTime?'Real 1×':stargazingSeconds>0?'Stargazing 1×':'Guided '+clockRate(shipRateAtRideSeconds(m.seconds));
  $('shipReadout').textContent=aboard+' aboard · '+pace;
  $('floatControls').hidden=!lightLoad||mode!=='walk';
  $('stand').hidden=lightLoad||mode==='cabin'||!world.restId;
  $('phase').textContent = m.name;
  $('alt').textContent = m.km<1?Math.round(m.km*1000).toLocaleString('en-US'):m.km<20?m.km.toFixed(1):kmText(m.km);
  $('altUnit').textContent=m.km<1?'m':'km';
  $('scaleFill').style.width = 100 * s.progress + '%';
  $('networkLabel').textContent = ROOMS[s.room];
  const t = m.traffic.inRange?m.traffic:null;
  $('passNote').hidden = !t;
  if (t) {
    $('passNote').lastElementChild.textContent =
      t.car+' · '+t.type+(t.eta>=0?' approaching':' passing astern');
    if (lastTraffic !== t.car) {
      audio.play('alert');
      lastTraffic = t.car;
    }
    if (s.progress >= t.at && lastEncounter !== t.car) {
      lastEncounter = t.car;
      audio.play('traffic');
    }
  }
  if (world.view==='window' && !modal) {
    if(hoverId&&!pointer)hoverId=world.pickEvent({clientX:hoverPoint.x,clientY:hoverPoint.y});
    target = hoverId || world.pick();
    if(world.restId||mode==='cabin'){
      const looking=['window','lounge_seat','nadir_port','field_glasses'].includes(target);
      if(!hoverId||looking||target===world.restId)target=null;
    }
    $('reticle').hidden=(!!world.restId||mode==='cabin')&&!target;
    $('target').hidden = !target;
    $('reticle').classList.toggle('active', !!target);
    const px = hoverId ? hoverPoint.x : innerWidth * 0.5;
    const py = hoverId ? hoverPoint.y : innerHeight * 0.5;
    $('reticle').style.left = px + 'px';
    $('reticle').style.top = py + 'px';
    const reading=target==='nav_screen'||target==='drive_screen'||target==='diagnostic_screen';
    $('target').style.left = (reading?innerWidth*.5:clamp(px, 100, Math.max(100, innerWidth - 100))) + 'px';
    $('target').style.top = (reading?(innerWidth<640?78:innerHeight-77):Math.min(py+17,innerHeight-54)) + 'px';
    if (target) {
      $('targetName').textContent = PROPS[target].name;
      const gesture=world.curtainHandleUnderAim?'   ·   Drag handle':world.fabricUnderAim?'   ·   Hold and drag':'';
      $('targetAction').textContent = 'E  '+actionLabel(target,s)+gesture+'   ·   F  Inspect';
    }
  } else {
    $('target').hidden = true;
    target = '';
  }
  if (modal) live(m);
}
function frame(stamp) {
  if (!aboard) return;
  requestAnimationFrame(frame);
  if (document.hidden) {
    previous = 0;
    return;
  }
  const gap=previous?(stamp-previous)/1000:.016;
  // A shader compilation or suspended GPU can hold the last picture for
  // seconds. Resume from that picture so the passenger still sees the cue.
  // GPU upload and shader compilation can block the first visible frames for
  // seconds. Both clocks start after the cabin has drawn, including at 1×.
  let visibleGap=warmupFrames>0?0:Math.max(0,gap);
  if(stargazingFence){
    // The browser can return from render before the driver has compiled and
    // drawn the optical passes. Start the eclipse clock after that first frame.
    const gl=world.r.getContext(),status=gl.clientWaitSync(stargazingFence,0,0);
    if(status!==gl.TIMEOUT_EXPIRED)releaseStargazingFrame();
    visibleGap=0;
  }
  const firstStargazingFrame=warmupFrames===2&&stargazingSeconds>0;
  if(warmupFrames>0)warmupFrames--;
  const elapsed=clamp(visibleGap,0,1/3),dt=Math.min(elapsed,.2);
  previous = stamp;
  time += elapsed;
  if(stargazingSeconds<=0)world.frameBudget(elapsed,time);
  const old = s.progress;
  if((s.realShipTime||stargazingSeconds>0)&&s.progress<1){
    const realStep=s.realShipTime?visibleGap:Math.min(visibleGap,stargazingSeconds);
    realShipClock=(realShipClock??shipTimeAtRideSeconds(s.progress*RIDE_SECONDS))+realStep;
    stargazingSeconds=Math.max(0,stargazingSeconds-realStep);
    s.progress=clamp(rideSecondsAtShipTime(realShipClock)/RIDE_SECONDS);
  }else if(!s.realShipTime)s.progress=clamp(s.progress+elapsed/RIDE_SECONDS);
  if(stargazingSeconds>0)nextUi=0;
  if (old < 1 && s.progress === 1) {
    audio.play('alert');
    notify(dockNotice());
  }
  const m = travel(s.progress);
  const heldWalk=modal==='inspect'&&world.inspection&&!world.restId;
  if(heldWalk&&world.keys.size)world.inspection.lowerUntil=performance.now()+800;
  world.update(s,m,time,dt,mode==='walk'&&(!modal||heldWalk)&&!graphics.dialog.open&&!journal.dialog.open,monitor,freePassenger(),visibleGap,stargazingSeconds>0);
  if(firstStargazingFrame){
    releaseStargazingFrame();
    const gl=world.r.getContext();
    stargazingFence=gl.fenceSync(gl.SYNC_GPU_COMMANDS_COMPLETE,0);
    gl.flush();
  }
  if(journal.waiting){
    const viewpoint=world.inspection?PROPS[world.inspection.id].name:
      mode==='cabin'?(plate.buttons.get(world.view)?.textContent??'Cabin window'):
      world.restId?(PROPS[world.restId]?.name??'Window seat'):ROOMS[roomAt(world.position.z)];
    journal.capture(world.r.domElement,{viewpoint,passage:m.seconds,km:m.km,load:m.forces.down/9.80665});
  }
  audio.structure(world,m,elapsed);
  const currentRoom=roomAt(world.position.z);
  if(s.room!==currentRoom){
    s.room=currentRoom;
    if(heldWalk)$('panelTag').textContent=PROPS[world.inspection.id].tag+'  /  '+ROOMS[currentRoom];
    sync();
  }
  if (time > nextUi) {
    updateUI(m);
    audio.update(m.speed,s.room,s.ventOn);
    nextUi = time + 0.1;
  }
  if (time > nextSave) {
    save(s);
    nextSave = time + 2.5;
  }
}
const drags = new Set([
  'panel_gain','camera_focus',
  'guide_flood','cabin_lights','solar_film','vent_fan','reading_lamp','breaker',
  'ascent_lever',
  'roller_shade',
  'privacy_curtain',
  'locker_drawer',
  'pressure_hatch',
  'service_cabinet',
  'docking_wheel',
]);
$('scene').addEventListener('pointerdown', (e) => {
  if (!aboard || modal || e.button !== 0) return;
  e.preventDefault();
  $('scene').focus({ preventScroll: true });
  const id=world.view==='window'?world.pickEvent(e):null;
  world.switchboard.contact(id,true);
  pointer = {
    x: e.clientX,
    y: e.clientY,
    startX: e.clientX,
    startY: e.clientY,
    started:performance.now(),
    id,
    dragged: false,
    rail:id==='privacy_curtain'&&world.curtainHandleUnderAim?world.curtainDragAxis():null,
    fabric:world.view==='window'?world.fabricHitEvent?.(e):null,
  };
  if(id==='accel_test'||id==='capillary_primer'){
    const own=pointer;own.pressTimer=setTimeout(()=>{
      if(own!==pointer||own.dragged||modal)return;
      own.pressed=true;operateFixture(id,true);
    },150);
  }
  if(id==='fracture_press'){pointer.pressed=true;operateFixture(id,true);}
  $('scene').setPointerCapture(e.pointerId);
  hoverId = null;
});
$('scene').addEventListener('pointermove', (e) => {
  if (!aboard || modal) return;
  if (!pointer) {
    hoverId = e.pointerType==='mouse' && world.view==='window' ? world.pickEvent(e) : null;
    hoverPoint.x = e.clientX;
    hoverPoint.y = e.clientY;
    return;
  }
  const dx = e.clientX - pointer.x,
    dy = e.clientY - pointer.y;
  const tx = e.clientX - pointer.startX,
    ty = e.clientY - pointer.startY;
  if (!pointer.dragged&&Math.hypot(tx,ty)>5){
    const holding=performance.now()-pointer.started>=160||e.altKey;
    pointer.dragged=true;pointer.softGrip=!!(!pointer.rail&&holding&&pointer.fabric&&world.gripFabric?.(pointer.fabric));
    pointer.gripped=!pointer.rail&&!pointer.softGrip&&drags.has(pointer.id)&&holding;
    if(!pointer.gripped)world.switchboard.contact(null,false);
  }
  if(pointer.rail&&pointer.dragged){
    const {start,x,y}=pointer.rail;
    const travel=clamp(start+tx*x+ty*y);
    if(!world.drawingCurtain&&Math.abs(travel-start)>.008){world.drawingCurtain=true;audio.play('slide');}
    s.curtain=travel;hoverId=null;
  }else if(pointer.softGrip){world.pullFabric(tx,ty);hoverId=null;}
  else if (pointer.dragged && pointer.gripped) {
    world.dragPreview = { id: pointer.id, travel: clamp(Math.hypot(tx, ty) / 62),direction:Math.sign(Math.abs(tx)>Math.abs(ty)?tx:-ty) };
    hoverId = pointer.id;
  } else if (pointer.dragged) {
    world.rotate(dx, dy);
    hoverId = null;
  }
  pointer.x = e.clientX;
  pointer.y = e.clientY;
});
$('scene').addEventListener('pointerup', (e) => {
  world?.switchboard.contact(null,false);
  if (!pointer) return;
  const p = pointer;
  cancelCabinGrip();
  pointer = null;
  world.dragPreview = null;
  const d = Math.hypot(e.clientX - p.startX, e.clientY - p.startY);
  if(p.dragged&&p.rail){
    if(s.curtain<.025||s.curtain>.975){s.curtain=s.curtain>.5;audio.play('click');}
    sync();
  }else if(!p.dragged&&p.fabric?.kind==='service'){
    if(world.touchFabric(p.fabric.id,p.fabric.point)){
      audio.play('pluck');notify(PROPS[p.fabric.id].name+' released.');
    }
  }else if (!p.pressed&&!p.softGrip&&(!p.dragged || (d > 23 && p.gripped)) && p.id)
    use(p.id,false,p.dragged&&['ascent_lever','panel_gain','camera_focus'].includes(p.id)&&e.clientX-p.startX< -12?-1:1);
  hoverId = null;
});
$('scene').addEventListener('pointercancel', () => {
  cancelCabinGrip();
  world?.switchboard.contact(null,false);
  pointer = null;
  if (world) world.dragPreview = null;
});
$('scene').addEventListener('pointerleave', () => {
  if (!pointer) hoverId = null;
});
$('scene').addEventListener('contextmenu', (e) => {
  e.preventDefault();
  if (aboard && !modal && mode === 'walk') {
    const id=world.view==='window'?world.pickEvent(e):null;
    if (id) inspect(id);
  }
});
addEventListener('keydown', (e) => {
  if (!aboard) return;
  const k = e.key.toLowerCase();
  if(journal.dialog.open){
    if(k==='j'&&!e.ctrlKey&&!e.altKey&&!e.metaKey){e.preventDefault();if(!e.repeat)journal.dialog.close();}
    return;
  }
  if(!graphics.dialog.open&&!e.ctrlKey&&!e.altKey&&!e.metaKey&&(k==='j'||k==='k')&&(!modal||modal==='inspect')){
    e.preventDefault();if(!e.repeat){if(k==='k')journal.request();else journal.open();}return;
  }
  if(k==='f2'&&!e.ctrlKey&&!e.altKey&&!e.metaKey){
    e.preventDefault();if(!e.repeat){if(graphics.dialog.open)graphics.dialog.close();else graphics.open();}return;
  }
  if(graphics.dialog.open)return;
  const plain=!e.ctrlKey&&!e.metaKey&&!e.altKey;
  if(plain&&(k==='n'||k==='p')&&(!modal||modal==='route'||(modal==='inspect'&&world.inspection))){
    e.preventDefault();if(!e.repeat)stepStop(k==='n'?1:-1);return;
  }
  if(plain&&k==='b'&&!modal&&s.room==='service'){
    e.preventDefault();if(!e.repeat)inspect('fracture_cell');return;
  }
  if(plain&&modal==='inspect'&&selected.startsWith('fracture_')&&['q','r'].includes(k)){
    e.preventDefault();if(!e.repeat){if(k==='q')operateFixture('fracture_press',true);else use('fracture_reload',true);}return;
  }
  const bracket=e.code==='BracketLeft'||k==='['?-1:e.code==='BracketRight'||k===']'?1:0;
  if(plain&&bracket){
    e.preventDefault();if(!e.repeat){if(e.shiftKey)stepStop(bracket);else stepMoment(bracket);}return;
  }
  if(k==='m'&&!e.repeat&&!e.ctrlKey&&!e.metaKey&&!e.altKey){
    e.preventDefault();if(modal==='moments')closePanel();else momentsPanel();return;
  }
  if (modal) {
    if(mode==='walk'&&world?.inspection&&plain&&['w','a','s','d','pageup','pagedown'].includes(k)){
      e.preventDefault();if(world.restId)stand();world.keys.add(k);return;
    }
    if(mode==='walk'&&world?.inspection&&world.deckLoad<=handrailLoad&&['x','h'].includes(k)){
      e.preventDefault();if(!e.repeat)pushOff(k==='x'?'down':'away');return;
    }
    if(world?.inspection?.id==='mug'&&k===' '&&e.target?.tagName!=='BUTTON'){e.preventDefault();pressValve(true);return;}
    if(world?.inspection?.id==='mug'&&k==='t'&&plain&&!e.repeat){e.preventDefault();returnVessel();return;}
    if(world?.inspection&&k==='g'&&!e.repeat){e.preventDefault();releaseHand();turning=null;gripStart=null;return;}
    if(world?.inspection&&['arrowleft','arrowright','arrowup','arrowdown',' '].includes(k)&&e.target?.tagName!=='BUTTON'){
      e.preventDefault();if(k===' ')operateHand();else world.inspection.turn(k==='arrowleft'?-10:k==='arrowright'?10:0,k==='arrowup'?-10:k==='arrowdown'?10:0);return;
    }
    if (k === 'escape') {
      e.preventDefault();
      closePanel();
      return;
    }
    if (k === 'tab') {
      const f = [...$('panel').querySelectorAll('button:not([disabled]),[tabindex="0"]')],
        first = f[0],
        last = f.at(-1);
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last?.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first?.focus();
      }
    }
    return;
  }
  if(world.deckLoad<=handrailLoad&&(k===' '||k==='x'||k==='control')&&!e.metaKey&&!e.altKey){
    if(k===' '&&e.target?.tagName==='BUTTON')return;
    e.preventDefault();if(!e.repeat)pushOff(k===' '?'away':'down');return;
  }
  if (k === 'tab' || k === '?') {
    e.preventDefault();
    guide();
    return;
  }
  if (k === 'escape') {
    guide();
    return;
  }
  if (k === 'i') {
    inventory();
    return;
  }
  if (k === 'r') {
    route();
    return;
  }
  if(k==='v'){e.preventDefault();if(mode==='cabin'&&world.view==='earth')selectView('window');else selectView('earth');return;}
  if(k==='o'&&!e.ctrlKey&&!e.metaKey&&!e.altKey){e.preventDefault();selectView('shaded');return;}
  if(mode==='cabin'&&['arrowleft','arrowright','arrowup','arrowdown'].includes(k)){
    e.preventDefault();world.rotate(k==='arrowleft'?-9:k==='arrowright'?9:0,k==='arrowup'?-9:k==='arrowdown'?9:0);return;
  }
  if (k === ' ' && world?.restId) {
    e.preventDefault();
    stand();
    return;
  }
  if (e.target?.tagName === 'BUTTON' && [' ', 'enter'].includes(k)) return;
  if (mode === 'walk') {
    if (
      [
        'w',
        'a',
        's',
        'd',
        'q',
        'c',
        'arrowup',
        'arrowdown',
        'arrowleft',
        'arrowright',
        'pageup',
        'pagedown',
      ].includes(k)
    ) {
      e.preventDefault();
      hoverId = null;
      momentOrigin=null;
      if (world.restId) stand();
      world.keys.add(k);
    }
    if (!e.repeat && ['f', 'e', 'enter'].includes(k)) {
      e.preventDefault();
      const id = hoverId || world.pick();
      if(id==='fracture_press'&&k!=='f')operateFixture(id,true);
      else if (id) k === 'f' ? inspect(id) : use(id);
    }
  }
});
addEventListener('keyup', (e) => {
  if(e.key===' ')pressValve(false);
  const k=e.key.toLowerCase();world?.keys.delete(k);
  if(k==='e'||k==='enter'||k==='q')world?.fracture?.release();
});
addEventListener('blur', () => {
  cancelCabinGrip();
  world?.clearKeys();
  world?.switchboard?.contact(null,false);
  pointer = null;
  hoverId = null;
});
addEventListener('resize', () => {
  world?.resize();

});
addEventListener('pagehide', () => {
  if (aboard){world.fracture.persist();save(s);}
});
$('pad')
  .querySelectorAll('button')
  .forEach((b) => {
    b.onpointerdown = (e) => {
      e.preventDefault();
      if (world?.restId) stand();
      b.setPointerCapture(e.pointerId);
      world?.keys.add(b.dataset.move);
    };
    b.onpointerup = b.onpointercancel = () => world?.keys.delete(b.dataset.move);
  });
$('board').onclick = () => board();
$('pushOff').onclick=()=>pushOff();
$('deckward').onclick=()=>pushOff('down');
$('seatBoard').onclick=()=>board(true);$('resumeRide').hidden=s.progress<.0001&&!s.items.length;$('resumeRide').onclick=()=>board(false,true);
$('menuButton').onclick = guide;
$('inventoryButton').onclick = inventory;
$('telemetry').onclick = route;
$('momentsButton').onclick=momentsPanel;
$('graphicsButton').onclick=()=>graphics.open();
$('inspectionMoments').onclick=momentsPanel;
$('momentPrev').onclick=()=>stepMoment(-1);
$('momentNext').onclick=()=>stepMoment(1);
$('backdrop').onclick=()=>{if(!world?.inspection)closePanel();};
$('panelClose').onclick = () => closePanel();
$('stand').onclick = stand;
$('soundButton').onclick = () => {
  audio.toggle();
  if(radio)radio.muted=!audio.enabled;
  syncSound();
};
$('fullButton').onclick = async () => {
  try {
    if (document.fullscreenElement) await document.exitFullscreen();
    else await document.documentElement.requestFullscreen();
  } catch {
    notify('Full screen is unavailable in this browser.');
  }
};
$('hints').querySelector('button').onclick = () => {
  $('hints').hidden = true;
  sessionStorageSafe('upwell.hints', '1');
};
syncSound();

let turning=null,gripStart=null,valvePointer=null,carryLook=null;
$('backdrop').addEventListener('pointerdown',e=>{
  const hand=world?.inspection;if(!hand)return;
  $('backdrop').setPointerCapture(e.pointerId);e.preventDefault();
  if(e.button===2||hand.carrying){carryLook={id:e.pointerId,x:e.clientX,y:e.clientY};return;}
  if(hand.id==='mug'&&!hand.moveMode&&hand.hitJoint(e.clientX,e.clientY,world.camera)){valvePointer=e.pointerId;pressValve(true);return;}
  turning=[e.clientX,e.clientY];gripStart=[...turning];
});
$('backdrop').addEventListener('pointermove',e=>{
  if(carryLook?.id===e.pointerId){world.rotate(e.clientX-carryLook.x,e.clientY-carryLook.y);carryLook.x=e.clientX;carryLook.y=e.clientY;return;}
  const held=world?.inspection;if(!turning||!held)return;
  if(held.moveMode)held.move(e.clientX-turning[0],e.clientY-turning[1],world.camera);
  else held.turn(e.clientX-turning[0],e.clientY-turning[1]);turning=[e.clientX,e.clientY];
});
$('backdrop').addEventListener('pointerup',e=>{
  if(carryLook?.id===e.pointerId){carryLook=null;return;}
  if(valvePointer===e.pointerId){valvePointer=null;pressValve(false);return;}
  if(gripStart&&world?.inspection?.moveMode)releaseHand();
  else if(gripStart&&Math.hypot(e.clientX-gripStart[0],e.clientY-gripStart[1])<7&&world?.inspection?.hitJoint(e.clientX,e.clientY,world.camera))operateHand();
  turning=null;gripStart=null;
});
function endValvePointer(){valvePointer=null;carryLook=null;pressValve(false);turning=null;gripStart=null;}
$('backdrop').addEventListener('contextmenu',e=>e.preventDefault());
$('backdrop').addEventListener('pointercancel',endValvePointer);
$('backdrop').addEventListener('lostpointercapture',()=>{if(valvePointer!==null)endValvePointer();});
addEventListener('blur',endValvePointer);
$('backdrop').addEventListener('wheel',e=>{if(!world?.inspection)return;e.preventDefault();world.inspection.magnify(e.deltaY<0?1.1:.91);},{passive:false});
$('scene').addEventListener('wheel',e=>{
  if(!world||modal)return;
  if(world.view==='window'){
    const id=world.pickEvent(e);if(!['panel_gain','camera_focus'].includes(id))return;
    e.preventDefault();if(performance.now()-(world.dialAt||0)>125){use(id,false,e.deltaY<0?1:-1);world.dialAt=performance.now();}return;
  }
  e.preventDefault();world.lensZoom=clamp(world.lensZoom*(e.deltaY<0?1.09:.92),.72,2.2);
},{passive:false});
