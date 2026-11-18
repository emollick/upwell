import * as T from 'three';
import {GLTFLoader} from './assets/vendor/loaders/GLTFLoader.js';
import {MeshoptDecoder} from './assets/vendor/meshopt.js';
import {smooth} from './journey.js';
import {guideFinishes,distantGuide} from './guide-finish.js';

const mat=(color,metalness,roughness)=>new T.MeshStandardMaterial({color,metalness,roughness});

function instancedAssembly(template,parent,total,period){
  template.updateWorldMatrix(true,true);
  const inverse=template.matrixWorld.clone().invert(),shift=new T.Matrix4(),m=new T.Matrix4();
  const group=new T.Group();parent.add(group);
  template.traverse(part=>{
    if(!part.isMesh)return;
    const local=inverse.clone().multiply(part.matrixWorld);
    const batch=new T.InstancedMesh(part.geometry,part.material,total);
    batch.castShadow=!part.material.transparent&&!part.material.emissive?.getHex();batch.receiveShadow=true;
    for(let i=0;i<total;i++){shift.makeTranslation(0,(i-(total-1)/2)*period,0);m.multiplyMatrices(shift,local);batch.setMatrixAt(i,m);}
    batch.computeBoundingSphere();group.add(batch);
  });
  return group;
}
export async function loadGuideway(parent){
  const folder='./assets/guideway/';
  const loader=new GLTFLoader().setMeshoptDecoder(MeshoptDecoder);
  const [response,model,journals]=await Promise.all([fetch(folder+'layout.json'),loader.loadAsync(folder+'guideway.glb'),loader.loadAsync(folder+'journal-caps.glb')]);
  if(!response.ok)throw Error('The guideway alignment could not be loaded.');
  const layout=await response.json(),root=model.scene;
  const span=root.getObjectByName('load_span'),splice=root.getObjectByName('splice'),bogie=root.getObjectByName('bogie');
  if(!span||!splice||!bogie)throw Error('The cable assembly is incomplete.');
  const tracks=layout.placements.map(p=>({x:p.position[0],y:p.position[1],z:p.position[2],yaw:0,bogie:p.id!=='counterline'}));
  const pitch=layout.repeatHeight,amount=matchMedia('(pointer: coarse)').matches?7:11,spanLength=pitch*amount/2;
  const finish=guideFinishes();finish.mountSpan(span);
  journals.scene.traverse(part=>{if(part.isMesh){part.castShadow=true;part.receiveShadow=true;}});
  const horizon=distantGuide(spanLength,[mat('#30383a',.42,.45),mat('#848c90',.84,.38),mat('#343b40',.41,.57),mat('#a4522a',.12,.64),mat('#337083',.18,.59)]);
  const driven=[],bogies=[];
  for(const track of tracks){
    const block=new T.Group();block.name=track.bogie?'Primary load bundle':'Counterline load bundle';
    block.position.set(track.x,0,track.z);block.rotation.y=track.yaw;parent.add(block);
    const skin=instancedAssembly(span,block,amount,pitch),collars=instancedAssembly(splice,block,7,layout.splicePeriod);
    const distant=horizon.clone();block.add(distant);
    const marker=new T.InstancedMesh(new T.CylinderGeometry(.077,.077,.13,10),
      new T.MeshBasicMaterial({color:0xe9b989,toneMapped:false}),28);
    for(let i=0;i<28;i++)marker.setMatrixAt(i,new T.Matrix4().makeTranslation(.09,(i-13.5)*79,.49));
    marker.computeBoundingSphere();block.add(marker);
    driven.push({skin,collars,distant,marker,track,block});
    if(track.bogie){
      const fixed=bogie.clone(true);fixed.position.set(0,track.y,0);block.add(fixed);
      fixed.traverse(n=>{if(n.name.startsWith('roller_')&&!n.parent?.name.startsWith('roller_')){
        const spec=(layout.rollers??[]).find(v=>(v.node??v.name)===n.name)??{};
        bogies.push({node:n,rest:n.quaternion.clone(),radius:spec.radius??.21,sign:spec.sign??spec.direction??1,spin:new T.Quaternion()});
      }});
      fixed.add(journals.scene.clone(true));
    }
  }
  const serviceLamp=new T.SpotLight(0xe2f4ff,7.5,6.5,.70,.6,2);
  serviceLamp.position.set(-2.46,2.13,4.18);serviceLamp.target.position.set(-3.42,1.42,3.58);
  parent.add(serviceLamp,serviceLamp.target);
  const spinAxis=new T.Vector3(0,0,1);
  serviceLamp.intensity=0;serviceLamp.layers.enable(1);
  for(const r of bogies)r.cover=finish.mountWheel(r.node,r.radius);
  let metres=0,lastTime,lastRoute=0,lastAltitude=0;
  return {counter:tracks[2],layout,serviceLamp,get distanceTravelled(){return metres;},update(metrics,time){
    const clockDelta=lastTime===undefined?0:Math.max(0,Math.min(1/3,time-lastTime));
    const seek=lastTime===undefined||Math.abs(metrics.seconds-lastRoute)>1.5||metrics.seconds<lastRoute-.002;
    metres=metrics.km*1000;
    const speed=seek||clockDelta<.001?0:Math.abs(metres-lastAltitude)/clockDelta;
    finish.shutter.value=Math.min(79,speed*Math.min(1/30,clockDelta*.5));
    lastTime=time;lastRoute=metrics.seconds;lastAltitude=metres;
    const wind=(1-smooth(7,15,metrics.km))*smooth(.035,.8,metrics.km);
    for(const {skin,collars,distant,marker,track,block} of driven){
      distant.position.y=skin.position.y=-(metres%pitch);collars.position.y=-(metres%layout.splicePeriod);marker.position.y=-(metres%79);
      if(!track.bogie){block.position.x=track.x+wind*.052*Math.sin(time*.51);block.position.z=track.z+wind*.039*Math.sin(time*.38+.9);}
    }
    for(const r of bogies){
      r.node.quaternion.copy(r.rest).multiply(r.spin.setFromAxisAngle(spinAxis,r.sign*(metres/r.radius%(2*Math.PI))));
      r.cover.visible=finish.shutter.value/r.radius>.24;
    }
  }};
}
