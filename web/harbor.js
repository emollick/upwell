import * as T from 'three';
import {GLTFLoader} from './assets/vendor/loaders/GLTFLoader.js';
import {MeshoptDecoder} from './assets/vendor/meshopt.js';

// Survey coordinates are metres east and south, with the origin at the guide well.
// The nine seconds alongside precede the carriage's physical acceleration clock.
export const harborSeconds=m=>Math.min(9,m.seconds)+m.forces.shipSeconds;
const soft=(x,w)=>w*Math.log1p(Math.exp(x/w));
const swells=[[.86,.51,18.3,.23],[.68,-.73,8.7,.10],[.96,-.27,4.1,.040],
  [.40,.916,2.06,.019],[.78,.626,35.7,.29],[-.42,.907,12.3,.075],[.99,-.14,6.48,.053]]
  .map(([x,z,period,height])=>({x,z,k:2*Math.PI/period,omega:Math.sqrt(9.81*2*Math.PI/period),height}));
const stations=[
  {id:'tug',length:24.6,beam:9.1,response:.72},
  {id:'pilot',length:11.9,beam:4.4,response:.95},
  {id:'supply',length:43.5,beam:10.6,response:.87},
  {id:'line_berth',length:32,beam:12,response:.72},
  {id:'buoy',x:39.2,z:-60.8,length:2.1,beam:2.1,response:1.18},
  {id:'buoy',x:68.1,z:-193.8,length:2.1,beam:2.1,response:1.13}
];
function waterLevel(x,z,t){
  const warp=.51*Math.sin(.045*x+.037*z+.025*t)+.33*Math.sin(-.019*x+.026*z);
  let height=0;
  for(const w of swells)height+=w.height*Math.sin(w.k*(w.x*x+w.z*z)-w.omega*t+warp);
  return height;
}
function route(station,t,out){
  let x,z,dx,dz;
  if(station.id==='pilot'){
    // The launch opens the throttles after clearing Nereid, then bears to starboard outside the marks.
    const d=.58*t+3.37*(soft(t-11,3.7)-soft(-11,3.7));
    const turn=soft(d-65,17)-soft(-65,17),curve=1/(1+Math.exp(-(d-65)/17));
    x=26+.026*d+.53*turn;z=-45-.996*d+.105*turn;dx=.026+.53*curve;dz=-.996+.105*curve;
  }else if(station.id==='supply'){
    const angle=(t-28)*.0124;
    x=-9+205*Math.sin(angle);z=-131+57*(1-Math.cos(angle))+24*Math.sin(angle);
    dx=205*Math.cos(angle);dz=57*Math.sin(angle)+24*Math.cos(angle);
  }else{
    const tug=station.id==='tug',berth=station.id==='line_berth';
    const phase=tug?.52:berth?2.8:station.x*.07;
    x=(tug?24.02:berth?-16.0:station.x)+(tug?.095:berth?.12:.21)*Math.sin(.193*t+phase);
    z=(tug?-17.5:berth?-78.6:station.z)+(tug?.23:berth?.17:.24)*Math.sin(.109*t+.6*phase);
    const yaw=(tug?0:berth?1.73:.37)+(tug?.011:berth?.009:.07)*Math.sin(.123*t+phase);
    dx=Math.sin(yaw);dz=-Math.cos(yaw);
  }
  const size=Math.hypot(dx,dz);return out.set(x,z,dx/size,dz/size);
}
const direction=new T.Vector3(),right=new T.Vector3(),up=new T.Vector3(),back=new T.Vector3(),basis=new T.Matrix4();
function floatBody(actor,station,course,t){
  const {x,y:z,z:fx,w:fz}=course,rx=-fz,rz=fx,fore=.29*station.length,side=.32*station.beam;
  const f=waterLevel(x+fore*fx,z+fore*fz,t),a=waterLevel(x-fore*fx,z-fore*fz,t);
  const s=waterLevel(x+side*rx,z+side*rz,t),p=waterLevel(x-side*rx,z-side*rz,t);
  actor.position.set(x,.16*waterLevel(x,z,t)+.21*(f+a)+.21*(s+p),z);
  direction.set(fx,station.response*(f-a)/(2*fore),fz).normalize();
  right.set(rx,station.response*(s-p)/(2*side),rz);
  back.copy(direction).negate();up.crossVectors(back,right).normalize();right.crossVectors(up,back).normalize();
  actor.quaternion.setFromRotationMatrix(basis.makeBasis(right,up,back));
}
const springs=[
  [0,[-3.06483,2.33264,-8.4],[18.63,5.31,-12.05],.44],
  [0,[-2.93376,1.97834,9.73],[18.63,5.31,-22.8],.59],
  [3,[4.5,2.12,-10.8],[-1.1,3.48,-69.45],.56],
  [3,[4.5,2.12,10.8],[-31.3,3.48,-70.8],.46],
];
function moorings(parent){
  const iron=new T.MeshStandardMaterial({color:0x46514e,metalness:.48,roughness:.58});
  const yellow=new T.MeshStandardMaterial({color:0xb7a05d,metalness:.28,roughness:.66});
  const hemp=new T.MeshStandardMaterial({color:0x8c806b,metalness:0,roughness:.91});
  const cylinders=new T.CylinderGeometry(1,1,1,9);
  const slots=[[],[]],pt=new T.Vector3(),scale=new T.Vector3(),identity=new T.Quaternion();
  const ring=(id,x,y,z,r,h)=>slots[id].push(new T.Matrix4().compose(pt.set(x,y,z),identity,scale.set(r,h,r)));
  for(const [boat,,[x,y,z]] of springs){
    if(boat===3){
      for(const [ox,oz] of [[-.43,-.22],[.43,-.22],[0,.40]])ring(0,x+ox,-.16,z+oz,.24,6.95);
      ring(0,x,y-.39,z,.77,.54);ring(1,x,y-.15,z,.63,.15);
    }
    ring(0,x,y-.18,z,boat===3?.26:.32,.40);
    ring(1,x,y+.035,z,boat===3?.33:.39,.082);
  }
  slots.forEach((mats,i)=>{const mesh=new T.InstancedMesh(cylinders,[iron,yellow][i],mats.length);
    mats.forEach((m,j)=>mesh.setMatrixAt(j,m));mesh.computeBoundingSphere();parent.add(mesh);});

  // Each spring has real diameter. Its end follows the surveyed bollard on the floating deck.
  const steps=12,sides=5,count=springs.length*(steps+1)*sides,positions=new Float32Array(count*3),normals=new Float32Array(count*3);
  const index=[];for(let l=0;l<springs.length;l++)for(let i=0;i<steps;i++)for(let j=0;j<sides;j++){
    const k=(l*(steps+1)+i)*sides+j,n=k-j+(j+1)%sides;
    index.push(k,k+sides,n,n,k+sides,n+sides);
  }
  const geom=new T.BufferGeometry();geom.setAttribute('position',new T.BufferAttribute(positions,3).setUsage(T.DynamicDrawUsage));
  geom.setAttribute('normal',new T.BufferAttribute(normals,3).setUsage(T.DynamicDrawUsage));geom.setIndex(index);
  const rope=new T.Mesh(geom,hemp);rope.name='Working springs and floating berth bridles';rope.frustumCulled=false;parent.add(rope);
  const leads=springs.map(([boat,al,bl,sag])=>({boat,point:new T.Vector3(...al),shore:new T.Vector3(...bl),sag}));
  const start=new T.Vector3(),axis=new T.Vector3(),side=new T.Vector3(),normal=new T.Vector3(),center=new T.Vector3(),v=new T.Vector3();
  return actors=>{
    let k=0;
    for(const lead of leads){
      const a=actors[lead.boat];start.copy(lead.point).applyQuaternion(a.quaternion).add(a.position);
      axis.subVectors(lead.shore,start);side.set(-axis.z,0,axis.x).normalize();
      const radius=lead.boat===0?.047:.056;
      for(let i=0;i<=steps;i++){
        const t=i/steps;center.lerpVectors(start,lead.shore,t);center.y-=4*lead.sag*t*(1-t);
        axis.subVectors(lead.shore,start);axis.y+=4*lead.sag*(2*t-1);
        normal.crossVectors(axis,side).normalize();
        for(let j=0;j<sides;j++){
          const angle=2*Math.PI*j/sides;v.copy(side).multiplyScalar(Math.cos(angle)).addScaledVector(normal,Math.sin(angle));
          normals[k]=v.x;normals[k+1]=v.y;normals[k+2]=v.z;
          positions[k++]=center.x+radius*v.x;positions[k++]=center.y+radius*v.y;positions[k++]=center.z+radius*v.z;
        }
      }
    }
    geom.attributes.position.needsUpdate=true;geom.attributes.normal.needsUpdate=true;
  };
}
export async function loadHarbor(parent){
  const loader=new GLTFLoader().setMeshoptDecoder(MeshoptDecoder),templates=new Map();
  await Promise.all([...new Set([...stations.map(x=>x.id),'offshore_depot'])].map(async id=>{
    const {scene}=await loader.loadAsync('./assets/harbor/'+id+'.glb');
    scene.traverse(n=>{if(n.isMesh){n.castShadow=!n.material.transparent;n.receiveShadow=true;
      for(const map of [n.material.map,n.material.normalMap])if(map)map.anisotropy=4;}});
    templates.set(id,scene);
  }));
  const root=new T.Group();root.name='Equatorial anchor working roadstead';parent.add(root);root.position.y=-7;
  const depot=templates.get('offshore_depot');depot.name='Cable stores offshore platform';
  depot.position.set(-48,0,-409);depot.rotation.y=.25;root.add(depot);
  const actors=stations.map(s=>{const actor=templates.get(s.id).clone(true);actor.name=s.id;root.add(actor);return actor;});
  const water={vessels:Array.from({length:4},()=>new T.Vector4()),trails:[new T.Vector4(),new T.Vector4()],speeds:new T.Vector2()};
  const ropes=moorings(root),course=new T.Vector4(),past=new T.Vector4(),old=new T.Vector4();
  return {root,actors,water,update(m,t){
    root.visible=m.km<1.95;if(!root.visible)return;
    stations.forEach((s,i)=>{
      route(s,t,course);floatBody(actors[i],s,course,t);
      if(i<4)water.vessels[i].copy(course);
      if(i===1||i===2){
        const dt=i===1?9:17,stern=i===1?5.68:20.15;
        route(s,t-dt,past);route(s,t-2*dt,old);
        water.trails[i-1].set(past.x-stern*past.z,past.y-stern*past.w,old.x-stern*old.z,old.y-stern*old.w);
        route(s,t-.1,past);water.speeds.setComponent(i-1,10*Math.hypot(course.x-past.x,course.y-past.y));
      }
    });
    ropes(actors);
  }};
}
