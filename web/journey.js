import {brakingDistanceAtTime,brakingTimeForRemainingMetres,heightAtShipTime,rideForces,terminalKm,tripSeconds} from './flight-physics.js';
import {SWITCHES,freshSwitchState,restoreSwitchState,switchLabel,switchVisible} from './control-catalog.js';
export const ROOMS = {
  observation: 'Observation saloon',
  berth: 'Crew sleeper',
  service: 'Service lock',
};

export const RIDE_SECONDS = 360;
const FLIGHT = [[0,0],[9,0],[12,.0025],[16,.012],[22,.040],[32,.150],[44,.55],[58,1.48],
  [75,3.35],[92,6.4],[108,12],[135,35],[154,100],[184,660],[213,3900],[244,12600],
  [267,22500],[290,32000],[305,35500],[315,terminalKm-6],[323,terminalKm-.180],[330,terminalKm-.095],
  [339,terminalKm-.046],[345,terminalKm-.021],[351,terminalKm-.006],[360,terminalKm]];
export const STOPS = [
  [0,0,'Equatorial anchor'],[32,.15,'Tower clearance'],[58,1.48,'Cloud field'],
  [108,12,'Cloud tops'],[135,35,'Stratosphere'],[154,100,'Kármán line'],
  [184,660,'Earth limb'],[244,12600,'High orbit'],[305,35500,'Terminal approach'],
  [339,terminalKm-.046,'Receiving bay'],[360,terminalKm,'Aster Reach'],
].map(([seconds,km,name])=>[seconds/RIDE_SECONDS,km,name]);
export const FEEDS = ['Horizon', 'Tether guide', 'Counterline'];
const hardware = [
  ['service','fracture_cell','Ceramic proof tester','FC / 327','A white ceramic strip rests across two steel rollers behind the guard. The black needle follows the load. The red witness holds the highest force applied.'],
  ['service','fracture_press','Proof-test lever','FC / 327A','Hold the orange cam to bend the strip. Let it return early to unload the rollers, or take it through the break and watch the pieces inside the guard.'],
  ['service','fracture_reload','Coupon magazine','FC / 327B','Pull the index under the glass to draw five shutters across the chamber. The magazine exchanges the spent coupon and resets the red witness.'],
  ['observation','accelerometer','Mechanical accelerometer','IM / 142','Two opposed springs suspend the proof mass. The orange pointer reads the load along the carriage, with reverse travel above zero.'],
  ['observation','accel_test','Accelerometer test plunger','IM / 142B','Holding the plunger adds a calibrated 0.10 g load to the proof mass. Release it to watch the pointer settle.'],
  ['berth','capillary_cell','Galley sight glass','FL / 338','This sealed cell belongs to the galley heat exchanger. A trace of dye makes the water visible. The wick draws liquid along the wall as the carriage unloads.'],
  ['berth','capillary_primer','Galley primer','FL / 338P','One stroke sends liquid past the wick. A spring returns the piston so the closed circuit can be primed again.'],
  ['service','loom_service_power','Power service loop','EW / P6','The heavy jacketed feeder hangs between two strain-relieved connectors. Its extra length lets the rack move without pulling on the contacts.'],
  ['service','loom_service_fiber','Fiber service loop','EW / F11','The optical return is held clear of the power feeder. Its broad bend protects the fiber when the equipment moves.'],
  ['observation','nadir_port','Floor observation port','PV / 203','A recessed laminated window passes through the pressure keel. The titanium flange and two independent seals carry the load around the pane.'],
  [
    'observation',
    'pilot_console',
    'Systems console',
    'AV / 101',
    'The passenger repeater mirrors the drive computer. A green pair confirms that both independent guide circuits have a return signal.',
  ],
  [
    'observation',
    'nav_screen',
    'Flight display',
    'AV / 104',
    'The bonded display has separate pages for the passage, the guideway and the two hatch seals.',
  ],
  [
    'observation',
    'ascent_lever',
    'Exterior camera selector',
    'AV / 108',
    'Three mechanical detents select the horizon camera, the guide bogie and the neighboring ribbon. The drive computer holds the timetable.',
  ],
  [
    'observation',
    'window',
    'Observation glazing',
    'PV / 201',
    'Three pressure panes sit inside the titanium frame. The outer pane takes particle strikes and can be replaced at the terminal.',
  ],
  [
    'observation',
    'roller_shade',
    'Solar shade',
    'PV / 207',
    'A perforated solar film travels in guides on either side of the forward glazing. Its silvered outer face sends heat back out of the cabin.',
  ],
  [
    'observation',
    'lounge_seat',
    'Observation seat',
    'HB / 302',
    'The molded seat carries its load through the graphite shell. The shoulder restraint keeps the occupant in place as apparent weight falls.',
  ],
  [
    'observation',
    'lamp',
    'Saloon luminaires',
    'EL / 211',
    'Two recessed light guides share a service circuit. The diffuser lifts out after the retaining clips are released.',
  ],
  [
    'observation',
    'field_glasses',
    'Stabilized field glasses',
    'OP / 012',
    'A two-axis optical stabilizer takes out vibration from the guide rollers. The wrist lanyard clips to the window rail.',
  ],
  [
    'berth',
    'bunk',
    'Sleep pod',
    'HB / 321',
    'The quilt attaches at six points. Two broad straps hold a sleeping crew member against the ventilated liner on the upper part of the climb.',
  ],
  [
    'berth',
    'privacy_curtain',
    'Berth screen',
    'HB / 325',
    'The pleated screen runs in a captive overhead channel. The tabs are large enough to find with the berth light out.',
  ],
  [
    'berth',
    'locker_drawer',
    'Crew drawer',
    'ST / 402',
    'A damped runner brings the drawer to a stop before its contents can lift free. A spare service credential sits in the tray.',
  ],
  [
    'berth',
    'access_card',
    'Service keycard',
    'KY / 007',
    'The orange band identifies local maintenance access. Press the ceramic contact patch to the reader beside the service hatch.',
  ],
  [
    'berth',
    'reading_lamp',
    'Berth light',
    'EL / 327',
    'A narrow-beam LED puts light on the flight log without illuminating the opposite berth wall.',
  ],
  [
    'berth',
    'logbook',
    'Flight log',
    'RC / 073',
    'Last watch, 04:12 ship time. “Blue witness stripe on the guide loom is holding. Left the spare credential in the crew tray.”  — N. Ibarra',
  ],
  [
    'berth',
    'mug',
    'Crew drink vessel',
    'HB / 332',
    'A spring-loaded drinking valve closes when released. A steel ring on the base engages the restraint clip.',
  ],
  [
    'berth',
    'grab_handle',
    'Transfer handhold',
    'SF / 330',
    'The load path runs straight into the pressure frame. The smooth patch on the lower grip marks where most riders pull across the bay.',
  ],
  [
    'service',
    'pressure_hatch',
    'Service hatch',
    'PV / 503',
    'The drive retracts the leaf only after the pressure transducer reports equalization. Two independent seals surround the passage.',
  ],
  [
    'service',
    'card_reader',
    'Service access reader',
    'AC / 506',
    'A local credential releases the pressure interlock. The light turns from amber to white when the leaf is clear.',
  ],
  [
    'service',
    'service_cabinet',
    'Cable inspection bay',
    'EW / 510',
    'The heavy orange pair carries the isolated power feed. Blue fiber runs in its own clamp comb. Each branch has a witness stripe at the connector.',
  ],
  [
    'service',
    'breaker',
    'Cable-bay light switch',
    'EL / 514',
    'A guarded switch powers the raking inspection light. A displaced clamp casts a long shadow across the loom.',
  ],
  [
    'service',
    'pressure_gauge',
    'Seal pressure instrument',
    'PV / 515',
    'Two independent pressure taps straddle the hatch. The difference must settle before the leaf can travel.',
  ],
  [
    'service',
    'intercom',
    'Crew intercom',
    'CO / 511',
    'Push to listen to a short operations announcement for this stretch of the guideway.',
  ],
  [
    'service',
    'tool_roll',
    'Tethered tool wallet',
    'TK / 610',
    'Captive bits and a torque-limited driver fit individual aramid pockets. Orange retention loops stop the tools from drifting.',
  ],
  [
    'service',
    'docking_wheel',
    'Docking override wheel',
    'DK / 518',
      'Turn the wheel to center the jaws, draw the collar in, and lock the seal. The dial in the hub measures the draw screw. At 18 mm the transfer sleeve can extend.',
  ],
];
export const PROPS = {...SWITCHES,...Object.fromEntries(
  hardware.map(([room, id, name, tag, description]) => [id, { room, id, name, tag, description }]),
)};
export const CARRIED = ['field_glasses', 'access_card', 'logbook', 'mug', 'tool_roll'];
export const freshState = () => ({
  ...freshSwitchState(),
  progress: 0,
  realShipTime: false,
  followMomentView: true,
  passenger:null,
  room: 'observation',
  items: [],
  loose:{},
  fracture:{broken:false,peak:0,pieces:[]},
  feed: 0,
  screen: 0,
  shade: false,
  berthLight: true,
  curtain: false,
  drawer: false,
  unlocked: false,
  hatch: false,
  cabinet: false,
  bayLight: false,
  lamps: true,
  clamp: 0,
  deviceStops:{field_glasses:0,mug:0,logbook:0,tool_roll:0},
});
export const clamp = (x, lo = 0, hi = 1) => Math.max(lo, Math.min(hi, x));
export function smooth(a, b, x) {
  const v = clamp((x - a) / (b - a));
  return v * v * (3 - 2 * v);
}
// Shape-preserving cubic interpolation gives continuous velocity at every
// survey marker, including the last six metres of the terminal approach.
const heightSlopes=FLIGHT.map(([t,h],i)=>{
  if(i===0||i===FLIGHT.length-1)return 0;
  const [t0,h0]=FLIGHT[i-1],[t1,h1]=FLIGHT[i+1];
  const a=t-t0,b=t1-t,left=(h-h0)/a,right=(h1-h)/b;
  if(left*right<=0)return 0;
  return 3*(a+b)/((2*b+a)/left+(b+2*a)/right);
});
function cubic(y0,m0,y1,m1,span,f){
  const f2=f*f,f3=f2*f;
  return (2*f3-3*f2+1)*y0+(f3-2*f2+f)*span*m0+(-2*f3+3*f2)*y1+(f3-f2)*span*m1;
}
function finalApproach(t){
  const i=FLIGHT.length-2,[t0,h0]=FLIGHT[i],[t1,h1]=FLIGHT[i+1],span=t1-t0,left=(t1-t)/span;
  const root0=Math.cbrt(h1-h0),b=heightSlopes[i]*span/(3*root0*root0),root=left*(root0+(b-root0)*(left-1));
  return {metres:1000*root**3,rate:3*root*root*(root0+(b-root0)*(2*left-1))/span};
}
function survey(t){
  if(t<=0)return {height:0,rate:0};
  const next=FLIGHT.findIndex(([time])=>time>t);
  if(next<0)return {height:terminalKm,rate:0};
  const i=next-1,[t0,h0]=FLIGHT[i],[t1,h1]=FLIGHT[next],span=t1-t0,f=(t-t0)/span;
  if(t>=9&&t<12){
    // Leave rest with finite ship-clock speed. Both heights and the outgoing
    // survey derivative at 12 s are preserved.
    const a=Math.cbrt(h1),b=heightSlopes[next]*span/(3*a*a),root=f*(a+(b-a)*(f-1));
    return {height:root**3,rate:3*root*root*(a+(b-a)*(2*f-1))/span};
  }
  if(i===FLIGHT.length-2){
    const final=finalApproach(t);return {height:terminalKm-final.metres/1000,rate:final.rate};
  }
  const a=heightSlopes[i],b=heightSlopes[next];
  return {height:cubic(h0,a,h1,b,span,f),rate:6*f*(1-f)*(h1-h0)/span+(3*f*f-4*f+1)*a+(3*f*f-2*f)*b};
}

