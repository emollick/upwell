// Persistent passenger viewpoints. Every button selects a camera in the same
// simulated scene as the walkable carriage and its onboard monitor.
export class CabinViews {
  constructor(element,onView,onWalk){
    this.element=element;this.buttons=new Map();element.replaceChildren();
    this.tray=document.createElement('nav');this.tray.className='watch-tray';this.tray.setAttribute('aria-label','Passenger viewing position');
    const picker=document.createElement('label');picker.className='watch-picker';
    this.select=document.createElement('select');this.select.setAttribute('aria-label','Window view');
    this.select.onchange=()=>onView(this.select.value);picker.append(this.select);this.tray.append(picker);
    for(const [id,label] of [['window','Cabin window'],['shaded','Shaded side window'],['floor','Floor port'],['forward','Forward camera'],['earth','Earth camera'],['guide','Guide rollers'],['counter','Counterline'],['stars','Star field'],['colony','Colony optics'],['valley','Valley gallery']]){
      const b=document.createElement('button');b.type='button';b.textContent=label;b.onclick=()=>onView(id);
      if(id==='shaded')b.title='Look opposite the Sun through the saloon glazing (O)';
      this.tray.append(b);this.buttons.set(id,b);
      this.select.add(new Option(label,id));
    }
    this.aisle=document.createElement('button');this.aisle.className='back-aisle';this.aisle.textContent='Stand up';this.aisle.onclick=onWalk;this.tray.append(this.aisle);
    this.open=document.createElement('button');this.open.className='watch-open';this.open.textContent='Window views';this.open.onclick=()=>onView('window');
    element.append(this.tray,this.open);
  }
  update(seated,view,room='observation'){
    this.element.hidden=false;this.tray.hidden=!seated;this.open.hidden=seated;
    for(const [id,b] of this.buttons){
      b.setAttribute('aria-pressed',String(id===view));
      if(id==='floor'||id==='shaded'){
        const option=this.select.querySelector('[value="'+id+'"]');option.disabled=option.hidden=b.hidden=room!=='observation';
      }
    }
    this.select.value=view;
  }
  setDocked(docked){
    if(this.docked===docked)return;this.docked=docked;
    const b=this.buttons.get('colony');b.textContent=docked?'Colony · hub relay':'Colony optics';
    const local=this.buttons.get('valley'),option=this.select.querySelector('[value="valley"]');
    local.hidden=option.hidden=option.disabled=!docked;
    local.title='Look into Aster Reach from its axial transfer gallery';
    this.select.querySelector('[value="colony"]').textContent=b.textContent;
    b.title=docked?'Colony optics via the receiving hub':'Carriage-mounted colony optics';
  }
  setLowLoad(low){
    if(this.lowLoad===low)return;
    this.lowLoad=low;this.aisle.textContent=low?'Push off':'Stand up';
    this.aisle.title=low?'Leave the viewing position and push off into the cabin (Space)':'Return to the aisle';
  }
}
