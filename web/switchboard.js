import * as T from 'three';
import {travel} from './journey.js';
import { SWITCHES, GAIN, FOV, LENS_MM, PAGES, PAGE_KEYS, CIRCUITS, TEST_NAMES, electrical } from './control-catalog.js';
import { TerminalScreens } from './terminal-displays.js';
import {CabinHardware} from './cabin-hardware.js';
export * from './control-catalog.js';

const toggles={guide_flood:'guideFlood',cabin_lights:'lamps',solar_film:'shade',vent_fan:'ventOn'};
const levels={panel_gain:'panelGain',camera_focus:'cameraLens'};
const latches={...toggles,reading_lamp:'berthLight',breaker:'bayLight'};
const traceColor=[0xffab52,0x54ddff,0xffc38c,0x8bf1c3];
const pulseSeconds=2.65;
const timing=(age,span)=>Math.max(0,Math.min(1,age/span));

// UV.u measures physical arc length along the witness fibre from the key to the connector.
function witnessMaterial(i){
  return new T.ShaderMaterial({
    name:'Live '+TEST_NAMES[i]+' witness', side:T.DoubleSide, toneMapped:false,
    uniforms:{positionOnLoom:{value:-1},testPower:{value:0},lightColour:{value:new T.Color(traceColor[i])}},
    vertexShader:'varying vec2 lineUv; void main(){lineUv=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}',
    fragmentShader:`varying vec2 lineUv;uniform float positionOnLoom,testPower;uniform vec3 lightColour;
      void main(){
        float trail=positionOnLoom-lineUv.x;
        float edge=smoothstep(-.013,.025,trail)*(1.-smoothstep(.018,.23,trail));
        float center=1.-.38*abs(lineUv.y*2.-1.);
        vec3 colour=mix(vec3(.016,.025,.026),lightColour,(.12+.88*edge)*testPower*center);
        gl_FragColor=vec4(colour,1.);
        #include <colorspace_fragment>
      }`,
  });
}

// The GLB combines the shell's emergency strips and work-light lenses in one
// draw call. Keep the egress strips powered when a rider switches a work circuit.
function wireDiffuser(mesh,room){
  const output={value:1},material=mesh.material.clone();
  const mask=room==='observation'?'step(2.14,worldVertex.y)':
    'step(1.83,worldVertex.x)*step(1.92,worldVertex.y)*(1.-step(2.04,worldVertex.y))*step(2.95,worldVertex.z)*(1.-step(4.18,worldVertex.z))';
  material.onBeforeCompile=shader=>{
    shader.uniforms.workLightOutput=output;
    shader.vertexShader=shader.vertexShader.replace('#include <common>','#include <common>\nvarying float workLens;')
      .replace('#include <begin_vertex>','#include <begin_vertex>\nvec3 worldVertex=(modelMatrix*vec4(transformed,1.)).xyz;workLens='+mask+';');
    shader.fragmentShader=shader.fragmentShader.replace('#include <common>','#include <common>\nvarying float workLens;uniform float workLightOutput;')
      .replace('#include <emissivemap_fragment>','#include <emissivemap_fragment>\ntotalEmissiveRadiance*=mix(1.,workLightOutput,workLens);');
  };
  material.customProgramCacheKey=()=>'work-lens-'+room;
  mesh.material=material;
  return output;
}

