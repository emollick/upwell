import * as T from 'three';
import { GLTFLoader } from './assets/vendor/loaders/GLTFLoader.js';
import {MeshoptDecoder} from './assets/vendor/meshopt.js';
import { smooth } from './journey.js';
import { CaptureCollar } from './docking.js';

const axes={x:new T.Vector3(1,0,0),y:new T.Vector3(0,1,0),z:new T.Vector3(0,0,1)};

function captureLeads(){
  const root=new T.Group(),round=new T.CylinderGeometry(1,1,1,9);
  const steel=new T.MeshStandardMaterial({color:0x85949a,metalness:.74,roughness:.33});
  const alloy=new T.MeshStandardMaterial({color:0xbbc0b9,metalness:.46,roughness:.4});
  const dark=new T.MeshStandardMaterial({color:0x374750,metalness:.52,roughness:.36});
  const glow=new T.MeshBasicMaterial({color:0xffb979,toneMapped:false});
  const struts=[],cross=[],sensors=[],lamps=[];
  const from=new T.Vector3(),to=new T.Vector3(),delta=new T.Vector3(),mid=new T.Vector3(),q=new T.Quaternion(),scale=new T.Vector3();
  function beam(list,a,b,r){
    from.fromArray(a);to.fromArray(b);delta.copy(to).sub(from);const length=delta.length();
    mid.copy(from).lerp(to,.5);q.setFromUnitVectors(axes.y,delta.normalize());
    list.push(new T.Matrix4().compose(mid,q,scale.set(r,length,r)));
  }
  for(const side of [-1,1]){
    const cx=side*6.85,cz=-10.95;
    for(let i=0;i<20;i++){
      const y=-168+i*8.25, w=.14+.43*i/19,w2=.14+.43*(i+1)/19;
      const corners=[[cx-w,y,cz],[cx+w,y,cz],[cx,y,cz-w*1.5]];
      const next=[[cx-w2,y+8.25,cz],[cx+w2,y+8.25,cz],[cx,y+8.25,cz-w2*1.5]];
      for(let k=0;k<3;k++){
        beam(struts,corners[k],next[k],.053+.016*i/19);
        beam(cross,corners[k],corners[(k+1)%3],.037);beam(cross,corners[k],next[(k+1)%3],.030);
      }
      if(i%2===0){
        beam(sensors,[cx,y-.16,cz],[cx,y+.16,cz],.29);
        beam(lamps,[cx,y+.16,cz],[cx,y+.23,cz],.28);
      }
    }
  }
  for(const [list,material] of [[struts,alloy],[cross,steel],[sensors,dark],[lamps,glow]]){
    const mesh=new T.InstancedMesh(round,material,list.length);list.forEach((m,i)=>mesh.setMatrixAt(i,m));
    mesh.castShadow=material!==glow;mesh.receiveShadow=material!==glow;mesh.computeBoundingSphere();root.add(mesh);
  }
  root.name='Berth lead-in trusses and acquisition heads';return root;
}
function fitDisplay(root,spec){
  const n=root.getObjectByName(spec.display);if(!n)return null;
  const c=document.createElement('canvas');c.width=512;c.height=224;const ctx=c.getContext('2d');
  const tex=new T.CanvasTexture(c);tex.flipY=false;tex.colorSpace=T.SRGBColorSpace;let active=false;
  n.traverse(m=>{
    if(!m.isMesh||!/Display/.test(m.material.name))return;
    m.geometry=m.geometry.clone();const uv=m.geometry.attributes.uv;if(!uv)return;
    let u0=1,u1=0,v0=1,v1=0;
    for(let i=0;i<uv.count;i++){u0=Math.min(u0,uv.getX(i));u1=Math.max(u1,uv.getX(i));v0=Math.min(v0,uv.getY(i));v1=Math.max(v1,uv.getY(i));}
    for(let i=0;i<uv.count;i++)uv.setXY(i,(uv.getX(i)-u0)/(u1-u0||1),(uv.getY(i)-v0)/(v1-v0||1));
    uv.needsUpdate=true;m.material=new T.MeshBasicMaterial({map:tex,toneMapped:false});active=true;
  });
  if(!active)return null;
  return (id,m,coupling)=>{
    const ground=id==='anchor';ctx.fillStyle='#061317';ctx.fillRect(0,0,512,224);
    ctx.fillStyle='#9bc7c1';ctx.font='20px monospace';ctx.fillText(ground?'PELAGIC  /  ASCENT CONTROL':'ASTER REACH  /  BERTH 03',19,35);
    ctx.fillRect(19,49,474,2);ctx.fillStyle='#f5f3d9';ctx.font='bold 39px monospace';
    const line=ground?(m.seconds<3?'BRIDGE SECURE':m.seconds<9?'RELEASING':'GUIDE CLEAR'):(m.remainingMeters>6?'ACQUIRING':coupling.status.toUpperCase());
    ctx.fillText(line,19,114);ctx.font='23px monospace';ctx.fillStyle='#eab27e';
    ctx.fillText(ground?'CAR 07   /   UPBOUND':Math.round(m.remainingMeters)+' M   /   CAR 07',20,178);tex.needsUpdate=true;
  };
}

