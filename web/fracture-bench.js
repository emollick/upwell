import * as T from 'three';
import {laminatedPane} from './laminated-pane.js';
import {Oscillator} from './fixture-physics.js';
import {RIDE_SECONDS,travel} from './journey.js';
import {passageBodyForce} from './car-dynamics.js';

const v = (a) => a ? new T.Vector3().fromArray(a) : new T.Vector3();
const bound = (a, lo = 0, hi = 1) => Math.max(lo, Math.min(hi, a));
const ease = (x) => { const t=bound(x); return t*t*(3-2*t); };
const axes = [v([1,0,0]),v([0,1,0]),v([0,0,1])];
const step = 1/120;

// The machined coupons are irregular planar prisms. Keep their measured faces
// for the glass and roller contacts, and use their convex envelopes for pairs.
function convexRim(vertices) {
  const points=vertices.slice(0,vertices.length/2).sort((a,b)=>a.x-b.x||a.y-b.y);
  const turn=(a,b,c)=>(b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x);
  const half=ordered=>{
    const rim=[];
    for(const p of ordered){
      while(rim.length>=2&&turn(rim.at(-2),rim.at(-1),p)<=0)rim.pop();
      rim.push(p);
    }
    return rim.slice(0,-1);
  };
  return [...half(points),...half(points.reverse())];
}
class Chip {
  constructor(spec, root) {
    this.spec=spec; this.node=root.getObjectByName(spec.name);
    this.local=spec.vertices.map(v);this.world=this.local.map(()=>v());
    this.p=v();this.q=new T.Quaternion();this.vel=v();this.spin=v();
    this.invQ=new T.Quaternion();this.arm=v();this.torque=v();this.contactSpeed=v();
    this.normal=v();this.corner=v();this.turn=new T.Quaternion();this.spinAxis=v();
    this.support=v();this.restNormal=v();this.faceNormal=v();this.stillTime=0;
    const size=new T.Box3().setFromPoints(this.local).getSize(v()),{x,y,z}=size;
    this.invMass=1/spec.massKg;
    this.invInertia=v([1/(y*y+z*z),1/(x*x+z*z),1/(x*x+y*y)]).multiplyScalar(12*this.invMass);
    this.radius=Math.max(...this.local.map(p=>p.length()));
    this.thickness=Math.abs(this.local[0].z);const rim=convexRim(this.local);
    this.sides=rim.map((a,i)=>{
      const b=rim[(i+1)%rim.length],n=v([b.y-a.y,a.x-b.x,0]).normalize();
      return {n,offset:n.dot(a)};
    });
    this.reset();
  }
  reset(saved) {
    this.p.fromArray(saved?.p??this.spec.pivot);
    if(saved)this.q.fromArray(saved.q).normalize();else this.q.identity();
    this.vel.fromArray(saved?.v??this.spec.velocity);
    this.spin.fromArray(saved?.w??this.spec.spin);
    this.sleeping=Array.isArray(saved?.restNormal);
    if(this.sleeping)this.restNormal.fromArray(saved.restNormal).normalize();
    this.stillTime=0;this.support.set(0,0,0);
    this.pose();
  }
  pose(){
    this.invQ.copy(this.q).invert();
    this.world.forEach((p,i)=>p.copy(this.local[i]).applyQuaternion(this.q).add(this.p));
  }
  step(force,dt){
    this.support.set(0,0,0);
    if(this.sleeping){
      const load=-force.dot(this.restNormal),shearSq=force.lengthSq()-load*load;
      if(load>=1&&shearSq<=.48*.48*load*load)return;
      this.sleeping=false;this.stillTime=0;
    }
    this.vel.addScaledVector(force,dt).multiplyScalar(Math.exp(-.06*dt));
    this.spin.multiplyScalar(Math.exp(-.10*dt));
    this.p.addScaledVector(this.vel,dt);
    const speed=this.spin.length();
    if(speed>1e-6)this.q.premultiply(this.turn.setFromAxisAngle(this.spinAxis.copy(this.spin).divideScalar(speed),speed*dt)).normalize();
    this.pose();
  }
  compliance(normal){
    const a=this.torque.crossVectors(this.arm,normal).applyQuaternion(this.invQ);
    return this.invMass+a.x*a.x*this.invInertia.x+a.y*a.y*this.invInertia.y+a.z*a.z*this.invInertia.z;
  }
  strike(impulse){
    this.vel.addScaledVector(impulse,this.invMass);
    this.spin.add(this.torque.crossVectors(this.arm,impulse).applyQuaternion(this.invQ).multiply(this.invInertia).applyQuaternion(this.q));
  }
  at(point){
    this.arm.copy(point).sub(this.p);
    return this.contactSpeed.crossVectors(this.spin,this.arm).add(this.vel);
  }
  // Depth and normal of a vertex embedded in this chip's support hull.
  inside(point){
    const local=this.corner.copy(point).sub(this.p).applyQuaternion(this.invQ);
    let depth=this.thickness-Math.abs(local.z);
    if(depth<=0)return 0;
    this.normal.set(0,0,local.z<0?-1:1);
    for(const {n,offset} of this.sides){
      const d=offset-n.dot(local);if(d<=0)return 0;
      if(d<depth){depth=d;this.normal.copy(n);}
    }
    this.normal.applyQuaternion(this.q);return depth;
  }
  sync(){this.node.position.copy(this.p);this.node.quaternion.copy(this.q);}
  settle(dt){
    if(this.sleeping)return;
    const flat=Math.abs(this.faceNormal.set(0,0,1).applyQuaternion(this.q).dot(this.support));
    const contactSpeed=this.vel.length()+this.radius*this.spin.length();
    if(!this.support.lengthSq()||contactSpeed>(flat>.90?.14:.004)){this.stillTime=0;return;}
    this.stillTime+=dt;
    this.vel.multiplyScalar(Math.exp(-8*dt));this.spin.multiplyScalar(Math.exp(-10*dt));
    if(this.stillTime<.28)return;
    this.sleeping=true;this.vel.set(0,0,0);this.spin.set(0,0,0);this.restNormal.copy(this.support);
  }
  snapshot(){
    const saved={p:this.p.toArray(),q:this.q.toArray(),v:this.vel.toArray(),w:this.spin.toArray()};
    if(this.sleeping)saved.restNormal=this.restNormal.toArray();
    return saved;
  }
}
export class FractureBench {
  constructor(c,root) {
    this.c=c;this.root=root;this.get=name=>root.getObjectByName(name);
    this.chips=c.shards.map(s=>new Chip(s,root));
    this.rotators=[c.press,c.needle,c.peakNeedle].map(s=>({n:this.get(s.name),axis:v(s.axis),angle:s.degrees*Math.PI/180}));
    this.slides=[c.punch,c.reload,...c.shutters].map(s=>{const n=this.get(s.name);return {n,start:n.position.clone(),travel:v(s.travel)};});
    this.coupon=this.get('fracture_coupon');this.flexFaces=[];
    this.coupon.traverse(n=>{if(n.morphTargetDictionary?.BeamFlex!==undefined)this.flexFaces.push(n);});
    this.low=v(c.chamberMin);this.high=v(c.chamberMax);
    this.rollers=c.supports.map(s=>({...s,p:v(s.center)}));
    this.normal=v();this.reverseNormal=v();this.point=v();this.delta=v();this.tangent=v();this.impulse=v();this.force=v();
    this.clock=0;this.lastHit=-1;this.accumulator=0;this.onSound=()=>{};
    this.boundState=null;this.savedAt=0;this.load=0;this.peak=0;
    this.liveNeedle=new Oscillator();this.snapAt=-10;
    this.stroke=0;this.index=-1;this.held=false;this.broken=false;
    this.draw();
  }
  bind(s){
    if(this.boundState===s)return;
    this.boundState=s;
    const f=s.fracture??={broken:false,peak:0,pieces:[]};
    this.held=false;this.stroke=0;this.index=-1;this.load=0;this.broken=f.broken;this.peak=f.peak;
    this.liveNeedle.reset();this.snapAt=-10;
    this.accumulator=0;this.chips.forEach((b,i)=>b.reset(f.pieces[i]));this.draw();
  }
  press(){
    if(this.held||this.broken||this.index>=0)return false;
    this.held=true;this.onSound('fractureCam');return true;
  }
  release(){this.held=false;}
  reload(){
    if(!this.broken||this.held||this.stroke>.10||this.index>=0)return false;
    this.index=0;this.onSound('fractureIndex');return true;
  }
  persist(){
    if(!this.boundState)return;
    const f=this.boundState.fracture;
    f.broken=this.broken;f.peak=this.peak;f.pieces=this.broken?this.chips.map(b=>b.snapshot()):[];
    this.savedAt=this.clock;
  }
  seek(s,from,to,clock){
    this.bind(s);this.release();this.accumulator=0;
    if(to<=from){
      if(this.broken){
        passageBodyForce(travel(to/RIDE_SECONDS),clock,this.force);
        for(const b of this.chips)if(b.sleeping)b.step(this.force,0);
        this.persist();
      }
      return;
    }
    if(!this.broken&&this.index<0&&this.stroke===0)return;
    const sound=this.onSound,force=v();
    this.onSound=()=>{};
    try{
      for(let t=from;t<to-1e-7;){
        const future=Math.min(t+1,to);
        if(this.broken&&this.index<0&&this.stroke===0&&this.chips.every(b=>b.sleeping)){
          passageBodyForce(travel(future/RIDE_SECONDS),clock+future-from,force);
          if(this.chips.every(b=>{
            const load=-force.dot(b.restNormal);
            return load>=1&&force.lengthSq()-load*load<=.48*.48*load*load;
          })){t=future;continue;}
        }
        const dt=Math.min(.2,to-t),mid=t+dt*.5;
        passageBodyForce(travel(mid/RIDE_SECONDS),clock+mid-from,force);
        this.advance(s,force,dt);t+=dt;
        if(!this.broken&&this.index<0&&this.stroke===0)break;
      }
      this.persist();
    }finally{this.onSound=sound;}
  }
  contact(a,b,point,normal,depth,bounce=true){
    const velocity=this.delta.copy(a.at(point));
    if(b)velocity.sub(b.at(point));
    const closing=velocity.dot(normal);
    if(b&&(a.sleeping||b.sleeping)){
      if(a.sleeping&&b.sleeping)return;
      if(closing>-.10){
        const moving=a.sleeping?b:a,face=a.sleeping?this.reverseNormal.copy(normal).negate():normal;
        if(-this.force.dot(face)>1)moving.support.copy(face);
        this.contact(moving,null,point,face,depth,false);return;
      }
      a.sleeping=b.sleeping=false;a.stillTime=b.stillTime=0;
    }
    if(closing<0){
      const loadSpeed=Math.max(0,-this.force.dot(normal))*step;
      const restitution=bounce&&-closing>Math.max(.045,2.8*loadSpeed)?.36:0;
      const magnitude=-(1+restitution)*closing/(a.compliance(normal)+(b?b.compliance(normal):0));
      const tangent=this.tangent.copy(velocity).addScaledVector(normal,-closing),speed=tangent.length();
      const j=this.impulse.copy(normal).multiplyScalar(magnitude);
      if(speed>1e-6){
        tangent.divideScalar(speed);
        const drag=Math.min(.48*magnitude,speed/(a.compliance(tangent)+(b?b.compliance(tangent):0)));
        j.addScaledVector(tangent,-drag);
      }
      a.strike(j);if(b)b.strike(j.negate());
      if(bounce&&-closing>Math.max(.15,3.2*loadSpeed)&&this.clock-this.lastHit>.08){
        this.onSound('fractureChip',Math.min(1,-closing*1.4));this.lastHit=this.clock;
      }
    }
    const move=depth/(a.invMass+(b?b.invMass:0));
    a.p.addScaledVector(normal,move*a.invMass);
    if(b)b.p.addScaledVector(normal,-move*b.invMass);
  }
  enclosure(b){
    if(b.sleeping)return;
    for(let i=0;i<3;i++)for(const sign of [1,-1]){
      const limit=(sign>0?this.low:this.high).getComponent(i);
      let depth=0;
      for(const p of b.world)depth=Math.max(depth,(limit-p.getComponent(i))*sign);
      if(!depth)continue;
      // A flat broken edge can carry the load at several vertices. Resolving
      // them together prevents the chip rocking between two artificial tips.
      const normal=this.normal.copy(axes[i]).multiplyScalar(sign);
      if(-this.force.dot(normal)>1)b.support.copy(normal);
      for(let pass=0;pass<5;pass++){
        for(const p of b.world)if((limit-p.getComponent(i))*sign>=-.00018)
          this.contact(b,null,p,normal,0,pass===0);
      }
      b.p.addScaledVector(normal,depth);
      b.pose();
    }
    for(const roller of this.rollers){
      let depth=0;
      for(const p of b.world){
        const dy=p.y-roller.p.y;if(Math.abs(dy)>=roller.halfHeight)continue;
        const dx=p.x-roller.p.x,dz=p.z-roller.p.z,r=Math.hypot(dx,dz);
        const side=roller.radius-r,cap=roller.halfHeight-Math.abs(dy),d=Math.min(side,cap);
        if(d<=depth||r<1e-7)continue;
        depth=d;this.point.copy(p);
        if(side<cap)this.normal.set(dx/r,0,dz/r);else this.normal.set(0,Math.sign(dy)||1,0);
      }
      if(depth){
        if(-this.force.dot(this.normal)>1)b.support.copy(this.normal);
        this.contact(b,null,this.point,this.normal,depth);b.pose();
      }
    }
  }
  pairs(){
    for(let i=0;i<this.chips.length;i++)for(let j=i+1;j<this.chips.length;j++){
      const a=this.chips[i],b=this.chips[j];
      if((a.sleeping&&b.sleeping)||a.p.distanceToSquared(b.p)>(a.radius+b.radius)**2)continue;
      let depth=0;
      for(const p of a.world){
        const d=b.inside(p);if(d>depth){depth=d;this.point.copy(p);this.normal.copy(b.normal);}
      }
      for(const p of b.world){
        const d=a.inside(p);if(d>depth){depth=d;this.point.copy(p);this.normal.copy(a.normal).negate();}
      }
      if(depth){this.contact(a,b,this.point,this.normal,depth);a.pose();b.pose();}
    }
  }
  mechanics(dt){
    const c=this.c;
    if(this.index>=0){
      const old=this.index;this.index=Math.min(1,old+dt/c.reloadSeconds);
      if(old<c.exchangeAt&&this.index>=c.exchangeAt){
        this.broken=false;this.peak=0;this.load=0;this.onSound('fractureSeat');this.persist();
      }
      if(this.index===1)this.index=-1;
    }
    const target=this.held&&this.index<0;
    this.stroke=bound(this.stroke+(target?dt/c.holdSeconds:-dt/.31));
    this.load=this.broken?0:c.breakLoadN*Math.pow(bound((this.stroke-.12)/(c.snapFraction-.12)),1.42);
    this.peak=Math.max(this.peak,this.load);
    if(!this.broken&&this.stroke>=c.snapFraction){
      this.broken=true;this.snapAt=this.clock;this.peak=c.breakLoadN;this.load=0;
      this.chips.forEach(b=>b.reset());this.onSound('fractureSnap');this.persist();
    }
    this.liveNeedle.advance(this.load/c.dialMaxN,42,.72,dt);
  }
  advance(s,force,dt){
    this.bind(s);this.force.copy(force);this.accumulator+=Math.min(dt,.2);
    while(this.accumulator>=step){
      this.clock+=step;this.mechanics(step);
      if(this.broken){
        for(const b of this.chips)b.step(force,step);
        this.pairs();
        for(const b of this.chips){this.enclosure(b);b.settle(step);}
      }
      this.accumulator-=step;
    }
    if(this.clock-this.savedAt>.20&&(this.broken||this.peak!==s.fracture.peak))this.persist();
    this.draw();
  }
  draw(){
    const [cam,needle,witness]=this.rotators;
    const sinceSnap=this.clock-this.snapAt,kick=this.broken?.055*Math.sin(sinceSnap*56)*Math.exp(-sinceSnap*20):0;
    cam.n.quaternion.setFromAxisAngle(cam.axis,cam.angle*bound(this.stroke+kick));
    needle.n.quaternion.setFromAxisAngle(needle.axis,needle.angle*bound(this.liveNeedle.x));
    witness.n.quaternion.setFromAxisAngle(witness.axis,witness.angle*this.peak/this.c.dialMaxN);
    const t=this.index,close=t<0?0:ease(t/.36)*(1-ease((t-.62)/.38));
    const stroke=t<0?0:ease(t/.31)*(1-ease((t-.53)/.4));
    const bend=this.load/this.c.breakLoadN,ram=this.c.punch;
    const nose=this.broken?bound(this.stroke/this.c.snapFraction):(ram.clearance*bound(this.stroke/.12)+ram.deflection*bend)/(ram.clearance+ram.deflection);
    this.slides.forEach(({n,start,travel},i)=>n.position.copy(start).addScaledVector(travel,i===0?nose:i===1?stroke:close));
    for(const n of this.flexFaces)n.morphTargetInfluences[n.morphTargetDictionary.BeamFlex]=bend;
    this.coupon.visible=!this.broken;
    for(const b of this.chips){b.node.visible=this.broken;if(this.broken)b.sync();}
  }
}

