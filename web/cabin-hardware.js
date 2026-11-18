import * as T from 'three';
import {installApertureResponse} from './cabin-light.js';

let survey,atlas,jacketInk,coverCloth,loading;
export function loadCabinContact(){
  if(!loading)loading=Promise.all([
    fetch('./assets/finish/cabin-contact.json').then(r=>{if(!r.ok)throw Error('Cabin contact calibration unavailable');return r.json();}),
    new T.TextureLoader().loadAsync('./assets/finish/cabin-contact.png'),
    new T.TextureLoader().loadAsync('./assets/finish/cable-jacket-print.png'),
    new T.TextureLoader().loadAsync('./assets/finish/berth-cover.png'),
  ]).then(([calibration,texture,ink,cover])=>{
    survey=calibration;
    atlas=texture;atlas.colorSpace=T.NoColorSpace;atlas.flipY=false;
    atlas.minFilter=atlas.magFilter=T.NearestFilter;atlas.generateMipmaps=false;atlas.needsUpdate=true;
    jacketInk=ink;ink.flipY=false;ink.wrapS=T.RepeatWrapping;ink.anisotropy=8;ink.colorSpace=T.NoColorSpace;ink.needsUpdate=true;
    coverCloth=cover;cover.flipY=false;cover.colorSpace=T.NoColorSpace;cover.anisotropy=6;cover.needsUpdate=true;
  });
  return loading;
}
const V=(x=0,y=0,z=0)=>new T.Vector3(x,y,z);
const ignored=new Set(['mug','capillary_cell','capillary_primer','accelerometer','accel_test','field_glasses','logbook','tool_roll','access_card','roller_shade','privacy_curtain']);
const glassNames=new Set(['Diagnostic','Drive','Access','Pressure','Seal','Berth','Service','Intercom']);
function ancestry(mesh){
  let prop='',room='';
  for(let n=mesh;n;n=n.parent){
    if(n.userData.fitting&&!prop)prop=n.userData.fitting;
    if(n.name.startsWith('shell_'))room=n.name.slice(6);
  }
  return {prop,room};
}

// Each projection is baked against the real static triangles. A per-texel
// depth comparison keeps recessed light wells on the well, even at silhouettes.
const occlusionGLSL=`
uniform sampler2D uCabinContact;
uniform vec2 uCabinTilePixels,uCabinAtlasPixels;
varying vec3 vHardwareRest;
float cabinTap(vec2 pix,vec2 tile,float depth,float tol){
  vec2 st=(tile*uCabinTilePixels+clamp(pix,vec2(0.),uCabinTilePixels-1.)+.5)/uCabinAtlasPixels;
  vec3 v=texture2D(uCabinContact,st).rgb;
  float recorded=dot(floor(v.gb*255.+.5),vec2(256.,1.))/8192.;
  return (1.-v.r)*(1.-smoothstep(tol,tol*2.15,abs(recorded-depth)));
}
float cabinSurvey(mat4 m,vec2 tile){
  vec3 proj=(m*vec4(vHardwareRest,1.)).xyz;
  float tol=clamp(.004+fwidth(proj.z)*1.4,.004,.020);
  if(proj.x<0.||proj.x>1.||proj.y<0.||proj.y>1.)return 0.;
  vec2 p=proj.xy*uCabinTilePixels-.5,b=floor(p),f=fract(p);
  return mix(mix(cabinTap(b,tile,proj.z,tol),cabinTap(b+vec2(1.,0.),tile,proj.z,tol),f.x),
    mix(cabinTap(b+vec2(0.,1.),tile,proj.z,tol),cabinTap(b+vec2(1.),tile,proj.z,tol),f.x),f.y);
}`;

