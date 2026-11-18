import * as T from 'three';
import { smooth } from './journey.js';
import { sampleCloudTransmission } from './weather-density.js';

const color=(r,g,b)=>new T.Color(r,g,b);

// This field stores solid angles through six real pressure apertures. Opaque
// bunks, consoles, casings and window webs were present during the ray survey.
// One pair of bilinear texture reads interpolates it in three dimensions.
const apertureFields={
  volume:{value:null},sky:{value:new T.Vector4()},earth:{value:new T.Vector3()},
  sun:{value:new T.Vector3()},gain:{value:new T.Vector4(0,0,0,1)}
};
let aperturePromise;
export function loadApertures(){
  return aperturePromise??=new T.TextureLoader().loadAsync('./assets/finish/aperture-transfer.png').then(map=>{
    map.colorSpace=T.NoColorSpace;map.flipY=false;map.generateMipmaps=false;
    map.minFilter=map.magFilter=T.LinearFilter;map.needsUpdate=true;apertureFields.volume.value=map;
  });
}
const daylightTransfer=`
  uniform sampler2D apertureVolume;uniform vec4 apertureSky,apertureGain;
  uniform vec3 apertureEarth,apertureSun;varying vec3 vCabinLightPos;
  vec2 apertureUV(vec2 xy,float layer){
    return (vec2(mod(layer,12.),floor(layer/12.))*vec2(36.,24.)+xy+.5)/vec2(432.,192.);
  }
  vec3 windowIrradiance(vec3 p,vec3 n,out float ambientFactor){
    vec3 q=clamp((p+n*.084-vec3(-2.27,-.08,-5.83))/vec3(4.54,2.83,11.66),0.,1.)*vec3(35.,23.,95.);
    float i=floor(q.z);
    vec4 field=mix(texture2D(apertureVolume,apertureUV(q.xy,i)),texture2D(apertureVolume,apertureUV(q.xy,min(i+1.,95.))),q.z-i);
    field*=field;bool fore=p.z< -1.90;
    vec3 east=vec3(2.18,fore?1.76:1.85,fore?-3.80:.03)-p,west=vec3(-2.18,fore?1.76:1.68,fore?-3.80:3.68)-p;
    vec3 front=vec3(0.,1.59,-5.67)-p,floorPort=vec3(0.,-.132,-3.80)-p;
    vec4 cosine=vec4(dot(n,normalize(east)),dot(n,normalize(west)),dot(n,normalize(front)),dot(n,normalize(floorPort)));
    vec4 flux=field*clamp(cosine+.25*field*(1.-abs(cosine)),0.,1.);flux.z*=apertureGain.w;
    ambientFactor=1.-apertureSky.a*(1.-clamp(dot(field,vec4(2.)),0.,1.));
    return apertureSky.rgb*(flux.x+flux.y+flux.z)+apertureEarth*flux.w+apertureSun*dot(flux.xyz,apertureGain.xyz);
  }`;
