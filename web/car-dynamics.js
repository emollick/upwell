import * as T from 'three';
import {TRAFFIC,clamp,smooth} from './journey.js';

const v=a=>new T.Vector3(...a);
const fixedStep=1/90;
const authoredGeometry=new WeakMap();

// Surface acceleration in the cabin frame. Both normal play and a timetable
// seek use the same drive motion; a seek never plays a skipped joint impact.
function driveMotion(m,time,shake,out){
  const wake=TRAFFIC.reduce((sum,e)=>sum+Math.exp(-(((m.seconds-e.at*360)/.72)**2)),0);
  const speed=m.forces.velocity/170,marine=(1-smooth(7,15,m.km))*Math.min(1,m.km*3);
  return out.set(.095*marine*Math.sin(time*.82)+.032*speed*Math.sin(time*2.7)+.49*shake+.13*wake*Math.sin(time*12),
    .035*speed*Math.sin(time*5.3)+.31*shake,.039*marine*Math.sin(time*.61)+.19*shake);
}
export function passageBodyForce(m,time,out){
  driveMotion(m,time,0,out).negate();
  out.x-=m.forces.west;out.y-=m.forces.down;
  return out;
}

// Skin the artist's actual cord or woven band to its simulated centreline.
// Offsets from the centreline retain its original thickness, stitching and UVs.
class FlexiblePart {
  constructor(spec,node,held=false){
    this.spec=spec;this.node=node;this.held=held;this.rest=spec.restPoints.map(v);
    this.pins=new Set(spec.pinIndices);this.old=this.rest.map(p=>p.clone());this.points=this.rest.map(p=>p.clone());
    this.targets=this.rest.map(p=>p.clone());this.lengths=this.rest.slice(1).map((p,i)=>p.distanceTo(this.rest[i]));
    this.skins=[];this.ready=false;this.lastOrigin=new T.Vector3();this.directions=[];
    this.local=this.rest.map(p=>p.clone());this.worldInverse=new T.Matrix4();this.tmp=new T.Vector3();this.correction=new T.Vector3();
    this.previousAcceleration=new T.Vector3();this.restTangents=this.rest.slice(1).map((p,i)=>p.clone().sub(this.rest[i]).normalize());
    this.rots=this.lengths.map(()=>new T.Quaternion());
    this.curve=new T.CatmullRomCurve3(this.local,false,'centripetal');
    this.smoothCenters=[];
    // The rigid bodies occupy these local volumes even when the carriage
    // unloads. Keep the web and wrist cords out of the optics and vessel.
    const bodies={field_glasses:[[-.041,-.022,-.011,.037,.037,.089],[.041,-.022,-.011,.037,.037,.089]],
      mug:[[0,.007,-.003,.045,.070,.046]],tool_roll:[[-.009,.004,.013,.108,.029,.164]]};
    this.exclusions=bodies[spec.parentId]||[];
    node.updateWorldMatrix(true,true);const inverse=node.matrixWorld.clone().invert();
    node.traverse(mesh=>{
      if(!mesh.isMesh)return;
      const source=authoredGeometry.get(mesh.geometry)??mesh.geometry;
      const geo=source.clone();authoredGeometry.set(geo,source);mesh.geometry=geo;
      const fromMesh=inverse.clone().multiply(mesh.matrixWorld),toMesh=fromMesh.clone().invert();
      const normalFrom=new T.Matrix3().getNormalMatrix(fromMesh),normalTo=new T.Matrix3().getNormalMatrix(toMesh);
      const pos=geo.attributes.position,norm=geo.attributes.normal,bindings=[];
      for(let j=0;j<pos.count;j++){
        const p=new T.Vector3().fromBufferAttribute(pos,j).applyMatrix4(fromMesh);
        const n=norm?new T.Vector3().fromBufferAttribute(norm,j).applyMatrix3(normalFrom).normalize():null;
        let best=Infinity,binding;
        for(let k=0;k<this.lengths.length;k++){
          const line=this.rest[k+1].clone().sub(this.rest[k]),f=clamp(p.clone().sub(this.rest[k]).dot(line)/Math.max(1e-12,line.lengthSq()));
          const off=p.clone().sub(this.rest[k].clone().addScaledVector(line,f));
          if(off.lengthSq()<best){best=off.lengthSq();binding={k,f,off,n};}
        }
        // The curve and rotation are common to all the vertices at a cross
        // section. Cache at 1/32 of a segment, below the mesh sampling pitch.
        binding.slot=binding.k*32+Math.round(binding.f*32);
        if(!this.smoothCenters[binding.slot])this.smoothCenters[binding.slot]={point:new T.Vector3(),q:new T.Quaternion()};
        bindings.push(binding);
      }
      pos.setUsage(T.DynamicDrawUsage);if(norm)norm.setUsage(T.DynamicDrawUsage);mesh.frustumCulled=false;
      this.skins.push({geo,bindings,toMesh,normalTo});
    });
  }
  reset(){
    this.node.updateWorldMatrix(true,false);
    for(let i=0;i<this.rest.length;i++){
      this.points[i].copy(this.rest[i]).applyMatrix4(this.node.matrixWorld);
      this.old[i].copy(this.points[i]);
    }
    this.lastOrigin.setFromMatrixPosition(this.node.matrixWorld);this.ready=true;
  }
  update(dt,accel){
    this.node.updateWorldMatrix(true,false);
    const origin=this.tmp.setFromMatrixPosition(this.node.matrixWorld);
    if(!this.ready||origin.distanceToSquared(this.lastOrigin)>.16)this.reset();
    this.lastOrigin.setFromMatrixPosition(this.node.matrixWorld);this.worldInverse.copy(this.node.matrixWorld).invert();
    this.rest.forEach((p,i)=>this.targets[i].copy(p).applyMatrix4(this.node.matrixWorld));
    const loss=Math.exp(-dt*(this.spec.kind==='cord'?3.3:4.1));
    const limit=this.spec.maxOffset;
    for(let i=0;i<this.points.length;i++){
      const p=this.points[i],old=this.old[i],t=this.targets[i];
      if(this.pins.has(i)){p.copy(t);old.copy(t);continue;}
      const vx=(p.x-old.x)*loss,vy=(p.y-old.y)*loss,vz=(p.z-old.z)*loss;old.copy(p);
      const memory=this.spec.kind==='cord'?26:50;
      // Nylon and folded webbing retain a little curvature as the loading
      // disappears. The circulation fan imparts only a few cm/s² of force.
      p.x+=vx+(accel.x+(t.x-p.x)*memory)*dt*dt;
      p.y+=vy+(accel.y+(t.y-p.y)*memory)*dt*dt;
      p.z+=vz+(accel.z+(t.z-p.z)*memory)*dt*dt;
    }
    for(let iter=0;iter<8;iter++){
      for(let i=0;i<this.lengths.length;i++){
        const a=this.points[i],b=this.points[i+1],d=this.correction.copy(b).sub(a),length=d.length();
        if(length<.000001)continue;
        const ia=!this.pins.has(i),ib=!this.pins.has(i+1);if(!ia&&!ib)continue;
        d.multiplyScalar((length-this.lengths[i])/length/(Number(ia)+Number(ib)));
        if(ia)a.add(d);if(ib)b.sub(d);
      }
      for(let i=0;i<this.points.length;i++){
        if(this.pins.has(i))continue;
        const p=this.points[i],t=this.targets[i],diff=this.correction.copy(p).sub(t);
        if(diff.lengthSq()>limit*limit)p.copy(t).add(diff.setLength(limit));
        for(const [x,y,z,rx,ry,rz] of this.exclusions){
          const local=this.tmp.copy(p).applyMatrix4(this.worldInverse);
          const dx=local.x-x,dy=local.y-y,dz=local.z-z;
          const d=Math.hypot(dx/rx,dy/ry,dz/rz);
          if(d>1e-5&&d<1){local.set(x+dx/d,y+dy/d,z+dz/d).applyMatrix4(this.node.matrixWorld);p.copy(local);}
        }
        if(!this.held&&this.spec.supportY!==null&&this.spec.supportY!==undefined){
          const local=this.tmp.copy(p).applyMatrix4(this.worldInverse);
          if(local.y<this.spec.supportY){local.y=this.spec.supportY;p.copy(local).applyMatrix4(this.node.matrixWorld);}
        }
      }
    }
  }
  skin(){
    this.points.forEach((p,i)=>this.local[i].copy(p).applyMatrix4(this.worldInverse));
    this.rots.forEach((q,i)=>q.setFromUnitVectors(this.restTangents[i],this.tmp.copy(this.local[i+1]).sub(this.local[i]).normalize()));
    this.smoothCenters.forEach((frame,slot)=>{
      const u=slot/32,k=Math.min(this.lengths.length-1,Math.floor(u)),f=u-k;
      this.curve.getPoint(u/this.lengths.length,frame.point);
      const other=f<.5?Math.max(k-1,0):Math.min(k+1,this.rots.length-1);
      frame.q.copy(this.rots[k]).slerp(this.rots[other],Math.abs(f-.5));
    });
    for(const {geo,bindings,toMesh,normalTo} of this.skins){
      const pos=geo.attributes.position,norm=geo.attributes.normal;
      for(let i=0;i<bindings.length;i++){
        const {slot,off,n}=bindings[i],{point,q}=this.smoothCenters[slot];
        this.tmp.copy(point).add(this.correction.copy(off).applyQuaternion(q)).applyMatrix4(toMesh);
        pos.setXYZ(i,this.tmp.x,this.tmp.y,this.tmp.z);
        if(n&&norm){this.tmp.copy(n).applyQuaternion(q).applyMatrix3(normalTo).normalize();norm.setXYZ(i,this.tmp.x,this.tmp.y,this.tmp.z);}
      }
      pos.needsUpdate=true;if(norm)norm.needsUpdate=true;
    }
  }
  dispose(){for(const s of this.skins)s.geo.dispose();}
}