function projection(def){
  const o=V(...def.origin),a=V(...def.right).multiplyScalar(1/def.extent[0]);
  const b=V(...def.up).multiplyScalar(-1/def.extent[1]),d=V(...def.forward);
  return new T.Matrix4().set(a.x,a.y,a.z,.5-a.dot(o),b.x,b.y,b.z,.5-b.dot(o),d.x,d.y,d.z,-d.dot(o),0,0,0,1);
}
// Centre lines of the five woven protective conduits in SourceModels. Their
// pitch is in metres along the run, so a braid continues around each elbow.
function bindShieldUV(mesh){
  const lines=[];
  for(const route of survey.shieldPaths){
    const p=[];for(let i=0;i<route.xyz.length;i+=3)p.push(V(...route.xyz.slice(i,i+3)));
    let u=V(1,0,0),arc=0;
    for(let j=0;j<p.length-1;j++){
      const delta=p[j+1].clone().sub(p[j]),length=delta.length();if(length<.0001)continue;
      const t=delta.multiplyScalar(1/length);u=u.clone().addScaledVector(t,-u.dot(t)).normalize();
      lines.push({center:p[j],axis:t,length,u,v:V().crossVectors(t,u),arc});arc+=length;
    }
  }
  const positions=mesh.geometry.attributes.position,a=new Float32Array(positions.count*4),q=V(),n=V();
  for(let i=0;i<positions.count;i++){
    q.fromBufferAttribute(positions,i).applyMatrix4(mesh.matrixWorld);let best=.018*.018;
    for(const line of lines){
      n.subVectors(q,line.center);const t=T.MathUtils.clamp(n.dot(line.axis),0,line.length);
      n.addScaledVector(line.axis,-t);const d=n.lengthSq();
      if(d<best){best=d;n.normalize();a[i*4]=line.arc+t;a[i*4+1]=n.dot(line.u);a[i*4+2]=n.dot(line.v);a[i*4+3]=1;}
    }
  }
  mesh.geometry.setAttribute('shieldMetric',new T.BufferAttribute(a,4));
}
function finishRigid(mesh,panes,kind,hotspot){
  const src=mesh.material,m=src.clone(),parentPass=src.onBeforeCompile,parentKey=src.customProgramCacheKey(),rest=mesh.matrixWorld.clone();
  const brushed=kind==='metal',grip=kind==='grip',coat=kind==='coat',braid=kind==='braid';
  if(kind==='pad'){
    m.map=null;m.normalMap=null;m.roughnessMap=null;m.roughness=.91;
    m.color.setRGB(.063,.091,.099);
  }
  if(braid)bindShieldUV(mesh);
  if(brushed&&m.isMeshPhysicalMaterial){m.anisotropy=.61;m.anisotropyRotation=.24;}
  if(grip){m.metalness=Math.min(m.metalness,.035);m.envMapIntensity*=.8;}
  m.onBeforeCompile=(sh,renderer)=>{
    parentPass.call(src,sh,renderer);
    sh.uniforms.uHardwareRest={value:rest};
    sh.uniforms.uCabinContact={value:atlas};
    sh.uniforms.uCabinTilePixels={value:new T.Vector2(survey.width,survey.height)};
    sh.uniforms.uCabinAtlasPixels={value:new T.Vector2(survey.width*survey.columns,survey.height*survey.rows)};
    sh.uniforms.uRubPoint={value:hotspot};
    let uniforms='',calls='';
    panes.forEach((p,i)=>{
      sh.uniforms['uSurvey'+i]={value:p.matrix};sh.uniforms['uTile'+i]={value:p.tile};
      uniforms+='uniform mat4 uSurvey'+i+';uniform vec2 uTile'+i+';\n';
      calls+='cavity=max(cavity,cabinSurvey(uSurvey'+i+',uTile'+i+'));\n';
    });
    sh.vertexShader=sh.vertexShader.replace('#include <common>','#include <common>\nuniform mat4 uHardwareRest; varying vec3 vHardwareRest;')
      .replace('#include <begin_vertex>','#include <begin_vertex>\nvHardwareRest=(uHardwareRest*vec4(position,1.)).xyz;');
    sh.fragmentShader=sh.fragmentShader.replace('#include <common>','#include <common>\n'+occlusionGLSL+'\n'+uniforms+'uniform vec3 uRubPoint;')
      .replace('#include <aomap_fragment>',`#include <aomap_fragment>
        float cavity=0.; ${calls}
        reflectedLight.indirectDiffuse*=pow(max(.06,1.-cavity),1.43);
        reflectedLight.indirectSpecular*=1.-cavity*.63;`);
    if(kind==='pad'){
      sh.uniforms.berthCover={value:coverCloth};
      sh.fragmentShader=sh.fragmentShader.replace('#include <common>','#include <common>\nuniform sampler2D berthCover;')
        .replace('#include <map_fragment>',`#include <map_fragment>
          vec2 piece=clamp(floor((vHardwareRest.zy-vec2(-.965,1.275))/vec2(.48,.374)+.5),vec2(0.),vec2(4.,1.));
          vec2 centre=vec2(-.965,1.275)+piece*vec2(.48,.374);
          vec2 cut=clamp(.5-(vHardwareRest.zy-centre)/vec2(.465,.353),vec2(.0014),vec2(.9986));
          float pattern=piece.x==3.&&piece.y==0.?5.:mod(piece.x*3.+piece.y*2.,5.);
          vec2 tile=vec2(mod(pattern,3.),floor(pattern/3.));
          vec4 pad=texture2D(berthCover,(tile+cut)/vec2(3.,2.));
          pad.a=clamp((pad.a-.502)*2.008,0.,1.);
          float paddedFace=smoothstep(-2.135,-2.098,vHardwareRest.x);
          diffuseColor.rgb*=mix(vec3(1.),vec3(1.13,1.11,1.07)*(pad.b/.67),paddedFace);
          diffuseColor.rgb=mix(diffuseColor.rgb,vec3(.238,.251,.219),pad.a*paddedFace);`)
        .replace('#include <normal_fragment_maps>',`#include <normal_fragment_maps>
          vec2 padSlope=2.*pad.rg-1.;
          normal=normalize(normal+mat3(viewMatrix)*vec3(0.,-padSlope.y,-padSlope.x)*paddedFace);`);
    }
    if(braid){
      sh.vertexShader=sh.vertexShader.replace('#include <common>','#include <common>\nattribute vec4 shieldMetric;varying vec4 vShield;')
        .replace('#include <begin_vertex>','#include <begin_vertex>\nvShield=shieldMetric;');
      sh.fragmentShader=sh.fragmentShader.replace('#include <common>','#include <common>\nvarying vec4 vShield;')
        .replace('#include <map_fragment>',`#include <map_fragment>
          float ang=atan(vShield.z,vShield.y)/6.2831853;
          vec2 yarn=vShield.x/.0078+ang*vec2(8.,-8.);
          vec2 count=exp(-2.2*abs(fwidth(yarn))),cut=cos(yarn*6.2831853)*count;
          float course=abs(cut.x)*.48+abs(cut.y)*.52,thread=max(cut.x,cut.y);
          float braidV=vShield.w;
          float threads=.00013*thread*braidV;
          diffuseColor.rgb*=mix(vec3(1.),vec3(.36,.37,.34)*(.92+course*.16+thread*.10),braidV);`)
        .replace('#include <roughnessmap_fragment>','#include <roughnessmap_fragment>\nroughnessFactor=mix(roughnessFactor,.48+.13*course,braidV);')
        .replace('#include <normal_fragment_maps>',`#include <normal_fragment_maps>
          vec3 e1=dFdx(-vViewPosition),e2=dFdy(-vViewPosition),b1=cross(e2,normal),b2=cross(normal,e1);
          float det=dot(e1,b1);
          normal=normalize(max(abs(det),1.e-12)*normal-sign(det)*(dFdx(threads)*b1+dFdy(threads)*b2));`);
    }
    if(brushed||grip||coat){
      // Longitudinal machining lines lose contrast as their spacing approaches
      // the pixel footprint. Bare thumb paths are restricted to actual grips.
      sh.fragmentShader=sh.fragmentShader.replace('#include <roughnessmap_fragment>',`#include <roughnessmap_fragment>
        vec3 hwP=vHardwareRest;
        float rub=${hotspot.x<100?'exp(-dot((hwP-uRubPoint)*vec3(8.2,10.1,8.2),(hwP-uRubPoint)*vec3(8.2,10.1,8.2)))':'0.'};
        float grain=(hwP.x*.31+hwP.y*.89+hwP.z*.147)*2800.;
        float line=sin(grain+2.*sin(grain*.014))*exp(-1.3*abs(fwidth(grain)));
        roughnessFactor=clamp(${brushed?'roughnessFactor*.85+.042+line*.047-rub*.085':grip?'roughnessFactor*.87+.04-rub*.155':'roughnessFactor-rub*.13'},.16,.94);
        diffuseColor.rgb*=1.-rub*${grip?'.093':'.025'};`);
    }
  };
  m.customProgramCacheKey=()=>parentKey+'/cabin-contact-v1/'+panes.length+'/'+kind+'/'+(hotspot.x<100);
  mesh.material=m;
}

