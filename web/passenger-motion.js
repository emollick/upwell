import * as T from 'three';
import {travel,RIDE_SECONDS} from './journey.js';
import {passageBodyForce} from './car-dynamics.js';
import {handrailLoad} from './flight-physics.js';

// Eye and body stay upright in this narrow cabin. The upper bound leaves
// clearance for the head; both doorways have a lower structural transom.
const headroom = 2.39;
const doorwayHeadroom = 1.99;
const reach = .39;
export const ceilingAt = z => Math.abs(Math.abs(z)-1.90)<.22 ? doorwayHeadroom : headroom;

// Use the same physical triangles that catch a free flask. The three probes
// represent the passenger's head, shoulders and hips. Neighboring positions
// reuse the local tangent planes over less than 3 cm of travel.
export class PassengerClearance {
  constructor(loose,base){
    this.loose=loose;this.base=base;this.center=new T.Vector3(Infinity,0,0);this.sample=new T.Vector3();this.old=new T.Vector3();
    this.near=new T.Vector3();this.hit={};
    this.probes=[[0,.19],[-.27,.235],[-.70,.205]].map(([offset,radius])=>({offset,radius,normal:new T.Vector3(),limit:0,hit:false}));
  }
  prepare(){
    this.loose.prepareProbe();
    const moving=[this.base.pressure_hatch.v,this.base.locker_drawer.v,this.base.service_cabinet.v];
    if(!this.moving||moving.some((v,i)=>Math.abs(v-this.moving[i])>.005)){this.center.x=Infinity;this.moving=moving;}
  }
  resolve(p,old,velocity){
    if(p.distanceToSquared(this.center)>.028**2){
      this.center.copy(p);
      for(const probe of this.probes){
        this.sample.copy(p);this.sample.y+=probe.offset;
        this.old.copy(old);this.old.y+=probe.offset;
        const hit=this.loose.probeContact(this.sample,this.old,probe.radius+.065,this.hit);
        probe.hit=!!hit;
        if(hit){
          probe.normal.copy(hit.normal);
          probe.limit=hit.normal.dot(hit.position)+probe.radius+.001-probe.offset*hit.normal.y;
        }
      }
    }
    this.near.set(0,0,0);
    for(const probe of this.probes){
      if(!probe.hit)continue;
      const n=probe.normal,d=n.dot(p)-probe.limit;
      if(d<.05)this.near.add(n);
      if(d>=0)continue;
      p.addScaledVector(n,-d);
      const inward=velocity.dot(n);if(inward<0)velocity.addScaledVector(n,-inward);
    }
    this.near.normalize();
  }
}

export class PassengerMotion {
  constructor(standingEye) {
    this.velocity=new T.Vector3();this.force=new T.Vector3();this.pushDirection=new T.Vector3();
    this.previous=new T.Vector3();this.normal=new T.Vector3();this.clearance=null;
    this.reset(standingEye);
  }
  reset(standingEye) {
    this.deckY=Math.max(1.38,Math.min(1.65,standingEye));this.velocity.set(0,0,0);this.ballistic=false;
    if(this.clearance){this.clearance.center.x=Infinity;this.clearance.near.set(0,0,0);}
  }
  bookmark() {return {deckY:this.deckY,velocity:this.velocity.toArray(),ballistic:this.ballistic};}
  restore(entry) {
    this.reset(entry.deckY);
    this.velocity.fromArray(entry.velocity);this.ballistic=entry.ballistic;
  }
  surface(position,walkable){
    const {x,y,z}=position;
    if(y-this.deckY<=reach)return 'deck';
    if(ceilingAt(z)-y<=reach)return 'ceiling';
    if(this.clearance?.near.lengthSq())return 'rail';
    if(!walkable(x-reach,z,y)||!walkable(x+reach,z,y)||!walkable(x,z-reach,y)||!walkable(x,z+reach,y))return 'rail';
    return '';
  }
  push(position,walkable,direction){
    const support=this.surface(position,walkable);if(!support)return false;
    const {x,y,z}=position,deck=y-this.deckY,roof=ceilingAt(z)-y,n=this.normal.set(0,0,0);
    if(direction==='down'){
      if(deck<=.015)return false;
      n.y=-1;
    }else{
      if(this.clearance?.near.lengthSq())n.copy(this.clearance.near);
      if(deck<.17)n.y+=1;else if(roof<.17)n.y-=1;
      if(!walkable(x-reach,z,y))n.x+=1;if(!walkable(x+reach,z,y))n.x-=1;
      if(!walkable(x,z-reach,y))n.z+=1;if(!walkable(x,z+reach,y))n.z-=1;
      if(n.lengthSq()<.001)n.y=deck<roof?1:-1;
      n.normalize();
    }
    // The impulse comes from feet or a hand on the cabin structure. Holding
    // the key in open space cannot apply another impulse.
    const normalSpeed=this.velocity.dot(n);
    this.velocity.addScaledVector(n,Math.min(.72,Math.max(.50,normalSpeed+.49))-normalSpeed);
    this.ballistic=true;return true;
  }
  advance(position,walkable,force,lowLoad,dt,wish=null){
    if(!lowLoad&&!this.ballistic)return false;
    if(!lowLoad&&position.y<=this.deckY+.002&&this.velocity.y<=0){
      position.y=this.deckY;this.ballistic=false;return false;
    }
    this.ballistic=true;
    const count=Math.max(1,Math.ceil(dt*60)),h=dt/count,v=this.velocity;
    for(let i=0;i<count;i++){
      this.previous.copy(position);
      if(lowLoad&&wish&&wish.lengthSq()&&this.surface(position,walkable)){
        const gain=Math.min(h*1.05,Math.max(0,.85-v.dot(wish)));
        v.addScaledVector(wish,gain);
      }
      v.addScaledVector(force,h);
      // Air drag uses speed relative to the cabin in passenger seconds.
      v.multiplyScalar(1/(1+.004*v.length()*h));
      const x=position.x+v.x*h,z=position.z+v.z*h;
      if(walkable(x,position.z,position.y))position.x=x;else v.x=0;
      if(walkable(position.x,z,position.y))position.z=z;else v.z=0;
      const ceiling=ceilingAt(position.z),y=position.y+v.y*h;
      position.y=Math.min(ceiling,Math.max(this.deckY,y));
      if(y<=this.deckY||y>=ceiling){
        v.y=0;
        const supportLoad=y<=this.deckY?-force.y:force.y;
        const speed=Math.hypot(v.x,v.z);
        if(speed>0&&supportLoad>0){
          const friction=Math.max(0,1-.42*supportLoad*h/speed);v.x*=friction;v.z*=friction;
        }
      }
      this.clearance?.resolve(position,this.previous,v);
    }
    return true;
  }
  seek(position,walkable,from,to,clock=from){
    // Rewinding moves the timetable. The player's physical pose and momentum
    // carry into the new load. Forward jumps also include the omitted braking.
    for(let t=from;t<to;){
      const dt=Math.min(.25,to-t),m=travel((t+dt*.5)/RIDE_SECONDS);
      passageBodyForce(m,clock+t+dt*.5-from,this.force);
      this.advance(position,walkable,this.force,m.forces.gravityG<=handrailLoad,dt);
      t+=dt;
    }
  }
}