export function installApertureResponse(meshes){
  const used=new Set();
  for(const mesh of meshes){
    const m=mesh.material;
    if(used.has(m)||!m?.isMeshStandardMaterial||m.transparent||m.alphaTest>.01||m.emissive?.getHex())continue;
    used.add(m);const previous=m.onBeforeCompile,cacheKey=m.customProgramCacheKey();
    m.onBeforeCompile=function(shader,renderer){
      previous.call(this,shader,renderer);
      for(const id of ['volume','sky','earth','sun','gain'])shader.uniforms['aperture'+id[0].toUpperCase()+id.slice(1)]=apertureFields[id];
      shader.vertexShader=shader.vertexShader.replace('#include <common>','#include <common>\nvarying vec3 vCabinLightPos;')
        .replace('#include <project_vertex>','#include <project_vertex>\nvCabinLightPos=(modelMatrix*vec4(transformed,1.)).xyz;');
      shader.fragmentShader=shader.fragmentShader.replace('#include <common>','#include <common>\n'+daylightTransfer)
        .replace('#include <aomap_fragment>',`float roomAmbient;
          vec3 apertureRadiance=windowIrradiance(vCabinLightPos,inverseTransformDirection(normal,viewMatrix),roomAmbient);
          reflectedLight.indirectDiffuse=reflectedLight.indirectDiffuse*roomAmbient+
            diffuseColor.rgb*(1.-metalnessFactor)*apertureRadiance;
          #include <aomap_fragment>`);
    };
    m.customProgramCacheKey=()=>cacheKey+'/aperture-irradiance';m.needsUpdate=true;
  }
}
function updateApertures(m,beam,dock,film){
  const {sky,earth,sun,gain}=apertureFields,dir=m.sunDirection;
  const air=(1-smooth(12,145,m.km))*smooth(-.12,.32,dir[1]);
  const size=6371/(6371+Math.max(0,m.km)),disk=1-Math.sqrt(Math.max(0,1-size*size));
  const angle=Math.acos(T.MathUtils.clamp(dir[1],-1,1)),ground=disk*(Math.sin(angle)+(Math.PI-angle)*Math.cos(angle))/Math.PI;
  const cover=1-.72*dock,skyFlux=air*(1.75+1.58*(1-beam))*cover,land=1.20*ground*cover;
  sky.value.set((.94+(.45-.94)*beam)*skyFlux+.39*land,(.95+(.64-.95)*beam)*skyFlux+.56*land,
    (.93+(1.-.93)*beam)*skyFlux+.77*land,.29*air);
  earth.value.set(.84+(.39-.84)*beam,.89+(.54-.89)*beam,.92+(.69-.92)*beam).multiplyScalar(2.7*ground*cover);
  const high=smooth(.04,.43,dir[1]),direct=m.sunVisible*beam*(.18+1.4*air)*cover;
  sun.value.set(1,.79+.15*high,.55+.29*high).multiplyScalar(direct);
  gain.value.set(Math.max(0,dir[0]),Math.max(0,-dir[0]),Math.max(0,-dir[2]),1-.82*film);
}

// Measured detail maps carry small-scale surface structure. Coating, weave
// and directional reflection require different lobes under the same sun.
export function physicalSurface(source) {
  if (!source?.isMeshStandardMaterial || source.emissive?.getHex() || source.alphaTest>.01) return source;
  const name=source.name;
  const furnishing=/Quilt_Ripstop|Quilt_Lining|Curtain_Acoustic/.test(name);
  const yarn=furnishing||/Twill|Webbing|Pressure_Fabric|Wallet_Canvas|Surface_(lounge_seat|bunk|tool_roll|privacy_curtain|logbook)/i.test(name);
  const metal=/Titanium|Aluminum|Graphite_Alloy|Vessel_Keeper|Credential_Contacts|Machined|Bead_Blast/i.test(name);
  const coat=/Ceramic|Composite|Vessel_Enamel|Surface_(mug|service_cabinet|pressure_hatch|locker_drawer|access_card)/i.test(name);
  const optics=/Optical_Coating|Lens_Glass|Optic_Lens|Sapphire/i.test(name);
  if(!yarn&&!metal&&!coat&&!optics)return source;
  const m=new T.MeshPhysicalMaterial();
  T.MeshStandardMaterial.prototype.copy.call(m,source);m.defines.PHYSICAL='';
  if(yarn){m.sheen=.65;m.sheenRoughness=.83;m.sheenColor.setRGB(.39,.45,.46);m.metalness=0;}
  if(furnishing){
    m.clearcoat=0;m.sheen=.27;m.sheenRoughness=.91;m.sheenColor.setRGB(.24,.27,.26);
    m.specularIntensity=.22;m.roughness=Math.max(.9,m.roughness);m.normalScale.multiplyScalar(1.40);
  }
  if(metal){m.anisotropy=/Aluminum|Titanium/i.test(name)?.44:.29;m.clearcoat=.06;m.clearcoatRoughness=.25;}
  if(coat){m.clearcoat=/access_card/i.test(name)?.59:.27;m.clearcoatRoughness=.29;m.ior=1.49;}
  if(name==='Vessel_Enamel'){m.clearcoat=.36;m.clearcoatRoughness=.26;m.specularIntensity=.64;}
  if(optics){m.ior=1.52;m.clearcoat=1;m.clearcoatRoughness=.035;m.roughness=.055;m.iridescence=.34;
    m.iridescenceIOR=1.29;m.iridescenceThicknessRange=[90,235];}
  return m;
}