function finishCable(mesh,part){
  const rest=part.rest,dist=[0],u=[],v=[],points=mesh.geometry.attributes.position,coord=new Float32Array(points.count*3);
  const fromMesh=part.inverse.clone().multiply(mesh.matrixWorld);
  let basis=V(1,0,0),tangent=V(),delta=V(),p=V(),radial=V(),bestRadial=V();
  for(let j=0;j<rest.length-1;j++){
    tangent.subVectors(rest[j+1],rest[j]).normalize();basis.addScaledVector(tangent,-basis.dot(tangent)).normalize();
    u.push(basis.clone());v.push(V().crossVectors(tangent,basis));dist.push(dist[j]+rest[j].distanceTo(rest[j+1]));
  }
  for(let i=0;i<points.count;i++){
    p.fromBufferAttribute(points,i).applyMatrix4(fromMesh);
    let best=Infinity,index=0,along=0;
    for(let j=0;j<rest.length-1;j++){
      delta.subVectors(rest[j+1],rest[j]);radial.subVectors(p,rest[j]);
      const t=T.MathUtils.clamp(radial.dot(delta)/delta.lengthSq(),0,1);radial.addScaledVector(delta,-t);
      if(radial.lengthSq()<best){best=radial.lengthSq();index=j;along=t;bestRadial.copy(radial);}
    }
    bestRadial.normalize();coord[i*3]=dist[index]+along*(dist[index+1]-dist[index]);
    coord[i*3+1]=bestRadial.dot(u[index]);coord[i*3+2]=bestRadial.dot(v[index]);
  }
  mesh.geometry.setAttribute('jacketMetric',new T.BufferAttribute(coord,3));
  const src=mesh.material,m=new T.MeshPhysicalMaterial();
  T.MeshStandardMaterial.prototype.copy.call(m,src);m.defines.PHYSICAL='';
  const power=part.id==='loom_service_power';
  m.metalness=.015;m.clearcoat=.11;m.clearcoatRoughness=.42;m.ior=1.46;m.specularIntensity=.61;
  m.color.multiply(new T.Color(...(power?[.77,.69,.59]:[.53,.79,.77])));
  m.onBeforeCompile=sh=>{
    sh.uniforms.uJacketLettering={value:jacketInk};
    sh.vertexShader=sh.vertexShader.replace('#include <common>','#include <common>\nattribute vec3 jacketMetric; varying vec3 vJacket;')
      .replace('#include <begin_vertex>','#include <begin_vertex>\nvJacket=jacketMetric;');
    sh.fragmentShader=sh.fragmentShader.replace('#include <common>','#include <common>\nuniform sampler2D uJacketLettering;varying vec3 vJacket;')
      .replace('#include <map_fragment>',`#include <map_fragment>
        float phi=atan(vJacket.z,vJacket.y)/6.2831853+.5;
        float ink=texture2D(uJacketLettering,vec2(vJacket.x/.213,phi*.5+${power?'0.':'.5'})).r;
        float extrusion=dot(normalize(vJacket.yz),vec2(.832,-.554));
        float ridge=smoothstep(.956,.999,extrusion);
        diffuseColor.rgb*=1.-.08*ridge;
        diffuseColor.rgb=mix(diffuseColor.rgb,${power?'vec3(.042,.029,.019)':'vec3(.026,.046,.061)'},ink*.84);`)
      .replace('#include <roughnessmap_fragment>',`#include <roughnessmap_fragment>
        float ribs=vJacket.x*4900.+phi*18.85;
        float imprint=cos(ribs)*exp(-1.8*abs(fwidth(ribs)));
        roughnessFactor=clamp(.44+.16*roughnessFactor+.05*imprint-.052*ridge,.34,.72);`);
  };
  m.customProgramCacheKey=()=>'metric-jacket-'+part.id;mesh.material=m;
}

