// Rasterize the same licensed Geist Mono face used by the browser instruments.
// Unity's dynamic telemetry can then draw it without loading a font/UI camera.
const {chromium}=require('playwright');
const fs=require('node:fs');
const path=require('node:path');

(async()=>{
  const root=path.resolve(__dirname,'..');
  const source=fs.readFileSync(path.join(root,'web/assets/fonts/geist-mono-latin.woff2')).toString('base64');
  const browser=await chromium.launch({channel:'chrome'});
  try{
    const page=await browser.newPage();
    const masks=await page.evaluate(async data=>{
      const face=await new FontFace('Cockpit Mono','url(data:font/woff2;base64,'+data+')',{weight:'100 900'}).load();
      document.fonts.add(face);
      const chars=Array.from({length:95},(_,i)=>String.fromCharCode(32+i)).join('')+'°²±×∞Á';
      const bytes=[];
      for(const size of [1,2,3]){
        const w=6*size,h=9*size,supersample=4;
        const high=document.createElement('canvas'),low=document.createElement('canvas');
        high.width=w*supersample;high.height=h*supersample;low.width=w;low.height=h;
        const a=high.getContext('2d'),b=low.getContext('2d',{willReadFrequently:true});
        a.font='550 '+(9.8*size*supersample)+'px "Cockpit Mono"';
        a.textAlign='center';a.fillStyle='white';b.imageSmoothingQuality='high';
        for(const ch of chars){
          a.clearRect(0,0,high.width,high.height);b.clearRect(0,0,w,h);
          a.fillText(ch,high.width/2,7.35*size*supersample);b.drawImage(high,0,0,w,h);
          const rgba=b.getImageData(0,0,w,h).data;
          for(let i=3;i<rgba.length;i+=4)bytes.push(rgba[i]);
        }
      }
      return bytes;
    },source);
    const name=path.join(root,'unity/Assets/Upwell/Resources/DisplayLettering.bytes');
    fs.writeFileSync(name,Buffer.from(masks));console.log('Baked '+masks.length+' bytes of instrument glyph coverage.');
  }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
