// Shared deterministic world-space weather medium. Distances km, time seconds.
export const EARTH_KM=6371;
export const WEATHER_DEFAULTS=Object.freeze({coverage:.58,wind:[.018,.007],evolution:.5});
let bytes, organization, pending;
export function marineOrganization(){return organization;}
export async function loadWeatherNoise(){
  if(!pending)pending=Promise.all(['cloud-noise-64.rgba','marine-organization.rgba'].map(async name=>{
    const r=await fetch(new URL('./assets/planet/'+name,import.meta.url));if(!r.ok)throw new Error('Weather field could not be loaded');
    return new Uint8Array(await r.arrayBuffer());
  })).then(([cube,regions])=>{if(cube.length!==64**3*4||regions.length!==256**2*4)throw new Error('Invalid weather field');
    bytes=cube;organization=regions;return bytes;});
  return pending;
}
const clamp=(x,a=0,b=1)=>Math.max(a,Math.min(b,x));
const smooth=(a,b,x)=>{const t=clamp((x-a)/(b-a));return t*t*(3-2*t);};
function marineTex(u,v){
  if(!organization)return [.5,.5,.5,.5];
  const x=(u-Math.floor(u))*256-.5,y=(v-Math.floor(v))*256-.5,ix=Math.floor(x),iy=Math.floor(y),fx=x-ix,fy=y-iy;
  const values=[0,0,0,0];
  for(let b=0;b<2;b++)for(let a=0;a<2;a++){
    const i=((((iy+b)&255)*256)+((ix+a)&255))*4,w=(a?fx:1-fx)*(b?fy:1-fy)/255;
    for(let c=0;c<4;c++)values[c]+=w*organization[i+c];
  }return values;
}
function tex(p,c){
  if(!bytes)return .5;
  const g=p.map(v=>(v-Math.floor(v))*64-.5),i=g.map(Math.floor),f=g.map((v,k)=>v-i[k]);let sum=0;
  for(let z=0;z<2;z++)for(let y=0;y<2;y++)for(let x=0;x<2;x++){
    const ix=(i[0]+x+64)%64,iy=(i[1]+y+64)%64,iz=(i[2]+z+64)%64;
    sum+=bytes[((iz*64+iy)*64+ix)*4+c]/255*(x?f[0]:1-f[0])*(y?f[1]:1-f[1])*(z?f[2]:1-f[2]);
  }return sum;
}
// A sinuous dry slot separates the moist marine streets from the sheared
// storm flank. The coordinates follow the moving air mass.
function drySlot(u,v){
  const center=-1.5+1.7*Math.sin(.115*u+.55)+2.2*Math.sin(.045*u-.75);
  const broadening=1.+.85*smooth(9.,34.,u);
  return (1.-smooth(1.20*broadening,4.90*broadening,Math.abs(v-center)))*(1.-smooth(27.,65.,Math.abs(u-8.)));
}
function thermal(x,y,z){return 1.-x*x-y*y-z*z;}
// A sloping intrusion of dry air intersects the edge of the marine bank.
// All coordinates move with the air parcel. Distances are kilometres.
function sunbreak(x,z,h,baseDensity){
  if(h>12.||x< -15.||x>53.||z< -27.||z>12.)return baseDensity;
  x+=3.20;
  z+=1.25;
  let along=.978*x-.209*z;
  let across=.209*x+.978*z;
  let bend=.44*Math.sin(.15*along+.4)+.19*Math.sin(.31*along);
  let span=smooth(-2.,1.4,along)*(1.-smooth(39.,49.,along));
  let core=1.-smooth(1.48,4.20,Math.abs(across-bend));
  let centre=3.15+.163*along+.10*Math.sin(.27*along)+.07*Math.sin(across*.7);
  let intrusion=span*core*(1.-smooth(.43,1.15,Math.abs(h-centre)));
  let density=baseDensity*(1.-intrusion);
  if(along< -8.||along>.75||Math.abs(across)>6.3||h<1.8||h>4.1)return density;
  let eddy=.57*tex([x/3.7,h/3.7,z/3.7],0)+.43*tex([x/.94,h/.94,z/.94],2);
  let lip=-.17+.16*Math.sin(2.17*across)+.59*(eddy-.5);
  let fringe=smooth(-7.8,-4.8,along)*(1.-smooth(lip-.14,lip+.16,along));
  fringe*=1.-smooth(2.0,6.1,Math.abs(across+.37*Math.sin(1.2*along)));
  let floorH=2.38+.14*Math.sin(.82*across+.4*along)+.22*(eddy-.5);
  let topH=3.12+.18*Math.sin(.92*across-.50*along)+.34*(eddy-.5)
              +.16*Math.sin(4.6*across+1.2*along)+.10*Math.sin(6.1*along-3.2*across);
  let hydro=smooth(floorH-.16,floorH+.16,h)*(1.-smooth(topH-.16,topH+.15,h));
  return Math.max(density,fringe*hydro*(2.75+2.65*eddy));
}
// Horizontal humidity belongs to a parcel, including where the ray crosses its roof.
function openBasin(u,v,bend,fold){
  let sound=thermal((u+2.8+7.2*bend)*.052,(v-21.4-7.8*fold-2.7*bend)*.126,0.);
  let inlet=thermal((u-40.-5.6*fold)*.058,(v+16.8-8.3*bend)*.116,0.);
  return smooth(-.22,.62,Math.max(sound,inlet));
}
function marineRaft(u,v,h,slot,cover,column,shore,ridge,grain,fraction,draft,breakup,moisture,upstream){
  let bend=column-.50,fold=shore-.47;
  let distortion=5.4*(breakup-.50)+3.2*(ridge-.55)+2.6*(grain-.50);
  let raggedSlot=drySlot(u+3.4*fold,v+distortion);
  let basin=openBasin(u+4.1*(breakup-.5),v+distortion,bend,fold);
  let humidity=.46+.85*(fraction-.55)+.42*bend+.28*fold+.25*(moisture-.50)+.17*(ridge-.52)+.12*(cover-.72)-.39*raggedSlot-.31*basin-.09*slot;
  humidity+=.18*smooth(.55,.78,moisture)*(1.-.86*raggedSlot)*(1.-.70*basin)-.31*(1.-smooth(.26,.46,moisture));
  let edge=smooth(.22,.60,humidity+.29*(grain-.48)+.20*(breakup-.50));
  let floorH=.89+.38*bend+.12*fold+.145*(ridge-.5)+.16*(breakup-.5)+.19*(1.-edge);
  let roof=floorH+.24+edge*(.43+.76*column+.51*ridge+1.36*draft)+.61*(grain-.48);
  let profile=smooth(floorH-.12,floorH+.135,h)*(1.-smooth(roof-.24,roof+.19,h));
  let wispH=floorH+.63+.61*draft+.31*ridge+.29*(breakup-.50);
  let torn=smooth(.12,.48,upstream-fraction)*smooth(.31,.77,upstream);
  let wisp=torn*smooth(wispH-.39,wispH-.08,h)*(1.-smooth(wispH+.03,wispH+.27,h));
  let mixing=.22+.78*smooth(.20,.72,grain+.37*edge+.24*(breakup-.50));
  return Math.max(edge*edge*profile*(.96+1.57*edge+.55*ridge)*mixing,.075*wisp);
}
function stratiformShield(u,v,h,slot,cover,column,shore,grain,curl,fraction,draft,breakup,moisture,upstream){
  let bend=column-.50,fold=shore-.47;
  let distortion=6.8*(breakup-.5)+4.2*(grain-.5)+3.7*(fraction-.57);
  let inlet=openBasin(u+4.7*(moisture-.5),v+distortion,bend,fold);
  let raggedSlot=drySlot(u+5.2*fold,v+.75*distortion);
  let front=Math.abs(v+3.2-8.3*bend-5.7*fold);
  let wing=smooth(2.4,9.8,front);
  let humidity=.36+.90*(moisture-.49)+.71*(fraction-.56)+.44*bend+.29*fold+.25*(wing-.50)+.12*(cover-.72)-.33*raggedSlot-.28*inlet-.08*slot;
  humidity+=.29*smooth(.56,.80,moisture)*(1.-.85*raggedSlot)*(1.-.75*inlet)-.40*(1.-smooth(.27,.45,moisture));
  // Upstream of the deep convection, entrainment erodes the lid from above.
  // The thinning slope and its cloudy filaments extend into the ocean lead.
  let along=u+.26*v+2.8*fold+1.46*(breakup-.5);
  let seam=Math.abs(v-(2.55+.22*u+4.34*fold+3.83*(breakup-.5)+2.1*(grain-.50)));
  let dryMix=smooth(-27.,-6.,along)*(1.-smooth(.3,16.,along))*(1.-smooth(2.75,12.15,seam));
  humidity-=dryMix*(.66+.49*smooth(5.05,8.63,h));
  let mass=smooth(.265,.65,humidity+.24*(grain-.50)+.21*(breakup-.50));
  let floorH=4.87+1.22*column+.44*fold+.38*(wing-.5)+.34*(breakup-.50)+.78*(1.-mass);
  let roof=floorH+.21+mass*(.61+1.06*column+.41*wing+2.32*draft)+.89*(grain-.50)+.46*(curl-.48);
  roof-=1.31*dryMix*(.51+.49*breakup);
  let profile=smooth(floorH-.23,floorH+.32,h)*(1.-smooth(roof-.34,roof+.24,h));
  let wispH=floorH+.52+.79*moisture+.77*draft+.48*(grain-.50)+.33*(breakup-.50);
  let torn=smooth(.12,.51,upstream-fraction)*smooth(.36,.77,upstream)*(.16+.84*smooth(.26,.75,breakup));
  let wisp=torn*smooth(wispH-.59,wispH-.11,h)*(1.-smooth(wispH+.06,wispH+.38,h));
  return Math.max(mass*mass*profile*(.78+1.34*mass),.118*wisp);
}
function stormCrown(u,v,h,shape,curl,erosion){
  if(u < -13.||u > 52.||v < -27.||v > 25.)return 0.;
  // The inflow rolls a cleft into the west face of the rising column; the
  // flanking roll stays attached to the core and curls around the opening.
  let gullyU=u-7.19-.46*(h-8.55)-1.34*(shape-.5)-.68*(erosion-.5);
  let gullyV=v+.03-.26*(h-8.55)+1.28*(curl-.50);
  let gully=thermal(gullyU*.45,gullyV*.66,(h-8.91)*.264);
  let drag=.12*(h-5.)+1.13*smooth(9.5,12.,h);
  u-=drag+1.51*(curl-.5);v-=.48*drag+2.17*(shape-.5)+.74*(erosion-.5);
  let rootA=thermal((u-8.70)*.136,(v-1.75)*.257,(h-4.31)*.306);
  let rootB=thermal((u-8.14)*.135,(v+16.90)*.225,(h-4.42)*.298);
  let roll=.78*(curl-.50)+.51*(erosion-.50);
  let shoulder=thermal((u-9.7+1.52*roll)*.224,(v-1.30-1.74*roll-.20*(h-7.4))*.304,(h-8.55)*.215);
  let turret=thermal((u-12.3)*.36,(v-1.88)*.40,(h-10.28)*.315);
  let flank=thermal((u-6.2)*.147,(v+8.8)*.239,(h-6.55)*.41);
  let farCore=thermal((u-8.5)*.195,(v+17.25)*.25,(h-8.72)*.223);
  let farTurret=thermal((u-7.0)*.35,(v+17.85)*.40,(h-10.76)*.378);
  let scud=thermal((u+2.25)*.22,(v+4.70)*.78,(h-7.80-.26*(v+4.6))*1.09);
  let plumeU=u-11.8;
  let driftV=2.35+.202*plumeU+1.55*(curl-.48)+.064*plumeU*(shape-.50);
  let reach=smooth(-6.,3.,plumeU)*(1.-smooth(16.,36.,plumeU+6.8*(shape-.47)));
  let halfWidth=2.0+.158*Math.max(0.,plumeU)+2.35*(shape-.46);
  let fringe=1.-smooth(halfWidth-.81,halfWidth+1.34,Math.abs(v-driftV));
  let roof=11.34+.020*plumeU+.38*(shape-.5)+.25*(curl-.50);
  let thickness=.26+.73*(1.-smooth(2.,29.,plumeU));
  let iceFan=reach*fringe*smooth(roof-thickness-.19,roof-thickness+.22,h)*(1.-smooth(roof-.06,roof+.32,h));
  let lift=Math.max(Math.max(rootA,rootB),Math.max(Math.max(shoulder,turret),Math.max(flank,Math.max(farCore,farTurret))));
  lift=Math.max(lift,.61*scud-.15);
  lift-=.97*smooth(-.45,.88,gully);
  let rolledShoulder=thermal((u-7.69-.31*(h-8.6))*.43,(v-1.03+.29*(h-8.6))*.74,(h-8.8)*.33);
  lift=Math.max(lift,.75*rolledShoulder-.16);
  let scallop=(.88*(shape-.50)+.54*(curl-.51)+.33*(erosion-.50))*(.46+.54*smooth(4.3,8.8,h));
  let column=smooth(-.085,.47,lift+scallop)*smooth(1.28,1.87,h)*(1.74+.72*shape+.75*curl+.63*erosion);
  return Math.max(column,iceFan*(.59+.79*(1.-smooth(6.,29.,plumeU))));
}
// A shelf at the leading edge of a marine squall line, with precipitation
// reaching down behind it and ice spreading downwind from the updraft.
function squallLine(x,z,h,density,widthKm){
  if(x < -45.||x>45.||z < -53.||z>4.||h>16.15)return density;
  const along=(x+7.)*.974-(z+25.)*.227;
  const across=(z+25.)*.974+(x+7.)*.227;
  const range=smooth(-36.,-23.,along)*(1.-smooth(23.,40.,along));
  if(range<=0.||across < -20.||across>27.)return density;
  const frontBow=2.7*Math.sin(.086*along+.52)+1.1*Math.sin(.163*along-.42);
  const distanceFromFront=across-frontBow;
  const billowsUV=[along/32.+.39,h/19.+.28,across/17.+.62];
  const eddy=(tex(billowsUV,0)-.5)*(1.-smooth(.8,3.,widthKm));
  const ridge=(tex(billowsUV,1)-.5)*(1.-smooth(1.4,5.5,widthKm));
  const depth=distanceFromFront+.93*eddy+.69*ridge;
  // Subsidence ahead of the front clears a winding lead in both lower decks.
  const opening=smooth(2.5,7.4,depth)*(1.-smooth(13.,23.,depth))
               *smooth(-27.,-12.,along)*(1.-smooth(4.3,11.,h));
  density*=1.-.96*range*opening;
  let wet=0.;
  if(h<5.3){
    const shelfEdge=5.55+.35*Math.sin(.61*along)+.19*Math.sin(1.32*along-.3)+1.09*ridge;
    const overlap=1.-smooth(shelfEdge-.55,shelfEdge+.38,depth);
    const wedge=smooth(-6.2,-2.7,depth)*overlap;
    const shelfBase=1.14+.145*depth+.52*eddy+.18*Math.sin(.46*along+.62*depth);
    const roof=3.84-.264*Math.max(0.,depth)+.42*ridge+.36*eddy;
    wet=wedge*smooth(shelfBase-.22,shelfBase+.22,h)*(1.-smooth(roof-.27,roof+.33,h))
        *(.95+.46*ridge+.67*eddy);
    const rainAxis=-2.2+.37*h+.68*ridge;
    const shaft=1.-smooth(1.25,4.10,Math.abs(depth-rainAxis));
    const streak=tex([(along-.32*h)/15.+.39,h/43.+.21,(depth-.20*h)/19.+.17],0);
    const showers=(.10+.92*smooth(.30,.72,streak))*(1.-smooth(2.9,4.55,h));
    wet=Math.max(wet,shaft*showers*smooth(-26.,-11.,along)*(1.-smooth(3.,16.,along)));
  }
  if(h>2.3){
    const foldsUV=[(along-.24*h)/9.3+.19,h/8.2+.55,(depth+.19*h)/7.7+.29];
    const roll=(.57*tex(foldsUV,0)+.43*tex(foldsUV,2)-.5)*(1.-smooth(.45,2.4,widthKm));
    const lift=Math.exp(-.014*(along+6.)*(along+6.))+.55*Math.exp(-.026*(along-5.)*(along-5.));
    const fan=smooth(10.3,14.3,h);
    const coreDepth=depth+1.15+.158*h-1.16*eddy-.53*ridge;
    const bulb=3.16*Math.exp(-.17*(along+5.-.61*(h-10.))*(along+5.-.61*(h-10.))-.054*(h-9.9)*(h-9.9));
    const halfWidth=1.85+1.01*lift+bulb+1.47*roll+1.24*eddy+(1.-smooth(2.4,6.2,h))*1.28;
    const column=1.-smooth(halfWidth-1.15,halfWidth+.58,Math.abs(coreDepth));
    const roof=5.87+8.64*Math.min(1.,lift)+2.45*eddy+1.28*ridge+1.24*roll;
    const updraft=column*smooth(2.3,3.65,h)*(1.-smooth(roof-.79,roof+.45,h));
    wet=Math.max(wet,updraft*(1.51+.39*eddy+.44*ridge));
    if(fan>.001){
      const drift=along+4.;
      const width=2.62+.12*Math.max(0.,drift)+1.88*eddy;
      const radius=Math.abs(coreDepth-.13*drift-.026*drift*ridge);
      const span=smooth(-8.,-1.7,drift)*(1.-smooth(12.,30.,drift+7.2*ridge+2.9*roll));
      const grainUV=[(drift+.71*coreDepth)/58.+.27,(h-.02*drift)/6.+.48,(coreDepth-.14*drift)/13.+.71];
      const strands=.52+(.64*tex(grainUV,0)+.36*tex(grainUV,2)-.52)*(1.-smooth(.46,2.2,widthKm));
      const fringe=1.-smooth(width-1.9,width+1.15,radius-3.5*(strands-.5));
      const cap=13.06+.021*drift+.26*Math.sin(.115*drift)+.89*eddy+.63*ridge+.83*roll;
      const fall=.42+1.16*(1.-smooth(-1.,24.,drift))+.72*(strands-.5);
      const ice=smooth(cap-fall-.48,cap-fall+.48,h)*(1.-smooth(cap-.28,cap+.24,h));
      wet=Math.max(wet,span*fringe*ice*(.09+.88*smooth(.35,.72,strands)));
      // A short turret breaks through the stable sheet at its feeding end.
      const turret=thermal((along+5.15+.99*eddy)*.28,(coreDepth-1.62-1.41*ridge)*.38,(h-14.08)*.599);
      wet=Math.max(wet,1.78*smooth(-.13,.42,turret+1.50*roll+.72*eddy));
    }
  }
  return Math.max(density,range*wet);
}
export function sampleCloudDensity(p,time=0,weather={}){
  const h=Math.hypot(...p)-EARTH_KM;if(h<.04||h>16.15)return 0;
  const coverage=clamp(weather.coverage??.58),wind=weather.wind??[.018,.007],e=clamp(weather.evolution??.5);
  const q=[p[0]-wind[0]*time,p[1]-EARTH_KM,p[2]-wind[1]*time];
  const n=(scale,c,offset=[0,0,0])=>tex(q.map((v,i)=>v/scale+offset[i]),c);
  const macro=.64*n(7600,3)+.36*n(1900,0);
  const cover=smooth(.26,.68,macro+(coverage-.5)*.65);
  const frontU=.72*q[0]-.69*q[2],frontV=.69*q[0]+.72*q[2],slot=drySlot(frontU,frontV);
  let density=0;
  const airMass=[frontU/123.+.34,.37,frontV/99.+.61],column=tex(airMass,3),shore=.58*tex(airMass,0)+.42*tex(airMass,1);
  const airX=(frontU-(h-1.5)*.49)/146.+.418,airY=(frontV-(h-1.5)*.25)/131.+.583,field=marineTex(airX,airY),upstream=marineTex(airX-.030,airY-.011)[0];
  if(h<4.28){
    const rows=[(frontU-2.8*(shore-.48))/56.+.41,.19,(frontV+6.7*(column-.5))/23.+.27];
    const ridge=smooth(.24,.74,.61*tex(rows,0)+.39*tex(rows,1));
    const grain=.65*n(12.4,0)+.35*n(12.4,1);
    density=marineRaft(frontU,frontV,h,slot,cover,column,shore,ridge,grain,...field,upstream);
  }
  if(h>1.28&&h<13.54){
    const cap=smooth(8.4,10.65,h),shear=[q[0]-(h-6)*(.28+1.05*cap),q[1]*(1+.45*cap),q[2]*(1+.23*cap)];
    const hn=(scale,c)=>tex(shear.map(v=>v/scale),c);
    const shape=.62*hn(30,0)+.38*hn(30,1),curl=n(6.2,2,[0,time*.00037*e,time*.00048*e]);
    const erosion=.61*curl+.39*n(1.4,0,[curl*.19,0,-curl*.15]);
    const stratiform=stratiformShield(frontU,frontV,h,slot,cover,column,shore,shape,curl,...field,upstream);
    density=Math.max(density,stratiform,stormCrown(frontU,frontV,h,shape,curl,erosion));
  }
  if(h>10.75){
    const u=q[0]+.47*q[2],v=q[2]-.47*q[0];
    const gust=[u/72+.16,.29,v/81+.40],bend=tex(gust,0)-.5,fold=tex(gust,1)-.5;
    const lane=v+9.6*bend+4.2*fold+(12.5-h)*(.75+.45*fold)+.08*u*bend;
    const bank=tex([u/91+.31,.07+h/31,lane/59],3);
    const fibre=tex([u/47+.26*bend+time*.000025,.30+h/9+.42*fold,lane/10.8+.18*tex(gust,2)],0);
    const crossFibre=tex([(u+.23*v)/34+.72*fold,h/14+.311,(v-.31*u)/16-.42*bend],0);
    const filament=smooth(.38,.70,.55*fibre+.45*crossFibre),base=11.02+.69*fold+.39*bend;
    const veil=smooth(base-.27,base+.66,h)*(1-smooth(base+1.34,base+2.22,h));
    const plume=smooth(-.16,.76,thermal((frontU-16)*.089,(frontV-6.2)*.145,(h-12.43)*1.62));
    density+=(smooth(.41,.73,bank)*veil*.042+plume*.051)*(.12+.88*filament);
  }
  const background=h<.65?0:sunbreak(q[0],q[2],h,density);
  return squallLine(q[0],q[2],h,background,0);
}
export function solarVisibility(km,sun){
  const dip=Math.acos(EARTH_KM/(EARTH_KM+Math.max(0,km)));
  return smooth(-.00465,.00465,Math.asin(clamp(sun[1],-1,1))+dip);
}
export function sampleCloudTransmission(km,time=0,sun=[-.6,.72,.35],weather={}){
  if(!bytes)return 1;
  const R=EARTH_KM,ro=[0,R+Math.max(0,km),0],len=Math.hypot(...sun)||1,d=sun.map(v=>v/len);
  if(solarVisibility(km,d)<.01)return .1;
  const b=ro[1]*d[1],c=ro[1]**2-(R+16.15)**2,disc=b*b-c;
  if(disc<=0)return 1;let start=Math.max(0,-b-Math.sqrt(disc)),end=-b+Math.sqrt(disc);
  if(end<=0)return 1;end=Math.min(end,start+400);
  const ds=(end-start)/28;let tau=0;
  for(let i=0;i<28;i++){
    const t=start+(i+.5)*ds;const p=ro.map((v,k)=>v+d[k]*t);
    tau+=sampleCloudDensity(p,time,weather)*ds;
  }
  return clamp(Math.exp(-tau),.1,1);
}