function coverDisplay(mesh,world,id){
  const material=new T.ShaderMaterial({name:id+' optical cover',transparent:true,depthWrite:false,
    uniforms:{cabReflection:{value:world.photometry.localProbe.texture},cabOrigin:{value:world.photometry.cubeCamera.position}},
    vertexShader:`varying vec3 pt,n;varying vec2 faceUV;void main(){faceUV=uv;
      vec3 q=position+normal*.00074;vec4 world=modelMatrix*vec4(q,1.);pt=world.xyz;
      n=normalize((vec4(normalMatrix*normal,0.)*viewMatrix).xyz);gl_Position=projectionMatrix*viewMatrix*world;}`,
    fragmentShader:`uniform samplerCube cabReflection;uniform vec3 cabOrigin;varying vec3 pt,n;varying vec2 faceUV;
      void main(){vec3 view=normalize(pt-cameraPosition),normal=normalize(n);
        if(dot(view,normal)>0.)normal=-normal;vec3 ray=reflect(view,normal);
        vec3 lo=vec3(-2.18,.025,cabOrigin.z-1.88),hi=vec3(2.18,2.60,cabOrigin.z+1.88);
        vec3 inv=sign(ray)/max(abs(ray),vec3(.0001));vec3 hit=max((hi-pt)*inv,(lo-pt)*inv);
        float travel=clamp(min(hit.x,min(hit.y,hit.z)),0.,5.5);vec3 dir=normalize(pt+ray*travel-cabOrigin);
        vec3 reflection=textureCube(cabReflection,dir).rgb;float f=.025+.72*pow(1.-max(0.,dot(-view,normal)),5.);
        float edge=min(min(faceUV.x,1.-faceUV.x),min(faceUV.y,1.-faceUV.y));
        float gasket=1.-smoothstep(0.,max(.002,fwidth(edge)*1.3),edge);
        gl_FragColor=vec4(mix(min(reflection,vec3(3.8))*vec3(.96,.99,1.025),vec3(.011,.017,.016),gasket),max(f,gasket*.56));
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }`});
  const cover=new T.Mesh(mesh.geometry,material);cover.name=id+' cover glass';cover.renderOrder=3;cover.castShadow=false;
  // A live room-probe capture must see the luminous display through its cover
  // without feeding the render target back into itself.
  cover.layers.set(4);world.camera.layers.enable(4);
  mesh.add(cover);
}