export class CarDynamics {
  constructor(data,nodes){
    this.specs=data.parts;this.parts=[];this.held=[];this.loose=new Map();
    for(const spec of this.specs){
      const node=nodes[spec.parentId]?.getObjectByName(spec.node);
      if(!node)throw Error('Missing flexible fitting '+spec.node);
      this.parts.push(new FlexiblePart(spec,node));
    }
    this.force=new T.Vector3();this.bodyForce=new T.Vector3();this.head=new T.Vector3();this.drive=new T.Vector3();
    this.accumulator=0;this.ringing=0;this.roll=0;this.lastTime=-100;this.lastJoint=-1;
    this.lastFloor=0;this.lastStep=-100;this.eventSign=1;this.mountOffset=new T.Vector3();
  }
  handling(id,copy){
    for(const part of this.held)part.dispose();this.held=[];
    if(!copy)return;
    for(const spec of this.specs){if(spec.parentId!==id)continue;const n=copy.getObjectByName(spec.node);if(n)this.held.push(new FlexiblePart(spec,n,true));}
  }
  handJolt(speed){
    // A latch moves the wrist tether attached to that item. Its impulse is
    // too small to move the carriage or deflect a gauge across the room.
    for(const part of this.held){
      if(!part.ready)continue;
      const impulse=part.tmp.set(.42,.23,.88).transformDirection(part.node.matrixWorld).multiplyScalar(speed*fixedStep);
      for(let i=0;i<part.old.length;i++)if(!part.pins.has(i))part.old[i].sub(impulse);
    }
  }
  looseRig(id,copy){
    for(const part of this.loose.get(id)??[])part.dispose();this.loose.delete(id);
    if(!copy)return;const result=[];
    for(const spec of this.specs){if(spec.parentId!==id)continue;const n=copy.getObjectByName(spec.node);if(n)result.push(new FlexiblePart(spec,n,true));}
    this.loose.set(id,result);
  }
  transportLoose(id,from,to){
    const parts=this.loose.get(id);if(!parts?.length)return;
    const change=from.clone().invert().premultiply(to);
    for(const part of parts){
      if(!part.ready)continue;
      for(const point of part.points)point.applyMatrix4(change);
      for(const previous of part.old)previous.applyMatrix4(change);
      part.lastOrigin.applyMatrix4(change);
    }
  }
  flexState(parts){
    return (parts||[]).filter(p=>p.ready).map(p=>({node:p.spec.node,points:p.points.map(v=>v.clone()),old:p.old.map(v=>v.clone()),origin:p.lastOrigin.clone()}));
  }
  restoreFlex(parts,snapshots){
    for(const p of parts||[]){
      const snapshot=snapshots.find(s=>s.node===p.spec.node);
      if(!snapshot)continue;
      p.points.forEach((v,i)=>{v.copy(snapshot.points[i]);p.old[i].copy(snapshot.old[i]);});
      p.lastOrigin.copy(snapshot.origin);p.ready=true;
    }
  }
  impulse(amount=.25){this.ringing=Math.min(1.3,this.ringing+amount);this.eventSign*=-1;}
  seek(m,time,ventilation=true){
    this.lastTime=m.seconds;this.lastJoint=Math.floor(m.km*1000/1450);this.lastStep=time;
    this.ringing=0;this.accumulator=0;this.airflow=Number(ventilation);this.seekEpoch=(this.seekEpoch??0)+1;
    this.advance(m,time,0,ventilation);
  }
  advance(m,time,dt,ventilation=true){
    const cut=Math.abs(this.lastTime-m.seconds)>1;
    if(cut){this.ringing=0;this.lastStep=time;this.accumulator=0;}
    const joint=Math.floor(m.km*1000/1450);
    if(!cut&&joint!==this.lastJoint&&time-this.lastStep>2.4&&m.speed>20){this.impulse(.24);this.lastStep=time;}
    if(!cut&&this.lastTime<9.2&&m.seconds>=9.2)this.impulse(.71);
    if(!cut&&this.lastTime<359.7&&m.seconds>=359.7)this.impulse(.68);
    this.lastTime=m.seconds;this.lastJoint=joint;this.ringing*=Math.exp(-dt*4.0);
    const v=m.forces.velocity/170;
    const shake=this.ringing*Math.sin(time*30)*this.eventSign;
    const {x,y,z}=driveMotion(m,time,shake,this.drive);
    this.airflow??=Number(ventilation);
    this.airflow+=(Number(ventilation)-this.airflow)*(1-Math.exp(-dt*2));
    this.bodyForce.set(-m.forces.west-x,-m.forces.down-y,-z);
    this.force.copy(this.bodyForce);
    this.force.x+=this.airflow*.055*Math.sin(time*2.13);
    this.force.z+=this.airflow*(.15+.045*Math.sin(time*1.37))+.025*v*Math.sin(time*.41);
    this.head.set(-x*.016,-m.forces.driveAcceleration*.008-y*.013,-z*.016);
    this.roll=-x*.010;this.mountOffset.set(-x*.007,-y*.004,-z*.004);
    this.accumulator+=Math.min(dt,.12);
  }
  deform(){
    let steps=0;
    while(this.accumulator>=fixedStep&&steps<11){
      for(const p of this.parts){let visible=true;for(let n=p.node;n;n=n.parent)if(!n.visible){visible=false;break;}if(visible)p.update(fixedStep,this.force);else p.ready=false;}
      for(const p of this.held)p.update(fixedStep,this.force);
      for(const list of this.loose.values())for(const p of list)p.update(fixedStep,this.force);
      this.accumulator-=fixedStep;steps++;
    }
    if(steps)for(const p of [...this.parts,...this.held,...[...this.loose.values()].flat()])if(p.ready)p.skin();
  }
}
