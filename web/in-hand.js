import * as T from 'three';
import {clamp} from './journey.js';

const poses={field_glasses:[.33,-.73,-.10],access_card:[1.31,-.10,-.09],
  logbook:[1.08,-.15,-.10],mug:[.22,1.61,.48],tool_roll:[1.08,-.15,-.05]};
export const heldMass={field_glasses:.73,mug:.32,logbook:.41,tool_roll:.86,access_card:.011};

export function rigidBounds(root){
  const box=new T.Box3().makeEmpty();
  root.traverse(mesh=>{
    if(!mesh.isMesh)return;
    let n=mesh;while(n&&n!==root&&!n.name.startsWith('flex_'))n=n.parent;
    if(n?.name.startsWith('flex_'))return;
    mesh.geometry.computeBoundingBox();box.union(mesh.geometry.boundingBox.clone().applyMatrix4(mesh.matrixWorld));
  });
  return box;
}

export class InHand {
  constructor(scene,node,id,panel,spec,state){
    this.scene=scene;this.panel=panel;this.id=id;this.rig=new T.Group();this.turntable=new T.Group();
    const copy=node.clone(true);copy.visible=true;copy.position.set(0,0,0);copy.quaternion.identity();copy.scale.set(1,1,1);
    copy.updateMatrixWorld(true);
    const box=new T.Box3().setFromObject(copy),dimensions=box.getSize(new T.Vector3());
    this.localCenter=rigidBounds(copy).getCenter(new T.Vector3());copy.position.sub(this.localCenter);
    this.size=Math.max(dimensions.x,dimensions.y,dimensions.z);this.focusBand=this.size*.55;
    this.angle=poses[id]?.slice()??[.35,-.22,0];this.turntable.rotation.set(...this.angle,'YXZ');
    this.turntable.add(copy);this.rig.add(this.turntable);scene.add(this.rig);
    this.copy=copy;this.zoom=1;this.easedZoom=1;this.appearance=0;this.offset=new T.Vector3();
    this.rotationGoal=new T.Quaternion();this.euler=new T.Euler(0,0,0,'YXZ');
    this.spec=spec;this.state=state;this.joint=spec?copy.getObjectByName(spec.node):null;
    if(this.joint){this.initialJoint=this.joint.quaternion.clone();this.axis=new T.Vector3();
      this.axis[spec.axis]=1;this.jointQ=new T.Quaternion();this.jointPosition=state.deviceStops[id]/(spec.detents-1);this.jointV=0;}
    this.workLamp=true;this.kick=0;this.ray=new T.Raycaster();
    this.moveMode=false;this.handOffset=new T.Vector3();this.handVelocity=new T.Vector3();this.handSpin=new T.Vector3();
    this.carryBlend=0;this.lowerUntil=0;
    this.lastPosition=null;this.lastAngle=null;this.qdelta=new T.Quaternion();this.currentAngle=new T.Quaternion();
    this.mouseImpulse=new T.Vector3();this.eventAt=0;this.tmpVec=new T.Vector3();this.previousDrag=0;
    this.carrierVelocity=new T.Vector3();this.anchor=new T.Vector3();this.lastAnchor=new T.Vector3();
    this.gripDeflection=new T.Vector3();this.previousDeflection=new T.Vector3();this.loadEpoch=-1;
  }
  turn(dx,dy){this.angle[1]+=dx*.012;this.angle[0]+=dy*.010;}
  flip(){this.angle[1]+=Math.PI;}
  magnify(step){this.zoom=clamp(this.zoom*step,.71,1.55);}
  move(dx,dy,camera){
    const stamp=performance.now(),dt=clamp((stamp-(this.previousDrag||stamp-16))*.001,.007,.1);
    this.previousDrag=stamp;const scale=2*Math.tan(camera.fov*Math.PI/360)*this.distance/innerHeight;
    this.tmpVec.copy(this.handOffset);
    this.handOffset.x+=dx*scale;this.handOffset.y-=dy*scale;
    this.handOffset.clampLength(0,Math.min(.31,this.distance*.56));
    const shift=this.tmpVec.subVectors(this.handOffset,this.tmpVec).applyQuaternion(camera.quaternion);
    if(shift.lengthSq()<1e-12)this.mouseImpulse.set(0,0,0);
    else this.mouseImpulse.lerp(shift.multiplyScalar(1/dt),.58).clampLength(0,1.85);
    this.eventAt=stamp;
  }
  releaseVelocity(){
    if(this.eventAt&&performance.now()-this.eventAt<140)
      return this.tmpVec.copy(this.mouseImpulse).add(this.carrierVelocity);
    return this.handVelocity;
  }
  releaseMotion(center,velocity,spin,carrierFallback){
    velocity.copy(this.releaseVelocity());spin.copy(this.handSpin);
    if(!this.hasVelocitySample&&carrierFallback)velocity.add(carrierFallback);
    // The physical centre of mass can sit off the hand pivot (e.g. the mug's
    // handle). It also inherits the tangential speed of a turning wrist.
    this.tmpVec.subVectors(center,this.rig.position).cross(spin);
    velocity.sub(this.tmpVec);
    const inbound=this.fromPose,remaining=(1-this.appearance)**3;
    if(inbound?.v&&remaining>.002){velocity.lerp(inbound.v,remaining);if(inbound.w)spin.lerp(inbound.w,remaining);}
    velocity.clampLength(0,5);spin.clampLength(0,10);
  }
  resetReleaseSample(){
    this.lastPosition=null;this.lastAngle=null;this.eventAt=0;this.previousDrag=0;this.hasVelocitySample=false;
    this.handVelocity.set(0,0,0);this.carrierVelocity.set(0,0,0);this.handSpin.set(0,0,0);this.mouseImpulse.set(0,0,0);
  }
  operate(direction=1){
    if(!this.joint)return false;
    const n=this.spec.detents,id=this.id;
    if(id==='mug'){
      this.state.deviceStops.mug=1;this.valveDelay=.64;
    }else{
      this.state.deviceStops[id]=(this.state.deviceStops[id]+direction+n)%n;
      this.kick=id==='logbook'?.044:id==='tool_roll'?.025:.013;
    }
    return true;
  }
  hitJoint(x,y,camera){
    if(!this.joint)return false;
    this.ray.setFromCamera(new T.Vector2(x/innerWidth*2-1,1-y/innerHeight*2),camera);
    const hit=this.ray.intersectObject(this.copy,true)[0];if(!hit)return false;
    for(let n=hit.object;n;n=n.parent)if(n===this.joint)return true;
    return false;
  }
  holdValve(down){
    if(this.id!=='mug'||this.valveHeld===down)return;
    this.valveHeld=down;
    if(down){this.state.deviceStops.mug=1;this.valveDelay=.34;}
    else if(!(this.valveDelay>0))this.state.deviceStops.mug=0;
  }
  tapReader(target,onRead,onFinish){
    this.tap={target:target.clone(),t:0,read:false,onRead,onFinish,q:new T.Quaternion().setFromEuler(new T.Euler(-Math.PI*.5,.06,-.04))};
  }
  update(camera,dt,motion){
    this.appearance=Math.min(1,this.appearance+dt*3.7);
    const grip=1-(1-this.appearance)**3;
    const layout=this.panel.getBoundingClientRect(),w=innerWidth,h=innerHeight;
    const mobile=w<720||layout.width>w*.78;
    const areaW=mobile?w:Math.max(w*.42,layout.left),areaH=mobile?Math.max(h*.34,layout.top):h;
    const walking=this.carrying||performance.now()<this.lowerUntil;
    this.carryBlend=T.MathUtils.damp(this.carryBlend,walking?1:0,6.5,dt);
    const x=areaW*(.5+.18*this.carryBlend),y=areaH*((mobile?.55:.492)+.24*this.carryBlend);
    this.easedZoom=T.MathUtils.lerp(this.easedZoom,this.zoom,1-Math.exp(-dt*14));
    const focal=Math.tan(T.MathUtils.degToRad(camera.fov)*.5);
    const fraction=Math.min(areaW/h,areaH/h)*(mobile?.72:.65)*(1.-.48*this.carryBlend);
    this.distance=Math.max(.13,this.size/(2*focal*fraction*this.easedZoom));
    this.rig.quaternion.copy(camera.quaternion);
    this.offset.set((2*x/w-1)*this.distance*focal*camera.aspect,
      (1-2*y/h)*this.distance*focal-this.size*(1-grip)*.56,
      -this.distance-this.size*.36*(1-grip)).add(this.handOffset).applyQuaternion(camera.quaternion);
    if(motion){
      this.offset.addScaledVector(motion.mountOffset,2.4);
      // The same grip yields under a heavy wallet and barely deflects under a
      // card. An editorial time jump changes its static load, not its throw speed.
      const equilibrium=this.tmpVec.copy(motion.bodyForce).multiplyScalar(heldMass[this.id]/330);
      if(this.loadEpoch!==(motion.seekEpoch??0)){
        this.previousDeflection.copy(this.gripDeflection);
        this.gripDeflection.copy(equilibrium);
        this.previousDeflection.subVectors(this.gripDeflection,this.previousDeflection);
        if(this.lastPosition){this.lastPosition.add(this.previousDeflection);this.lastAnchor.add(this.previousDeflection);}
        this.loadEpoch=motion.seekEpoch??0;
      }else this.gripDeflection.lerp(equilibrium,1-Math.exp(-dt*12));
      this.offset.add(this.gripDeflection);
    }
    this.rig.position.copy(camera.position).add(this.offset);
    this.kick*=Math.exp(-dt*10);
    const thumbLoad=this.id==='mug'?(this.jointPosition??0)*.032:0;
    this.euler.set(this.angle[0]+(1-grip)*.19+this.kick-thumbLoad,this.angle[1],this.angle[2],'YXZ');
    this.rotationGoal.setFromEuler(this.euler);
    const response={mug:12.3,field_glasses:11.0,tool_roll:12.0,logbook:13.5,access_card:20}[this.id]??15;
    this.turntable.quaternion.slerp(this.rotationGoal,1-Math.exp(-dt*response));
    if(this.fromPose&&grip<.998){
      this.rig.position.lerp(this.fromPose.p,1-grip);
      this.rig.quaternion.slerp(this.qdelta.copy(this.fromPose.q).multiply(this.turntable.quaternion.clone().invert()),1-grip);
    }
    if(this.joint){
      if(this.valveDelay>0){this.valveDelay-=dt;if(this.valveDelay<=0&&!this.valveHeld)this.state.deviceStops.mug=0;}
      const target=this.state.deviceStops[this.id]/(this.spec.detents-1);
      const speed=this.id==='mug'?(target===0?31:19):this.id==='logbook'?13:26;
      const damping=this.id==='mug'?1.72:1.65;
      const steps=Math.max(1,Math.ceil(dt/.012)),step=dt/steps;
      for(let i=0;i<steps;i++){
        this.jointV+=(speed*speed*(target-this.jointPosition)-damping*speed*this.jointV)*step;
        const next=this.jointPosition+this.jointV*step;
        this.jointPosition=clamp(next,0,1);
        if(this.jointPosition!==next)this.jointV=0;
      }
      this.joint.quaternion.copy(this.initialJoint).multiply(this.jointQ.setFromAxisAngle(this.axis,this.spec.amount*Math.PI/180*this.jointPosition));
    }
    if(this.tap){
      const a=this.tap;a.t+=dt;
      const rise=clamp(a.t/.37),fall=clamp((1.06-a.t)/.32),f=rise*rise*(3-2*rise)*fall*fall*(3-2*fall);
      this.rig.position.lerp(a.target,f);this.rig.quaternion.slerp(this.rotationGoal.copy(a.q).multiply(this.turntable.quaternion.clone().invert()),f);
      this.distance=camera.position.distanceTo(this.rig.position);
      if(a.t>=.37&&!a.read){a.read=true;a.onRead();}
      if(a.t>=1.06){this.tap=null;a.onFinish?.();}
    }
    this.currentAngle.copy(this.rig.quaternion).multiply(this.turntable.quaternion);
    this.anchor.copy(this.handOffset).applyQuaternion(camera.quaternion).negate().add(this.rig.position);
    if(this.lastPosition&&grip>.996&&dt>0){
      this.hasVelocitySample=true;
      this.handVelocity.lerp(this.tmpVec.copy(this.rig.position).sub(this.lastPosition).multiplyScalar(1/dt),1-Math.exp(-dt*22));
      this.carrierVelocity.lerp(this.tmpVec.copy(this.anchor).sub(this.lastAnchor).multiplyScalar(1/dt),1-Math.exp(-dt*22));
      this.qdelta.copy(this.currentAngle).multiply(this.lastAngle.clone().invert());
      if(this.qdelta.w<0)this.qdelta.set(-this.qdelta.x,-this.qdelta.y,-this.qdelta.z,-this.qdelta.w);
      const angle=2*Math.acos(clamp(this.qdelta.w,-1,1)),sin=Math.sin(angle/2);
      if(sin>.00001)this.tmpVec.set(this.qdelta.x,this.qdelta.y,this.qdelta.z).multiplyScalar(angle/(sin*dt));else this.tmpVec.set(0,0,0);
      this.handSpin.lerp(this.tmpVec,1-Math.exp(-dt*22));
    }
    (this.lastPosition??=new T.Vector3()).copy(this.rig.position);(this.lastAngle??=new T.Quaternion()).copy(this.currentAngle);this.lastAnchor.copy(this.anchor);
  }
  release(){
    if(this.id==='mug'){this.valveHeld=false;this.state.deviceStops.mug=0;}
    this.rig.removeFromParent();
  }
}
