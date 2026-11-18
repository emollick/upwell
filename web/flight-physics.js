const R = 6378137;
const MU = 3.986004418e14;
const OMEGA = 7.292115e-5;
const G0 = 9.80665;
// Equatorial WGS 84 monopole. The fixed receiver co-rotates at the
// synchronous radius, where gravitational and centrifugal accelerations match.
const DISTANCE = Math.cbrt(MU/(OMEGA*OMEGA))-R;
export const terminalKm = DISTANCE/1000;
const CRUISE = 170;
export const handrailLoad = .06;

export function loadLabel(forces) {
  if(forces.gravityG<.001)return 'Microgravity · <0.001 g';
  if(forces.down<-.012)return forces.gravityG.toFixed(3)+' g · toward ceiling';
  if(forces.gravityG<=handrailLoad)return 'Low gravity · '+forces.gravityG.toFixed(3)+' g';
  return forces.gravityG.toFixed(3)+' g · cabin load';
}

function ramp(acceleration, jerkTime) {
  const duration = CRUISE / acceleration + jerkTime;
  return { acceleration, jerkTime, duration, length: CRUISE * duration / 2 };
}
const launch = ramp(.30,4), braking = ramp(.14,7);
const coastLength = DISTANCE - launch.length - braking.length;
export const tripSeconds = launch.duration + braking.duration + coastLength / CRUISE;

// Symmetric finite-jerk acceleration. Integrating position and inverting it
// keeps the physical clock independent of the six-minute viewing timetable.
function sampleRamp(t, r) {
  const a=r.acceleration,j=a/r.jerkTime,remain=r.duration-t;
  if(t<r.jerkTime)return {x:j*t*t*t/6,v:j*t*t/2,a:j*t};
  if(remain<r.jerkTime)return {x:r.length-CRUISE*remain+j*remain**3/6,
    v:CRUISE-j*remain*remain/2,a:j*remain};
  const u=t-r.jerkTime,v0=.5*a*r.jerkTime;
  return {x:a*r.jerkTime*r.jerkTime/6+v0*u+a*u*u/2,v:v0+a*u,a};
}
function atDistance(x,r) {
  if(x<=0)return {v:0,a:0,t:0};
  let lo=0,hi=r.duration;
  for(let i=0;i<40;i++){const t=(lo+hi)/2;if(sampleRamp(t,r).x<x)lo=t;else hi=t;}
  const t=(lo+hi)/2;
  return {...sampleRamp(t,r),t};
}
export function heightAtShipTime(t) {
  if(t<=0)return 0;
  if(t>=tripSeconds)return terminalKm;
  if(t<launch.duration)return sampleRamp(t,launch).x/1000;
  const left=tripSeconds-t;
  if(left<braking.duration)return (DISTANCE-sampleRamp(left,braking).x)/1000;
  return (launch.length+CRUISE*(t-launch.duration))/1000;
}
export function brakingTimeForRemainingMetres(metres){
  const q=atDistance(Math.max(0,metres),braking);
  return {time:q.t,velocity:q.v};
}
export function brakingDistanceAtTime(timeLeft){return sampleRamp(timeLeft,braking).x;}
export function rideForces(km) {
  const h=Math.min(DISTANCE,Math.max(0,km*1000)),remain=DISTANCE-h;
  let velocity=CRUISE,driveAcceleration=0,shipSeconds=launch.duration+(h-launch.length)/CRUISE;
  if(h<launch.length){const q=atDistance(h,launch);velocity=q.v;driveAcceleration=q.a;shipSeconds=q.t;}
  else if(remain<braking.length){const q=atDistance(remain,braking);velocity=q.v;driveAcceleration=-q.a;shipSeconds=tripSeconds-q.t;}
  const radius=R+h;
  const earthGravity=MU/(radius*radius),centrifugal=OMEGA*OMEGA*radius;
  const effectiveDown=earthGravity-centrifugal,down=effectiveDown+driveAcceleration;
  const west=2*OMEGA*velocity;
  return {velocity,driveAcceleration,shipSeconds,earthGravity,centrifugal,effectiveDown,down,west,
    gravityG:Math.hypot(down,west)/G0,driveG:driveAcceleration/G0};
}
