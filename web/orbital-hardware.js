import * as T from 'three';
import {GLTFLoader} from './assets/vendor/loaders/GLTFLoader.js';
import {MeshoptDecoder} from './assets/vendor/meshopt.js';
import {mountHabitatMembers} from './habitat-members.js';

const base='./assets/orbital/';
const indoorFinishes=new Set(['Aster_Soil','Aster_Water','Aster_Timber','Aster_Building','Aster_Roof',
  'Aster_Greenhouse','Aster_TowerGlass','Aster_PaleStone','Aster_WindowBank','Aster_LitWindow','Aster_Liner']);

// A daylight collector illuminates each valley from off-axis. Direct solar
// lighting and exterior probes have no line of sight through occupied decks.
function valleyIrradiance(mat,spec,flow){
  const block=`
    vec3 q=vValleyPosition;
    float a=atan(q.x,q.z),sector=floor(a/2.0943951+.5)*2.0943951;
    vec3 radial=vec3(sin(sector),0.,cos(sector)),side=vec3(cos(sector),0.,-sin(sector));
    vec3 key=normalize(-radial*.79+side*.64+vec3(0.,-.41,0.));
    vec3 n=normalize(vValleyNormal);
    float sun=max(0.,dot(n,key));
    float wash=.78+.15*sin(q.y*.21+.64)+.059*cos(q.y*.49+a*2.);
    float roof=clamp(dot(n,-normalize(vec3(q.x,0.,q.z))),0.,1.);
    float gate=.99-.17*smoothstep(6.3,7.23,length(q.xz))*(1.-roof);
    vec3 received=diffuseColor.rgb*(vec3(.29,.34,.355)+vec3(.87,.75,.55)*sun*wash)*gate;
    ${spec.name==='Aster_Soil'?`float stream=.146*sin(q.y*.31+.26)+.055*sin(q.y*.72-.48),angs=a-sector-stream;
      received*=1.-.13*exp(-abs(angs-.18)*50.)-.12*exp(-abs(abs(angs)-.060)*53.);`:''}
    ${spec.name==='Aster_Water'?`float along=q.y*80.;float across=(a-sector)*577.6;
      float crest=across*1.7+along*.53,wind=across*.71-along*1.21;
      float cap=sin(crest+valleyTime*2.7)*sin(wind+valleyTime*.8);
      cap*=1.-smoothstep(1.,3.14,max(fwidth(crest),fwidth(wind)));
      float wakes=.56+.20*sin(along*.095+across*.13)+.19*cap;
      received=mix(vec3(.018,.064,.069),vec3(.112,.212,.196),wakes*.85);
      received+=vec3(.021,.034,.030)*pow(max(cap,0.),4.);
    `:''}
    ${spec.name==='Aster_Greenhouse'||spec.name==='Aster_WindowBank'||spec.name==='Aster_TowerGlass'?`
      received+=vec3(.030,.051,.053)*(.45+.55*roof);
    `:''}
    ${spec.name==='Aster_LitWindow'?`
      received=vec3(.76,.54,.28)*(.83+.12*cos(q.y*8.));
    `:''}
    ${spec.name==='Aster_Liner'?`received=mix(vec3(.087,.119,.133),vec3(.225,.243,.223),smoothstep(1.2,7.3,length(q.xz)));
      received*=.95+.05*cos(a*48.);`:''}
    outgoingLight=received;`;
  mat.onBeforeCompile=shader=>{
    shader.uniforms.valleyTime=flow;
    shader.vertexShader='varying vec3 vValleyPosition;varying vec3 vValleyNormal;\n'+shader.vertexShader
      .replace('#include <begin_vertex>','#include <begin_vertex>\n vValleyPosition=position;vValleyNormal=normal;');
    shader.fragmentShader='varying vec3 vValleyPosition;varying vec3 vValleyNormal;uniform float valleyTime;\n'+shader.fragmentShader
      .replace('#include <opaque_fragment>',block+'\n#include <opaque_fragment>');
  };
  mat.customProgramCacheKey=()=> 'valley-collector-'+spec.name;
}

function take(model,name){
  const node=model.getObjectByName(name);
  if(!node)throw Error('Missing orbital assembly '+name);
  node.removeFromParent();return node;
}

function carMark(id){
  const canvas=document.createElement('canvas');canvas.width=768;canvas.height=192;
  const ctx=canvas.getContext('2d');ctx.fillStyle='#c6c8bf';ctx.fillRect(0,0,768,192);
  ctx.fillStyle='#a95336';ctx.fillRect(0,0,17,192);ctx.fillRect(685,25,52,17);
  ctx.fillStyle='#29363a';ctx.font='600 88px Arial';ctx.fillText('TL  /  '+id,43,108);
  ctx.font='25px monospace';ctx.fillText('COUNTERLINE   ·   TETHER AUTHORITY',45,157);
  const map=new T.CanvasTexture(canvas);map.colorSpace=T.SRGBColorSpace;map.anisotropy=4;
  return new T.MeshStandardMaterial({map,metalness:.16,roughness:.63});
}

