import * as T from 'three';

const STEP=1/90;
const G=9.80665;
const clamp=(value,min=0,max=1)=>Math.max(min,Math.min(max,value));
const vector=a=>new T.Vector3().fromArray(a);
const zero=()=>new T.Vector3();

function interval(knots,value){
  let lo=0,hi=knots.length-1;
  while(hi-lo>1){const mid=(lo+hi)>>1;if(value<knots[mid])hi=mid;else lo=mid;}
  return [lo,clamp((value-knots[lo])/(knots[lo+1]-knots[lo]))];
}

// A cage follows the sewn surface or the cable centreline. Each exported
// vertex keeps its offset and normal in the rotating frame of that cage.
// This carries the underside, piping, relief stitching, and cable radius
// with the visible face while leaving the original material UVs in place.
class FabricPart {
  constructor(spec,scene){
    this.id=spec.id;this.spec=spec;this.node=scene.getObjectByName(spec.node);
    if(!this.node)throw Error('Missing furnishing '+spec.node);
    this.kind=this.id.includes('quilt')?'quilt':this.id.includes('curtain')?'curtain':'service';
    this.grid=spec.grid;
    this.rest=(this.grid?.restPoints??spec.restPoints).map(vector);
    this.open=this.grid?.openPoints?.map(vector);
    this.nu=this.grid?.u.length??this.rest.length;this.nv=this.grid?.v.length??1;
    this.points=this.rest.map(p=>p.clone());this.old=this.rest.map(p=>p.clone());
    this.reference=this.rest.map(p=>p.clone());this.pins=new Uint8Array(this.rest.length);
    for(const i of spec.pinIndices)this.pins[i]=1;
    this.beltRows=new Set(spec.beltRows??[]);
    this.bodyDent=this.kind==='quilt'?new Float32Array(this.rest.length):null;
    this.node.updateWorldMatrix(true,true);
    this.matrix=this.node.matrixWorld.clone();this.inverse=this.matrix.clone().invert();
    this.localDirection=new T.Matrix3().setFromMatrix4(this.inverse);
    this.worldDirection=new T.Matrix3().setFromMatrix4(this.matrix);
    this.tmp=zero();this.tmp2=zero();this.a=zero();this.b=zero();this.c=zero();this.d=zero();
    this.frameMatrix=new T.Matrix4();this.rotation=new T.Quaternion();
    this.restFrames=this.rest.map((_,i)=>this.frame(this.rest,i,new T.Quaternion()).invert());
    this.frames=this.rest.map(()=>new T.Quaternion());
    this.directions=this.rest.map((_,i)=>this.tangent(this.rest,i,zero()));
    this.links=[];this.makeLinks();this.bounds=new T.Box3().setFromPoints(this.rest);
    this.envelope=this.bounds.clone();if(this.open)this.open.forEach(p=>this.envelope.expandByPoint(p));
    this.envelope.expandByScalar(.27);
    this.worldEnvelope=this.envelope.clone().applyMatrix4(this.matrix);
    this.lastSkin=-Infinity;this.lastPose=null;this.skinCount=0;
    const limits=spec.clearance?.localBounds??spec.clearance?.worldBounds;
    this.clearance=limits?new T.Box3(vector(limits[0]),vector(limits[1])):null;
    if(this.clearance&&!spec.clearance.localBounds)this.clearance.applyMatrix4(this.inverse);
    this.weights=this.rest.map((p,i)=>this.properties(p,i));
    if(this.kind==='curtain')this.bedLimit=new Float64Array(this.rest.length);
    this.neutralLine=this.grid?null:this.relaxedCable();
    this.closedX=this.rowCenters(this.rest);this.openX=this.open?this.rowCenters(this.open):null;
    this.hardware=(spec.hardware??[]).map(item=>{
      const node=scene.getObjectByName(item.node);if(!node)throw Error('Missing curtain hardware '+item.node);
      return {node,home:node.position.clone(),delta:vector(item.openTranslation)};
    });
    this.skins=[];this.node.traverse(mesh=>{if(mesh.isMesh)this.bind(mesh);});
    this.tri=new T.Triangle();this.hit=zero();this.hitNormal=zero();this.query=zero();this.prior=zero();
    this.lastTravel=-1;this.maxSpeed=0;
  }
  tangent(points,i,out){
    const col=i%this.nu;
    return out.subVectors(points[i+(col<this.nu-1?1:0)],points[i-(col>0?1:0)]).normalize();
  }
  frame(points,i,out){
    if(!this.grid)return out.identity();
    const row=Math.floor(i/this.nu),u=this.tangent(points,i,this.a);
    const v=this.b.subVectors(points[i+(row<this.nv-1?this.nu:0)],points[i-(row?this.nu:0)]);
    const n=this.c.crossVectors(u,v).normalize();v.crossVectors(n,u).normalize();
    return out.setFromRotationMatrix(this.frameMatrix.makeBasis(u,v,n));
  }
  rowCenters(points){
    if(!this.grid)return null;
    return this.grid.v.map((_,row)=>{
      let min=Infinity,max=-Infinity;for(let col=0;col<this.nu;col++){const x=points[row*this.nu+col].x;min=Math.min(x,min);max=Math.max(x,max);}
      return (max+min)*.5;
    });
  }
  makeLinks(){
    const add=(a,b,min,max,stiff)=>this.links.push({a,b,min,max,stiff,length:this.rest[a].distanceTo(this.rest[b])});
    for(let y=0;y<this.nv;y++)for(let x=0;x<this.nu;x++){
      const i=y*this.nu+x,quilt=this.kind==='quilt';
      if(x+1<this.nu)add(i,i+1,this.grid ? .94 : .999,this.grid?(quilt?1.045:1.014):1.001,.94);
      if(y+1<this.nv)add(i,i+this.nu,.974,quilt?1.045:1.009,.94);
      if(x+1<this.nu&&y+1<this.nv){add(i,i+this.nu+1,.94,1.055,.65);add(i+1,i+this.nu,.94,1.055,.65);}
      // Second neighbours bound the bend radius without making every fold a rigid panel.
      if(x+2<this.nu)add(i,i+2,this.grid ? .88 : .91,this.grid?1.065:1.006,.57);
      if(y+2<this.nv)add(i,i+2*this.nu,.947,1.04,.55);
    }
  }
  properties(p,i){
    const col=i%this.nu,row=Math.floor(i/this.nu);
    const u=this.grid?.u[col]??i/(this.nu-1),v=this.grid?.v[row]??0;
    const torso=Math.exp(-(((u-.52)/.32)**2+((v-.37)/.31)**2)*1.37);
    const legs=.58*Math.exp(-(((u-.49)/.24)**2+((v-.77)/.23)**2)*1.45);
    const belt=this.beltRows.has(row);
    // A filled, baffled quilt has recoverable loft. The two webbing strips
    // limit that recovery where they actually cross the cover.
    const beltDistance=this.grid&&this.beltRows.size?Math.min(...[...this.beltRows].map(r=>Math.abs(v-this.grid.v[r]))):1;
    const puff=clamp(beltDistance/.125);
    const foot=clamp((v-.69)/.29),freeFoot=foot*foot*(3-2*foot);
    const loft=(.026+.047*u+.048*freeFoot*(.48+.52*u))*(puff*puff*(3-2*puff));
    return {u,v,row,belt,loft,person:Math.min(1,torso+legs)};
  }
  relaxedCable(){
    const first=this.rest[0],last=this.rest.at(-1),axis=last.clone().sub(first).normalize();
    const mid=this.rest[Math.floor(this.nu/2)].clone().sub(first);
    const sign=new T.Vector3().crossVectors(axis,mid).x>0?-1:1;
    // Coiled cable retains a bend out from the backplane when its weight
    // comes off. Rotation around the socket chord preserves its free length.
    return this.rest.map((p,i)=>p.clone().sub(first).applyAxisAngle(axis,sign*.91*Math.min(1,Math.sin(Math.PI*i/(this.nu-1))*2.8)).add(first));
  }
  binding(point,uv){
    if(this.grid){
      const first=this.rest[0],last=this.rest.at(-1);
      const u=uv?.x??(this.kind==='quilt'?(point.x-first.x)/(last.x-first.x):(point.z-first.z)/(last.z-first.z));
      const v=uv?.y??(this.kind==='quilt'?(point.z-first.z)/(last.z-first.z):(point.y-first.y)/(last.y-first.y));
      const [x,fx]=interval(this.grid.u,u),[y,fy]=interval(this.grid.v,v),i=y*this.nu+x;
      return {indices:[i,i+1,i+this.nu,i+this.nu+1],weights:[(1-fx)*(1-fy),fx*(1-fy),(1-fx)*fy,fx*fy]};
    }
    let best=Infinity,index=0,t=0;
    for(let i=0;i<this.nu-1;i++){
      const d=this.a.subVectors(this.rest[i+1],this.rest[i]),size=d.lengthSq();
      const f=clamp(this.b.subVectors(point,this.rest[i]).dot(d)/Math.max(size,1e-12));
      const dist=this.b.copy(this.rest[i]).addScaledVector(d,f).distanceToSquared(point);
      if(dist<best){best=dist;index=i;t=f;}
    }
    return {indices:[index,index+1],weights:[1-t,t]};
  }
  bind(mesh){
    const geometry=mesh.geometry.clone();mesh.geometry=geometry;mesh.userData.fabricPart=this;
    // The curtain has separately sewn front and lining meshes with opposing
    // winding. Drawing their reverse faces exposes strips of lining through
    // a tightly bent pleat. Each outward face remains visible from its side.
    if(this.kind==='curtain'&&['Curtain_Acoustic','Quilt_Lining'].includes(mesh.material.name)){
      mesh.material=mesh.material.clone();mesh.material.side=T.FrontSide;
    }
    const fromMesh=this.inverse.clone().multiply(mesh.matrixWorld),toMesh=fromMesh.clone().invert();
    const fromNormal=new T.Matrix3().getNormalMatrix(fromMesh),toNormal=new T.Matrix3().getNormalMatrix(toMesh);
    const {position,normal,uv1}=geometry.attributes,bindings=[];
    for(let i=0;i<position.count;i++){
      const p=zero().fromBufferAttribute(position,i).applyMatrix4(fromMesh);
      const uv=uv1?new T.Vector2().fromBufferAttribute(uv1,i):null;
      const entry=this.binding(p,uv);
      for(let k=0;k<entry.indices.length;k++)p.addScaledVector(this.rest[entry.indices[k]],-entry.weights[k]);
      entry.offset=p;entry.normal=normal?zero().fromBufferAttribute(normal,i).applyMatrix3(fromNormal).normalize():null;
      bindings.push(entry);
    }
    position.setUsage(T.DynamicDrawUsage);if(normal)normal.setUsage(T.DynamicDrawUsage);
    geometry.boundingBox=this.envelope.clone().applyMatrix4(toMesh);
    geometry.boundingSphere=geometry.boundingBox.getBoundingSphere(new T.Sphere());
    this.skins.push({mesh,position,normal,toMesh,toNormal,bindings});
  }
  setRail(travel){
    if(!this.open||Math.abs(travel-this.lastTravel)<1e-6)return;
    this.lastTravel=travel;
    const shutSpan=this.rest[this.nu-1].z-this.rest[0].z,openSpan=this.open[this.nu-1].z-this.open[0].z;
    const span=shutSpan+(openSpan-shutSpan)*travel;
    // Advance the rail projection and unfold the returns. Squared projected
    // lengths give the intermediate angle of a pleat of fixed material width.
    const q=clamp((span*span-shutSpan*shutSpan)/(openSpan*openSpan-shutSpan*shutSpan));
    for(let i=0;i<this.nu*this.nv;i++){
      const r=this.rest[i],o=this.open[i],p=this.reference[i],row=this.weights[i].row;
      p.copy(r).lerp(o,travel);
      const a=r.x-this.closedX[row],b=o.x-this.openX[row];
      if(a*b>=0)p.x=this.closedX[row]*(1-travel)+this.openX[row]*travel+(Math.sign(a)||Math.sign(b))*Math.sqrt((1-q)*a*a+q*b*b);
    }
    for(const link of this.links)link.length=this.reference[link.a].distanceTo(this.reference[link.b]);
    for(const h of this.hardware)h.node.position.copy(h.home).addScaledVector(h.delta,travel);
  }
  solveLengths(reverse){
    for(let k=0;k<this.links.length;k++){
      const {a,b,min,max,stiff,length}=this.links[reverse?this.links.length-1-k:k];
      const pa=this.points[a],pb=this.points[b],dx=pb.x-pa.x,dy=pb.y-pa.y,dz=pb.z-pa.z;
      const l2=dx*dx+dy*dy+dz*dz,short=min*length,long=max*length;
      if((l2>=short*short&&l2<=long*long)||l2<1e-14)continue;
      const invA=1-this.pins[a],invB=1-this.pins[b],sum=invA+invB;if(!sum)continue;
      const l=Math.sqrt(l2),f=(l-(l<short?short:long))*stiff/(l*sum);
      if(invA){pa.x+=dx*f;pa.y+=dy*f;pa.z+=dz*f;}
      if(invB){pb.x-=dx*f;pb.y-=dy*f;pb.z-=dz*f;}
    }
  }
  berthClearance(){
    const quilt=this.berth;if(!quilt)return;
    const m=this.matrix.elements,bm=quilt.matrix.elements,head=quilt.rest[0].z+bm[14],foot=quilt.rest.at(-1).z+bm[14];
    for(let i=0;i<this.points.length;i++){
      const p=this.points[i],z=p.z+m[14],y=p.y+m[13];this.bedLimit[i]=-Infinity;
      if(y>1.27||z<head-.016||z>foot+.016)continue;
      const [row,f]=interval(quilt.grid.v,(z-head)/(foot-head)),index=(row+1)*quilt.nu-1;
      const a=quilt.points[index],b=quilt.points[index+quilt.nu];
      const insideA=quilt.points[index-1],insideB=quilt.points[index+quilt.nu-1];
      const frontX=a.x+(b.x-a.x)*f+bm[12],top=Math.max(a.y+(b.y-a.y)*f,insideA.y+(insideB.y-insideA.y)*f)+bm[13];
      const under=clamp((top+.106-y)/.075);
      let x=-1.355+(frontX+.014+1.355)*under;
      if(y<1.09&&(Math.abs(z+.461)<.049||Math.abs(z-.538)<.052))x=Math.max(x,-1.239);
      this.bedLimit[i]=x-m[12];
    }
  }
  step(force,time,fan,travel,door,doorSpeed,occupancy){
    this.setRail(travel);
    const quilt=this.kind==='quilt',curtain=this.kind==='curtain',cable=!this.grid;
    const localForce=this.d.copy(force).applyMatrix3(this.localDirection);
    const load=clamp(-localForce.y/G)*occupancy,dt2=STEP*STEP;
    const memory=quilt?25:curtain?5.2:5.6,drag=Math.exp(-STEP*(quilt?5.3:curtain?6.7:3.05));
    if(this.press){this.press.age+=STEP;if(this.press.age>.38)this.press=null;}
    const press=this.press?Math.min(1,this.press.age/.09,Math.max(0,(.34-this.press.age)/.13)):0;
    const cover=cable?door:1,pivot=this.matrix.elements;
    for(let i=0;i<this.points.length;i++){
      const p=this.points[i],old=this.old[i],r=this.reference[i],w=this.weights[i];
      if(this.pins[i]){old.copy(p);p.copy(r);continue;}
      if(this.bodyDent)this.bodyDent[i]*=.947;
      let tx=r.x,ty=r.y,tz=r.z;
      if(quilt){ty+=w.loft;tx+=.013*w.u*w.loft/.10;}
      if(curtain){const curl=Math.sin(w.u*Math.PI)*w.v*w.v;tx+=.086*curl;ty+=.031*curl;}
      if(cable){const rel=this.neutralLine[i];tx=rel.x;ty=rel.y;tz=rel.z;}
      const wx=p.x+pivot[12],wy=p.y+pivot[13],wz=p.z+pivot[14];
      const drop=2.58-wy,roomZ=cable?3.8:0;
      const dz=Math.min(Math.abs(wz-(roomZ-.4715)),Math.abs(wz-(roomZ+1.4145)));
      const jet=(Math.abs(wx)-.80*drop)/(.29+.23*drop);
      const air=fan*cover*Math.exp(-.5*jet*jet-.5*(dz/(.45+.18*drop))**2);
      const gust=air*(1+.28*Math.sin(time*4.4-wy*3+wz*2.1)+.13*Math.sin(time*7.1-wz*3.3));
      const wind=gust*(quilt ? .29 : curtain ? .24 : .16);
      const vx=(p.x-old.x)*drag,vy=(p.y-old.y)*drag,vz=(p.z-old.z)*drag;old.copy(p);
      p.x+=vx+(localForce.x+(tx-p.x)*memory+Math.sign(wx)*wind-(cable?.74*doorSpeed:0))*dt2;
      p.y+=vy+(localForce.y+(ty-p.y)*memory-.22*wind-(quilt?load*w.person*15:0)-(this.press?press*this.press.weights[i]*26:0))*dt2;
      // In the stow pocket the stacked pleats constrain one another along
      // the track. The free hem still bends outward with the fan.
      const alongRail=curtain?36*(1-travel)*(1-travel):0;
      p.z+=vz+(localForce.z+(tz-p.z)*(memory+alongRail)+.31*wind)*dt2;
    }
    if(curtain)this.berthClearance();
    const nPass=cable?34:6;
    for(let pass=0;pass<nPass;pass++){
      if(this.grip)for(const entry of this.grip.entries){
        const target=this.a.copy(entry.home).add(this.grip.delta);
        this.points[entry.index].lerp(target,entry.weight*.46);
      }
      this.solveLengths(pass%2===1);
      for(let i=0;i<this.points.length;i++){
        if(this.pins[i])continue;
        const p=this.points[i],r=this.reference[i],w=this.weights[i];
        const d=this.a.subVectors(p,r),limit=this.spec.maxLift??this.spec.maxSway??this.spec.maxOffset;
        if(d.lengthSq()>limit*limit)p.copy(r).add(d.setLength(limit));
        if(this.clearance)p.clamp(this.clearance.min,this.clearance.max);
        if(quilt){
          const pressure=(this.grip?Math.min(.022,Math.max(0,-this.grip.delta.y))*this.grip.weights[i]:0)+(this.press?.weights[i]??0)*.030*press;
          const depth=Math.min(.046,(this.spec.maxCompression??.04)*load*w.person+pressure+this.bodyDent[i]);
          const support=Math.min(r.y,this.spec.mattressTopLocalY+this.spec.undersideThickness);
          p.y=Math.max(p.y,r.y-depth,support);
          if(w.belt)p.y=Math.min(p.y,r.y+.0015);
        }else if(curtain){
          // Keep the cloth outside the mattress and rigid berth end-jambs.
          const y=p.y+pivot[13];if(y<1.08)p.x=Math.max(p.x,-1.322-pivot[12]);
          p.x=clamp(p.x,-1.355-pivot[12],-.98-pivot[12]);p.z=clamp(p.z,-1.208-pivot[14],1.213-pivot[14]);
          p.x=Math.max(p.x,this.bedLimit[i]);
          const zReach=.002+(.003+.071*travel)*w.v;
          p.z=clamp(p.z,r.z-zReach,r.z+zReach);
          // The woven header is reinforced between its metal carriers.
          p.y=clamp(p.y,r.y-(.007+.055*w.v),r.y+.005+.064*w.v);
          if(i%this.nu>0){const left=this.points[i-1],gap=.24*(r.z-this.reference[i-1].z);p.z=Math.max(p.z,left.z+gap);}
        }else{
          // The service panel shuts over the looms. The fixed backplane and
          // its clips bound cable travel even when the panel is wide open.
          p.x=clamp(p.x,1.805-.065*door-pivot[12],2.042-pivot[12]);
          p.y=Math.max(p.y,.982-pivot[13]);
        }
      }
    }
    this.bounds.setFromPoints(this.points).expandByScalar(cable?(this.spec.radius??.009):.021);
    this.maxSpeed=0;for(let i=0;i<this.points.length;i++)this.maxSpeed=Math.max(this.maxSpeed,this.points[i].distanceToSquared(this.old[i]));
    this.maxSpeed=Math.sqrt(this.maxSpeed)/STEP;
  }
  skin(){
    for(let i=0;i<this.points.length;i++){
      if(this.grid)this.frame(this.points,i,this.frames[i]).multiply(this.restFrames[i]);
      else this.frames[i].setFromUnitVectors(this.directions[i],this.tangent(this.points,i,this.a));
      if(this.frames[i].w<0){const q=this.frames[i];q.set(-q.x,-q.y,-q.z,-q.w);}
    }
    for(const skin of this.skins){
      const {position,normal,toMesh,toNormal,bindings}=skin;
      for(let i=0;i<bindings.length;i++){
        const {indices,weights,offset,normal:n}=bindings[i];let x=0,y=0,z=0,w=0;this.a.set(0,0,0);
        for(let k=0;k<indices.length;k++){
          const j=indices[k],f=weights[k],q=this.frames[j];this.a.addScaledVector(this.points[j],f);
          x+=q.x*f;y+=q.y*f;z+=q.z*f;w+=q.w*f;
        }
        const q=this.rotation.set(x,y,z,w).normalize(),p=this.b.copy(offset).applyQuaternion(q).add(this.a).applyMatrix4(toMesh);
        position.setXYZ(i,p.x,p.y,p.z);
        if(n){p.copy(n).applyQuaternion(q).applyMatrix3(toNormal).normalize();normal.setXYZ(i,p.x,p.y,p.z);}
      }
      position.needsUpdate=true;if(normal)normal.needsUpdate=true;
    }
    if(!this.lastPose)this.lastPose=this.points.map(p=>p.clone());
    else this.lastPose.forEach((p,i)=>p.copy(this.points[i]));
    this.skinCount++;
  }
  sample(u,v=0){
    if(!this.grid){const i=Math.round(clamp(u)*(this.nu-1));return this.points[i].clone().applyMatrix4(this.matrix);}
    const [x,fx]=interval(this.grid.u,u),[y,fy]=interval(this.grid.v,v),i=y*this.nu+x;
    return this.points[i].clone().lerp(this.points[i+1],fx).lerp(this.a.copy(this.points[i+this.nu]).lerp(this.points[i+this.nu+1],fx),fy).applyMatrix4(this.matrix);
  }
  materialPoint(patch,out){
    return out.copy(this.points[patch.i]).multiplyScalar(patch.wi).addScaledVector(this.points[patch.j],patch.wj)
      .addScaledVector(this.points[patch.k],patch.wk).applyMatrix4(this.matrix);
  }
  bearWeight(point,newtons,radius){
    if(!this.bodyDent||newtons<=0)return;
    const local=this.a.copy(point).applyMatrix4(this.inverse),depth=Math.min(.025,newtons/740),area=radius*radius;
    for(let i=0;i<this.points.length;i++){
      const r2=this.points[i].distanceToSquared(local);
      if(!this.pins[i]&&r2<area*4)this.bodyDent[i]=Math.max(this.bodyDent[i],depth*Math.exp(-r2/area));
    }
  }
  impulse(worldPoint,worldVelocity,radius,indent=0){
    const origin=this.a.copy(worldPoint).applyMatrix4(this.inverse),vel=this.b.copy(worldVelocity).applyMatrix3(this.localDirection);
    let max=0;
    for(let i=0;i<this.points.length;i++){
      if(this.pins[i])continue;const distance2=this.points[i].distanceToSquared(origin);
      if(distance2>radius*radius*5)continue;
      const weight=Math.exp(-distance2/(radius*radius));this.old[i].addScaledVector(vel,-STEP*weight);max=Math.max(max,weight);
      if(indent&&this.bodyDent)this.bodyDent[i]=Math.max(this.bodyDent[i],indent*weight);
    }
    return max>.10;
  }
  beginGrip(worldPoint){
    const p=this.a.copy(worldPoint).applyMatrix4(this.inverse);let nearest=-1,distance=Infinity;
    for(let i=0;i<this.points.length;i++){
      if(this.pins[i])continue;const d=this.points[i].distanceToSquared(p);
      if(d<distance){nearest=i;distance=d;}
    }
    if(nearest<0||distance>.17*.17)return false;
    const origin=this.points[nearest],entries=[],weights=new Float32Array(this.points.length),anchor=this.weights[nearest],radius=this.grid ? .13 : .075;
    for(let i=0;i<this.points.length;i++){
      const w=this.weights[i];if(this.pins[i]||Math.abs(w.u-anchor.u)>.238||Math.abs(w.v-anchor.v)>.25)continue;
      const dist=this.points[i].distanceToSquared(origin),weight=Math.exp(-dist/(radius*radius*.55));
      if(weight>.06){weights[i]=weight;entries.push({index:i,home:this.points[i].clone(),weight});}
    }
    this.grip={entries,weights,delta:zero()};return true;
  }
  pressQuilt(worldPoint){
    const p=this.a.copy(worldPoint).applyMatrix4(this.inverse);
    const weights=this.points.map((node,i)=>this.pins[i]?0:Math.exp(-node.distanceToSquared(p)/(.128*.128)));
    if(Math.max(...weights)<.15)return false;this.press={age:0,weights};return true;
  }
  contact(worldPoint,oldWorld,radius,hit){
    const p=this.query.copy(worldPoint).applyMatrix4(this.inverse);
    if(this.bounds.distanceToPoint(p)>radius+.035)return;
    const old=this.prior.copy(oldWorld).applyMatrix4(this.inverse);
    if(!this.grid){
      const coverage=radius+(this.spec.radius??.009);
      for(let i=0;i<this.nu-1;i++){
        const a=this.points[i],d=this.a.subVectors(this.points[i+1],a);
        const t=clamp(this.b.subVectors(p,a).dot(d)/Math.max(1e-10,d.lengthSq()));
        const q=this.hit.copy(a).addScaledVector(d,t),dist=p.distanceTo(q),pen=coverage-dist;
        if(pen<=hit.pen||dist<1e-6)continue;
        this.hitNormal.subVectors(p,q).multiplyScalar(1/dist);this.setHit(hit,pen,q,this.hitNormal,i,i+1,i,1-t,t,0);
      }
      return;
    }
    const cells=this.grid,ref=this.reference,quilt=this.kind==='quilt';
    const u=quilt?(p.x-ref[0].x)/(ref[this.nu-1].x-ref[0].x):(p.z-ref[0].z)/(ref[this.nu-1].z-ref[0].z);
    const v=quilt?(p.z-ref[0].z)/(ref.at(-1).z-ref[0].z):(p.y-ref[0].y)/(ref.at(-1).y-ref[0].y);
    const marginU=(quilt?.065:.20)+radius,marginV=(quilt?.06:.16)+radius;
    const du=marginU/Math.abs(quilt?ref[this.nu-1].x-ref[0].x:ref[this.nu-1].z-ref[0].z);
    const dv=marginV/Math.abs(quilt?ref.at(-1).z-ref[0].z:ref.at(-1).y-ref[0].y);
    const x0=interval(cells.u,u-du)[0],x1=interval(cells.u,u+du)[0],y0=interval(cells.v,v-dv)[0],y1=interval(cells.v,v+dv)[0];
    for(let y=y0;y<=y1;y++)for(let x=x0;x<=x1;x++){
      const i=y*this.nu+x,b=i+1,c=i+this.nu;
      this.triangleContact(i,b,c,p,old,radius,hit);this.triangleContact(c,b,c+1,p,old,radius,hit);
    }
  }
  triangleContact(i,j,k,p,old,radius,hit){
    const a=this.points[i],b=this.points[j],c=this.points[k];
    const tri=this.tri.set(a,b,c),q=tri.closestPointToPoint(p,this.hit),n=this.hitNormal.subVectors(p,q);
    const dist=n.length(),thickness=this.kind==='quilt'?.006:.0017;
    let pen=radius+thickness-dist;
    if(dist>1e-7)n.multiplyScalar(1/dist);else tri.getNormal(n);
    const face=tri.getNormal(this.a),before=face.dot(this.b.subVectors(old,a)),now=face.dot(this.b.subVectors(p,a));
    if(before*now<0&&Math.abs(now-before)>1e-8){
      const crossing=this.b.copy(old).lerp(p,before/(before-now));
      if(tri.containsPoint(crossing)){pen=radius+thickness+Math.abs(now);q.copy(crossing);n.copy(face).multiplyScalar(Math.sign(before));}
    }
    if(pen>hit.pen){const weight=tri.getBarycoord(q,this.c);if(weight)this.setHit(hit,pen,q,n,i,j,k,weight.x,weight.y,weight.z);}
  }
  setHit(hit,pen,point,normal,i,j,k,wi,wj,wk){
    hit.pen=pen;hit.fabric=this;hit.position.copy(point).applyMatrix4(this.matrix);hit.normal.copy(normal).transformDirection(this.matrix);
    hit.cageI=i;hit.cageJ=j;hit.cageK=k;hit.wi=wi;hit.wj=wj;hit.wk=wk;
  }
}

