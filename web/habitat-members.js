import * as T from 'three';

const vp=new T.Vector4(),center=new T.Vector3(),scale=new T.Vector3();
function opticalScale(renderer,mesh,camera){
  renderer.getCurrentViewport(vp);center.setFromMatrixPosition(mesh.matrixWorld).applyMatrix4(camera.matrixWorldInverse);
  scale.setFromMatrixScale(mesh.matrixWorld);
  return Math.abs(camera.projectionMatrix.elements[5])*vp.w*.5*scale.x/Math.max(.01,-center.z);
}

// The CDF of a rectangular pixel projected onto the normal of a line. The
// difference of two evaluations gives its actual covered area even for a
// diagonal member whose width is a small fraction of one sensor pixel.
const coverage=`
float memberCDF(float d,vec2 n){
  vec2 a=abs(n)*.5;float hi=max(a.x,a.y),lo=min(a.x,a.y);
  if(lo<.002)return clamp(.5+d/(2.*max(.001,hi)),0.,1.);
  float q=abs(d),tail=max(0.,hi+lo-q);
  float value=q<hi-lo?.5+q/(2.*hi):1.-tail*tail/(8.*hi*lo);
  return d<0.?1.-value:value;
}
varying vec2 memberA,memberAxis;
varying vec2 memberDimensions,memberBaked;
varying vec3 memberFront,memberSide;
varying vec3 memberFaceU,memberFaceV,memberProfile;
varying float memberWidthPixels;
uniform vec4 memberViewport;
uniform float memberScale;
`;
const attributes=`
attribute vec3 otherEnd,sectionU,sectionV;
attribute vec2 corner,finishMR;
attribute float rectangular;
`;
const setup=`
// The source endpoints and section come from the same Blender member as the
// detailed geometry. Construction in projected pixels leaves real parallax.
vec4 va=modelViewMatrix*vec4(position,1.),vb=modelViewMatrix*vec4(otherEnd,1.);
vec4 ca=projectionMatrix*va,cb=projectionMatrix*vb;
vec2 pa=(ca.xy/ca.w*.5+.5)*memberViewport.zw+memberViewport.xy;
vec2 pb=(cb.xy/cb.w*.5+.5)*memberViewport.zw+memberViewport.xy;
vec2 direction=pb-pa;float len=max(.002,length(direction));direction/=len;
vec2 across=vec2(-direction.y,direction.x);
vec3 mid=(va.xyz+vb.xyz)*.5,vu=mat3(modelViewMatrix)*sectionU,vv=mat3(modelViewMatrix)*sectionV;
vec4 cm=projectionMatrix*vec4(mid,1.),cu=projectionMatrix*vec4(mid+vu,1.),cv=projectionMatrix*vec4(mid+vv,1.);
vec2 hu=(cu.xy/cu.w-cm.xy/cm.w)*.5*memberViewport.zw;
vec2 hv=(cv.xy/cv.w-cm.xy/cm.w)*.5*memberViewport.zw;
vec2 section=vec2(dot(hu,across),dot(hv,across));
float radius=mix(length(section),abs(section.x)+abs(section.y),rectangular);
vec2 pixel=mix(pa,pb,corner.x)+direction*((corner.x*2.-1.)*.86)+across*corner.y*(radius+.86);
vec4 mvPosition=mix(va,vb,corner.x);
vec3 axis=normalize(vb.xyz-va.xyz),toward=normalize(-mid);
vec3 front=normalize(toward-axis*dot(toward,axis)+vec3(.000001));
vec3 lateral=normalize(cross(axis,front));if(dot(lateral.xy,across)<0.)lateral=-lateral;
mvPosition.xyz+=front*max(length(vu),length(vv))*.53;
gl_Position=projectionMatrix*mvPosition;
gl_Position.xy=((pixel-memberViewport.xy)/memberViewport.zw*2.-1.)*gl_Position.w;
memberWidthPixels=2.*max(length(sectionU),length(sectionV))*memberScale;
if(memberWidthPixels>=5.1)gl_Position=vec4(2.,2.,1.,1.);
memberA=pa;memberAxis=direction;memberDimensions=vec2(len,radius);memberBaked=finishMR;
memberFront=front;memberSide=lateral;
float fu=dot(vu,toward)>=0.?1.:-1.,fv=dot(vv,toward)>=0.?1.:-1.;
memberFaceU=normalize(vu)*fu;memberFaceV=normalize(vv)*fv;
memberProfile=vec3(rectangular,section.x*fu,abs(section.y));
`;
const lighting=`
{
  ReflectedLight sampleA=ReflectedLight(vec3(0.),vec3(0.),vec3(0.),vec3(0.));
  ReflectedLight sampleB=ReflectedLight(vec3(0.),vec3(0.),vec3(0.),vec3(0.));
  ReflectedLight sampleC=ReflectedLight(vec3(0.),vec3(0.),vec3(0.),vec3(0.));
  RE_Direct(directLight,geometryPosition,sectionA,geometryViewDir,geometryClearcoatNormal,material,sampleA);
  RE_Direct(directLight,geometryPosition,sectionB,geometryViewDir,geometryClearcoatNormal,material,sampleB);
  RE_Direct(directLight,geometryPosition,sectionC,geometryViewDir,geometryClearcoatNormal,material,sampleC);
  reflectedLight.directDiffuse+=sampleA.directDiffuse*weights.x+sampleB.directDiffuse*weights.y+sampleC.directDiffuse*weights.z;
  reflectedLight.directSpecular+=sampleA.directSpecular*weights.x+sampleB.directSpecular*weights.y+sampleC.directSpecular*weights.z;
}`;
function makeRepresentation(buffer,survey) {
  const data=new DataView(buffer);if(data.getUint32(0,false)!==0x41535231)throw Error('The habitat member survey is unavailable.');
  const count=data.getUint32(4,true),packed=Array.from(survey.values());
  const g=new T.BufferGeometry(),a={},index=[];
  for(const [key,dim] of Object.entries({position:3,otherEnd:3,sectionU:3,sectionV:3,corner:2,finishMR:2,rectangular:1,color:3}))a[key]=[];
  const p=new T.Color(),bounds=new T.Box3();
  for(let i=0;i<count;i++){
    const at=8+i*52,points=Array.from({length:12},(_,j)=>data.getFloat32(at+j*4,true));
    const shape=data.getUint8(at+48),spec=packed[data.getUint8(at+49)];p.set(spec.color);
    bounds.expandByPoint(new T.Vector3(...points.slice(0,3)));bounds.expandByPoint(new T.Vector3(...points.slice(3,6)));
    for(const [along,side] of [[0,-1],[1,-1],[1,1],[0,1]]){
      for(const [j,k] of ['position','otherEnd','sectionU','sectionV'].entries())a[k].push(...points.slice(j*3,j*3+3));
      a.corner.push(along,side);a.finishMR.push(spec.metal,spec.rough);
      a.rectangular.push(shape);a.color.push(p.r,p.g,p.b);
    }
    const j=i*4;index.push(j,j+1,j+2,j,j+2,j+3);
  }
  for(const [key,values] of Object.entries(a))g.setAttribute(key,new T.Float32BufferAttribute(values,values.length/(count*4)));
  // The standard lighting path expects a normal attribute before it receives
  // the view-dependent same-section normal below.
  g.setAttribute('normal',g.getAttribute('sectionU'));g.setIndex(index);g.boundingBox=bounds.expandByScalar(.12);g.boundingSphere=new T.Sphere();bounds.getBoundingSphere(g.boundingSphere);
  const viewport={value:new T.Vector4()},pixels={value:1};
  const m=new T.MeshStandardMaterial({vertexColors:true,transparent:true,depthWrite:false,side:T.DoubleSide,roughness:.42,metalness:.6});
  m.name='Aster structural area coverage';m.forceSinglePass=true;
  m.onBeforeCompile=shader=>{
    shader.uniforms.memberViewport=viewport;shader.uniforms.memberScale=pixels;
    shader.vertexShader=shader.vertexShader.replace('#include <common>','#include <common>\n'+attributes+coverage)
      .replace('#include <project_vertex>',setup);
    shader.fragmentShader=shader.fragmentShader.replace('#include <common>','#include <common>\n'+coverage)
      .replace('#include <color_fragment>',`#include <color_fragment>
        vec2 q=gl_FragCoord.xy-memberA,across=vec2(-memberAxis.y,memberAxis.x);
        float x=dot(q,memberAxis),y=dot(q,across),r=memberDimensions.y;
        float width=memberCDF(y+r,across)-memberCDF(y-r,across);
        float ends=memberCDF(x,memberAxis)-memberCDF(x-memberDimensions.x,memberAxis);
        diffuseColor.a*=width*ends*(1.-smoothstep(3.7,5.1,memberWidthPixels));
        if(diffuseColor.a<.0015)discard;`)
      .replace('#include <roughnessmap_fragment>','float roughnessFactor=memberBaked.y;')
      .replace('#include <metalnessmap_fragment>','float metalnessFactor=memberBaked.x;')
      .replace('#include <normal_fragment_maps>',`float off=clamp(y/max(r,.001),-.96,.96);
        vec3 nr=normalize(memberFront*sqrt(1.-off*off)+memberSide*off);
        vec3 sectionA=normalize(memberFront*.70-memberSide*.715);
        vec3 sectionB=memberFront,sectionC=normalize(memberFront*.70+memberSide*.715);
        float left=(memberCDF(y+r,across)-memberCDF(y+r*.3333,across))/max(.00001,width);
        float right=(memberCDF(y-r*.3333,across)-memberCDF(y-r,across))/max(.00001,width);
        vec3 weights=vec3(left,max(0.,1.-left-right),right);
        if(memberProfile.x>.5){
          float t=y-memberProfile.y,w=memberProfile.z;
          float uf=clamp((memberCDF(t+w,across)-memberCDF(t-w,across))/max(width,.00001),0.,1.);
          weights=vec3(uf,0.,1.-uf);sectionA=memberFaceU;sectionC=memberFaceV;
        }else{
          float resolved=smoothstep(1.75,4.2,r);
          sectionA=normalize(mix(sectionA,nr,resolved));sectionB=normalize(mix(sectionB,nr,resolved));sectionC=normalize(mix(sectionC,nr,resolved));
        }
        normal=normalize(sectionA*weights.x+sectionB*weights.y+sectionC*weights.z);`)
      .replace('#include <lights_fragment_begin>',T.ShaderChunk.lights_fragment_begin.replaceAll(
        'RE_Direct( directLight, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );',lighting))
      .replace('#include <lights_fragment_maps>',T.ShaderChunk.lights_fragment_maps
        .replace('getIBLIrradiance( geometryNormal )','(getIBLIrradiance(sectionA)*weights.x+getIBLIrradiance(sectionB)*weights.y+getIBLIrradiance(sectionC)*weights.z)')
        .replace('getIBLRadiance( geometryViewDir, geometryNormal, material.roughness )','(getIBLRadiance(geometryViewDir,sectionA,material.roughness)*weights.x+getIBLRadiance(geometryViewDir,sectionB,material.roughness)*weights.y+getIBLRadiance(geometryViewDir,sectionC,material.roughness)*weights.z)'))
      .replace('#include <lights_fragment_end>',`#include <lights_fragment_end>
        vec3 nw=inverseTransformDirection(normal,viewMatrix);
        float broad=.29+.41*max(0.,dot(nw,normalize(vec3(.47,.31,.82))))+.30*(.5-.5*nw.y);
        reflectedLight.indirectDiffuse+=diffuseColor.rgb*broad*.40*vec3(.81,.9,1.);`);
  };
  m.customProgramCacheKey=()=> 'aster-pressure-member-area-v1';
  const result=new T.Mesh(g,m);result.name='Spatially integrated pressure members';result.renderOrder=-2;
  result.onBeforeRender=(renderer,scene,camera)=>{pixels.value=opticalScale(renderer,result,camera);viewport.value.copy(vp);};
  return result;
}