function shadow(light,size,near,far){
  light.castShadow=true;light.shadow.mapSize.set(size,size);light.shadow.bias=-.00016;light.shadow.normalBias=.0019;
  light.shadow.camera.near=near;light.shadow.camera.far=far;light.shadow.autoUpdate=false;light.shadow.needsUpdate=true;
}
function taskLamp(scene,rgb,position,axis,reach,angle,size){
  const l=new T.SpotLight(rgb,0,reach,angle,.77,2);l.position.fromArray(position);l.target.position.fromArray(axis);
  shadow(l,size,.055,reach);scene.add(l,l.target);return l;
}

// The surveyed five three-way blocks terminate at 52 mm pitch. Their metal
// compression nuts, elastomer throats and seals stay on the chassis when
// a passenger moves the service loops. Four batches cover all 15 glands.
function installGlands(scene){
  const contour=(rings,sides)=>{
    const geo=new T.LatheGeometry(rings.slice().reverse().map(([radius,y])=>new T.Vector2(radius,y)),sides);
    if(sides!==6)return geo;
    const hard=geo.toNonIndexed();geo.dispose();hard.computeVertexNormals();return hard;
  };
  const metal=new T.MeshStandardMaterial({color:0x9b9c94,metalness:.87,roughness:.31});
  const sleeve=new T.MeshStandardMaterial({color:0x242a2c,metalness:.025,roughness:.48});
  const nickel=new T.MeshStandardMaterial({color:0xbbb9a9,metalness:.84,roughness:.24});
  const bands=[
    [contour([[.0180,.0053],[.0215,.0036],[.0215,-.0053],[.0181,-.0079]],6),metal,1.8004],
    [contour([[.0191,.0020],[.0205,.0012],[.0205,-.0011],[.0191,-.0020]],24),nickel,1.8081],
    [contour([[.0179,.0018],[.0186,.0013],[.0189,0],[.0185,-.0014],[.0176,-.0020]],20),sleeve,1.7922],
    [contour([[.0158,.0154],[.0166,.0140],[.0166,.0115],[.0143,.0108],[.0142,.0086],[.0157,.0077],
      [.0150,.0053],[.0130,.0045],[.0126,.0017],[.0140,.0010],[.0132,-.0014],[.0118,-.0025],[.0110,-.0088]],16),sleeve,1.7648],
  ];
  const transform=new T.Object3D();
  for(const [geometry,material,height] of bands){
    const batch=new T.InstancedMesh(geometry,material,15);batch.name='Compression gland chassis hardware';batch.castShadow=true;batch.receiveShadow=true;
    for(let j=0;j<15;j++){
      transform.position.set(1.992,height,3.029+Math.floor(j/3)*.25+(j%3-1)*.052);
      transform.rotation.y=(j*.87)%Math.PI;const scale=j%3===1&&height<1.78?.86:1;
      transform.scale.set(scale,1,scale);transform.updateMatrix();batch.setMatrixAt(j,transform.matrix);
    }
    batch.computeBoundingSphere();scene.add(batch);
  }
}