export class Furnishings {
  constructor(data,scene){
    this.parts=data.parts.filter(spec=>spec.grid||spec.restPoints).map(spec=>new FabricPart(spec,scene));
    this.part('curtain').berth=this.part('quilt');
    this.accumulator=0;this.rail=0;this.cover=0;this.occupied=0;
    this.kick=zero();this.gripped=null;this.clock=0;this.frustum=new T.Frustum();this.cameraMatrix=new T.Matrix4();
  }
  advance(dt,time,force,fan,curtain,cabinet,occupied){
    const elapsed=Math.min(Math.max(0,dt),.12);this.accumulator+=elapsed;this.clock+=elapsed;
    const steps=Math.floor((this.accumulator+1e-9)/STEP);if(!steps)return;
    const rail0=this.rail,door0=this.cover,doorSpeed=clamp((cabinet-door0)/(steps*STEP),-5,5);
    for(let i=1;i<=steps;i++){
      const f=i/steps,rail=rail0+(curtain-rail0)*f,door=door0+(cabinet-door0)*f;
      this.occupied+=(Number(occupied)-this.occupied)*(1-Math.exp(-STEP*8));
      for(const p of this.parts)p.step(force,time-(steps-i)*STEP,fan,rail,door,doorSpeed,this.occupied);
    }
    this.rail=curtain;this.cover=cabinet;this.accumulator=Math.max(0,this.accumulator-steps*STEP);
  }
  deform(camera,view='window'){
    if(camera)this.frustum.setFromProjectionMatrix(this.cameraMatrix.multiplyMatrices(camera.projectionMatrix,camera.matrixWorldInverse));
    for(const p of this.parts){
      // Keep the collision cages live at 90 Hz everywhere. A textile outside
      // the passenger's field of view only refreshes occasionally for probes.
      // Turning or walking into view immediately restores full-cadence skinning.
      const visible=!camera||(view==='window'&&this.frustum.intersectsBox(p.worldEnvelope)&&(p.kind!=='service'||this.cover>.012));
      if(!visible&&this.clock-p.lastSkin<.27)continue;
      const tolerance=visible ? .00015 : .0010;
      if(p.lastPose&&!p.points.some((q,i)=>p.lastPose[i].distanceToSquared(q)>tolerance*tolerance))continue;
      p.skin();p.lastSkin=this.clock;
    }
  }
  part(kind){return this.parts.find(p=>p.id===kind||p.kind===kind);}
  target(kind){const p=this.part(kind);return p?.sample(p.kind==='quilt'?.76:.50,p.kind==='quilt'?.88:.78);}
  touch(kind,point){
    const part=this.part(kind);if(!part||part.kind==='service'&&this.cover<.6)return false;
    if(part.kind==='quilt')return part.pressQuilt(point??this.target(kind));
    const kick=part.kind==='curtain'?[.91,.19,.15]:[-1.05,.27,.10];
    return part.impulse(point??this.target(kind),this.kick.fromArray(kick),part.kind==='service'?.104:.225);
  }
  grip(hit){
    this.release();const p=this.part(hit.id??hit.kind);
    if(!p||p.kind==='service'&&this.cover<.6||!p.beginGrip(hit.point))return false;
    this.gripped=p;return true;
  }
  pull(delta){
    if(!this.gripped)return false;
    const p=this.gripped,limit=p.kind==='service'?.12:p.kind==='quilt'?.145:.19;
    p.grip.delta.copy(delta).applyMatrix3(p.localDirection).clampLength(0,limit);return true;
  }
  release(){if(!this.gripped)return false;this.gripped.grip=null;this.gripped=null;return true;}
  contact(point,previous,radius,hit){for(const p of this.parts)p.contact(point,previous,radius,hit);}
  velocityAt(hit,out){
    const part=hit.fabric;out.set(0,0,0);if(!part||hit.cageI===undefined)return out;
    const {points,old}=part;
    out.addScaledVector(part.a.subVectors(points[hit.cageI],old[hit.cageI]),hit.wi);
    out.addScaledVector(part.a.subVectors(points[hit.cageJ],old[hit.cageJ]),hit.wj);
    out.addScaledVector(part.a.subVectors(points[hit.cageK],old[hit.cageK]),hit.wk);
    return out.multiplyScalar(1/STEP).applyMatrix3(part.worldDirection);
  }
  react(hit,impulse){
    if(!hit.fabric||impulse<.0005)return;
    const p=hit.fabric;this.kick.copy(hit.normal).multiplyScalar(-Math.min(.74,impulse*(p.kind==='service'?3.5:2.4)));
    const indent=p.kind==='quilt'&&hit.normal.y>.25?Math.min(.025,.060*impulse*hit.normal.y):0;
    p.impulse(hit.position,this.kick,p.kind==='service' ? .072 : .145,indent);
  }
}