// Aster's sun collectors redirect daylight into the valleys. The sunlit
// land and pressure shell also illuminate adjoining structure. Their angular
// extent is large relative to a hull plate, so a diffuse wrap approximates
// that local reflection without placing moving point lights kilometres away.
function localIrradiance(material,gain){
  if(!gain)return;
  material.onBeforeCompile=shader=>{
    shader.uniforms.asterBounce={value:gain};
    shader.fragmentShader='uniform float asterBounce;\n'+shader.fragmentShader.replace('#include <lights_fragment_end>',
      `#include <lights_fragment_end>
       vec3 habitatNormal=inverseTransformDirection(geometryNormal,viewMatrix);
       float broad=0.29+0.41*max(0.,dot(habitatNormal,normalize(vec3(.47,.31,.82))))
                       +0.30*(.5-.5*habitatNormal.y);
       reflectedLight.indirectDiffuse+=diffuseColor.rgb*broad*asterBounce*vec3(.81,.90,1.0);`);
  };
  material.customProgramCacheKey=()=> 'upwell-orbital-reflected-daylight';
}

export async function loadOrbitalHardware(terminal,traffic){
  const range=terminal.bays.aster.root;
  const loader=new GLTFLoader().setMeshoptDecoder(MeshoptDecoder);
  const [colony,car,receiver,finishes,memberSurvey,workFleet]=await Promise.all([
    loader.loadAsync(base+'AsterReach.glb'),loader.loadAsync(base+'CounterCar.glb'),loader.loadAsync(base+'Receiver.glb'),
    fetch(base+'finishes.json').then(r=>{if(!r.ok)throw Error('Orbital finish survey unavailable');return r.json();}),
    fetch(base+'members.bin').then(r=>{if(!r.ok)throw Error('Orbital beam survey unavailable');return r.arrayBuffer();}),
    loader.loadAsync(base+'CounterFleet.glb')
  ]);
  const survey=new Map(finishes.materials.map(record=>[record.name,record]));
  const flow={value:0};
  for(const model of [colony.scene,car.scene,receiver.scene,workFleet.scene]){
    const seen=new Set();
    model.traverse(node=>{
      if(!node.isMesh)return;
      const mat=node.material,spec=survey.get(mat.name);if(!spec||seen.has(mat))return;seen.add(mat);
      mat.color.set(spec.color);mat.metalness=spec.metal;mat.roughness=spec.rough;
      mat.emissive.set(spec.emit);mat.emissiveIntensity=spec.gain;
      if(mat.map)mat.map.anisotropy=8;
      if(model===colony.scene&&indoorFinishes.has(spec.name))valleyIrradiance(mat,spec,flow);
      else if(spec.alpha<1){mat.transparent=true;mat.opacity=spec.alpha;mat.depthWrite=false;mat.side=T.FrontSide;}
      else if(spec.gain===0){
        const colonyBounce=spec.name==='Aster_Mirror'?.135:spec.name==='Aster_Radiator'?.23:
          spec.name==='Aster_Frame'?.34:.43;
        localIrradiance(mat,model===colony.scene?colonyBounce:model===receiver.scene?.16:.25);
      }
    });
  }
  const habitat=new T.Group(),rotor=new T.Group(),train=take(colony.scene,'maintenance_train');
  rotor.add(take(colony.scene,'rotating_habitat'),train);
  mountHabitatMembers(rotor,take(colony.scene,'pressure_members'),memberSurvey,survey);
  habitat.add(rotor,take(colony.scene,'stationary_axle'));
  habitat.name='Aster Reach rotating valleys';habitat.rotation.set(.36,.3,-1.17);
  // Entrance pupil on the fixed spindle. The edge of the window and the
  // pointing reference are independent of the valley bearings.
  const radial=new T.Vector3(Math.sin(-.70),0,Math.cos(-.70)),axis=new T.Vector3(0,1,0);
  const origin=axis.clone().multiplyScalar(-16.1).addScaledVector(radial,1.58);
  const galleryForward=axis.clone().multiplyScalar(.888).addScaledVector(radial,.46).normalize();
  const galleryUp=axis.clone().multiplyScalar(.46).addScaledVector(radial,-.888).normalize();
  const galleryAim=new T.Vector3();
  function valleyPose(camera){
    habitat.updateWorldMatrix(true,false);
    camera.position.copy(origin).applyMatrix4(habitat.matrixWorld);
    camera.up.copy(galleryUp).transformDirection(habitat.matrixWorld);
    galleryAim.copy(galleryForward).transformDirection(habitat.matrixWorld).add(camera.position);
    camera.lookAt(galleryAim);
  }
  const other=new T.Group(),wheel=take(car.scene,'counter_wheels');
  const passenger=take(car.scene,'counter_body'),common=take(workFleet.scene,'counter_common_bogie');
  const freight=take(workFleet.scene,'counter_freight_carrier'),tender=take(workFleet.scene,'counter_inspection_tender');
  other.name='Downbound climber';other.add(passenger,common,freight,tender);
  const wheels=[];
  for(const y of [-2.50,2.46])for(const z of [-.50,.47]){
    const assembly=wheel.clone(true);assembly.position.set(-1.28,y,z);other.add(assembly);wheels.push(assembly);
  }
  const labels=Object.fromEntries(traffic.map(t=>[t.car,carMark(t.car)]));
  const plate=new T.Mesh(new T.PlaneGeometry(1.04,.262),labels[traffic[0].car]);
  plate.position.set(0,1.70,1.359);other.add(plate);
  const scanHead=take(receiver.scene,'survey_head'),optics=take(receiver.scene,'survey_gimbal');
  const scanner=new T.Group(),trunnion=new T.Group();trunnion.position.y=.244;optics.position.y=-.244;trunnion.add(optics);
  scanner.name='Arrival range optics';scanner.add(scanHead,trunnion);
  scanner.position.set(1.48,1.02,-6.76);range.add(scanner);
  // The docked carriage can request a relay from the outboard gallery.
  // Its optical origin is the actual entrance pupil, past the last hoop.
  const relayDatum=new T.Vector3(-5.14,4.64,-26.85),relayTarget=new T.Vector3(13.7,12.9,-103);
  const relayDir=relayTarget.clone().sub(relayDatum).normalize(),relay=new T.Group();
  relay.name='Aster outboard optical relay';relay.position.copy(relayDatum).addScaledVector(relayDir,-.291);relay.position.y-=.244;
  relay.rotation.y=Math.atan2(relayDir.x,relayDir.z);range.add(relay);
  const pedestalHeight=relay.position.y-3.86,steel=scanHead.isMesh?scanHead.material:scanHead.children.find(n=>n.isMesh).material;
  const pedestal=new T.Mesh(new T.CylinderGeometry(.113,.158,pedestalHeight,18),steel);
  pedestal.position.y=-pedestalHeight*.5;relay.add(pedestal,scanHead.clone(true));
  const relayGimbal=trunnion.clone(true),relayEye=new T.Object3D();relayEye.position.z=.291;relayGimbal.add(relayEye);relay.add(relayGimbal);
  const inspection=take(receiver.scene,'receiver_carriage');
  inspection.position.set(-6.12,.073,-11);range.add(inspection);
  const track=take(receiver.scene,'receiver_track');track.position.set(-6.12,.048,-12.6);range.add(track);
  let lastTime=null,parkTime=0;
  return {habitat,rotor,train,other,freight,wheels,plate,labels,relayEye,valleyPose,
    update(metrics,time,nearest){
      const dt=lastTime===null?0:Math.min(.15,Math.max(0,time-lastTime));lastTime=time;
      parkTime=metrics.seconds>=360?parkTime+dt:0;
      const phase=metrics.seconds+parkTime;
      const shipTime=metrics.forces.shipSeconds+parkTime;
      // Common period of both capillary waves (2.7 and .8 radians/second).
      flow.value=shipTime%(20*Math.PI);
      rotor.rotation.y=(1.12+shipTime*.125)%(2*Math.PI);
      // The soil is 577.6 m from the bearing: 0.125 rad/s gives 0.9203 g.
      // Two waterfront stations lie 1,496 m apart. Service dwells for 14 s,
      // then accelerates and brakes smoothly over its 78 s trip (peak 30 m/s).
      const service=(shipTime+46)%184;
      const outward=service<92;
      const leg=Math.min(1,Math.max(0,((outward?service:service-92)-14)/78));
      const transit=.5-.5*Math.cos(Math.PI*leg);
      train.position.y=-11.4+18.7*(outward?transit:1-transit);
      train.rotation.y=.18;
      plate.material=labels[nearest.car];passenger.visible=nearest.kind==='passenger';common.visible=!passenger.visible;
      freight.visible=nearest.kind==='freight';tender.visible=nearest.kind==='tender';
      if(other.visible){const angle=(nearest.km*1000/.269)%(Math.PI*2);for(const wheel of wheels)wheel.rotation.z=angle;}
      if(range.visible){
        const look=1-Math.min(1,metrics.remainingMeters/100);
        trunnion.rotation.set(Math.min(.94,Math.atan2(metrics.remainingMeters+.48,5.7)),-.51+.91*look+.035*Math.sin(phase*.82),0,'YXZ');
        inspection.position.z=-12.6+Math.sin(phase*.058)*.98;
        relayTarget.y=12.9+metrics.remainingMeters/80;relayGimbal.lookAt(relayTarget);
      }
    }};
}