// The entire timetable enters 1:20 slow motion for each window encounter.
// Join in ship seconds so both cars, the cable and the sky use the same clock.
const passRate=.05;
function shipClock(t){
  if(t>=351&&t<RIDE_SECONDS){
    const q=finalApproach(t),r=brakingTimeForRemainingMetres(q.metres);
    return {time:tripSeconds-r.time,rate:r.velocity>0?q.rate*1000/r.velocity:0};
  }
  const sample=survey(t),forces=rideForces(sample.height);
  return {time:forces.shipSeconds,rate:forces.velocity>0?sample.rate*1000/forces.velocity:0};
}
function surveySeconds(km){
  let lo=9,hi=RIDE_SECONDS;
  for(let i=0;i<44;i++){const m=(lo+hi)/2;if(survey(m).height<km)lo=m;else hi=m;}
  return (lo+hi)/2;
}
const dispatchInterval=8*3600, fleet=['C12','F18','F26','C19','F11','T03','C21','F22','F16','C25','F28','T06','C15','F31','F24','C07','F35','T09'];
const classes={C:['passenger','Passenger'],F:['freight','Freight'],T:['tender','Cable tender']};
const firstDispatch=2*shipClock(129.6).time-tripSeconds;
const orbitTurn=firstDispatch+15*dispatchInterval-tripSeconds;
function service(car,dispatchShipSeconds,extra=false,featuredSeconds){
  const [kind,type]=classes[car[0]],shipSeconds=(dispatchShipSeconds+tripSeconds)/2;
  const seconds=featuredSeconds??(car==='T03'?244.15:surveySeconds(heightAtShipTime(shipSeconds)));
  return {car,kind,type,shipSeconds,seconds,at:seconds/RIDE_SECONDS,dispatchShipSeconds,
    arrivalShipSeconds:dispatchShipSeconds+tripSeconds,upDispatchShipSeconds:extra?null:dispatchShipSeconds-orbitTurn-tripSeconds,
    extra,featured:featuredSeconds!==undefined,recommended:car==='T03'};
}
export const TRAFFIC=[];
for(let i=0;firstDispatch+i*dispatchInterval<tripSeconds;i++)
  TRAFFIC.push(service(fleet[i%fleet.length],firstDispatch+i*dispatchInterval,false,i===0?129.6:undefined));