export function mountHabitatMembers(parent,fine,buffer,survey){
  parent.add(fine,makeRepresentation(buffer,survey));
  fine.traverse(part=>{
    if(!part.isMesh)return;
    const widths=part.geometry.getAttribute('uv1');
    if(!widths)throw Error('Aster pressure member gauge data are missing.');
    part.geometry.setAttribute('asterSection',widths);
    const original=part.material,mat=original.clone(),prior=original.onBeforeCompile,amount={value:1};
    mat.transparent=true;mat.depthWrite=true;mat.forceSinglePass=true;
    mat.onBeforeCompile=(s,r)=>{
      prior.call(mat,s,r);s.uniforms.asterFineWeight=amount;
      s.vertexShader='uniform float asterFineWeight;attribute vec2 asterSection;varying float physicalWeight;\n'+s.vertexShader.replace('#include <project_vertex>',
        '#include <project_vertex>\nphysicalWeight=smoothstep(2.8,4.6,asterSection.x*asterFineWeight);if(physicalWeight<.001)gl_Position=vec4(2.,2.,1.,1.);');
      s.fragmentShader='varying float physicalWeight;\n'+s.fragmentShader.replace('#include <color_fragment>',
        '#include <color_fragment>\ndiffuseColor.a*=physicalWeight;if(diffuseColor.a<.001)discard;');
    };
    mat.customProgramCacheKey=()=>'aster-authored-close-members';part.material=mat;part.renderOrder=-1;
    part.onBeforeRender=(r,s,c)=>{amount.value=opticalScale(r,part,c);};
  });
}