function setActuator(motion, value) {
  const { node, kind, axis, amount, origin, rotation } = motion;
  if (kind === 'translate') node.position.copy(origin).addScaledVector(axes[axis],amount*value);
  else node.quaternion.copy(rotation).multiply(motion.turn.setFromAxisAngle(axes[axis],T.MathUtils.degToRad(amount*value)));
}

export async function loadTerminals(exteriorRoot) {
  const base='./assets/terminals/';
  const response=await fetch(base+'layout.json');
  if(!response.ok) throw Error('The terminal survey could not be loaded.');
  const data=await response.json(), loader=new GLTFLoader().setMeshoptDecoder(MeshoptDecoder);
  const pairs=await Promise.all(['anchor','aster'].map(async id=>{
    const spec=data.stations[id];
    if(id==='aster'){
      // The compact gallery is a reflecting enclosure. The local point
      // approximation stands in for a recessed, louvered area luminaire.
      // Its direct contribution at the booth glazing is correspondingly small.
      for(const light of spec.lights){
        const factor=light.id.includes('booth')?.19:light.id.includes('gallery')?.16:
          light.id.includes('underdeck')?.56:light.id.includes('capture_key')?.72:.85;
        light.power*=factor;
      }
    }
    const {scene:root}=await loader.loadAsync(base+spec.file);
    const actions=(spec.motions||[]).map(m=>{
      const node=root.getObjectByName(m.node);
      if(!node)throw Error('Missing terminal mechanism '+m.node);
      return {...m,node,origin:node.position.clone(),rotation:node.quaternion.clone(),turn:new T.Quaternion()};
    });
    root.traverse(node=>{
      if(!node.isMesh)return;
      const m=node.material;
      node.castShadow=!m.transparent && !/glass|screen|light_strip|glow|stencil/i.test(m.name);
      node.receiveShadow=!m.transparent;
      if(m.map)m.map.anisotropy=4;
      if(node.castShadow)m.shadowSide=T.DoubleSide;
    });
    if(id==='aster')root.add(captureLeads());
    const display=fitDisplay(root,spec);exteriorRoot.add(root);
    return [id,{root,actions,spec,display,lastDisplay:-1,bridge:1}];
  }));
  const bays=Object.fromEntries(pairs);
  bays.aster.coupling=new CaptureCollar();
  return {
    bays,
    update(metrics,time,clampTurns){
      const sec=metrics.seconds,alt=metrics.km*1000,toGo=metrics.remainingMeters;
      const aster=bays.aster, coupling=aster.coupling;
      const skipped=aster.lastRoute===undefined||Math.abs(sec-aster.lastRoute)>1.5||sec<aster.lastRoute-.01;
      coupling.update(clampTurns,sec>=360,clampDelta(time,aster.lastTime),skipped);
      aster.bridge=coupling.bridgeClearance;
      aster.lastTime=time;aster.lastRoute=sec;
      bays.anchor.root.visible=alt<2200;
      bays.anchor.root.position.y=-alt;
      bays.aster.root.visible=toGo<2000;
      bays.aster.root.position.y=toGo;
      for(const [id,bay] of pairs){
        if(!bay.root.visible)continue;
        const outgoing=id==='anchor';
        const softOpen=.18*(1-coupling.travel);
        const disengaged=outgoing?smooth(2.0,8.8,sec):softOpen+(1-softOpen)*(1-smooth(355,360,sec));
        if(time-bay.lastDisplay>.35||time<bay.lastDisplay){bay.display?.(id,metrics,coupling);bay.lastDisplay=time;}
        for(const action of bay.actions) {
          let value=disengaged;
          if(action.channel==='bridge')value=outgoing?smooth(.7,7.3,sec):bay.bridge;
          if(action.channel==='shutter')value=outgoing?smooth(.8,10.6,sec):smooth(320,343,sec);
          if(action.channel==='drum')value=(outgoing?Math.min(100,alt):Math.min(100,toGo))*.08+(outgoing?0:coupling.travel*.72);
          if(action.channel==='beacon')value=time*.46;
          if(action.channel==='clamp')value=outgoing?disengaged:1-clampTurns/3;
          setActuator(action,value);
        }
      }
    },
  };
}
function clampDelta(time,previous){return previous===undefined?.016:Math.min(.2,Math.max(0,time-previous));}
