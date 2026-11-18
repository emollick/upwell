import * as T from 'three';
import {CARRIED,RIDE_SECONDS,travel,roomAt} from './journey.js';
import {passageBodyForce} from './car-dynamics.js';
import {rigidBounds,heldMass} from './in-hand.js';

const specs={
  field_glasses:{mass:heldMass.field_glasses,area:.018,restitution:.22,friction:.60},
  mug:{mass:heldMass.mug,area:.010,restitution:.25,friction:.50},
  logbook:{mass:heldMass.logbook,area:.034,restitution:.14,friction:.67},
  tool_roll:{mass:heldMass.tool_roll,area:.056,restitution:.09,friction:.75},
  access_card:{mass:heldMass.access_card,area:.0046,restitution:.20,friction:.48},
};
const cell=.30;
const hash=(x,y,z)=>(x+50)*16384+(y+50)*128+z+50;
const v=()=>new T.Vector3();
const fixedStep=1/90;
function supported(b,normal,force){
  const load=-normal.dot(force);
  return load>.012 && Math.max(0,force.lengthSq()-load*load)<=(b.cfg.friction*load)**2;
}
function ancestorId(n){for(;n;n=n.parent)if(n.userData.fitting)return n.userData.fitting;return '';}

// A spatial hash of the modeled pressure hull and furnishings, plus local
// hashes on the three moving rigid fittings. A card can land inside a drawer.
class SurfaceGrid{
  constructor(parent){
    this.parent=parent;this.cells=new Map();this.inv=new T.Matrix4();this.forward=new T.Matrix4();
    this.previous=new T.Matrix4();this.previousInv=new T.Matrix4();
    this.probeForward=new T.Matrix4();this.probeInv=new T.Matrix4();
    this.start=v();this.finish=v();this.place=v();this.startQ=new T.Quaternion();this.finishQ=new T.Quaternion();this.turn=new T.Quaternion();
    this.scale=v().setScalar(1);this.stamp=0;this.tmp=v();this.old=v();this.closest=v();this.point=v();this.dir=v();
  }
  add(mesh){
    const geo=mesh.geometry,positions=geo.attributes.position,indices=geo.index;if(!positions)return;
    const matrix=this.parent?this.parent.matrixWorld.clone().invert().multiply(mesh.matrixWorld):mesh.matrixWorld;
    const part=ancestorId(mesh)||mesh.parent?.name||mesh.name;
    const coords=[];for(let i=0;i<positions.count;i++)coords.push(v().fromBufferAttribute(positions,i).applyMatrix4(matrix));
    for(let i=0;i<(indices?indices.count:positions.count);i+=3){
      const a=coords[indices?indices.getX(i):i],b=coords[indices?indices.getX(i+1):i+1],c=coords[indices?indices.getX(i+2):i+2];
      const tri=new T.Triangle(a,b,c);if(tri.getArea()<.000007)continue;
      tri.normal=tri.getNormal(v());tri.stamp=0;tri.part=part;
      const low=a.clone().min(b).min(c).divideScalar(cell).floor(),high=a.clone().max(b).max(c).divideScalar(cell).floor();
      for(let x=low.x;x<=high.x;x++)for(let y=low.y;y<=high.y;y++)for(let z=low.z;z<=high.z;z++){
        const key=hash(x,y,z);let list=this.cells.get(key);if(!list)this.cells.set(key,list=[]);list.push(tri);
      }
    }
  }
  begin(){
    if(!this.parent)return false;
    if(!this.ready){this.forward.copy(this.parent.matrixWorld);this.ready=true;}
    this.moving=!this.forward.equals(this.parent.matrixWorld);
    this.forward.decompose(this.start,this.startQ,this.scale);
    this.parent.matrixWorld.decompose(this.finish,this.finishQ,this.scale);
    return this.moving;
  }
  sample(fraction,dt){
    if(!this.parent)return;
    this.previous.copy(this.forward);this.previousInv.copy(this.previous).invert();
    if(this.moving){
      this.place.lerpVectors(this.start,this.finish,fraction);
      this.turn.slerpQuaternions(this.startQ,this.finishQ,fraction);
      this.forward.compose(this.place,this.turn,this.scale);
    }
    this.inv.copy(this.forward).invert();this.invStep=1/dt;
  }
  freeze(){
    if(!this.parent)return;
    this.forward.copy(this.parent.matrixWorld);this.inv.copy(this.forward).invert();
    this.previous.copy(this.forward);this.previousInv.copy(this.inv);this.ready=true;this.moving=false;
  }
  prepareProbe(){
    if(!this.parent)return;
    this.parent.updateWorldMatrix(true,false);
    this.probeForward.copy(this.parent.matrixWorld);this.probeInv.copy(this.probeForward).invert();
  }
  contact(world,previous,r,result,probe=false){
    const inv=probe?this.probeInv:this.inv,forward=probe?this.probeForward:this.forward;
    const p=this.tmp.copy(world).applyMatrix4(inv),old=this.old.copy(previous).applyMatrix4(probe?inv:this.previousInv);
    const x0=Math.floor((Math.min(p.x,old.x)-r)/cell),x1=Math.floor((Math.max(p.x,old.x)+r)/cell);
    const y0=Math.floor((Math.min(p.y,old.y)-r)/cell),y1=Math.floor((Math.max(p.y,old.y)+r)/cell);
    const z0=Math.floor((Math.min(p.z,old.z)-r)/cell),z1=Math.floor((Math.max(p.z,old.z)+r)/cell);
    const stamp=++this.stamp;
    for(let x=x0;x<=x1;x++)for(let y=y0;y<=y1;y++)for(let z=z0;z<=z1;z++){
      const list=this.cells.get(hash(x,y,z));if(!list)continue;
      for(const tri of list){if(tri.stamp===stamp)continue;tri.stamp=stamp;
        const a=tri.normal.dot(this.dir.copy(old).sub(tri.a)),b=tri.normal.dot(this.dir.copy(p).sub(tri.a));
        let pen=0;
        if(a*b<0&&Math.abs(a-b)>.000001){
          this.closest.copy(old).lerp(p,a/(a-b));
          if(tri.containsPoint(this.closest)){pen=r+Math.abs(b);this.dir.copy(tri.normal).multiplyScalar(Math.sign(a));}
        }
        if(!pen){tri.closestPointToPoint(p,this.closest);this.dir.copy(p).sub(this.closest);
          const d=this.dir.length();if(d>=r)continue;pen=r-d;
          if(d>.00001)this.dir.multiplyScalar(1/d);else this.dir.copy(tri.normal).multiplyScalar(a>=0?1:-1);
        }
        if(pen<=result.pen)continue;result.pen=pen;
        result.normal.copy(this.dir).transformDirection(forward);result.position.copy(this.closest).applyMatrix4(forward);result.part=tri.part;
        result.surface=this.parent?this:null;
        if(!probe&&this.parent&&this.moving){
          const oldContact=this.point.copy(this.closest).applyMatrix4(this.previous);
          result.surfaceVelocity.copy(result.position).sub(oldContact).multiplyScalar(this.invStep);
        }else result.surfaceVelocity.set(0,0,0);
      }
    }
  }
}

