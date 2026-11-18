import * as T from 'three';
import { FEEDS, TRAFFIC, altitudeText, travel } from './journey.js';
import { BULLETINS, CIRCUITS, TEST_NAMES, LENS_MM, FOV, crewClock, electrical } from './control-catalog.js';

const C={bg:'#08191e',low:'#1c343a',rule:'#395b61',dim:'#9bb9b8',text:'#e0e9de',cyan:'#90d8cd',amber:'#efb97a'};
const sizes={Diagnostic:[340,270],Drive:[340,270],Pressure:[320,234],Access:[384,173],Berth:[512,208],Seal:[242,337],
  Intercom:[448,129],Service:[820,103],Folio:[1088,667],Vessel:[440,106],Optic:[248,145]};
const makeCanvas=(w,h)=>{const c=document.createElement('canvas');c.width=w;c.height=h;return c;};

function label(ctx,text,x,y,size,color=C.text,bold=false,maxWidth){
  ctx.font=(bold?'600 ':'400 ')+size+'px "Geist Mono", Consolas, monospace';
  ctx.fillStyle=color;
  if(maxWidth)ctx.fillText(String(text),x,y,maxWidth);else ctx.fillText(String(text),x,y);
}
function line(ctx,x,y,x2,y2,color=C.rule,width=1){
  ctx.beginPath();ctx.moveTo(x,y);ctx.lineTo(x2,y2);ctx.lineWidth=width;ctx.strokeStyle=color;ctx.stroke();
}
function rect(ctx,x,y,w,h,color){ctx.fillStyle=color;ctx.fillRect(x,y,w,h);}
function clear(ctx,w,h){rect(ctx,0,0,w,h,C.bg);}
const tripSeconds=travel(1).forces.shipSeconds;
function elapsedHM(seconds){
  const minutes=Math.floor(seconds/60);
  return Math.floor(minutes/60)+' h '+String(minutes%60).padStart(2,'0')+' m';
}
function lamp(ctx,x,y,r,color){
  ctx.beginPath();ctx.arc(x,y,r,0,Math.PI*2);ctx.fillStyle=color;ctx.fill();
}
function words(ctx,str,max,lineCount=3){
  const out=[];let row='';
  for(const word of str.split(' ')){
    if(row&&ctx.measureText(row+' '+word).width>max){out.push(row);row=word;}else row+=(row?' ':'')+word;
  }
  if(row)out.push(row);return out.slice(0,lineCount);
}
function readout(ctx,x,y,w,name,value,unit=''){
  label(ctx,name,x,y,17,C.dim);
  label(ctx,value,x,y+39,31,C.text,true,w);
  if(unit)label(ctx,unit,x,y+65,16,C.amber);
}
function bar(ctx,x,y,w,h,ratio,color=C.cyan,count=16){
  const gap=3;for(let i=0;i<count;i++)rect(ctx,x+i*w/count,y,w/count-gap,h,i/count<ratio?color:C.low);
}
const clockShort=n=>n<60?Math.ceil(n)+' s':n<3600?Math.floor(n/60)+' min':(n/3600).toFixed(1)+' h';
const loadRanges=[.002,.020,.12,1.2];
function loadText(g){
  const milli=Math.abs(g)<.1,n=milli?g*1000:g,digits=milli?1:3;
  const result=Math.abs(n).toFixed(digits),sign=Number(result)===0?'':g<0?'−':'+';
  return sign+result+(milli?' mg':' g');
}

