import * as T from 'three';

export async function loadGalacticLight(){
  const response=await fetch(new URL('./assets/planet/galactic-light.rgba',import.meta.url));
  if(!response.ok)throw Error('Could not load Galactic photometry');
  const data=new Uint8Array(await response.arrayBuffer());
  if(data.length!==360*180*4)throw Error('Incomplete Galactic photometry');
  const texture=new T.DataTexture(data,360,180,T.RGBAFormat);
  texture.wrapS=T.RepeatWrapping;texture.minFilter=texture.magFilter=T.LinearFilter;texture.needsUpdate=true;
  return texture;
}

export async function loadStarCatalog(){
  const response=await fetch(new URL('./assets/planet/bright-stars.bin',import.meta.url));
  if(!response.ok)throw Error('Could not load the stellar catalogue');
  const data=new Uint8Array(await response.arrayBuffer()),header=new DataView(data.buffer);
  if(header.getUint32(0)!==0x59535431||data[4]!==64||data[5]!==16)throw Error('Unknown stellar catalogue format');
  const pixels=new Uint8Array(1024*384*4),groups=header.getUint16(8,true);
  let at=12;
  for(let i=0;i<groups;i++){
    const tile=header.getUint16(at,true),count=data[at+2];at+=3;
    pixels.set(data.subarray(at,at+count*4),tile*16*4);at+=count*4;
  }
  if(at!==data.length)throw Error('Incomplete stellar catalogue');
  const texture=new T.DataTexture(pixels,1024,384,T.RGBAFormat);
  texture.minFilter=texture.magFilter=T.NearestFilter;texture.generateMipmaps=false;texture.needsUpdate=true;
  return texture;
}

// Bright equipment bleaches sensitivity quickly. Darkness restores it over several
// passenger seconds, independent of ship time. The optical camera has its own gain.
export function adaptStellarEye(previous,state,metrics,dt){
  const glare=(state.lamps ? .76 : 0)+.032*state.panelGain+.24*metrics.sunVisible*Math.max(0,metrics.sunDirection[1]);
  const target=Math.max(0,1-glare);
  return previous+(target-previous)*(1-Math.exp(-Math.max(0,dt)/(target>previous?4.0:.38)));
}

export const STELLAR_GLSL=`
uniform sampler2D starCatalogue;
uniform sampler2D galacticLight;
uniform vec2 siderealBasis;
uniform float stellarEye;
vec3 catalogueLight(vec3 ray){
  // Local equatorial frame (+X east,+Y zenith,+Z north) to J2000 directions.
  vec3 dir=vec3(dot(ray.xy,vec2(-siderealBasis.y,siderealBasis.x)),dot(ray.xy,siderealBasis),ray.z);
  vec3 a=abs(dir);vec2 uv;float face,major;
  if(a.x>=a.y&&a.x>=a.z){face=dir.x>=0.?0.:1.;major=a.x;uv=dir.yz;}
  else if(a.y>=a.z){face=dir.y>=0.?2.:3.;major=a.y;uv=dir.zx;}
  else{face=dir.z>=0.?4.:5.;major=a.z;uv=dir.xy;}
  vec2 grid=(uv/major*.5+.5)*64.,tile=clamp(floor(grid),0.,63.);
  vec2 pixel=clamp(vec2(length(vec2(dFdx(grid.x),dFdy(grid.x))),length(vec2(dFdx(grid.y),dFdy(grid.y)))),.003,.30);
  vec2 cellCentre=vec2(tile.x*16.+.5,tile.y+64.*face+.5),local=grid-tile;
  // ICRS to Galactic rotation. Map the two IPP bands into a near-achromatic
  // scotopic response. The bright catalogue stars were removed from the maps.
  vec3 gal=vec3(dot(dir,vec3(-.05487556,-.87343709,-.48383502)),
                dot(dir,vec3(.49410943,-.44482963,.74698224)),dot(dir,vec3(-.86766615,-.19807637,.45598378)));
  vec2 bands=texture2D(galacticLight,vec2(atan(gal.y,gal.x)/6.2831853,asin(clamp(gal.z,-1.,1.))/3.14159265+.5)).rg;
  bands=bands*bands*vec2(768.,1536.);
  float adapted=smoothstep(.15,.95,stellarEye);
  float diffuse=max(0.,dot(bands,vec2(.72,.2016))-28.)*.000074*adapted*adapted;
  vec3 light=vec3(.96,1.,1.055)*diffuse;
  for(int i=0;i<16;i++){
    vec4 entry=texture2D(starCatalogue,(cellCentre+vec2(float(i),0.))/vec2(1024.,384.));
    if(entry.b<.001)break;
    float magnitude=(entry.b*255.-1.)*(8./254.)-1.5;
    float visible=smoothstep(-.55,.55,mix(3.60,6.58,stellarEye)-magnitude);
    if(visible<=0.)break;
    vec2 delta=(local-(entry.rg*1.6-.30))/pixel;
    float square=dot(delta,delta);
    // The unresolved source is sampled at the final display size. A narrow core
    // and an optical skirt soften the brightest stars without diffraction spikes.
    float core=exp(-1.26*square),skirt=exp(-.23*square);
    float energy=.79*exp2(-1.02*magnitude);
    float radiance=energy*(core+.048*skirt)*visible*mix(.48,1.,stellarEye);
    float bv=entry.a*2.6-.4;
    vec3 cool=mix(vec3(.65,.79,1.),vec3(1.,.98,.94),smoothstep(-.3,.58,bv));
    vec3 colour=mix(cool,vec3(1.,.63,.42),smoothstep(.58,1.85,bv));
    light+=radiance*mix(vec3(1.),colour,1.-.66*smoothstep(0.,3.,magnitude));
  }
  return light;
}`;
