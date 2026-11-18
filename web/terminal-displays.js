import * as T from 'three';
import { crewClock } from './control-catalog.js';

// The terminal fabrication atlas puts four LCD images alongside each other.
// A single live atlas per station also serves the joined material on the rack faces.
const rects=[[11,951,490,301],[520,951,490,301],[1029,951,490,301],[1538,951,490,301]];
const tileWidth=384,tileHeight=208;

function installTerminal(bay){
  const canvas=document.createElement('canvas');
  canvas.width=2*tileWidth;canvas.height=2*tileHeight;
  const texture=new T.CanvasTexture(canvas);texture.colorSpace=T.SRGBColorSpace;texture.flipY=false;
  texture.anisotropy=4;
  const material=new T.MeshBasicMaterial({name:'Live terminal racks and booth displays',map:texture,toneMapped:false});
  const screens=[],facesByPage=[0,0,0,0];
  bay.root.traverse(node=>{
    if(!node.isMesh||node.material.name!=='Terminal_Display')return;
    const geometry=node.geometry.clone(),uv=geometry.attributes.uv;if(!uv)return;
    const tileAt=[];
    for(let i=0;i<uv.count;i++){
      const x=uv.getX(i)*2048,y=uv.getY(i)*2048;
      const k=Math.min(3,Math.max(0,Math.floor(x/512)));
      tileAt[i]=k;
      const [left,top,width,height]=rects[k];
      uv.setXY(i,(k%2+(x-left)/width)/2,(Math.floor(k/2)+(y-top)/height)/2);
    }
    const ix=geometry.index,count=ix?.count??uv.count;
    for(let i=0;i<count;i+=3)facesByPage[tileAt[ix?ix.getX(i):i]]+=.5;
    uv.needsUpdate=true;node.geometry=geometry;node.material=material;node.castShadow=false;screens.push(node);
  });
  return {root:bay.root,texture,ctx:canvas.getContext('2d'),screens,facesByPage,last:-5};
}

function tile(ctx,index,header,body,small,time,signal){
  const x=(index%2)*tileWidth,y=Math.floor(index/2)*tileHeight;
  ctx.save();ctx.translate(x,y);
  ctx.fillStyle='#0b1a21';ctx.fillRect(0,0,tileWidth,tileHeight);
  ctx.fillStyle='#9cbab7';ctx.font='bold 18px monospace';ctx.fillText(header,15,30);
  ctx.fillStyle='#396367';ctx.fillRect(15,39,354,2);
  if(signal){
    ctx.strokeStyle='#285056';ctx.lineWidth=1;
    for(let k=0;k<9;k++){ctx.beginPath();ctx.moveTo(19+43*k,57);ctx.lineTo(19+43*k,139);ctx.stroke();}
    for(let k=0;k<4;k++){ctx.beginPath();ctx.moveTo(19,61+k*24);ctx.lineTo(365,61+k*24);ctx.stroke();}
    ctx.beginPath();ctx.lineWidth=3;ctx.strokeStyle='#89d8ca';
    for(let k=0;k<174;k++){
      const phase=(k/173*4+time*.65)%1;
      const amp=phase>.43&&phase<.58?35:4*Math.sin(phase*6.28);
      const py=107-amp*signal;
      if(k===0)ctx.moveTo(18,py);else ctx.lineTo(18+k*2,py);
    }
    ctx.stroke();
  }else{
    ctx.fillStyle='#e1ead8';ctx.font='bold '+(body.length>14?26:34)+'px monospace';ctx.fillText(body,16,107,351);
    for(let k=0;k<12;k++){
      ctx.fillStyle=k<7+Math.floor(Math.sin(time*.57)*2)?'#69a69d':'#233c40';
      ctx.fillRect(17+k*27,129,21,4);
    }
  }
  ctx.fillStyle='#d8b482';ctx.font='17px monospace';ctx.fillText(small,16,177,353);
  ctx.restore();
}

export class TerminalScreens{
  constructor(terminals){
    this.bays=Object.fromEntries(Object.entries(terminals?.bays??{}).map(([id,bay])=>[id,installTerminal(bay)]));
    this.coupling=terminals?.bays.aster.coupling;
  }
  update(s,m,time){
    for(const [id,bay] of Object.entries(this.bays)){
      if(!bay.root.visible||time-bay.last<.48)continue;
      bay.last=time;const c=bay.ctx,ground=id==='anchor',clamp=s.clamp||0;
      tile(c,0,'ANCHOR MET   /   OCEAN',m.km<1?'CAR 07 ABOVE':'UPLINK ACTIVE',Math.round(m.km*1000).toLocaleString('en-US')+' m   |   '+crewClock(m.forces.shipSeconds),time,0);
      tile(c,1,'ASTER REACH   /   BAY 03',m.remainingMeters<.25?this.coupling.status.toUpperCase():'ACQUIRING',
        m.remainingMeters.toFixed(m.remainingMeters<100?1:0)+' m   |   CLAMPS '+clamp+'/3',time,0);
      tile(c,2,ground?'GANTRY   /   DRIVE RETURN':'CAPTURE   /   DETENT',ground?(m.seconds<9?'BRIDGE LOCK':'GUIDE CLEAR'):('CLAMP '+clamp+' OF 3'),
        ground?'FEED A + B    '+m.speed+' km/h':(m.remainingMeters<2?'FOLLOWER '+(18*this.coupling.travel).toFixed(1)+' mm':'RANGE TRACKING'),time,0);
      tile(c,3,ground?'EAST GUIDE   /   TACH':'BERTH BEACON   /   RX','','REFERENCE  1.00 kHz   |   LOCKED',time,ground?.58+Math.min(1,m.speed/612)*.37:.85);
      bay.texture.needsUpdate=true;
    }
  }
}