export class Instruments{
  constructor(softwareGpu=false){
    this.canvas=makeCanvas(960,300);this.ctx=this.canvas.getContext('2d');
    this.tex=new T.CanvasTexture(this.canvas);this.tex.colorSpace=T.SRGBColorSpace;this.tex.flipY=false;this.tex.anisotropy=6;
    this.target=new T.WebGLRenderTarget(504,240,{minFilter:T.LinearMipmapLinearFilter,magFilter:T.LinearFilter,depthBuffer:true});
    this.target.texture.colorSpace=T.SRGBColorSpace;this.target.texture.generateMipmaps=true;this.target.texture.anisotropy=8;
    this.videoHz=softwareGpu?8:24;this.lastVideo=-Infinity;this.lastReadback=-Infinity;this.history=[];
    this.material=new T.ShaderMaterial({
      name:'Live_Passage_Display',side:T.DoubleSide,toneMapped:false,
      uniforms:{readout:{value:this.tex},feed:{value:this.target.texture},cameraOn:{value:0},gain:{value:.8}},
      vertexShader:'varying vec2 vUv;void main(){vUv=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}',
      fragmentShader:`varying vec2 vUv;uniform sampler2D readout,feed;uniform float cameraOn,gain;
      void main(){
        vec4 ink=texture2D(readout,vUv);
        vec2 camUv=vec2(vUv.x,.5+(.5-vUv.y)*.65625);
        vec3 cam=texture2D(feed,camUv).rgb;
        gl_FragColor=vec4(mix(cam*cameraOn,ink.rgb,ink.a)*gain,1.);
        #include <colorspace_fragment>
      }`,
    });
    this.last=-20;this.panels={};this.boundCounts={};this.gain=.8;
  }
  bindCabin(scene){
    this.mountedValve=this.board?.world.fixedDevices.find(d=>d.id==='mug');
    scene.traverse(node=>{
      if(!node.isMesh)return;
      const m=node.material;
      if(!m.name?.startsWith('Pixels_'))return;
      const id=m.name.slice(7);
      if(!sizes[id])return;
      if(!this.panels[id]){
        const canvas=makeCanvas(...sizes[id]),texture=new T.CanvasTexture(canvas);
        texture.colorSpace=T.SRGBColorSpace;texture.flipY=false;texture.anisotropy=6;
        this.panels[id]={canvas,ctx:canvas.getContext('2d'),texture,standby:m.map?.image,
          material:new T.MeshBasicMaterial({name:'Live_'+id+'_Display',map:texture,toneMapped:false})};
      }
      this.boundCounts[id]=(this.boundCounts[id]||0)+1;
      node.material=this.panels[id].material;node.castShadow=false;
    });
    this.setGain(this.gain);
  }
  setGain(scalar){
    this.gain=scalar;this.material.uniforms.gain.value=scalar;
    for(const id of ['Diagnostic','Drive'])this.panels[id]?.material.color.setScalar(scalar);
  }
  valveLift(s){
    const item=this.board?.world.inspection;
    const travel=item?.id==='mug'?item.jointPosition:this.mountedValve?.factor??Number(!!s.deviceStops?.mug);
    // Height gained at the silicone port, 22 mm forward of the 38-degree lever pin.
    return 22*Math.sin(travel*38*Math.PI/180);
  }
  drawVessel(panel,m,lift){
    const c=panel.ctx;clear(c,panel.canvas.width,panel.canvas.height);
    const open=lift>=2.4;
    label(c,'VALVE  /  '+m.forces.gravityG.toFixed(2)+' g',12,30,20,C.dim);
    label(c,'PORT LIFT',260,30,20,C.dim);
    label(c,lift<.2?'SEALED':open?'PORT OPEN':'UNSEATING',10,82,42,open?C.amber:C.cyan,true,230);
    label(c,lift.toFixed(1)+' mm',256,82,39,C.text,true,171);
    this.vesselTenth=Math.round(lift*10);
  }
  traffic(s,m){
    const passing=m.traffic.inRange?m.traffic:null,next=passing||TRAFFIC.find(t=>t.at>s.progress);
    const when=next?Math.max(0,passing?passing.eta:travel(next.at).forces.shipSeconds-m.forces.shipSeconds):0;
    return {next,passing,when};
  }
  resetTrace(){
    this.history.length=0;this.loadRange=0;this.last=-Infinity;this.lastVideo=-Infinity;this.lastReadback=-Infinity;
  }
  loadWatch(s,m,time){
    const c=this.ctx,g=m.forces.down/9.80665,mag=Math.abs(g);
    const desired=loadRanges.find(range=>mag<=range*.90)??1.2;
    if(!this.loadRange||desired>this.loadRange||mag<desired*.78)this.loadRange=desired;
    const range=this.loadRange,reference=s.loadReference,marked=Number.isFinite(reference);
    const left=438,right=920,mid=144,half=55;
    const yy=value=>mid+half*value/range;
    const direction=mag<.00005?'NEUTRAL':g<0?'TOWARD CEILING':'TOWARD DECK';
    label(c,direction,23,84,25,g<-.00005?C.amber:C.cyan,true);
    label(c,loadText(g),18,151,65,C.text,true,389);
    label(c,'WEST   '+(m.forces.west*1000/9.80665).toFixed(2)+' mg',24,194,23,C.dim);
    if(this.mechanical){
      const test=this.mechanical.plunger.x>.02;
      label(c,(test?'TEST   ':'PROOF  ')+loadText(this.mechanical.proof.x),24,228,23,test?C.amber:C.dim);
    }
    label(c,'LAST 24 s',left,74,20,C.dim,true);
    c.save();c.textAlign='right';label(c,'±'+(range>=1?'1.2 g':Math.round(range*1000)+' mg'),right,74,23,C.text,true);c.restore();
    for(let j=0;j<=4;j++){const x=left+(right-left)*j/4;line(c,x,mid-half,x,mid+half,C.low,2);}
    line(c,left,mid-half,right,mid-half,C.rule);line(c,left,mid,right,mid,C.dim,2);
    line(c,left,mid+half,right,mid+half,C.rule);
    if(marked&&Math.abs(reference)<=range){
      c.save();c.setLineDash([7,6]);line(c,left,yy(reference),right,yy(reference),C.amber,2);c.restore();
    }
    c.save();c.beginPath();c.rect(left,mid-half-2,right-left,2*half+4);c.clip();
    c.beginPath();c.lineWidth=3.6;c.strokeStyle=C.cyan;
    let first=true;
    for(const sample of this.history){
      const age=time-sample.time;if(age>24)continue;
      const x=right-(right-left)*age/24,y=yy(sample.load);
      if(first)c.moveTo(x,y);else c.lineTo(x,y);first=false;
    }
    c.stroke();c.restore();
    const y=yy(Math.min(range,Math.max(-range,g)));
    lamp(c,right,y,4.5,C.text);
    label(c,'CEILING −  /  + DECK',left,228,19,C.dim);
    c.save();c.textAlign='right';label(c,'NOW',right,228,19,C.text,true);c.restore();
    line(c,17,249,943,249,C.rule,2);
    if(marked){
      label(c,'MARK  '+loadText(reference),22,281,22,C.amber,true,315);
      label(c,'CHANGE  '+loadText(g-reference),338,281,22,C.text,true,365);
      label(c,'LOAD / CLEAR',775,280,19,C.dim);
    }else label(c,'PRESS LOAD TO MARK THIS READING',22,281,21,C.amber,true);
  }
  trace(ctx,channel,time,x,y,w,h){
    const pressure=channel==='pressure',samples=this.history;
    label(ctx,pressure?'ΔP  /  LAST 24 s':'RX  /  LAST 24 s',x,y+h-3,14,C.dim);
    const left=x+158,width=w-158,limit=.40;
    line(ctx,left,y+h,left+width,y+h,C.rule);
    ctx.beginPath();ctx.strokeStyle=pressure?C.cyan:C.amber;ctx.lineWidth=2;
    let priorY;
    for(const sample of samples){
      const age=time-sample.time;if(age>24)continue;
      const xx=left+width*(1-age/24);
      const reading=pressure?Math.min(1,Math.max(0,sample.pressure/limit)):sample.carrier*.82+.06;
      const yy=y+h*(1-reading);
      if(priorY===undefined)ctx.moveTo(xx,yy);
      else{if(!pressure)ctx.lineTo(xx,priorY);ctx.lineTo(xx,yy);}
      priorY=yy;
    }
    ctx.stroke();
  }
  draw(s,m,time){
    const ctx=this.ctx,w=960,h=300,id=s.screen||0;
    const b=this.board,live=b?.live??{...electrical(s),differential:s.hatch?0:.02,measured:s.hatch?0:.02};
    while(this.history.length&&this.history[0].time<time-24)this.history.shift();
    this.history.push({time,pressure:live.measured,carrier:Number(!!live.voiceOn),load:m.forces.down/9.80665});
    this.material.uniforms.cameraOn.value=Number(id===1);
    ctx.clearRect(0,0,w,h);
    if(id!==1)clear(ctx,w,h);
    rect(ctx,0,0,w,42,id===1?'rgba(5,18,22,.88)':'#10282d');
    label(ctx,'07  /  '+['PASSAGE','EXTERIOR OPTICS','PRESSURE VESSEL','VERTICAL LOAD','COUNTERLINE','CREW RADIO'][id],18,28,19,C.text,true);
    label(ctx,'SHIP CLOCK  /  '+crewClock(m.forces.shipSeconds),630,27,17,C.dim,false,309);
    line(ctx,0,42,w,42,C.rule,2);
    if(id===0){
      const heights=[0,12,100,660,3900,12600,35786],markers=['0','12','100','660','4k','13k','GEO'];
      const x=36,y=201,rw=360;
      label(ctx,'EQUATORIAL TETHER  /  LOG ALTITUDE',x,83,17,C.dim);
      const f=Math.log1p(m.km)/Math.log1p(35786);
      line(ctx,x,y,x+rw,y,C.rule,4);line(ctx,x,y,x+f*rw,y,C.cyan,4);
      for(let j=0;j<heights.length;j++){
        const xx=x+Math.log1p(heights[j])/Math.log1p(35786)*rw;
        line(ctx,xx,y-6,xx,y+7,C.dim,1);label(ctx,markers[j],xx-7,y+26,13,C.dim);
      }
      lamp(ctx,x+f*rw,y,7,C.amber);
      label(ctx,m.name.toUpperCase(),x,139,29,C.text,true,370);
      line(ctx,438,65,438,245);
      label(ctx,'ALTIMETER',471,85,18,C.dim);
      label(ctx,altitudeText(m.km),467,155,52,C.text,true,460);
      label(ctx,'CLIMB SPEED   '+m.speed+' km/h',472,218,23,C.cyan);
    }else if(id===1){
      const k=s.cameraLens??1;
      for(const [x,y,dx,dy] of [[59,75,1,1],[901,75,-1,1],[59,218,1,-1],[901,218,-1,-1]]){
        line(ctx,x,y,x+25*dx,y,C.cyan,2);line(ctx,x,y,x,y+16*dy,C.cyan,2);
      }
      line(ctx,466,151,477,151,C.text,1.4);line(ctx,483,151,494,151,C.text,1.4);
      line(ctx,480,137,480,147,C.text,1.4);line(ctx,480,155,480,165,C.text,1.4);
      rect(ctx,0,254,w,46,'rgba(5,18,22,.90)');
      label(ctx,'CAM 0'+(s.feed+1)+'  /  '+FEEDS[s.feed].toUpperCase(),20,284,21,C.text,true);
      label(ctx,LENS_MM[k]+' mm     '+FOV[k]+'° VERTICAL',645,284,19,C.amber);
    }else if(id===2){
      readout(ctx,26,87,315,'VESSEL DIFFERENTIAL',live.differential.toFixed(2)+' kPa','TAPS A + B');
      readout(ctx,368,87,239,'SERVICE LEAF',s.hatch?'OPEN':'SEALED',s.unlocked?'ACCESS RELEASED':'ACCESS SECURED');
      readout(ctx,664,87,253,'TRANSFER CLAMP',s.clamp+' / 3','INDEXED DETENTS');
      this.trace(ctx,'pressure',time,26,167,906,30);
      label(ctx,live.reference?'TRANSDUCER REFERENCE   '+live.measured.toFixed(2)+' kPa':'CABIN PRESSURE   101.3 kPa',26,235,21,live.reference?C.amber:C.cyan);
    }else if(id===3){
      this.loadWatch(s,m,time);
    }else if(id===4){
      const {next,passing,when}=this.traffic(s,m);
      const cx=113,cy=148;ctx.strokeStyle=C.rule;
      for(const r of [20,40,61]){ctx.beginPath();ctx.arc(cx,cy,r,0,Math.PI*2);ctx.stroke();}
      line(ctx,cx-79,cy,cx+79,cy);line(ctx,cx,cy-79,cx,cy+79);lamp(ctx,cx,cy,4,C.cyan);
      if(next)lamp(ctx,cx-25,cy-Math.max(-55,Math.min(55,(next.at-s.progress)*2700)),5,C.amber);
      readout(ctx,234,101,255,'DOWNBOUND',next?next.car:'CLEAR',next?next.type.toUpperCase():'NO FURTHER SERVICE');
      readout(ctx,539,101,363,'COUNTERLINE',passing?'PASSING':next?clockShort(when):'TRACK CLEAR',passing?'CONTACT IN ACQUISITION ZONE':'SHIP TIME TO CLOSEST APPROACH');
    }else{
      label(ctx,'CHANNEL 07   /   OPERATIONS',30,88,19,C.cyan);
      lamp(ctx,852,79,6,live.voiceOn?C.amber:C.cyan);label(ctx,live.voiceOn?'VOICE':'READY',872,86,17,C.text);
      ctx.font='600 30px "Geist Mono", Consolas, monospace';
      const lines=words(ctx,BULLETINS[m.index]||BULLETINS[0],871,3);
      lines.forEach((t,i)=>label(ctx,t,32,145+36*i,30,C.text,true));
      this.trace(ctx,'carrier',time,30,223,899,20);
    }
    if(id!==1&&id!==3){
      line(ctx,16,256,w-16,256);
      if(id===0&&!live.lampTest){
        const aboard=Math.min(m.seconds,9)+m.forces.shipSeconds;
        label(ctx,'ABOARD   '+elapsedHM(aboard),21,284,18,C.text);
        label(ctx,'TO DOCK   '+elapsedHM(Math.max(0,tripSeconds+9-aboard)),467,284,18,C.cyan);
      }else{
        label(ctx,live.lampTest?'ANNUNCIATOR TEST':m.atmosphere.toUpperCase(),21,284,16,live.lampTest?C.amber:C.dim);
        label(ctx,'UPBOUND   /   CAR 07',651,284,16,C.cyan);
      }
    }
    this.tex.needsUpdate=true;
    for(const [key,panel] of Object.entries(this.panels)){
      this.drawPanel(key,panel,s,m,time,live);
      panel.texture.needsUpdate=true;
    }
  }
  drawPanel(id,panel,s,m,time,d){
    const {ctx:c,canvas}=panel,w=canvas.width,h=canvas.height,b=this.board;
    clear(c,w,h);
    const heading=text=>{label(c,text,12,27,18,C.dim,true,w-24);line(c,12,38,w-12,38);};
    const stat=(left,right,y)=>{label(c,left,13,y,16,C.dim);c.save();c.textAlign='right';label(c,right,w-12,y,17,C.text);c.restore();};
    const large=(txt,y,size,max=w-26)=>label(c,txt,12,y,size,C.text,true,max);
    if(id==='Diagnostic'){
      heading(s.diagElectrical?'ELECTRICAL  /  28 V':'ENVIRONMENT  /  ECLSS');
      if(s.diagElectrical){
        large(d.volts.toFixed(2)+' V',110,46);bar(c,14,131,w-28,8,d.volts/32);
        stat('LOAD',d.amps.toFixed(2)+' A',178);stat('WORK FLOOD',s.guideFlood?'ON':'OFF',218);
      }else{
        large('101.3 kPa',110,46);bar(c,14,131,w-28,8,.86);
        stat('CIRCULATION',Math.round((d.fan??Number(s.ventOn))*100)+' %',178);
        stat('FORWARD FILM',s.shade?'DOWN':'UP',218);
      }
      label(c,s.diagElectrical?'02 / 02   BUS MONITOR':'01 / 02   PRESSURE VESSEL',13,251,14,C.cyan);
    }else if(id==='Drive'){
      heading(s.driveGuides?'GUIDE PICKUPS  /  A+B':'TRACTION  /  AUTO');
      if(s.driveGuides){
        large(d.guideReturn.toFixed(2)+' ms',110,48);
        bar(c,15,132,w-30,8,.88);
        stat('HEAD A','LINK',178);stat('HEAD B','LINK',218);
      }else{
        large(m.forces.velocity.toFixed(1)+' m/s',110,46);
        bar(c,15,132,w-30,8,m.forces.velocity/170);
        stat('ACCELERATION',m.forces.driveAcceleration.toFixed(2)+' m/s²',178);
        stat('APPARENT LOAD',m.forces.gravityG.toFixed(3)+' g',218);
      }
      label(c,s.driveGuides?'02 / 02   PAIRED RETURNS':m.forces.driveAcceleration<-.001?'01 / 02   BRAKING':m.speed?'01 / 02   DRIVE ONLINE':'01 / 02   STATION HOLD',13,251,14,C.cyan);
    }else if(id==='Pressure'){
      heading(d.reference?'CALIBRATION REFERENCE':'SEAL DIFFERENTIAL');
      large(d.measured.toFixed(2),137,75,207);label(c,'kPa',222,135,30,C.cyan);
      bar(c,15,160,w-30,9,d.measured/.22,d.reference?C.amber:C.cyan);
      label(c,d.reference?'ISOLATED  /  TEST':s.hatch?'A + B  /  CONNECTED':'A + B  /  SEALED',14,210,19,C.dim);
    }else if(id==='Access'){
      heading('CREW ACCESS   /   AC 506');
      const msg=d.reader==='denied'?'CARD REQUIRED':d.reader==='reading'?'EQUALIZING':s.unlocked?'AUTHORIZED':'PRESENT CARD';
      large(msg,106,41);
      label(c,s.unlocked?'LOCAL KEY 07   /   ACCEPTED':'CONTACT READER   /   READY',13,148,17,s.unlocked?C.cyan:C.amber);
    }else if(id==='Seal'){
      heading('PRESSURE LOCK');
      large(s.hatch?'OPEN':'SEALED',120,48);
      for(let i=0;i<2;i++){
        c.strokeStyle=s.hatch?C.amber:C.cyan;c.lineWidth=4;
        c.strokeRect(33+26*i+(s.hatch?26*i:0),145+15*i,124-26*i,79-30*i);
      }
      label(c,d.differential.toFixed(2)+' kPa',13,268,29,C.text,true);
      label(c,s.unlocked?'ACCESS RELEASED':'INTERLOCK SECURE',13,309,16,C.dim);
    }else if(id==='Berth'){
      heading('BERTH 02    /    CREW ENVIRONMENT');
      large(m.forces.gravityG.toFixed(3)+' g',108,48,240);
      label(c,s.berthLight?'LAMP ON':'LAMP OFF',285,104,26,s.berthLight?C.amber:C.dim);
      stat('CIRCULATION',s.ventOn?'FLOWING':'STOPPED',159);
      const screen=Number(s.curtain);
      stat('PRIVACY SCREEN',screen>=.98?'DRAWN':screen<=.02?'STOWED':Math.round(screen*100)+'% DRAWN',191);
    }else if(id==='Intercom'){
      heading('OPERATIONS   /   RX 07');
      large(d.voiceOn?'RECEIVING':'STANDBY',91,39,273);
      for(let i=0;i<7;i++){
        const height=d.voiceOn?10+36*Math.abs(Math.sin(time*6.1+i*.86)):5;
        rect(c,299+i*18,89-height,10,height,d.voiceOn?C.amber:C.cyan);
      }
      label(c,'SECTOR '+String(m.index+1).padStart(2,'0')+'     '+crewClock(m.forces.shipSeconds),14,116,15,C.dim);
    }else if(id==='Service'){
      const key=b?.lastCircuit,i=CIRCUITS.indexOf(key),start=b?.tests[key];
      label(c,'EW / 510   '+(key?TEST_NAMES[i]:'CIRCUIT TEST BUS'),14,34,23,C.dim,true);
      const message=start!==undefined?'TEST IN PROGRESS':key&&b.results[key]?('RETURN  '+b.results[key]):'SELECT A CHANNEL';
      label(c,message,16,82,34,C.text,true,535);
      if(key==='test_fiber'&&Number.isFinite(d.fiberBendMM)){
        label(c,'MIN BEND RADIUS',555,32,17,C.dim,true,240);
        label(c,d.fiberBendMM+' mm',555,82,34,C.cyan,true,240);
      }else bar(c,575,56,222,15,start!==undefined?Math.min(1,(time-start)/2.65):key?1:0,C.amber,12);
    }else if(id==='Folio'){
      // Retain all six original watch entries. Only the telemetry/status band is rewritten.
      if(panel.standby)c.drawImage(panel.standby,0,0,w,h);
      else{
        heading('ENGINEERING WATCH   /   N. IBARRA');
        ['02:46   Optical guide heads cleared','03:10   Counterline return verified','03:32   Dock seal held at 101.3 kPa',
          '03:55   Fiber loop continuity checked','04:09   Blue loom witness stripe holding','04:12   Spare key returned to crew tray']
          .forEach((note,i)=>label(c,note,37,154+i*74,30,C.text));
      }
      rect(c,24,h-83,w-48,59,'#10252c');line(c,24,h-83,w-24,h-83,C.rule,2);
      label(c,crewClock(m.forces.shipSeconds)+'    '+m.name.toUpperCase()+'    '+m.forces.gravityG.toFixed(3)+' g',39,h-47,24,C.cyan,false,w-80);
    }else if(id==='Vessel'){
      this.drawVessel(panel,m,this.valveLift(s));
    }else if(id==='Optic'){
      const focus=['3 m','6 m','12 m','30 m','100 m','∞'][s.deviceStops?.field_glasses??0];
      heading('FG–01   /   8×42');large(focus,96,48,152);label(c,'FOCUS',153,91,17,C.amber);
      label(c,'STABILIZER LOCK',13,131,18,C.cyan);
    }
  }
  capture(renderer,exterior,s,m,time,monitor){
    if(time<this.last)this.resetTrace();
    if(time-this.last>=.24||this.lastPage!==s.screen){
      this.last=time;this.lastPage=s.screen;this.draw(s,m,time);
    }
    const vessel=this.panels.Vessel;
    if(vessel&&time!==this.last){
      const lift=this.valveLift(s);
      if(Math.round(lift*10)!==this.vesselTenth){
        this.drawVessel(vessel,m,lift);vessel.texture.needsUpdate=true;
      }
    }
    if(s.screen!==1&&!monitor)return;
    const period=1/this.videoHz,elapsed=time-this.lastVideo;
    if(s.feed===this.lastFeed&&elapsed<period)return;
    this.lastVideo=s.feed===this.lastFeed&&Number.isFinite(elapsed)?time-elapsed%period:time;this.lastFeed=s.feed;
    const old=renderer.getRenderTarget();renderer.setRenderTarget(this.target);
    renderer.clear(true,true,true);renderer.render(exterior.scene,exterior.cams[s.feed]);renderer.setRenderTarget(old);
    if(!monitor||time-this.lastReadback<1/15)return;
    this.lastReadback=time;
    const w=this.target.width,h=this.target.height;
    if(!this.pixelData){this.pixelData=new Uint8Array(w*h*4);this.imageData=new ImageData(w,h);}
    renderer.readRenderTargetPixels(this.target,0,0,w,h,this.pixelData);
    for(let y=0;y<h;y++)this.imageData.data.set(this.pixelData.subarray((h-1-y)*w*4,(h-y)*w*4),y*w*4);
    if(monitor.width!==w||monitor.height!==h){monitor.width=w;monitor.height=h;}
    monitor.getContext('2d').putImageData(this.imageData,0,0);
  }
}