export async function loadFractureBench(world,loader) {
  const [gltf,contract]=await Promise.all([
    loader.loadAsync('./assets/fracture/FractureCartridge.glb'),
    fetch('./assets/fracture/cartridge.json').then(r=>{if(!r.ok)throw Error('Missing fracture cartridge survey');return r.json();}),
  ]);
  const root=gltf.scene;root.position.fromArray(contract.origin);world.scene.add(root);root.updateMatrixWorld(true);
  const bench=new FractureBench(contract,root),filter=Math.min(8,world.r.capabilities.getMaxAnisotropy());
  for(const id of ['fracture_cell','fracture_press','fracture_reload']){
    const n=id==='fracture_cell'?root:bench.get(id);
    n.userData.fitting=id;world.nodes[id]=n;
    world.base[id]={pos:n.position.clone(),quat:n.quaternion.clone(),scale:n.scale.clone(),restInverse:n.matrixWorld.clone().invert(),v:0};
    const box=id==='fracture_cell'?new T.Box3(v([-.251,-.152,-.135]),v([.252,.145,-.025])).translate(root.position):new T.Box3().setFromObject(n);
    world.layout.props[id]={room:'service',webCenter:box.getCenter(v()).toArray(),webBounds:[box.min.toArray(),box.max.toArray()]};
  }
  root.traverse(n=>{
    if(!n.isMesh)return;
    const m=n.material,glass=m.name==='FC_Guard';
    if(glass){
      n.material=laminatedPane(n,m,world);
      n.material.side=T.FrontSide;n.renderOrder=2;
    }
    for(const map of [m.map,m.normalMap,m.roughnessMap,m.metalnessMap])if(map)map.anisotropy=filter;
    n.castShadow=!glass;n.receiveShadow=!glass;n.userData.isGlass=glass;
    n.userData.cartridgeInterior=!glass&&!n.name.startsWith('fracture_frame')&&n.parent.name!=='fracture_frame';
    world.hull.push(n);
  });
  const lamp=new T.SpotLight(0xffdda7,.075,.32,1,.7,2);
  lamp.position.set(-.029,.075,-.072);lamp.target.position.set(.042,.002,-.067);
  root.add(lamp,lamp.target);
  return bench;
}