export class CabinLight {
  constructor(scene,renderer,exterior){
    this.scene=scene;this.renderer=renderer;this.exterior=exterior;
    this.beam=1;this.cloudAt=-100;this.sunAt=-1;this.probeAt=-100;this.probeKey='';
    this.hemi=new T.HemisphereLight(0xcadfe9,0x5c6561,.64);this.hemi.layers.enable(1);scene.add(this.hemi);
    this.sun=new T.DirectionalLight(0xffe5c5,3.5);this.sun.layers.enable(1);
    this.sun.castShadow=true;this.sun.shadow.mapSize.set(2048,2048);this.sun.shadow.normalBias=.0055;
    this.sun.shadow.bias=-.000055;
    Object.assign(this.sun.shadow.camera,{left:-11.2,right:11.2,top:11,bottom:-11,near:.3,far:114});
    this.sun.shadow.camera.layers.enable(1);
    this.sun.target.position.set(0,1.14,-.75);scene.add(this.sun,this.sun.target);
    this.baySpots=[];
    for(let i=0;i<2;i++){
      const l=new T.SpotLight(0xffd7ab,0,43,.69,.66,2);l.layers.enable(1);l.castShadow=true;
      l.shadow.mapSize.set(1024,1024);l.shadow.normalBias=.004;l.shadow.bias=-.00009;
      l.shadow.camera.near=.28;l.shadow.camera.far=44;l.shadow.camera.layers.enable(1);
      scene.add(l,l.target);this.baySpots.push(l);
    }
    this.bayFill=[];
    for(let i=0;i<3;i++){
      const lamp=new T.PointLight(0xffe2cb,0,18,2);lamp.layers.enable(1);scene.add(lamp);this.bayFill.push(lamp);
    }
    this.localProbe=new T.WebGLCubeRenderTarget(64,{type:T.HalfFloatType,generateMipmaps:false});
    this.cubeCamera=new T.CubeCamera(.045,1900,this.localProbe);
    this.cubeCamera.layers.enable(1);this.cubeCamera.children.forEach(c=>c.layers.enable(1));
    this.skyProbe=new T.WebGLCubeRenderTarget(64,{type:T.HalfFloatType,generateMipmaps:true,minFilter:T.LinearMipmapLinearFilter});
    this.skyCam=new T.CubeCamera(.065,2100,this.skyProbe);this.skyCam.layers.set(3);
    this.skyCam.children.forEach(c=>c.layers.set(3));this.exterior.planet.mesh.layers.enable(3);
    this.outsideMaterials=new Set();this.exterior.root.traverse(n=>{if(n.isMesh&&n.material?.isMeshStandardMaterial)this.outsideMaterials.add(n.material);});
    this.filter=new T.PMREMGenerator(renderer);
    this.warm=color(1,.56,.27);this.day=color(1,.97,.90);this.blue=color(.48,.66,1);
    this.skyColor=new T.Color();this.down=color(.19,.23,.24);this.solar=new T.Vector3();this.lastSolar=new T.Vector3();
    this.filteredScene=null;this.lastProbeRoom='';
  }
  dockLighting(m){
    const anchor=m.km<2.2, arriving=m.remainingMeters<2000;
    const bay=this.exterior.terminals.bays[anchor?'anchor':'aster'];
    const strength=anchor?1-smooth(.017,.064,m.km):arriving?1-smooth(12,70,m.remainingMeters):0;
    const below=arriving&&!anchor&&m.remainingMeters>8;
    const fixtures=bay.spec.lights.filter(l=>(below?/underdeck_[01]$/:/front_key|capture_key/).test(l.id));
    this.baySpots.forEach((lamp,i)=>{
      const data=fixtures[i];
      lamp.intensity=data&&(anchor||arriving)?data.power*(i===0?1.12:.51):0;
      if(!data||!lamp.intensity)return;
      lamp.position.fromArray(data.position).add(bay.root.position);lamp.target.position.fromArray(data.target).add(bay.root.position);
      lamp.color.fromArray(data.color);lamp.angle=below?.94:anchor?.72:.78;
    });
    const all=bay.spec.lights.filter(l=>(below?/underdeck_[245]$/:/booth|gallery|sea_portal/).test(l.id));
    this.bayFill.forEach((l,i)=>{
      const f=all[i];l.intensity=f&&(anchor||arriving)?f.power*(below?.88:/booth/.test(f.id)?.57:.29):0;
      if(!l.intensity)return;l.position.fromArray(f.position).add(bay.root.position);l.position.y-=.31;
      l.color.fromArray(f.color);
    });
    return strength;
  }
  update(s,m,time,dt,eye,stargazing=false){
    const cut=Math.abs(this.sunAt-m.seconds)>1.5;
    if(cut||time-this.cloudAt>.13){
      this.transmission=sampleCloudTransmission(m.km,m.weatherSeconds,m.sunDirection,m.weather);
      this.cloudAt=time;
    }
    this.sunAt=m.seconds;
    this.beam=T.MathUtils.lerp(this.beam,this.transmission??1,cut?1:1-Math.exp(-dt*6));
    const atmosphere=Math.exp(-m.km/8);
    this.solar.fromArray(m.sunDirection);
    this.sun.position.copy(this.sun.target.position).addScaledVector(this.solar,53);
    const warm=atmosphere*(1-smooth(.03,.46,this.solar.y));
    this.sun.color.copy(this.day).lerp(this.warm,warm*.83);
    this.sun.intensity=(3.95+.85*(1-atmosphere))*m.sunVisible*this.beam*(1-.31*warm);
    this.sun.shadow.radius=1.1+2.2*(1-this.beam);
    const dock=this.dockLighting(m);
    const air=smooth(-.10,.32,this.solar.y)*(1-smooth(12,155,m.km));
    const skyColor=this.skyColor.copy(this.blue).lerp(color(.85,.83,.75),atmosphere*(1-this.beam)*.77);
    this.hemi.color.copy(skyColor);this.hemi.groundColor.copy(this.down);
    this.hemi.intensity=.19+.78*air+.32*dock+.16*m.sunVisible;
    this.scene.environmentIntensity=.92;
    this.exterior.beam=this.beam;
    this.exposure=T.MathUtils.lerp(this.exposure??1.06,1.10+.09*dock+.15*(1-air),cut?1:1-Math.exp(-dt*.85));
    this.renderer.toneMappingExposure=this.exposure;
    const film=this.shadeTravel?.v??Number(s.shade);
    this.bounce=(.20+air*(1.55+1.20*(1-this.beam))+.29*m.sunVisible)*(1-.52*film)*.49;
    updateApertures(m,this.beam,dock,film);
    const region=eye.z < -1.9?'observation':eye.z<1.9?'berth':'service';
    const key=[region,s.lamps,s.berthLight,s.bayLight,s.shade,s.panelGain,s.cabinet,s.hatch].join('/');
    const dueForRefresh=!stargazing&&time-this.probeAt>(dock?.95:4.3);
    this.wantProbe=cut||this.lastProbeRoom!==region||key!==this.probeKey||dueForRefresh||this.solar.distanceToSquared(this.lastSolar)>.045;
    this.nextProbeKey=key;this.nextProbeRoom=region;
  }
  reflect(time,held){
    if(!this.wantProbe)return;
    const r=this.renderer,auto=r.autoClear,shadows=r.shadowMap.autoUpdate;
    const prev=held?.visible;
    if(held)held.visible=false;
    r.autoClear=true;r.shadowMap.autoUpdate=false;
    this.exterior.planet.setOceanSky(null);
    this.skyCam.position.set(0,3.1,-6.1);this.skyCam.updateMatrixWorld();this.skyCam.update(r,this.scene);
    this.exterior.planet.setOceanSky(this.skyProbe.texture);
    this.outdoorLight=this.filter.fromCubemap(this.skyProbe.texture,this.outdoorLight);
    for(const mat of this.outsideMaterials){
      if(mat.envMap!==this.outdoorLight.texture){
        mat.envMap=this.outdoorLight.texture;mat.envMapIntensity=.88;mat.needsUpdate=true;
      }
    }
    this.exterior.sea.setEnvironment(this.skyProbe.texture);
    const z=this.nextProbeRoom==='observation'?-3.83:this.nextProbeRoom==='berth'?-.08:3.73;
    this.cubeCamera.position.set(.12,1.34,z);this.cubeCamera.updateMatrixWorld();
    this.cubeCamera.update(r,this.scene);
    this.filteredScene=this.filter.fromCubemap(this.localProbe.texture,this.filteredScene);
    this.scene.environment=this.filteredScene.texture;
    r.autoClear=auto;r.shadowMap.autoUpdate=shadows;
    if(held)held.visible=prev;
    this.probeAt=time;this.probeKey=this.nextProbeKey;this.lastProbeRoom=this.nextProbeRoom;
    this.lastSolar.copy(this.solar);this.wantProbe=false;
  }
}
