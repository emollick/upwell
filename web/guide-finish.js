import * as T from 'three';

// Surface dimensions are metres in the fabricated guideway's local frame.
// Preserve the environment, shadows and PBR response of each original glTF
// finish. Only the material on the moving guideway receives this treatment.
const mean={
  Tow_Carbon:0x2f3739,Precision_Titanium:0x8f979a,Titanium:0x8e9699,
  Graphite_Alloy:0x484f56,Anodized_Frame:0x495056,Signal_Orange:0xb74926,
};
const source=`
varying vec3 vGuideP;
varying vec3 vGuideN;
uniform float guideShutter,guideRadius;
uniform vec3 guideMean;
float guideWave(float phase,float smear){
  float visibility=1.-smoothstep(.16,.82,fwidth(phase)+smear);
  return cos(6.2831853*phase)*visibility;
}
float coverageIntegral(float cycle,float duty){
  return floor(cycle)*duty+min(fract(cycle),duty);
}
`;
const finish=`
float guideNormalWeight=1.;
#if GUIDE_KIND == 1
  // Pultruded parallel filaments bound by opposed fine resin tapes.
  float fiber=guideWave(vGuideP.z*267.,0.);
  float tape=.6*guideWave(vGuideP.z*94.+.2,0.)+.4*guideWave(vGuideP.z*157.,0.);
  float binder=.5*(guideWave(vGuideP.z*114.+vGuideP.y*57.,guideShutter*57.)+
                   guideWave(vGuideP.z*111.-vGuideP.y*57.,guideShutter*57.));
  float blur=smoothstep(.003,.11,guideShutter);
  diffuseColor.rgb=mix(diffuseColor.rgb,guideMean,blur*.85)*(.79+.087*tape+.058*fiber+.049*binder);
  roughnessFactor=mix(roughnessFactor,.53,.52+blur*.36)+fiber*.026+tape*.030+binder*.021;
  guideNormalWeight=mix(.68,.085,blur);
#elif GUIDE_KIND == 2
  // A Hertzian wear lane follows each roller contact. The separate stranded
  // messenger shares this alloy but never contacts a traction wheel.
  float isRail=step(abs(abs(vGuideP.z)-.485),.065)*step(-.012,vGuideP.x);
  float nz=abs(normalize(vGuideN).z);
  float aa=min(.23,fwidth(nz));
  float track=(1.-smoothstep(.12-aa,.39+aa,nz))*isRail;
  float grain=guideWave(vGuideP.z*491.,0.);
  float blur=smoothstep(.003,.105,guideShutter);
  diffuseColor.rgb=mix(diffuseColor.rgb,guideMean,blur*.81)*mix(.73,1.13,track)*(1.+.019*grain);
  roughnessFactor=mix(mix(.44,.29,track),roughnessFactor,.19*(1.-blur))+.019*grain;
  guideNormalWeight=mix(.61,.10,blur);
#elif GUIDE_KIND == 3
  float radial=length(vGuideP.xy);
  float radius=guideRadius;
  if(abs(vGuideP.z)<.026 && radial<radius*.818 && guideShutter/radius>.24) discard;
  float face=step(radius*.25,radial)*step(.030,abs(vGuideP.z));
  float lathe=guideWave(radial*470.,0.);
  float norm=radial/radius,aa=min(.025,fwidth(norm));
  float groove=1.-smoothstep(.004,.012+aa,abs(norm-.863));
  float land=smoothstep(.545-aa,.565+aa,norm)*(1.-smoothstep(.834-aa,.852+aa,norm));
  float turn=face*(.76+.20*smoothstep(.0,.11,guideShutter));
  diffuseColor.rgb=mix(diffuseColor.rgb,guideMean,turn)*(1.+face*(-.18+.090*land-.30*groove+lathe*.022));
  roughnessFactor=mix(roughnessFactor,.46-.102*land+.085*groove+lathe*.014,turn);
  guideNormalWeight=1.-turn*.91;
#elif GUIDE_KIND == 4
  if(guideShutter/guideRadius>.24) discard;
#elif GUIDE_KIND == 5
  // Rotational integration of six struts and three painted witness ticks.
  // A transparent swept annulus covers only the angular area which actually
  // crossed the pixel during the exposure. The real hub still occludes it.
  float radial=length(vGuideP.xy), tick=step(.018,abs(vGuideP.z));
  float n=mix(6.,3.,tick),width=mix(.020,.019,tick);
  float duty=clamp(width*n/(6.2831853*max(.015,radial)),.015,.68);
  float phase=atan(vGuideP.y,vGuideP.x)*n/6.2831853+.5*duty;
  float shutter=max(fwidth(phase),guideShutter*n/(guideRadius*6.2831853));
  float cover=(coverageIntegral(phase+.5*shutter,duty)-coverageIntegral(phase-.5*shutter,duty))/max(.001,shutter);
  diffuseColor.a*=mix(cover,duty,smoothstep(1.5,3.5,shutter));
  if(diffuseColor.a<.004)discard;
#endif
`;