function contacts(id,size){
  const h=size.clone().multiplyScalar(.5),out=[];
  const push=(x,y,z,r)=>out.push({p:new T.Vector3(x,y,z),r});
  if(id==='field_glasses'){
    const r=Math.min(h.y*.59,h.x*.38,h.z*.33);
    for(const sx of [-1,1])for(const sz of [-1,0,1])push(sx*(h.x-r)*.73,-h.y*.10,sz*(h.z-r),r);
  }else if(id==='mug'){
    const r=Math.min(h.y*.17,h.x*.16,h.z*.19);
    for(const sy of [-1,1])for(let i=0;i<6;i++){const a=i*Math.PI/3;push(Math.cos(a)*(h.x-r)*.83,sy*(h.y-r),Math.sin(a)*(h.z-r)*.88,r);}
  }else{
    const r=Math.min(h.y*.79,h.x*.14,h.z*.14);
    for(const sx of [-1,1])for(const sz of [-1,1])for(const sy of [-1,1])push(sx*(h.x-r),sy*(h.y-r),sz*(h.z-r),r);
  }
  return out;
}

export class LooseItems{
  constructor(world){this.world=world;this.bodies=new Map();this.meshes=[];this.fixedTime=0;this.hitSound=()=>{};this.clock=0;
    this.contact={pen:0,position:v(),normal:v(),surfaceVelocity:v()};this.vel=v();this.cross=v();this.torque=v();this.normal=v();this.point=v();this.oldPoint=v();this.rel=v();this.friction=v();this.invQ=new T.Quaternion();this.rotation=new T.Quaternion();}
  buildCollision(){
    const staticGrid=new SurfaceGrid(null);this.grids=[staticGrid];const moving=new Map();
    for(const mesh of this.world.hull){
      if(mesh.userData.fabricPart||mesh.userData.cartridgeInterior)continue;
      const id=ancestorId(mesh);if(CARRIED.includes(id)||['roller_shade','privacy_curtain','lamp','reading_lamp'].includes(id))continue;
      if(/stencil|emitter|print|active_pixels/i.test(mesh.material.name))continue;
      if(mesh.name.startsWith('flex_'))continue;
      if(['pressure_hatch','locker_drawer','service_cabinet'].includes(id)){
        let grid=moving.get(id);if(!grid){grid=new SurfaceGrid(this.world.nodes[id]);moving.set(id,grid);this.grids.push(grid);}grid.add(mesh);
      }else staticGrid.add(mesh);
    }
  }
  prepareProbe(){
    if(!this.grids)this.buildCollision();
    for(const grid of this.grids)grid.prepareProbe();
  }
  probeContact(point,previous,radius,result){
    if(!this.grids)this.prepareProbe();
    result.pen=0;result.surface=null;result.part=null;
    result.normal??=v();result.position??=v();result.surfaceVelocity??=v();
    for(const grid of this.grids)grid.contact(point,previous,radius,result,true);
    return result.pen>0?result:null;
  }
  body(id,entry){
    if(!this.grids)this.buildCollision();
    const root=new T.Group(),copy=this.world.nodes[id].clone(true);
    root.userData.fitting=id;root.userData.loose=true;root.name='Released '+id;
    copy.position.set(0,0,0);copy.quaternion.identity();copy.scale.setScalar(1);copy.visible=true;
    copy.updateMatrixWorld(true);const box=rigidBounds(copy);
    const center=box.getCenter(v()),size=box.getSize(v());copy.position.sub(center);
    root.add(copy);this.world.scene.add(root);root.position.fromArray(entry.p);root.quaternion.fromArray(entry.q).normalize();root.updateMatrixWorld(true);
    const cfg=specs[id],m=cfg.mass,invI=new T.Vector3(12/(m*(size.y**2+size.z**2)),12/(m*(size.x**2+size.z**2)),12/(m*(size.x**2+size.y**2)));
    const samples=contacts(id,size);
    const fixed=this.world.fixedDevices.find(d=>d.id===id);
    const b={id,root,copy,center,size,cfg,invI,device:fixed&&{fixed,joint:copy.getObjectByName(fixed.spec.node)},contacts:samples,hits:samples.map(()=>({pen:0,position:v(),normal:v(),surfaceVelocity:v()})),vel:v().fromArray(entry.v),spin:v().fromArray(entry.w),
      prevPos:root.position.clone(),prevQ:root.quaternion.clone(),bedPatch:{point:v(),velocity:v()},supportNormal:v(),sleeping:false,settled:0,lastSound:-10};
    copy.traverse(n=>{if(n.isMesh)this.meshes.push(n);});
    this.bodies.set(id,b);this.world.dynamics.looseRig(id,copy);return b;
  }
  remove(id){
    const b=this.bodies.get(id);if(!b)return;
    const set=new Set();b.copy.traverse(n=>set.add(n));this.meshes=this.meshes.filter(n=>!set.has(n));
    b.root.removeFromParent();this.world.dynamics.looseRig(id,null);this.bodies.delete(id);
  }
  sync(s){
    for(const id of this.bodies.keys())if(!s.loose[id])this.remove(id);
    for(const [id,entry] of Object.entries(s.loose))if(!this.bodies.has(id))this.body(id,entry);
  }
  release(item,s){
    const id=item.id;
    if(!item.lastPosition)item.update(this.world.camera,0,this.world.dynamics);
    item.copy.updateWorldMatrix(true,true);
    const q=item.copy.getWorldQuaternion(new T.Quaternion());
    s.items=s.items.filter(k=>k!==id);
    s.loose[id]={p:item.rig.position.toArray(),q:q.toArray(),v:[0,0,0],w:[0,0,0],rest:false};
    this.sync(s);
    const b=this.bodies.get(id);
    item.copy.localToWorld(b.root.position.copy(b.center));
    const carrier=this.world.restId?null:this.world.flight?.velocity;
    item.releaseMotion(b.root.position,b.vel,b.spin,carrier);
    b.root.position.toArray(s.loose[id].p);b.vel.toArray(s.loose[id].v);b.spin.toArray(s.loose[id].w);
    b.root.updateMatrixWorld(true);
    this.world.dynamics.restoreFlex(this.world.dynamics.loose.get(id),this.world.dynamics.flexState(this.world.dynamics.held));
    return b;
  }
  invInertia(b,vector,out){
    return out.copy(vector).applyQuaternion(this.invQ.copy(b.root.quaternion).invert()).multiply(b.invI).applyQuaternion(b.root.quaternion);
  }
  resolve(b,hit){
    const n=hit.normal,p=hit.position,r=this.rel.copy(p).sub(b.root.position),cfg=b.cfg;
    this.vel.copy(b.spin).cross(r).add(b.vel).sub(hit.surfaceVelocity);
    const vn=this.vel.dot(n);if(vn>=0)return;
    const rn=this.cross.copy(r).cross(n);this.invInertia(b,rn,this.torque);
    const denom=1/cfg.mass+rn.dot(this.torque);
    const j=-(1+(Math.abs(vn)>.28?cfg.restitution:0))*vn/Math.max(.01,denom);
    if(hit.fabric&&!this.seeking)this.world.furnishings.react(hit,j);
    b.vel.addScaledVector(n,j/cfg.mass);b.spin.addScaledVector(this.torque,j);
    const tangent=this.friction.copy(this.vel).addScaledVector(n,-vn),vt=tangent.length();
    if(vt>1e-6){tangent.multiplyScalar(1/vt);this.invInertia(b,this.cross.copy(r).cross(tangent),this.torque);
      const jt=Math.min(cfg.friction*j,vt/(1/cfg.mass+this.cross.dot(this.torque)));
      b.vel.addScaledVector(tangent,-jt/cfg.mass);b.spin.addScaledVector(this.torque,-jt);}
    if(!this.seeking&&-vn>.29&&this.clock-b.lastSound>.16){b.lastSound=this.clock;this.hitSound(b.id,Math.min(1,-vn),p);}
  }
  step(b,m,force,dt){
    if(b.sleeping){
      const borne=supported(b,b.supportNormal,force)&&(this.seeking||this.world.dynamics.ringing<.55),cloth=b.softSupport;
      if(cloth){
        const patch=b.bedPatch;cloth.materialPoint(patch,this.point);
        const shift=this.oldPoint.copy(this.point).sub(patch.point);
        this.vel.copy(shift).multiplyScalar(1/dt);
        patch.velocity.lerp(this.vel,1-Math.exp(-dt*48));
        if(borne&&this.vel.lengthSq()<.12**2){
          b.root.position.add(shift);patch.point.copy(this.point);
          if(!this.seeking)cloth.bearWeight(this.point,b.cfg.mass*Math.max(0,m.forces.down),Math.sqrt(b.cfg.area)*.74);
          return;
        }
        // A cup lifting off moving fabric takes the velocity of its support.
        b.vel.copy(patch.velocity);
      }else if(borne)return;
      b.settled=0;
    }
    b.softSupport=null;
    b.sleeping=false;const {root,cfg}=b;
    b.prevPos.copy(root.position);b.prevQ.copy(root.quaternion);
    b.vel.addScaledVector(force,dt);
    const cx=-.00014584*b.vel.y,cy=.00014584*b.vel.x;b.vel.x+=cx*dt;b.vel.y+=cy*dt;
    const drag=.5*1.18*.92*cfg.area/cfg.mass;
    // Drag responds to velocity relative to the circulating cabin air.
    // A palm-sized card experiences far more acceleration than a tool case.
    const air=.17*this.world.dynamics.airflow*Math.exp(-Math.abs(root.position.z+3.3)*.21);
    const relative=this.vel.copy(b.vel);relative.z-=air;
    b.vel.addScaledVector(relative,-Math.min(.4,drag*relative.length()*dt));
    b.spin.multiplyScalar(1/(1+drag*.013*b.spin.length()*dt));root.position.addScaledVector(b.vel,dt);
    const w=b.spin.length();if(w>.00001)root.quaternion.premultiply(this.rotation.setFromAxisAngle(this.normal.copy(b.spin).multiplyScalar(1/w),w*dt)).normalize();
    // Solve the entire contact patch as one event. Resolving only the deepest
    // corner rocks a flat card from edge to edge and produces phantom taps.
    let deepest=null,supports=0,support=null;
    b.contacts.forEach((sample,i)=>{
      const hit=b.hits[i];hit.pen=0;hit.fabric=null;hit.surface=null;hit.surfaceVelocity.set(0,0,0);
      this.point.copy(sample.p).applyQuaternion(root.quaternion).add(root.position);
      this.oldPoint.copy(sample.p).applyQuaternion(b.prevQ).add(b.prevPos);
      for(const grid of this.grids)grid.contact(this.point,this.oldPoint,sample.r,hit);
      this.world.furnishings?.contact(this.point,this.oldPoint,sample.r,hit);
      if(hit.fabric){hit.surface=null;hit.surfaceVelocity.set(0,0,0);this.world.furnishings.velocityAt?.(hit,hit.surfaceVelocity);}
      const keel=.0015+sample.r-this.point.y;
      if(keel>hit.pen){hit.pen=keel;hit.fabric=null;hit.surface=null;hit.surfaceVelocity.set(0,0,0);hit.normal.set(0,1,0);hit.position.set(this.point.x,.0015,this.point.z);}
      if(hit.pen>.00003){
        if(!deepest||hit.pen>deepest.pen)deepest=hit;
        if(supported(b,hit.normal,force)){supports++;if(!support||hit.pen>support.pen)support=hit;}
      }
    });
    if(deepest){
      if(deepest.fabric&&deepest.normal.y>.5){
        b.softSupport=deepest.fabric;const patch=b.bedPatch;
        patch.i=deepest.cageI;patch.j=deepest.cageJ;patch.k=deepest.cageK;
        patch.wi=deepest.wi;patch.wj=deepest.wj;patch.wk=deepest.wk;patch.point.copy(deepest.position);
      }
      root.position.addScaledVector(deepest.normal,Math.max(0,deepest.pen-.00012)*.91);
      const patch=this.contact;patch.fabric=deepest.fabric;patch.position.set(0,0,0);patch.normal.set(0,0,0);patch.surfaceVelocity.set(0,0,0);
      let count=0;
      for(const hit of b.hits)if(hit.pen>.00003&&hit.surface===deepest.surface&&hit.fabric===deepest.fabric&&hit.normal.dot(deepest.normal)>.96){
        patch.position.add(hit.position);patch.normal.add(hit.normal);patch.surfaceVelocity.add(hit.surfaceVelocity);count++;
      }
      if(count>1){patch.position.multiplyScalar(1/count);patch.normal.normalize();patch.surfaceVelocity.multiplyScalar(1/count);this.resolve(b,patch);}
      for(let pass=0;pass<5;pass++)for(const hit of b.hits)if(hit.pen>.00003)this.resolve(b,hit);
      if(supports)b.spin.multiplyScalar(Math.exp(-dt*(supports>1?3.5:.7)));
      if(b.softSupport?.kind==='quilt'){
        // The shell has to compress fresh batting as it rolls across the quilt.
        // This resistance scales with supported weight and falls away in free fall.
        const load=Math.max(0,-force.dot(deepest.normal));
        const tangent=this.friction.copy(b.vel).sub(deepest.surfaceVelocity);
        tangent.addScaledVector(deepest.normal,-tangent.dot(deepest.normal));
        const speed=tangent.length(),resistance=.16*load*dt;
        if(speed>0)b.vel.addScaledVector(tangent,-Math.min(1,resistance/speed));
        const rimSpeed=b.spin.length()*Math.max(.025,b.size.length()*.32);
        if(rimSpeed>0)b.spin.multiplyScalar(Math.max(0,1-resistance/rimSpeed));
        if(!this.seeking)b.softSupport.bearWeight(deepest.position,cfg.mass*load,Math.sqrt(cfg.area)*.74);
      }
    }
    const rimSpeed=b.spin.length()*Math.max(.025,b.size.length()*.38);
    b.touching=Boolean(deepest);
    // At small loads static friction takes much longer to arrest a sliding
    // object. A gently pushed cup cannot be parked by the Earth-gravity tolerance.
    const stoppingSpeed=support?Math.min(.11,.0015+cfg.friction*Math.max(0,-force.dot(support.normal))*.08):0;
    if(support&&b.vel.length()<stoppingSpeed&&rimSpeed<stoppingSpeed*.72)b.settled+=dt;
    else b.settled=Math.max(0,b.settled-dt*2);
    if(b.settled>.48&&support){
      b.supportNormal.copy(support.normal);b.sleeping=true;b.bedPatch.velocity.copy(b.vel);b.vel.set(0,0,0);b.spin.set(0,0,0);
    }
    // Pressure hull backstop for sub-millimetre card edges at triangulation seams.
    const p=root.position;
    if(p.y<-.016){p.y=.002+Math.min(.015,b.size.y*.42);b.vel.y=Math.max(0,b.vel.y);}
    if(p.y>2.61){p.y=2.61;if(b.vel.y>0)b.vel.y*=-.1;}
    if(Math.abs(p.x)>2.155){p.x=Math.sign(p.x)*2.155;if(p.x*b.vel.x>0)b.vel.x*=-.15;}
    if(Math.abs(p.z)>5.64){p.z=Math.sign(p.z)*5.64;if(p.z*b.vel.z>0)b.vel.z*=-.15;}
  }
  seek(s,fromSeconds,toSeconds){
    this.fixedTime=0;
    if(!Object.keys(s.loose).length&&!this.bodies.size)return;
    this.sync(s);if(!this.bodies.size)return;
    for(const grid of this.grids)grid.freeze();
    const bodies=[...this.bodies.values()],force=v();
    const starts=toSeconds>fromSeconds?bodies.map(b=>b.root.matrixWorld.clone()):null;
    const sample=seconds=>{
      const metrics=travel(seconds/RIDE_SECONDS);
      passageBodyForce(metrics,this.clock+seconds-fromSeconds,force);
      return metrics;
    };
    // Keep the rider's objects and their momenta on a backwards seek. There is
    // no earlier state for a mug the rider has just taken out of their pocket.
    // Re-evaluate every supporting surface in the destination's signed load.
    if(toSeconds>fromSeconds){
      this.seeking=true;
      try{
        for(let t=fromSeconds;t<toSeconds-1e-7;){
          const end=Math.min(toSeconds,t+1);
          if(bodies.every(b=>b.sleeping)){
            sample(end);
            if(bodies.every(b=>supported(b,b.supportNormal,force))){t=end;continue;}
          }
          // A swept contact query follows the entire path of each contact point.
          // Use smaller steps under load and larger steps on unobstructed coasts.
          const m=sample(t),moving=bodies.reduce((speed,b)=>Math.max(speed,b.vel.length()+b.spin.length()*b.size.length()*.5),0);
          const contactStep=bodies.some(b=>b.touching&&!b.sleeping)?1/60:.08;
          const dt=Math.min(toSeconds-t,contactStep,.060/(.25+moving),Math.sqrt(.012/Math.max(.01,force.length())));
          for(const b of bodies)this.step(b,m,force,dt);
          this.collideItems();t+=dt;
        }
      }finally{this.seeking=false;}
    }
    sample(toSeconds);
    for(const b of bodies){
      if(!supported(b,b.supportNormal,force)){b.sleeping=false;b.settled=0;b.softSupport=null;}
      b.prevPos.copy(b.root.position);b.prevQ.copy(b.root.quaternion);
    }
    this.writePoses(s);
    if(starts)for(let i=0;i<bodies.length;i++)
      this.world.dynamics.transportLoose(bodies[i].id,starts[i],bodies[i].root.matrixWorld);
  }
  update(s,m,dt,time){
    if(!Object.keys(s.loose).length&&!this.bodies.size)return;
    this.sync(s);this.clock=time;this.fixedTime+=Math.min(dt,.2);
    const step=fixedStep;
    const steps=Math.floor(this.fixedTime/step);
    if(steps){
      let moved=false;
      for(const grid of this.grids??[])if(grid.begin())moved=true;
      if(moved)for(const b of this.bodies.values()){b.sleeping=false;b.settled=0;}
    }
    for(let i=0;i<steps;i++){
      for(const grid of this.grids??[])grid.sample((i+1)/steps,step);
      for(const b of this.bodies.values())this.step(b,m,this.world.dynamics.bodyForce,step);
      this.collideItems();this.fixedTime-=step;
    }
    this.writePoses(s);
  }
  writePoses(s){
    for(const [id,b] of this.bodies){
      const e=s.loose[id];b.root.position.toArray(e.p);b.root.quaternion.toArray(e.q);b.vel.toArray(e.v);b.spin.toArray(e.w);
      e.rest=b.sleeping;if(b.device)b.device.joint.quaternion.copy(b.device.fixed.node.quaternion);b.root.updateMatrixWorld(true);
    }
  }
  collideItems(){
    const list=[...this.bodies.values()];
    for(let i=0;i<list.length;i++)for(let k=i+1;k<list.length;k++){
      const a=list[i],b=list[k];
      if(a.root.position.distanceToSquared(b.root.position)>((a.size.length()+b.size.length())*.5)**2)continue;
      let pen=0;
      for(const u of a.contacts)for(const v of b.contacts){
        this.point.copy(u.p).applyQuaternion(a.root.quaternion).add(a.root.position);
        this.oldPoint.copy(v.p).applyQuaternion(b.root.quaternion).add(b.root.position);
        const n=this.cross.copy(this.oldPoint).sub(this.point),len=n.length(),overlap=u.r+v.r-len;
        if(overlap>pen&&len>.00001){pen=overlap;this.normal.copy(n).multiplyScalar(1/len);}
      }
      if(!pen)continue;
      const invA=1/a.cfg.mass,invB=1/b.cfg.mass,total=invA+invB,n=this.normal;
      a.root.position.addScaledVector(n,-pen*invA/total);b.root.position.addScaledVector(n,pen*invB/total);
      const closing=this.vel.copy(b.vel).sub(a.vel).dot(n);
      if(closing<0){const j=-1.16*closing/total;a.vel.addScaledVector(n,-j*invA);b.vel.addScaledVector(n,j*invB);a.sleeping=b.sleeping=false;}
    }
  }
  room(id){const b=this.bodies.get(id);return b?roomAt(b.root.position.z):null;}
}