// GLSL version of the exact same medium; sample 3D LUT with repeat/trilinear.
export const WEATHER_GLSL=/*glsl*/`
uniform highp sampler3D noiseVolume;
uniform sampler2D marineCells;
uniform sampler2D broadCloudMap,regionalMap;
uniform float weatherTime, coverage, evolution, weatherLod;
uniform vec2 wind;
float densityFilterKm=0.;
float broadCloudDensity(vec3 p){
  vec3 n=normalize(p),up=vec3(cos(longitude),0.,sin(longitude)),east=vec3(-sin(longitude),0.,cos(longitude));
  vec3 e=n.x*east+n.y*up+vec3(0.,n.z,0.);
  vec2 uv=vec2(atan(e.z,e.x)/6.28318530718+.5,asin(clamp(e.y,-1.,1.))/3.14159265359+.5);
  uv+=vec2(weatherTime*.0000013,0.);
  uv+=vec2(sin(uv.y*31.+weatherTime*.00008),cos(uv.x*43.-weatherTime*.00006))*.0017;
  float initial=textureLod(broadCloudMap,vec2(fract(uv.x),clamp(uv.y,.001,.999)),0.).r;
  return smoothstep(.12,.80,initial+(coverage-.58)*.3);
}
vec4 fieldNoise(vec3 p){return textureLod(noiseVolume,fract(p),0.);}
float noiseC(vec3 p, int c){return fieldNoise(p)[c];}
// Two archived ABI scalar measurements: optical depth and physical cloud top.
// Advect the weather cells across the sphere; longitude is fixed to the tether.
vec4 regionalColumn(vec3 p){
  // Once the entire Atlantic fits in one view the global field has the
  // appropriate footprint. Never project a rectangular survey onto a globe.
  float regionalWeight=1.-smoothstep(950.,4200.,altitudeKm);
  if(regionalWeight<.0001)return vec4(0.);
  vec3 n=normalize(p);
  vec2 ll=degrees(vec2(longitude+atan(n.x,n.y),asin(clamp(n.z,-1.,1.))));
  // Large-scale weather drifts more slowly than a local parcel inside a cloud.
  ll-=wind*weatherTime*.23/111.2;
  // Horizontal domain warp is measured in kilometres, not source texels.
  // It deforms coarse ABI sampling footprints without replacing measured systems.
  vec3 surface=normalize(p)*6371.;
  vec2 warp=vec2(noiseC(surface/170.+vec3(.13,.7,.2),0),noiseC(surface/170.+vec3(.6,.3,.8),0))-.5;
  warp+=.32*(vec2(noiseC(surface/47.+vec3(.2,.8,.4),0),noiseC(surface/47.+vec3(.9,.1,.6),0))-.5);
  ll+=warp*vec2(.25/max(.3,cos(radians(ll.y))),.25);
  vec2 uv=(ll-vec2(-57.,-15.))/vec2(42.,30.);
  float radius=length((uv-.5)*2.);
  float margin=.077*(noiseC(surface/1430.+vec3(.41,.61,.17),3)-.5);
  float weight=regionalWeight*(1.-smoothstep(.38,.96,radius+margin));
  if(weight<=0.)return vec4(0.);
  float footprint=max(1.35,log2(max(1.,altitudeKm/730.)));
  vec3 field=textureLod(regionalMap,uv,footprint).rgb;
  float tau=exp(field.r*4.39445)-1.,top=clamp(field.g*18.,1.4,13.45);
  return vec4(tau,top,field.b,weight);
}
// A sinuous dry slot separates the moist marine streets from the sheared
// storm flank. The coordinates follow the moving air mass.
float drySlot(float u,float v){
  float center=-1.5+1.7*sin(.115*u+.55)+2.2*sin(.045*u-.75);
  float broadening=1.+.85*smoothstep(9.,34.,u);
  return (1.-smoothstep(1.20*broadening,4.90*broadening,abs(v-center)))*(1.-smoothstep(27.,65.,abs(u-8.)));
}
float thermal(float x,float y,float z){return 1.-x*x-y*y-z*z;}
// A sloping intrusion of dry air intersects the edge of the marine bank.
// All coordinates move with the air parcel. Distances are kilometres.
float sunbreak(float x,float z,float h,float baseDensity){
  if(h>12.||x< -15.||x>53.||z< -27.||z>12.)return baseDensity;
  x+=3.20;
  z+=1.25;
  float along=.978*x-.209*z;
  float across=.209*x+.978*z;
  float bend=.44*sin(.15*along+.4)+.19*sin(.31*along);
  float span=smoothstep(-2.,1.4,along)*(1.-smoothstep(39.,49.,along));
  float core=1.-smoothstep(1.48,4.20,abs(across-bend));
  float centre=3.15+.163*along+.10*sin(.27*along)+.07*sin(across*.7);
  float intrusion=span*core*(1.-smoothstep(.43,1.15,abs(h-centre)));
  float density=baseDensity*(1.-intrusion);
  if(along< -8.||along>.75||abs(across)>6.3||h<1.8||h>4.1)return density;
  float eddy=.57*noiseC(vec3(x,h,z)/3.7,0)+.43*noiseC(vec3(x,h,z)/.94,2);
  float lip=-.17+.16*sin(2.17*across)+.59*(eddy-.5);
  float fringe=smoothstep(-7.8,-4.8,along)*(1.-smoothstep(lip-.14,lip+.16,along));
  fringe*=1.-smoothstep(2.0,6.1,abs(across+.37*sin(1.2*along)));
  float floorH=2.38+.14*sin(.82*across+.4*along)+.22*(eddy-.5);
  float topH=3.12+.18*sin(.92*across-.50*along)+.34*(eddy-.5)
              +.16*sin(4.6*across+1.2*along)+.10*sin(6.1*along-3.2*across);
  float hydro=smoothstep(floorH-.16,floorH+.16,h)*(1.-smoothstep(topH-.16,topH+.15,h));
  return max(density,fringe*hydro*(2.75+2.65*eddy));
}
// Horizontal humidity belongs to a parcel, including where the ray crosses its roof.
float openBasin(float u,float v,float bend,float fold){
  float sound=thermal((u+2.8+7.2*bend)*.052,(v-21.4-7.8*fold-2.7*bend)*.126,0.);
  float inlet=thermal((u-40.-5.6*fold)*.058,(v+16.8-8.3*bend)*.116,0.);
  return smoothstep(-.22,.62,max(sound,inlet));
}
float marineRaft(float u,float v,float h,float slot,float cover,float column,float shore,float ridge,float grain,float fraction,float draft,float breakup,float moisture,float upstream){
  float bend=column-.50,fold=shore-.47;
  float distortion=5.4*(breakup-.50)+3.2*(ridge-.55)+2.6*(grain-.50);
  float raggedSlot=drySlot(u+3.4*fold,v+distortion);
  float basin=openBasin(u+4.1*(breakup-.5),v+distortion,bend,fold);
  float humidity=.46+.85*(fraction-.55)+.42*bend+.28*fold+.25*(moisture-.50)+.17*(ridge-.52)+.12*(cover-.72)-.39*raggedSlot-.31*basin-.09*slot;
  humidity+=.18*smoothstep(.55,.78,moisture)*(1.-.86*raggedSlot)*(1.-.70*basin)-.31*(1.-smoothstep(.26,.46,moisture));
  float edge=smoothstep(.22,.60,humidity+.29*(grain-.48)+.20*(breakup-.50));
  float floorH=.89+.38*bend+.12*fold+.145*(ridge-.5)+.16*(breakup-.5)+.19*(1.-edge);
  float roof=floorH+.24+edge*(.43+.76*column+.51*ridge+1.36*draft)+.61*(grain-.48);
  float profile=smoothstep(floorH-.12,floorH+.135,h)*(1.-smoothstep(roof-.24,roof+.19,h));
  float wispH=floorH+.63+.61*draft+.31*ridge+.29*(breakup-.50);
  float torn=smoothstep(.12,.48,upstream-fraction)*smoothstep(.31,.77,upstream);
  float wisp=torn*smoothstep(wispH-.39,wispH-.08,h)*(1.-smoothstep(wispH+.03,wispH+.27,h));
  float mixing=.22+.78*smoothstep(.20,.72,grain+.37*edge+.24*(breakup-.50));
  return max(edge*edge*profile*(.96+1.57*edge+.55*ridge)*mixing,.075*wisp);
}
float stratiformShield(float u,float v,float h,float slot,float cover,float column,float shore,float grain,float curl,float fraction,float draft,float breakup,float moisture,float upstream){
  float bend=column-.50,fold=shore-.47;
  float distortion=6.8*(breakup-.5)+4.2*(grain-.5)+3.7*(fraction-.57);
  float inlet=openBasin(u+4.7*(moisture-.5),v+distortion,bend,fold);
  float raggedSlot=drySlot(u+5.2*fold,v+.75*distortion);
  float front=abs(v+3.2-8.3*bend-5.7*fold);
  float wing=smoothstep(2.4,9.8,front);
  float humidity=.36+.90*(moisture-.49)+.71*(fraction-.56)+.44*bend+.29*fold+.25*(wing-.50)+.12*(cover-.72)-.33*raggedSlot-.28*inlet-.08*slot;
  humidity+=.29*smoothstep(.56,.80,moisture)*(1.-.85*raggedSlot)*(1.-.75*inlet)-.40*(1.-smoothstep(.27,.45,moisture));
  // Upstream of the deep convection, entrainment erodes the lid from above.
  // The thinning slope and its cloudy filaments extend into the ocean lead.
  float along=u+.26*v+2.8*fold+1.46*(breakup-.5);
  float seam=abs(v-(2.55+.22*u+4.34*fold+3.83*(breakup-.5)+2.1*(grain-.50)));
  float dryMix=smoothstep(-27.,-6.,along)*(1.-smoothstep(.3,16.,along))*(1.-smoothstep(2.75,12.15,seam));
  humidity-=dryMix*(.66+.49*smoothstep(5.05,8.63,h));
  float mass=smoothstep(.265,.65,humidity+.24*(grain-.50)+.21*(breakup-.50));
  float floorH=4.87+1.22*column+.44*fold+.38*(wing-.5)+.34*(breakup-.50)+.78*(1.-mass);
  float roof=floorH+.21+mass*(.61+1.06*column+.41*wing+2.32*draft)+.89*(grain-.50)+.46*(curl-.48);
  roof-=1.31*dryMix*(.51+.49*breakup);
  float profile=smoothstep(floorH-.23,floorH+.32,h)*(1.-smoothstep(roof-.34,roof+.24,h));
  float wispH=floorH+.52+.79*moisture+.77*draft+.48*(grain-.50)+.33*(breakup-.50);
  float torn=smoothstep(.12,.51,upstream-fraction)*smoothstep(.36,.77,upstream)*(.16+.84*smoothstep(.26,.75,breakup));
  float wisp=torn*smoothstep(wispH-.59,wispH-.11,h)*(1.-smoothstep(wispH+.06,wispH+.38,h));
  return max(mass*mass*profile*(.78+1.34*mass),.118*wisp);
}
float stormCrown(float u,float v,float h,float shape,float curl,float erosion){
  if(u < -13.||u > 52.||v < -27.||v > 25.)return 0.;
  // The inflow rolls a cleft into the west face of the rising column; the
  // flanking roll stays attached to the core and curls around the opening.
  float gullyU=u-7.19-.46*(h-8.55)-1.34*(shape-.5)-.68*(erosion-.5);
  float gullyV=v+.03-.26*(h-8.55)+1.28*(curl-.50);
  float gully=thermal(gullyU*.45,gullyV*.66,(h-8.91)*.264);
  float drag=.12*(h-5.)+1.13*smoothstep(9.5,12.,h);
  u-=drag+1.51*(curl-.5);v-=.48*drag+2.17*(shape-.5)+.74*(erosion-.5);
  float rootA=thermal((u-8.70)*.136,(v-1.75)*.257,(h-4.31)*.306);
  float rootB=thermal((u-8.14)*.135,(v+16.90)*.225,(h-4.42)*.298);
  float roll=.78*(curl-.50)+.51*(erosion-.50);
  float shoulder=thermal((u-9.7+1.52*roll)*.224,(v-1.30-1.74*roll-.20*(h-7.4))*.304,(h-8.55)*.215);
  float turret=thermal((u-12.3)*.36,(v-1.88)*.40,(h-10.28)*.315);
  float flank=thermal((u-6.2)*.147,(v+8.8)*.239,(h-6.55)*.41);
  float farCore=thermal((u-8.5)*.195,(v+17.25)*.25,(h-8.72)*.223);
  float farTurret=thermal((u-7.0)*.35,(v+17.85)*.40,(h-10.76)*.378);
  float scud=thermal((u+2.25)*.22,(v+4.70)*.78,(h-7.80-.26*(v+4.6))*1.09);
  float plumeU=u-11.8;
  float driftV=2.35+.202*plumeU+1.55*(curl-.48)+.064*plumeU*(shape-.50);
  float reach=smoothstep(-6.,3.,plumeU)*(1.-smoothstep(16.,36.,plumeU+6.8*(shape-.47)));
  float halfWidth=2.0+.158*max(0.,plumeU)+2.35*(shape-.46);
  float fringe=1.-smoothstep(halfWidth-.81,halfWidth+1.34,abs(v-driftV));
  float roof=11.34+.020*plumeU+.38*(shape-.5)+.25*(curl-.50);
  float thickness=.26+.73*(1.-smoothstep(2.,29.,plumeU));
  float iceFan=reach*fringe*smoothstep(roof-thickness-.19,roof-thickness+.22,h)*(1.-smoothstep(roof-.06,roof+.32,h));
  float lift=max(max(rootA,rootB),max(max(shoulder,turret),max(flank,max(farCore,farTurret))));
  lift=max(lift,.61*scud-.15);
  lift-=.97*smoothstep(-.45,.88,gully);
  float rolledShoulder=thermal((u-7.69-.31*(h-8.6))*.43,(v-1.03+.29*(h-8.6))*.74,(h-8.8)*.33);
  lift=max(lift,.75*rolledShoulder-.16);
  float scallop=(.88*(shape-.50)+.54*(curl-.51)+.33*(erosion-.50))*(.46+.54*smoothstep(4.3,8.8,h));
  float column=smoothstep(-.085,.47,lift+scallop)*smoothstep(1.28,1.87,h)*(1.74+.72*shape+.75*curl+.63*erosion);
  return max(column,iceFan*(.59+.79*(1.-smoothstep(6.,29.,plumeU))));
}
// A shelf at the leading edge of a marine squall line, with precipitation
// reaching down behind it and ice spreading downwind from the updraft.
float squallLine(float x,float z,float h,float density,float widthKm){
  if(x < -45.||x>45.||z < -53.||z>4.||h>16.15)return density;
  float along=(x+7.)*.974-(z+25.)*.227;
  float across=(z+25.)*.974+(x+7.)*.227;
  float range=smoothstep(-36.,-23.,along)*(1.-smoothstep(23.,40.,along));
  if(range<=0.||across < -20.||across>27.)return density;
  float frontBow=2.7*sin(.086*along+.52)+1.1*sin(.163*along-.42);
  float distanceFromFront=across-frontBow;
  vec4 billows=fieldNoise(vec3(along/32.+.39,h/19.+.28,across/17.+.62));
  float eddy=mix(billows.r,.5,smoothstep(.8,3.,widthKm))-.5;
  float ridge=mix(billows.g,.5,smoothstep(1.4,5.5,widthKm))-.5;
  float depth=distanceFromFront+.93*eddy+.69*ridge;
  // Subsidence ahead of the front clears a winding lead in both lower decks.
  float opening=smoothstep(2.5,7.4,depth)*(1.-smoothstep(13.,23.,depth))
               *smoothstep(-27.,-12.,along)*(1.-smoothstep(4.3,11.,h));
  density*=1.-.96*range*opening;
  float wet=0.;
  if(h<5.3){
    float shelfEdge=5.55+.35*sin(.61*along)+.19*sin(1.32*along-.3)+1.09*ridge;
    float overlap=1.-smoothstep(shelfEdge-.55,shelfEdge+.38,depth);
    float wedge=smoothstep(-6.2,-2.7,depth)*overlap;
    float shelfBase=1.14+.145*depth+.52*eddy+.18*sin(.46*along+.62*depth);
    float roof=3.84-.264*max(0.,depth)+.42*ridge+.36*eddy;
    wet=wedge*smoothstep(shelfBase-.22,shelfBase+.22,h)*(1.-smoothstep(roof-.27,roof+.33,h))
        *(.95+.46*ridge+.67*eddy);
    float rainAxis=-2.2+.37*h+.68*ridge;
    float shaft=1.-smoothstep(1.25,4.10,abs(depth-rainAxis));
    float streak=noiseC(vec3((along-.32*h)/15.+.39,h/43.+.21,(depth-.20*h)/19.+.17),0);
    float showers=(.10+.92*smoothstep(.30,.72,streak))*(1.-smoothstep(2.9,4.55,h));
    wet=max(wet,shaft*showers*smoothstep(-26.,-11.,along)*(1.-smoothstep(3.,16.,along)));
  }
  if(h>2.3){
    vec4 folds=fieldNoise(vec3((along-.24*h)/9.3+.19,h/8.2+.55,(depth+.19*h)/7.7+.29));
    float roll=(.57*folds.r+.43*folds.b-.5)*(1.-smoothstep(.45,2.4,widthKm));
    float lift=exp(-.014*(along+6.)*(along+6.))+.55*exp(-.026*(along-5.)*(along-5.));
    float fan=smoothstep(10.3,14.3,h);
    float coreDepth=depth+1.15+.158*h-1.16*eddy-.53*ridge;
    float bulb=3.16*exp(-.17*(along+5.-.61*(h-10.))*(along+5.-.61*(h-10.))-.054*(h-9.9)*(h-9.9));
    float halfWidth=1.85+1.01*lift+bulb+1.47*roll+1.24*eddy+(1.-smoothstep(2.4,6.2,h))*1.28;
    float column=1.-smoothstep(halfWidth-1.15,halfWidth+.58,abs(coreDepth));
    float roof=5.87+8.64*min(1.,lift)+2.45*eddy+1.28*ridge+1.24*roll;
    float updraft=column*smoothstep(2.3,3.65,h)*(1.-smoothstep(roof-.79,roof+.45,h));
    wet=max(wet,updraft*(1.51+.39*eddy+.44*ridge));
    if(fan>.001){
      float drift=along+4.;
      float width=2.62+.12*max(0.,drift)+1.88*eddy;
      float radius=abs(coreDepth-.13*drift-.026*drift*ridge);
      float span=smoothstep(-8.,-1.7,drift)*(1.-smoothstep(12.,30.,drift+7.2*ridge+2.9*roll));
      vec4 grain=fieldNoise(vec3((drift+.71*coreDepth)/58.+.27,(h-.02*drift)/6.+.48,(coreDepth-.14*drift)/13.+.71));
      float strands=mix(.64*grain.r+.36*grain.b,.52,smoothstep(.46,2.2,widthKm));
      float fringe=1.-smoothstep(width-1.9,width+1.15,radius-3.5*(strands-.5));
      float cap=13.06+.021*drift+.26*sin(.115*drift)+.89*eddy+.63*ridge+.83*roll;
      float fall=.42+1.16*(1.-smoothstep(-1.,24.,drift))+.72*(strands-.5);
      float ice=smoothstep(cap-fall-.48,cap-fall+.48,h)*(1.-smoothstep(cap-.28,cap+.24,h));
      wet=max(wet,span*fringe*ice*(.09+.88*smoothstep(.35,.72,strands)));
      // A short turret breaks through the stable sheet at its feeding end.
      float turret=thermal((along+5.15+.99*eddy)*.28,(coreDepth-1.62-1.41*ridge)*.38,(h-14.08)*.599);
      wet=max(wet,1.78*smoothstep(-.13,.42,turret+1.50*roll+.72*eddy));
    }
  }
  return max(density,range*wet);
}
float localCloud(vec3 q,float h,float footprint){
  float macro=.64*noiseC(q/7600.,3)+.36*noiseC(q/1900.,0);
  float cover=smoothstep(.26,.68,macro+(coverage-.5)*.65),den=0.;
  float frontU=.72*q.x-.69*q.z,frontV=.69*q.x+.72*q.z,slot=drySlot(frontU,frontV);
  vec4 airMass=fieldNoise(vec3(frontU/123.+.34,.37,frontV/99.+.61));
  float column=airMass.a,shore=.58*airMass.r+.42*airMass.g;
  vec2 airUv=vec2((frontU-(h-1.5)*.49)/146.+.418,(frontV-(h-1.5)*.25)/131.+.583);
  vec4 field=textureLod(marineCells,airUv,max(0.,log2(max(1.,footprint*.87))));
  float upstream=textureLod(marineCells,airUv-vec2(.030,.011),max(.45,log2(max(1.,footprint*.87)))).r;
  if(h<4.28){
    vec4 rows=fieldNoise(vec3((frontU-2.8*(shore-.48))/56.+.41,.19,(frontV+6.7*(column-.5))/23.+.27));
    float ridge=smoothstep(.24,.74,.61*rows.r+.39*rows.g);
    vec4 grains=fieldNoise(q/12.4);
    float grain=mix(.65*grains.r+.35*grains.g,.5,.72*smoothstep(.81,4.1,footprint));
    den=marineRaft(frontU,frontV,h,slot,cover,column,shore,ridge,grain,field.r,field.g,field.b,field.a,upstream);
  }
  if(h>1.28&&h<13.54){
    float cap=smoothstep(8.4,10.65,h);
    vec3 shear=vec3(q.x-(h-6.)*(.28+1.05*cap),q.y*(1.+.45*cap),q.z*(1.+.23*cap));
    vec4 big=fieldNoise(shear/30.);
    float shape=mix(.62*big.r+.38*big.g,.50,.73*smoothstep(1.5,7.1,footprint));
    float curl=noiseC(q/6.2+vec3(0.,weatherTime*.00037*evolution,weatherTime*.00048*evolution),2);
    curl=mix(curl,.50,.88*smoothstep(.22,1.35,footprint));
    float fine=noiseC(q/1.4+vec3(curl*.19,0.,-curl*.15),0);
    float erosion=.61*curl+.39*mix(fine,.50,smoothstep(.080,.37,footprint));
    float stratiform=stratiformShield(frontU,frontV,h,slot,cover,column,shore,shape,curl,field.r,field.g,field.b,field.a,upstream);
    den=max(den,max(stratiform,stormCrown(frontU,frontV,h,shape,curl,erosion)));
  }
  if(h>10.75){
    float u=q.x+.47*q.z,v=q.z-.47*q.x;
    vec4 gust=fieldNoise(vec3(u/72.+.16,.29,v/81.+.40));float bend=gust.r-.5,fold=gust.g-.5;
    float lane=v+9.6*bend+4.2*fold+(12.5-h)*(.75+.45*fold)+.08*u*bend;
    float bank=noiseC(vec3(u/91.+.31,.07+h/31.,lane/59.),3);
    float fibre=noiseC(vec3(u/47.+.26*bend+weatherTime*.000025,.30+h/9.+.42*fold,lane/10.8+.18*gust.b),0);
    float crossFibre=noiseC(vec3((u+.23*v)/34.+.72*fold,h/14.+.311,(v-.31*u)/16.0-.42*bend),0);
    float filament=mix(smoothstep(.38,.70,.55*fibre+.45*crossFibre),.363,smoothstep(.36,1.85,footprint));
    float base=11.02+.69*fold+.39*bend;
    float veil=smoothstep(base-.27,base+.66,h)*(1.-smoothstep(base+1.34,base+2.22,h));
    float plume=smoothstep(-.16,.76,thermal((frontU-16.)*.089,(frontV-6.2)*.145,(h-12.43)*1.62));
    den+=(smoothstep(.41,.73,bank)*veil*.042+plume*.051)*(.12+.88*filament);
  }
  float background=h<.65?0.:sunbreak(q.x,q.z,h,den);
  return squallLine(q.x,q.z,h,background,footprint);
}
float cloudDensity(vec3 p){
  float h=length(p)-6371.;if(h<.04||h>16.15)return 0.;
  vec3 q=p-vec3(wind.x*weatherTime,6371.,wind.y*weatherTime);
  // The anchor occupies one mesoscale air mass. At oblique angles the
  // distant horizon already samples the surrounding observed Atlantic weather.
  float lod=max(weatherLod,smoothstep(55.,176.,length(q.xz)));
  float den=lod<.999?localCloud(q,h,densityFilterKm):0.;
  if(lod<.001)return den;
  float large=pow(broadCloudDensity(p),1.8);
  float low=smoothstep(.7,1.05,h)*(1.-smoothstep(2.,3.5,h));
  float high=smoothstep(4.6,6.3,h)*(1.-smoothstep(10.4,12.1,h));
  vec4 obs=regionalColumn(p);
  float deck=large*(low*1.2+high*.35);
  if(obs.w>.001){
    float top=obs.y;
    float depth=clamp(.58+.25*top+.025*min(obs.x,40.),.76,6.);
    float bottom=max(.67,top-depth);
    float w=smoothstep(bottom-.34,bottom+.34,h)*(1.-smoothstep(top-.45,top+.30,h));
    float sculpt=.56*noiseC(q/67.,0)+.29*noiseC(q/19.,1)+.15*noiseC(q/5.7,2);
    float fractional=smoothstep(.25,.67,sculpt+.16*log(1.+obs.x));
    float breakup=mix(.28+1.05*fractional,1.,smoothstep(1200.,6200.,altitudeKm));
    float total=1.9*log(1.+obs.x*.70)*obs.z;
    deck=mix(deck,total*w/max(.70,top-bottom)*breakup,obs.w);
  }
  return mix(den,deck,lod);
}
`;