export function guideFinishes(){
  const shutter={value:0},cache=new Map();
  function material(original,kind,radius=1){
    const key=original.uuid+'/'+kind+'/'+radius;
    if(cache.has(key))return cache.get(key);
    const m=original.clone(),color=mean[original.name]??0x8e9699;
    m.onBeforeCompile=shader=>{
      shader.uniforms.guideShutter=shutter;
      shader.uniforms.guideRadius={value:radius};
      shader.uniforms.guideMean={value:new T.Color(color)};
      shader.vertexShader=shader.vertexShader.replace('#include <common>',
        '#include <common>\nvarying vec3 vGuideP;varying vec3 vGuideN;')
        .replace('#include <beginnormal_vertex>',`#include <beginnormal_vertex>
          vGuideP=position;vGuideN=normal;
          ${kind===3?`float rr=length(position.xy);
          if(rr>.012 && abs(position.z)>.030){
            vec2 r=position.xy/rr;
            objectNormal=normalize(vec3(r*dot(r,objectNormal.xy),objectNormal.z));
          }`:''}`);
      shader.fragmentShader=shader.fragmentShader.replace('#include <common>',
        '#include <common>\n#define GUIDE_KIND '+kind+'\n'+source)
        .replace('#include <roughnessmap_fragment>','#include <roughnessmap_fragment>\n'+finish)
        .replace('#include <metalnessmap_fragment>',`#include <metalnessmap_fragment>
          #if GUIDE_KIND == 1
            metalnessFactor*=.48;
          #endif`)
        .replace('#include <normal_fragment_maps>',`vec3 guideMacroNormal=normal;
          #include <normal_fragment_maps>
          normal=normalize(mix(guideMacroNormal,normal,guideNormalWeight));`);
    };
    m.customProgramCacheKey=()=> 'upwell-guide-finish-1/'+kind;
    cache.set(key,m);return m;
  }
  function mountSpan(span){
    span.traverse(o=>{
      if(!o.isMesh)return;
      const k=o.material.name;
      if(k==='Tow_Carbon'||k==='Precision_Titanium')o.material=material(o.material,k==='Tow_Carbon'?1:2);
    });
  }
  const envelope=new T.MeshStandardMaterial({vertexColors:true,metalness:.65,roughness:.42,transparent:true,opacity:1,side:T.DoubleSide,depthWrite:false});
  const rings=new Map();
  function mountWheel(wheel,radius){
    wheel.traverse(o=>{
      if(!o.isMesh)return;
      if(o.material.name==='Titanium')o.material=material(o.material,3,radius);
      if(o.material.name==='Signal_Orange')o.material=material(o.material,4,radius);
    });
    let geometry=rings.get(radius);
    if(!geometry){
      const position=[],normal=[],colors=[],indices=[];
      function ring(inner,outer,z,color){
        const start=position.length/3,c=new T.Color(color);
        for(let i=0;i<=56;i++){
          const a=i*Math.PI*2/56;
          for(const r of [inner,outer]){
            position.push(r*Math.cos(a),r*Math.sin(a),z);normal.push(0,0,1);colors.push(c.r,c.g,c.b);
          }
          if(i<56){const j=start+i*2;indices.push(j,j+1,j+3,j,j+3,j+2);}
        }
      }
      ring(radius*.22,radius*.755,0,mean.Titanium);
      const width=radius>.18?.123:.100;
      ring(radius*.71-.009,radius*.71+.009,width*.56+.0026,mean.Signal_Orange);
      geometry=new T.BufferGeometry();geometry.setAttribute('position',new T.Float32BufferAttribute(position,3));
      geometry.setAttribute('normal',new T.Float32BufferAttribute(normal,3));
      geometry.setAttribute('color',new T.Float32BufferAttribute(colors,3));geometry.setIndex(indices);rings.set(radius,geometry);
    }
    const disc=new T.Mesh(geometry,material(envelope,5,radius));disc.name='Swept spoke and paint coverage';disc.visible=false;
    wheel.add(disc);return disc;
  }
  return {shutter,mountSpan,mountWheel};
}

// Extrude the SAME cross-section as the near Blender member. All distant
// sections share five material batches even when the guide crosses the sky.
export function distantGuide(length,materials){
  const p=[],n=[],indices=materials.map(()=>[]);
  function tube(x,z,rx,rz,steps,slot,lens=false){
    const start=p.length/3;
    for(let j=0;j<steps;j++){
      const a=j*2*Math.PI/steps,c=Math.cos(a),s=Math.sin(a);
      const dx=rx*c*(lens?.67+.33*Math.abs(c):1),dz=rz*(lens?Math.sign(s)*Math.pow(Math.abs(s),.77):s);
      let nx=dx/(rx*rx),nz=dz/(rz*rz),len=Math.hypot(nx,nz);nx/=len;nz/=len;
      for(const y of [-4800,-length,length,4800]){p.push(x+dx,y,z+dz);n.push(nx,0,nz);}
    }
    for(let j=0;j<steps;j++)for(const side of [0,2]){
      const a=start+j*4+side,b=start+((j+1)%steps)*4+side;
      indices[slot].push(a,a+1,b+1,a,b+1,b);
    }
  }
  tube(0,0,.108,.376,40,0,true);
  for(const side of [-1,1]){
    for(let k=-4;k<=4;k++){const z=k*.076;tube(side*.094*Math.sqrt(1-(z/.383)**2),z,.0185,.044,12,0,true);}
    tube(.059,side*.485,.063,.063,22,1);tube(-.062,side*.401,.028,.028,12,2);
  }
  tube(-.121,.607,.049,.049,14,1);tube(-.124,-.516,.033,.033,13,3);
  tube(-.171,-.464,.037,.037,13,2);tube(-.172,-.555,.024,.024,13,4);
  const result=new T.Group(),position=new T.Float32BufferAttribute(p,3),normal=new T.Float32BufferAttribute(n,3);
  result.name='Continuous guide cross sections';
  for(let slot=0;slot<indices.length;slot++){
    const g=new T.BufferGeometry();g.setAttribute('position',position);g.setAttribute('normal',normal);g.setIndex(indices[slot]);
    result.add(new T.Mesh(g,materials[slot]));
  }
  return result;
}