function wireWitnessBank(mesh){
  const flags={value:new T.Vector4()},m=mesh.material.clone();
  m.onBeforeCompile=shader=>{
    shader.uniforms.circuitFlags=flags;
    shader.vertexShader=shader.vertexShader.replace('#include <common>','#include <common>\nuniform vec4 circuitFlags;varying float witnessPower;')
      .replace('#include <begin_vertex>',`#include <begin_vertex>
        float lampX=(modelMatrix*vec4(transformed,1.)).x;
        witnessPower=lampX<.673?circuitFlags.x:(lampX<.716?circuitFlags.y:(lampX<.759?circuitFlags.z:circuitFlags.w));`);
    shader.fragmentShader=shader.fragmentShader.replace('#include <common>','#include <common>\nvarying float witnessPower;')
      .replace('#include <color_fragment>','#include <color_fragment>\ndiffuseColor.rgb*=mix(.10,1.,witnessPower);')
      .replace('#include <emissivemap_fragment>','#include <emissivemap_fragment>\ntotalEmissiveRadiance*=mix(.01,1.,witnessPower);');
  };
  m.customProgramCacheKey=()=>'flight-witness-bank';mesh.material=m;
  return flags;
}

export class Switchboard{
  constructor(world,layout){
    this.world=world;
    this.time=0;this.fanSpeed=0;this.lens=-1;this.gain=-1;
    this.motions=new Map();this.lights=[];this.traces=[];this.diffusers=[];this.transient=new Map();
    this.tests={};this.results={};this.lastCircuit=null;
    this.reader={status:'',time:-100};this.testLamps=-100;
    this.rotation=new T.Quaternion();this.statusLight=new T.Color();
    const spec=layout.switchboard;
    if(spec){
      for(const def of spec.controls){
        const node=world.nodes[def.id];
        if(!node)continue;
        this.motions.set(def.id,{...def,node,axis:new T.Vector3(...def.axis).normalize(),rest:node.position.clone(),
          orientation:node.quaternion.clone(),value:0,velocity:0});
      }
      this.fan=world.scene.getObjectByName(spec.fan.node);
    }
    world.scene.traverse(node=>{
      if(!node.isMesh)return;
      const material=node.material;
      if(material.name.startsWith('Ann_')){
        node.castShadow=false;node.material=material.clone();
        const nativeColour=material.emissive?.clone()??material.color.clone();
        this.lights.push({id:material.name.slice(4),material:node.material,nativeColour,lens:material.color.clone(),last:-2});
      }
      if(material.name==='Berth_Diffuser')this.berthDiffuser=material;
      if(material.name==='Opal_Emitter'){
        for(let parent=node;parent;parent=parent.parent){
          const room=parent.name==='shell_observation'?'observation':parent.name==='shell_service'?'service':null;
          if(room){this.diffusers.push([room==='observation'?'lamps':'bayLight',wireDiffuser(node,room)]);break;}
        }
      }
      const i=['Trace_Power','Trace_Fiber','Trace_Seal','Trace_Return'].indexOf(material.name);
      if(i>=0){
        node.material=witnessMaterial(i);node.castShadow=false;this.traces.push([CIRCUITS[i],node.material]);
      }
    });
    world.nodes.nav_screen?.traverse(node=>{
      if(node.isMesh&&node.material.name==='Blue_Emitter')this.witnessBank=wireWitnessBank(node);
    });
    this.flood=world.exterior.guideway.serviceLamp;
    this.floodOutput=0;
    this.terminalScreens=new TerminalScreens(world.exterior.terminals);
    world.instruments.board=this;
    world.instruments.bindCabin(world.scene);
    this.hardware=new CabinHardware(world);
  }
  trigger(id,detail){
    this.transient.set(id,this.time);
    if(id==='card_reader')this.reader={status:detail||'reading',time:this.time};
    if(this.world.instruments)this.world.instruments.last=-100;
  }
  contact(id,pressed){
    this.held=pressed&&this.motions.has(id)?id:null;
  }
  operate(id,s,direction=1){
    if(!SWITCHES[id])return null;
    if(CIRCUITS.includes(id)&&!s.cabinet)return {message:'Open the inspection cover to reach the test bank.',sound:'no'};
    this.trigger(id);
    const page=PAGE_KEYS.indexOf(id);
    if(page>=0){
      if(id==='key_load'&&s.screen===3){
        s.loadReference=Number.isFinite(s.loadReference)?null:travel(s.progress).forces.down/9.80665;
        return {message:s.loadReference===null?'Load reference cleared.':'Vertical load reference marked.',sound:'click'};
      }
      s.screen=page;
      return {message:PAGES[page],sound:'click',dispatch:id==='key_comms'};
    }
    if(toggles[id]){
      const flag=toggles[id];s[flag]=!s[flag];
      const phrases={guide_flood:['Guide flood off.','Port guide work light on.'],cabin_lights:['Saloon lights off.','Saloon lights on.'],
        solar_film:['Solar film retracting.','Solar film descending.'],vent_fan:['Circulation fan coasting down.','Circulation fan running.']};
      return {message:phrases[id][+s[flag]],sound:id==='solar_film'?'shade':'detent'};
    }
    if(levels[id]){
      const key=levels[id],previous=s[key];
      s[key]=Math.max(0,Math.min(4,previous+Math.sign(direction)));
      if(id==='camera_focus')s.screen=1;
      const stop=s[key]===previous?' · end stop':'';
      return {sound:'detent',message:id==='camera_focus'?LENS_MM[s[key]]+' mm · '+FOV[s[key]]+'° vertical field'+stop:'Flight display gain · '+Math.round(GAIN[s[key]]*100)+'%'+stop};
    }
    if(id==='diagnostic_screen'){
      s.diagElectrical=!s.diagElectrical;
      return {message:s.diagElectrical?'Diagnostic repeater · electrical bus':'Diagnostic repeater · cabin air',sound:'click'};
    }
    if(id==='drive_screen'){
      s.driveGuides=!s.driveGuides;
      return {message:s.driveGuides?'Traction repeater · guide pickups':'Traction repeater · motor output',sound:'click'};
    }
    if(id==='key_lamp_test'){
      this.testLamps=this.time;
      return {message:'Annunciator check · all witness lights energized.',sound:'click'};
    }
    const circuit=CIRCUITS.indexOf(id);
    this.tests[id]=this.time;delete this.results[id];this.lastCircuit=id;
    return {message:['Power feeder · load applied.','Fiber loop · packet sent.','Seal tap · calibration reference applied.','Guide pickup · reference pulse sent.'][circuit],sound:circuit===2?'valve':'click'};
  }
  sample(s,m){
    const values=electrical(s),load=m.forces.gravityG;
    const inTest=id=>this.tests[id]!==undefined?timing(this.time-this.tests[id],pulseSeconds):1;
    const sample=inTest('test_seal');
    const tested=sample<1&&s.cabinet;
    const readerReading=this.reader.status==='reading'&&this.time-this.reader.time<1.9;
    const differential=s.hatch?0:readerReading?.02*(1-timing(this.time-this.reader.time,1.4)):.02;
    const measured=tested?.20*Math.min(1,sample*6,(1-sample)*7):differential;
    const volts=values.volts-(inTest('test_power')<1?.26:0);
    const fiberLoss=.84+.055*load;
    const guideReturn=1.08+Math.abs(m.forces.west)*1.4;
    return {volts,amps:values.amps,differential,measured,reference:tested,fiberLoss,guideReturn,
      lampTest:this.time-this.testLamps<2.4,voiceOn:this.receiving?.()??false,
      reader: this.time-this.reader.time<2.1?this.reader.status:'',fan:this.fanSpeed/17,
      fiberBendMM:this.lastCircuit==='test_fiber'?this.hardware.bendRadius():0};
  }
  update(s,m,time,dt){
    this.hardware.update(s,time,dt);
    this.time=time;
    if(this.state&&this.state!==s){
      this.transient.clear();this.tests={};this.results={};this.lastCircuit=null;this.testLamps=-100;this.reader={status:'',time:-100};
    }
    this.state=s;
    const mix=1-Math.exp(-dt*6);
    this.fanSpeed+=(17*Number(s.ventOn)-this.fanSpeed)*(1-Math.exp(-dt*(s.ventOn?2.8:1.8)));
    if(this.fan)this.fan.rotation.y-=this.fanSpeed*dt;
    this.floodOutput+=(Number(s.guideFlood)*48-this.floodOutput)*mix;
    if(this.flood)this.flood.intensity=this.floodOutput;
    if(this.berthDiffuser)this.berthDiffuser.emissiveIntensity=s.berthLight?1.6:.025;
    for(const [flag,lens] of this.diffusers)lens.value=s[flag]?1:.012;
    if(this.lens!==s.cameraLens){
      this.lens=s.cameraLens;
      for(const cam of this.world.exterior.cams){cam.fov=FOV[s.cameraLens]??52;cam.updateProjectionMatrix();}
    }
    if(this.gain!==s.panelGain){
      this.gain=s.panelGain;this.world.instruments.setGain(GAIN[s.panelGain]??.8);
    }
    if(!s.cabinet&&Object.keys(this.tests).length){this.tests={};this.lastCircuit=null;}
    this.live=this.sample(s,m);
    if(this.witnessBank){
      const lamps=this.witnessBank.value;
      if(this.live.lampTest)lamps.set(1,1,1,1);
      else lamps.set(+s.guideFlood,+s.lamps,+s.shade,+s.ventOn);
    }
    for(const [id,start] of Object.entries(this.tests)){
      if(time-start<pulseSeconds)continue;
      const i=CIRCUITS.indexOf(id);
      this.results[id]=[this.live.volts.toFixed(2)+' V',( -this.live.fiberLoss).toFixed(2)+' dB','0.20 kPa',this.live.guideReturn.toFixed(2)+' ms'][i];
      delete this.tests[id];
    }
    for(const [id,motion] of this.motions){
      let target=latches[id]?Number(s[latches[id]]):levels[id]?(s[levels[id]]??0)/4:
        Number(this.held===id||time-(this.transient.get(id)??-100)<.29);
      const drag=this.world.dragPreview;
      if(drag?.id===id){
        const next=latches[id]?1-target:levels[id]?Math.max(0,Math.min(1,target+(drag.direction||1)*.25)):1;
        target+=(next-target)*Math.min(1,drag.travel)*.94;
      }
      const steps=Math.max(1,Math.ceil(Math.min(dt,.09)/.011)),step=Math.min(dt,.09)/steps;
      const spring=motion.kind==='press'?36:23;
      for(let i=0;i<steps;i++){
        motion.velocity+=((target-motion.value)*spring*spring-1.73*spring*motion.velocity)*step;
        motion.value=Math.max(0,Math.min(1,motion.value+motion.velocity*step));
      }
      if(motion.kind==='press')motion.node.position.copy(motion.rest).addScaledVector(motion.axis,motion.amount*motion.value);
      else motion.node.quaternion.copy(motion.orientation).multiply(this.rotation.setFromAxisAngle(motion.axis,motion.amount*Math.PI/180*motion.value));
    }
    for(const light of this.lights){
      const {id,material,nativeColour,lens}=light;
      const on=this.live.lampTest||latches[id]&&s[latches[id]]||PAGE_KEYS[s.screen]===id||
        (id==='intercom'&&this.live.voiceOn)||(this.tests[id]!==undefined&&Math.sin((time-this.tests[id])*19)>.0)||
        (id===this.lastCircuit&&!!this.results[id]);
      const level=on?1:0;
      if(level===light.last)continue;light.last=level;
      material.color.setRGB(.036,.050,.047).lerp(lens,on?.84:.08);
      material.emissive.copy(nativeColour);material.emissiveIntensity=on?1.9:.012;
    }
    for(const [id,material] of this.traces){
      const start=this.tests[id],u=material.uniforms;
      u.testPower.value=start===undefined?0:1;
      if(start!==undefined)u.positionOnLoom.value=1.32*(((time-start)/.87)%1);
    }
    this.terminalScreens.update(s,m,time);
  }
}