export class CabinHardware{
  constructor(world){
    this.world=world;this.clock=-100;this.rackMix=0;this.lastEye='';this.lastKey='';
    const byId=Object.fromEntries(survey.surveys.map(d=>[d.id,{matrix:projection(d),tile:new T.Vector2(...d.tile)}]));
    const contacts={ascent_lever:[1.46,1.235,-5.0],pilot_console:[.83,1.001,-4.76],pressure_hatch:[.49,1.18,1.81],
      card_reader:[1.02,1.34,1.72],service_cabinet:[1.69,1.49,4.10],grab_handle:[-1.23,1.34,1.0],lounge_seat:[-1.38,.89,-3.51]};
    const covers=[];
    for(const mesh of world.hull){
      const {prop,room}=ancestry(mesh),name=mesh.material.name;
      if(ignored.has(prop))continue;
      const display=mesh.material===world.instruments.material?'Flight':name.match(/^Live_(.+)_Display$/)?.[1];
      if(display&&(display==='Flight'||glassNames.has(display))){covers.push([mesh,display]);continue;}
      const fabric=mesh.userData.fabricPart;
      if(fabric){if(fabric.kind==='service'&&/^Cable_(Orange|Cyan)$/.test(name)){
        finishCable(mesh,fabric);
      }continue;}
      if(!mesh.material.isMeshStandardMaterial||mesh.material.transparent||mesh.material.emissive?.getHex()||/Print|Stencils|Legends|Emit|Pixels|Glass/.test(name))continue;
      const area=room||world.layout.props[prop]?.room;if(!area)continue;
      const tiles=prop==='pressure_hatch'?['hatch']:prop==='service_cabinet'?[]:
        area==='service'?['rack','lock']:area==='observation'?['seat','deck']:['berth'];
      const kind=room==='berth'&&name==='Pressure_Fabric'?'pad':room==='service'&&name==='Technical_Twill'?'braid':/Titanium|Aluminum|Anodized|Graphite_Alloy/.test(name)?'metal':/Rubber|Grip|Cable_/.test(name)?'grip':/Ceramic|Composite|Surface_/.test(name)?'coat':'';
      if(!tiles.length&&!kind)continue;
      finishRigid(mesh,tiles.map(id=>byId[id]),kind,contacts[prop]?V(...contacts[prop]):V(512,512,512));
    }
    covers.forEach(([mesh,id])=>coverDisplay(mesh,world,id));this.covers=covers.length;
    installApertureResponse(world.hull);
    world.photometry.shadeTravel=world.base.roller_shade;
    installGlands(world.scene);
    const size=world.softwareGpu?384:768;
    shadow(world.practical,size,.13,5.7);
    this.rack=taskLamp(world.scene,0xffead4,[1.868,1.94,3.36],[2.065,1.32,3.62],2.15,1.02,size);
    this.read=taskLamp(world.scene,0xffddae,[-1.976,1.492,-.839],[-1.61,.94,-.40],2.34,.90,size);
    this.fiber=world.furnishings.part('loom_service_fiber');this.a=V();this.b=V();this.c=V();
  }
  bendRadius(){
    const p=this.fiber.points;let min=Infinity;
    for(let j=4;j<p.length-4;j++){
      this.a.subVectors(p[j],p[j-3]);this.b.subVectors(p[j+3],p[j]);this.c.addVectors(this.a,this.b);
      const num=this.a.length()*this.b.length()*this.c.length(),den=2*this.c.crossVectors(this.a,this.b).length();
      if(den>1e-9)min=Math.min(min,num/den);
    }
    return Math.round(min*1000);
  }
  update(s,time,dt){
    const w=this.world,z=w.position.z,area=z<-1.9?'deck':z<1.9?'berth':'service';
    this.rackMix+=(Number(s.bayLight)-this.rackMix)*(1-Math.exp(-dt*9));
    this.rack.intensity=this.rackMix*1.55;w.loom.intensity=.84*this.rackMix;
    w.sleeper.intensity=s.berthLight?.72:.035;this.read.intensity=s.berthLight?1.62:0;
    w.service.intensity=2.05;
    const key=[s.lamps,s.bayLight,s.cabinet,s.berthLight,s.hatch].join('/');
    if(time-this.clock>(w.softwareGpu?.30:.075)||this.lastEye!==area||key!==this.lastKey){
      w.practical.shadow.needsUpdate=area==='deck'&&s.lamps;
      this.read.shadow.needsUpdate=area==='berth'&&s.berthLight;
      this.rack.shadow.needsUpdate=area==='service'&&s.bayLight;
      this.clock=time;this.lastEye=area;this.lastKey=key;
    }
  }
}