TRAFFIC.push(service('F04',2*shipClock(194.4).time-tripSeconds,true,194.4));
TRAFFIC.sort((a,b)=>a.shipSeconds-b.shipSeconds);
export const servicePattern={dispatchInterval,encounterInterval:dispatchInterval/2,cycle:fleet.length*dispatchInterval,orbitTurn,
  anchorTurn:fleet.length*dispatchInterval-2*tripSeconds-orbitTurn};

// Normal through cars have a brief pass; T03 has its own longer optical
// observation after the sunrise. The high-orbit stage follows its true height.
const protectedTimes=[...FLIGHT.map(p=>p[0]),142,148,223.5,226.5,233.7,236,238.3,240.3,310].sort((a,b)=>a-b);
const windows=TRAFFIC.map((service,i)=>{
  if(service.recommended)return {center:service.seconds,start:240.3,end:248.7,innerStart:240.90,innerEnd:247.45,
    ship:service.shipSeconds,entry:shipClock(240.3),exit:shipClock(248.7)};
  const center=service.seconds,extent=service.featured?8:1.12,core=service.featured?5:.52;
  const before=protectedTimes.filter(t=>t<center-1e-7).at(-1),after=protectedTimes.find(t=>t>center+1e-7);
  const previous=TRAFFIC[i-1]?.seconds??0,next=TRAFFIC[i+1]?.seconds??RIDE_SECONDS;
  const start=Math.max(center-extent,before,(previous+center)/2),end=Math.min(center+extent,after,(center+next)/2);
  const innerStart=center-Math.min(core,(center-start)*.65),innerEnd=center+Math.min(core,(end-center)*.65);
  return {center,start,end,innerStart,innerEnd,ship:service.shipSeconds,entry:shipClock(start),exit:shipClock(end)};
});
function encounterClock(w,t){
  const clock=u=>w.ship+(u-w.center)*passRate;
  let a,m,b,n,width,u;
  if(t<w.innerStart){a=w.entry.time;m=w.entry.rate;b=clock(w.innerStart);n=passRate;width=w.innerStart-w.start;u=(t-w.start)/width;}
  else if(t>w.innerEnd){a=clock(w.innerEnd);m=passRate;b=w.exit.time;n=w.exit.rate;width=w.end-w.innerEnd;u=(t-w.innerEnd)/width;}
  else return {time:clock(t),rate:passRate};
  return {time:cubic(a,m,b,n,width,u),rate:6*u*(1-u)*(b-a)/width+(3*u*u-4*u+1)*m+(3*u*u-2*u)*n};
}
function flightHeight(t){
  const w=windows.find(v=>t>v.start&&t<v.end);
  return w?heightAtShipTime(encounterClock(w,t).time):survey(t).height;
}
export function shipTimeAtRideSeconds(t){
  if(t<=9)return Math.max(0,t);
  if(t>=RIDE_SECONDS)return tripSeconds+9;
  const w=windows.find(v=>t>v.start&&t<v.end);
  return 9+(w?encounterClock(w,t).time:shipClock(t).time);
}
export function shipRateAtRideSeconds(t){
  if(t<=9)return 1;
  if(t>=RIDE_SECONDS)return 0;
  const w=windows.find(v=>t>v.start&&t<v.end);
  return w?encounterClock(w,t).rate:shipClock(t).rate;
}
export function rideSecondsAtShipTime(t){
  if(t<=9)return Math.max(0,t);
  if(t>=tripSeconds+9)return RIDE_SECONDS;
  const drive=t-9,km=heightAtShipTime(drive);
  if(drive>tripSeconds-brakingTimeForRemainingMetres(6).time){
    const remaining=brakingDistanceAtTime(tripSeconds-drive);
    let lo=351,hi=RIDE_SECONDS;
    // Compare distances to the docking datum, retaining submillimetre precision.
    for(let i=0;i<36;i++){const m=(lo+hi)/2;
      if(finalApproach(m).metres>remaining)lo=m;else hi=m;}
    return (lo+hi)/2;
  }
  const w=windows.find(v=>drive>v.entry.time&&drive<v.exit.time);
  if(w&&drive>=w.ship+(w.innerStart-w.center)*passRate&&drive<=w.ship+(w.innerEnd-w.center)*passRate)
    return w.center+(drive-w.ship)/passRate;
  let lo=w?.start??9,hi=w?.end??RIDE_SECONDS;
  for(let i=0;i<36;i++){const m=(lo+hi)/2;if(w?encounterClock(w,m).time<drive:survey(m).height<km)lo=m;else hi=m;}
  return (lo+hi)/2;
}
const highOrbit=STOPS.find(s=>s[1]===12600);
highOrbit[0]=rideSecondsAtShipTime(9+rideForces(highOrbit[1]).shipSeconds)/RIDE_SECONDS;
export function counterlineAt(km,shipSeconds,ownVelocity=rideForces(km).velocity){
  let i=0;
  for(let j=1;j<windows.length;j++)if(Math.abs(windows[j].ship-shipSeconds)<Math.abs(windows[i].ship-shipSeconds))i=j;
  const cross=windows[i].ship,returnKm=heightAtShipTime(2*cross-shipSeconds),separation=(returnKm-km)*1000;
  return {...TRAFFIC[i],index:i,shipSeconds:cross,eta:cross-shipSeconds,km:returnKm,separation,
    closingMps:ownVelocity+rideForces(returnKm).velocity,inRange:Math.abs(separation)<1100};
}
for(let i=0;i<windows.length;i++){
  const w=windows[i];let low=w.start,high=w.center;
  for(let step=0;step<34;step++){
    const time=(low+high)/2,km=flightHeight(time),own=rideForces(km);
    if(counterlineAt(km,own.shipSeconds,own.velocity).separation>1100)low=time;else high=time;
  }
  TRAFFIC[i].approachAt=high/RIDE_SECONDS;
}
export function travel(p) {
  const progress = clamp(p);
  let i = 0;
  while (i < STOPS.length - 1 && progress >= STOPS[i + 1][0] - 1e-8) i++;
  const seconds=progress*RIDE_SECONDS,km=flightHeight(seconds);
  const forces=rideForces(km);
  const elapsedHours=forces.shipSeconds/3600, solarHour=6.58+elapsedHours;
  const angle=(solarHour/24-.5)*2*Math.PI,dec=-12*Math.PI/180;
  const sunDirection=[-Math.cos(dec)*Math.sin(angle),Math.cos(dec)*Math.cos(angle),Math.sin(dec)];
  const horizonDip=Math.acos(6371/(6371+km));
  const sunVisible=smooth(-.00465,.00465,Math.asin(sunDirection[1])+horizonDip);
  const speed=Math.round(forces.velocity*3.6);
  return {
    km, speed, seconds, elapsedHours, sunDirection, sunVisible,forces,traffic:counterlineAt(km,forces.shipSeconds,forces.velocity),
    atmosphere:km<16?'Troposphere':km<50?'Stratosphere':km<85?'Mesosphere':km<600?'Thermosphere':km<10000?'Exosphere':'Outer space',
    remainingMeters:Math.max(0,(terminalKm-km)*1000), localSolarHour:solarHour%24,
    weatherSeconds:seconds*1.2+elapsedHours*2200,
    weather:{coverage:.59+.055*Math.sin(seconds*.016+.5),wind:[.018,.007],evolution:.57},
    name:STOPS[i][2],
    index: i,
    orbital: smooth(15,105,km), deep:smooth(650,16000,km), approach:smooth(286,357,seconds),
  };
}
export const kmText = (n) => Math.round(n).toLocaleString('en-US');
export const altitudeText=km=>km<1?Math.round(km*1000).toLocaleString('en-US')+' m':(km<20?km.toFixed(1):kmText(km))+' km';
export function activeTraffic(p){
  const km=flightHeight(clamp(p)*RIDE_SECONDS),traffic=counterlineAt(km,rideForces(km).shipSeconds);
  return traffic.inRange?traffic:undefined;
}
export const roomAt = (z) => (z < -1.9 ? 'observation' : z < 1.9 ? 'berth' : 'service');
export function restore() {
  const state = freshState();
  try {
    const stored=localStorage.getItem('upwell.passage.3');
    const raw = JSON.parse(stored??localStorage.getItem('upwell.passage.2'));
    if (!raw || !Number.isFinite(raw.progress)) return state;
    for (const k of Object.keys(state))
      if (typeof state[k] === 'boolean')
        state[k] = raw[k] === undefined ? state[k] : raw[k] === true;
    if(Number.isFinite(raw.curtain))state.curtain=clamp(raw.curtain);
    state.progress = clamp(raw.progress);
    if (!stored && state.progress>0 && state.progress<1) {
      const oldStops=[[0,12],[.14,38],[.3,100],[.5,660],[.79,16000],[1,35786]];
      const n=oldStops.findIndex(([x])=>x>state.progress);
      const [a,h]=oldStops[n-1],[b,k]=oldStops[n];
      const oldAltitude=h*(k/h)**((state.progress-a)/(b-a));
      let low=0,high=1;
      for(let j=0;j<36;j++){const mid=(low+high)/2;if(flightHeight(mid*RIDE_SECONDS)<oldAltitude)low=mid;else high=mid;}
      state.progress=(low+high)/2;
    }
    state.room = Object.hasOwn(ROOMS, raw.room) ? raw.room : 'observation';
    if (state.room === 'service' && !state.unlocked) state.room = 'berth';
    const pose=raw.passenger;
    const finiteVector=(value,n)=>Array.isArray(value)&&value.length===n&&value.every(Number.isFinite);
    if(pose&&finiteVector(pose.position,3)&&finiteVector(pose.flight?.velocity,3)&&
      [pose.yaw,pose.pitch,pose.seconds,pose.flight.deckY].every(Number.isFinite)&&
      Math.abs(pose.position[0])<=2.0&&Math.abs(pose.position[2])<=5.4&&pose.position[1]>=1.25&&pose.position[1]<=2.42){
      const room=roomAt(pose.position[2]);
      if(room!=='service'||state.unlocked){
        state.passenger={room,position:pose.position,yaw:pose.yaw,pitch:clamp(pose.pitch,-1.28,1.28),
          seconds:clamp(pose.seconds,0,RIDE_SECONDS),flight:{deckY:clamp(pose.flight.deckY,1.38,1.65),
            velocity:pose.flight.velocity.map(v=>clamp(v,-8,8)),ballistic:pose.flight.ballistic===true}};
      }
    }
    state.items = [
      ...new Set((Array.isArray(raw.items) ? raw.items : []).filter((k) => CARRIED.includes(k))),
    ];
    for(const id of CARRIED){
      const e=raw.loose?.[id];
      const valid=(arr,n)=>Array.isArray(arr)&&arr.length===n&&arr.every(Number.isFinite);
      if(!e||!valid(e.p,3)||!valid(e.q,4)||!valid(e.v,3)||!valid(e.w,3)||state.items.includes(id))continue;
      if(Math.abs(e.p[0])>2.22||e.p[1]<-.04||e.p[1]>2.69||Math.abs(e.p[2])>5.71)continue;
      state.loose[id]={p:e.p,q:e.q,v:e.v.map(x=>clamp(x,-8,8)),w:e.w.map(x=>clamp(x,-30,30)),rest:e.rest===true};
    }
    for (const [k, hi] of [
      ['feed', 2],
      ['screen', 5],
      ['clamp', 3],
    ])
      state[k] = clamp(Math.trunc(Number(raw[k]) || 0), 0, hi);
    if (state.progress < 1) state.clamp = 0;
    for(const id of ['field_glasses','logbook','tool_roll'])
      state.deviceStops[id]=clamp(Math.trunc(Number(raw.deviceStops?.[id])||0),0,id==='field_glasses'?5:1);
    const cell=raw.fracture;
    if(cell){
      state.fracture.broken=cell.broken===true;
      state.fracture.peak=state.fracture.broken?320:clamp(Number(cell.peak)||0,0,320);
      const finite=(a,n)=>Array.isArray(a)&&a.length===n&&a.every(Number.isFinite);
      if(state.fracture.broken&&Array.isArray(cell.pieces)&&cell.pieces.length===5&&cell.pieces.every(
        b=>b&&finite(b.p,3)&&finite(b.q,4)&&finite(b.v,3)&&finite(b.w,3)&&Math.hypot(...b.q)>.01&&b.p.every(x=>Math.abs(x)<.25))){
        state.fracture.pieces=cell.pieces.map(b=>{
          const piece={p:b.p,q:b.q,v:b.v.map(x=>clamp(x,-2,2)),w:b.w.map(x=>clamp(x,-40,40))};
          if(finite(b.restNormal,3)&&Math.abs(Math.hypot(...b.restNormal)-1)<.01)piece.restNormal=b.restNormal;
          return piece;
        });
      }
    }
    restoreSwitchState(state,raw);
    if (!state.unlocked) state.hatch = false;
  } catch {
    /* Storage can be disabled in private browsing. */
  }
  return state;
}
export function save(s) {
  try {
    localStorage.setItem('upwell.passage.3', JSON.stringify(s));
  } catch {}
}
export function visibleProp(id, s) {
  if(id.startsWith('loom_service_'))return s.cabinet&&s.unlocked;
  if(SWITCHES[id])return switchVisible(id,s);
  if(s.loose?.[id])return true;
  if (s.items.includes(id)) return false;
  if (id === 'access_card') return s.drawer;
  return true;
}
export function actionLabel(id, s) {
  if(SWITCHES[id])return switchLabel(id,s);
  if(s.loose?.[id])return travel(s.progress).forces.gravityG<.08?'Catch':'Pick up';
  if (CARRIED.includes(id)) return s.items.includes(id) ? 'Inspect' : 'Pick up';
  const labels = {
    loom_service_power:'Pluck cable',loom_service_fiber:'Pluck cable',
    accelerometer:'Read mechanical load',accel_test:'Apply test load',
    capillary_cell:'Look into cell',capillary_primer:'Stroke primer',
    fracture_cell:'Read tester',fracture_press:'Hold proof-test lever',fracture_reload:'Index next coupon',
    nadir_port: 'Look down through glass',
    pilot_console: 'Check systems',
    nav_screen: 'Change page',
    ascent_lever: 'Select camera',
    window: 'Look outside',
    roller_shade: s.shade ? 'Raise shade' : 'Lower shade',
    lounge_seat: 'Take a seat',
    lamp: s.lamps ? 'Lights off' : 'Lights on',
    bunk: 'Rest in berth',
    privacy_curtain: Number(s.curtain)>=.5 ? 'Stow screen' : 'Draw screen',
    locker_drawer: s.drawer ? 'Close drawer' : 'Open drawer',
    reading_lamp: s.berthLight ? 'Switch off' : 'Switch on',
    grab_handle: 'Take hold',
    pressure_hatch: s.hatch ? 'Close hatch' : s.unlocked ? 'Open hatch' : 'Check interlock',
    card_reader: s.unlocked ? 'Check access' : 'Present keycard',
    service_cabinet: s.cabinet ? 'Close panel' : 'Expose looms',
    breaker: s.bayLight ? 'Light off' : 'Light the looms',
    pressure_gauge: 'Read pressure',
    intercom: 'Listen',
    docking_wheel: s.clamp === 3 ? 'Read clamp' : 'Turn wheel',
  };
  return labels[id] || 'Inspect';
}
