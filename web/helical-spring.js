import * as T from 'three';

// Change the pitch of Blender's helix without stretching its wire. Bind
// vertices to the surveyed centreline and rotate each wire cross section to
// the new tangent. The two captive end rings remain circular.
export class HelicalSpring {
  constructor(node,spec) {
    this.node=node;this.spec=spec;
    const sign=-spec.fixedEndSign,turns=spec.turns??(sign<0?7:5);
    this.rate=2*Math.PI*turns;this.radius=spec.radius??.0092;this.length=spec.restLength;
    this.restPitch=Math.atan2(spec.restLength,this.radius*this.rate);
    this.parts=[];this.q=new T.Quaternion();this.point=new T.Vector3();this.offset=new T.Vector3();
    const L=spec.restLength,r=this.radius,rate=this.rate;
    node.updateWorldMatrix(true,true);const inv=node.matrixWorld.clone().invert();
    node.traverse(mesh=>{
      if(!mesh.isMesh)return;
      const g=mesh.geometry.clone();mesh.geometry=g;mesh.frustumCulled=false;
      const toSpring=inv.clone().multiply(mesh.matrixWorld),toMesh=toSpring.clone().invert();
      const fromN=new T.Matrix3().getNormalMatrix(toSpring),toN=new T.Matrix3().getNormalMatrix(toMesh);
      const ring=/Anodized_Frame/.test(mesh.material.name);
      const pos=g.attributes.position,norm=g.attributes.normal,bindings=[];
      for(let i=0;i<pos.count;i++){
        const p=new T.Vector3().fromBufferAttribute(pos,i).applyMatrix4(toSpring);
        const n=norm?new T.Vector3().fromBufferAttribute(norm,i).applyMatrix3(fromN).normalize():null;
        if(ring){bindings.push({ring:true,t:sign*p.y>L*.5?1:0,p,n});continue;}
        let t=T.MathUtils.clamp(sign*p.y/L,0,1);
        for(let j=0;j<5;j++){
          const c=Math.cos(rate*t),s=Math.sin(rate*t);
          const x=r*c-p.x,y=sign*L*t-p.y,z=-sign*r*s-p.z;
          const dx=-r*rate*s,dy=sign*L,dz=-sign*r*rate*c;
          const second=dx*dx+dy*dy+dz*dz-x*r*rate*rate*c+z*sign*r*rate*rate*s;
          if(Math.abs(second)<1e-9)break;
          t=T.MathUtils.clamp(t-(x*dx+y*dy+z*dz)/second,0,1);
        }
        const radial=new T.Vector3(Math.cos(rate*t),0,-sign*Math.sin(rate*t));
        const center=radial.clone().multiplyScalar(r);center.y=sign*L*t;
        bindings.push({t,radial,offset:p.sub(center),n});
      }
      pos.setUsage(T.DynamicDrawUsage);if(norm)norm.setUsage(T.DynamicDrawUsage);
      this.parts.push({g,bindings,toMesh,toN});
    });
    this.sign=sign;
  }
  setLength(length){
    length=Math.max(.008,length);
    if(Math.abs(this.length-length)<.000012)return;
    this.length=length;
    const pitch=Math.atan2(length,this.radius*this.rate)-this.restPitch;
    for(const {g,bindings,toMesh,toN} of this.parts){
      const pos=g.attributes.position,norm=g.attributes.normal;
      for(let i=0;i<bindings.length;i++){
        const b=bindings[i],p=this.point;
        if(b.ring){
          p.copy(b.p);p.y+=this.sign*(length-this.spec.restLength)*b.t;
        }else{
          this.q.setFromAxisAngle(b.radial,pitch);
          p.copy(b.radial).multiplyScalar(this.radius);p.y=this.sign*length*b.t;
          p.add(this.offset.copy(b.offset).applyQuaternion(this.q));
        }
        p.applyMatrix4(toMesh);pos.setXYZ(i,p.x,p.y,p.z);
        if(norm&&b.n){
          p.copy(b.n);if(!b.ring)p.applyQuaternion(this.q);
          p.applyMatrix3(toN).normalize();norm.setXYZ(i,p.x,p.y,p.z);
        }
      }
      pos.needsUpdate=true;if(norm)norm.needsUpdate=true;
      g.computeBoundingBox();g.computeBoundingSphere();
    }
  }
}
