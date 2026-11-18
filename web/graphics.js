const storageKey='upwell.graphics.1';
export const defaultGraphics=Object.freeze({aa:'auto',shadows:'auto',resolution:'auto'});
const choices={aa:['auto','off','fxaa','msaa2','msaa4','msaa8'],shadows:['auto','off','standard','fine'],resolution:['auto','0.75','1','1.5']};

export function readGraphics(software){
  let saved;
  try{
    const profile=localStorage.getItem(storageKey+(software?'.software':'.hardware'));
    saved=JSON.parse(profile??(software?null:localStorage.getItem(storageKey)));
  }catch{}
  const result={...defaultGraphics};
  for(const [key,values] of Object.entries(choices))if(values.includes(saved?.[key]))result[key]=saved[key];
  return result;
}
function saveGraphics(world){
  try{localStorage.setItem(storageKey+(world.softwareGpu?'.software':'.hardware'),JSON.stringify(world.graphics));}catch{}
}

export class GraphicsDialog{
  constructor(dialog,getWorld,onOpen){
    this.dialog=dialog;this.getWorld=getWorld;this.beforeOpen=onOpen;
    this.controls=Object.fromEntries([...dialog.querySelectorAll('select')].map(s=>[s.name,s]));
    this.readout=dialog.querySelector('output');
    for(const select of Object.values(this.controls))select.onchange=()=>{
      const world=getWorld();
      world.applyGraphics({...world.graphics,[select.name]:select.value});saveGraphics(world);this.refresh();
    };
    dialog.querySelector('[data-defaults]').onclick=()=>{
      const world=getWorld();world.applyGraphics({...defaultGraphics});saveGraphics(world);this.showValues();
    };
    dialog.querySelector('[data-done]').onclick=()=>dialog.close();
    dialog.addEventListener('click',event=>{
      if(event.target!==dialog)return;
      const box=dialog.getBoundingClientRect(),{clientX:x,clientY:y}=event;
      if(x<box.left||x>box.right||y<box.top||y>box.bottom)dialog.close();
    });
  }
  showValues(){
    const world=this.getWorld();
    for(const [key,control] of Object.entries(this.controls))control.value=world.graphics[key];
    this.refresh();
  }
  open(){
    const world=this.getWorld();if(!world||this.dialog.open)return;
    this.beforeOpen();
    this.controls.aa.replaceChildren(...world.optics.aaModes.map(([id,label])=>new Option(label,id)));
    this.controls.aa.disabled=world.optics.aaModes.length===1;
    this.dialog.showModal();this.showValues();
  }
  refresh(){
    if(!this.dialog.open)return;
    const w=this.getWorld(),canvas=w.r.domElement;
    const parts=[canvas.width+' × '+canvas.height+' px',w.optics.activeAA];
    if(w.softwareGpu)parts.push('Software renderer');
    if(w.resolutionLimited)parts.push('Scale limited');
    const message=parts.join('  ·  ');
    if(this.readout.textContent!==message)this.readout.textContent=message;
  }
}
