const LIMIT=6;
const DATABASE='upwell-passenger-photos';

function readDatabase(){
  return new Promise((resolve,reject)=>{
    const request=indexedDB.open(DATABASE,1);
    request.onupgradeneeded=()=>request.result.createObjectStore('photos',{keyPath:'id',autoIncrement:true});
    request.onsuccess=()=>resolve(request.result);
    request.onerror=()=>reject(request.error);
  });
}

function transact(db,mode,operation){
  return new Promise((resolve,reject)=>{
    const transaction=db.transaction('photos',mode),store=transaction.objectStore('photos');
    let result;
    operation(store,value=>{result=value;});
    transaction.oncomplete=()=>resolve(result);
    transaction.onerror=transaction.onabort=()=>reject(transaction.error??new Error('Photo storage unavailable'));
  });
}

function photoClock(seconds){
  const n=Math.floor(seconds);
  return String(Math.floor(n/60)).padStart(2,'0')+':'+String(n%60).padStart(2,'0');
}
function caption(photo){
  const g=Math.abs(photo.load)<.0005?0:photo.load;
  const alt=photo.km<1?Math.round(photo.km*1000)+' m':Math.round(photo.km).toLocaleString('en-US')+' km';
  return 'Route '+photoClock(photo.passage)+'  ·  '+alt+'  ·  '+(g>0?'+':g<0?'−':'')+Math.abs(g).toFixed(3)+' g';
}
function element(tag,className,text){
  const el=document.createElement(tag);if(className)el.className=className;
  if(text!==undefined)el.textContent=text;return el;
}
function action(text,callback,className='quiet'){
  const button=element('button',className,text);button.type='button';button.onclick=callback;return button;
}

export class PhotoJournal{
  constructor(dialog,notify,prepare){
    this.dialog=dialog;this.notify=notify;this.prepare=prepare;this.urls=new Map();this.photos=[];
    this.body=dialog.querySelector('[data-photos]');this.count=dialog.querySelector('[data-photo-count]');
    dialog.querySelector('[data-close-photos]').onclick=()=>dialog.close();
    dialog.addEventListener('close',()=>{
      this.requestVersion++;this.clearUrls();this.photos=[];this.selected=null;this.body.replaceChildren();
    });
    dialog.addEventListener('cancel',e=>{if(this.selected!==null){e.preventDefault();this.showGrid(true);}});
    this.requestVersion=0;this.selected=null;this.waiting=false;this.encoding=false;
  }
  connection(){
    if(!this.connectionPromise)this.connectionPromise=readDatabase().catch(err=>{this.connectionPromise=null;throw err;});
    return this.connectionPromise;
  }
  async list(){
    return transact(await this.connection(),'readonly',(store,done)=>{
      const rows=store.getAll();rows.onsuccess=()=>done(rows.result.reverse());
    });
  }
  async add(photo){
    return transact(await this.connection(),'readwrite',(store,done)=>{
      const slots=store.count();
      slots.onsuccess=()=>{
        if(slots.result>=LIMIT){done(0);return;}
        store.add(photo);done(slots.result+1);
      };
    });
  }
  request(){
    if(!this.dialog.open&&!this.waiting&&!this.encoding)this.waiting=true;
  }
  capture(canvas,metadata){
    if(!this.waiting)return;
    this.waiting=false;this.encoding=true;
    const complete=()=>{this.encoding=false;};
    try{
      const negative=document.createElement('canvas');
      const scale=Math.min(1,960/Math.max(canvas.width,canvas.height));
      negative.width=Math.max(1,Math.round(canvas.width*scale));
      negative.height=Math.max(1,Math.round(canvas.height*scale));
      const context=negative.getContext('2d',{alpha:false});
      context.drawImage(canvas,0,0,negative.width,negative.height);
      const photo={...metadata,width:negative.width,height:negative.height};
      negative.toBlob(async image=>{
        try{
          if(!image)throw new Error('Frame could not be encoded');
          const n=await this.add({...photo,image});
          this.notify(n?'Photo saved  ·  '+n+' / '+LIMIT:'Journal full. Delete a photo to make room.');
          if(this.dialog.open)await this.refresh();
        }catch{this.notify('Could not save this photo on this device.');}
        finally{complete();}
      },'image/jpeg',.81);
    }catch{complete();this.notify('Could not save this photo on this device.');}
  }
  clearUrls(){
    for(const url of this.urls.values())URL.revokeObjectURL(url);
    this.urls.clear();
  }
  async open(){
    if(this.dialog.open)return;
    this.prepare();this.selected=null;this.count.textContent='';this.body.replaceChildren();
    this.dialog.showModal();await this.refresh();
  }
  async refresh(){
    const version=++this.requestVersion;
    try{
      const photos=await this.list();
      if(!this.dialog.open||version!==this.requestVersion)return;
      this.clearUrls();this.photos=photos;
      for(const p of photos)this.urls.set(p.id,URL.createObjectURL(p.image));
      this.count.textContent=photos.length+' / '+LIMIT+' photos';
      const selected=photos.find(p=>p.id===this.selected);
      if(selected)this.showPhoto(selected,false);else this.showGrid();
    }catch{
      if(this.dialog.open&&version===this.requestVersion)
        this.body.replaceChildren(element('p','photo-empty','Photo storage is unavailable on this device.'));
    }
  }
  image(photo){
    const img=element('img');img.src=this.urls.get(photo.id);
    img.alt=photo.viewpoint+' at route '+photoClock(photo.passage);img.width=photo.width;img.height=photo.height;return img;
  }
  showGrid(focus=false){
    const prior=this.selected;this.selected=null;this.body.replaceChildren();this.body.className='photo-grid';
    if(!this.photos.length){this.body.append(element('p','photo-empty','Use the shutter to save a view of your passage.'));return;}
    for(const photo of this.photos){
      const card=action('',()=>this.showPhoto(photo,true),'photo-card');
      card.setAttribute('aria-label','Open '+photo.viewpoint+' at route '+photoClock(photo.passage));
      card.append(this.image(photo),element('strong','',photo.viewpoint),element('span','photo-caption',caption(photo)));
      this.body.append(card);if(focus&&photo.id===prior)card.focus();
    }
  }
  showPhoto(photo,focus){
    this.selected=photo.id;this.body.className='photo-detail';this.body.replaceChildren();
    const actions=element('div','photo-actions'),back=action('All photos',()=>this.showGrid(true));
    const del=action('Delete photo',async()=>{
      del.disabled=true;
      try{
        await transact(await this.connection(),'readwrite',store=>store.delete(photo.id));
        this.selected=null;await this.refresh();
        (this.body.querySelector('button')??this.dialog.querySelector('[data-close-photos]')).focus();
      }catch{del.disabled=false;this.count.textContent='Could not delete this photo on this device.';}
    });
    actions.append(back,del);
    this.body.append(this.image(photo),element('h3','',photo.viewpoint),element('p','photo-caption',caption(photo)),actions);
    if(focus)back.focus();
  }
}
