import * as T from 'three';
import {loadCabinContact} from './cabin-hardware.js';
import {loadApertures} from './cabin-light.js';

const rooms = ['observation', 'berth', 'service'];
export async function loadFinishes() {
  const hardware=Promise.all([loadCabinContact(),loadApertures()]);
  const base = './assets/finish/';
  const response = await fetch(base + 'cameras.json');
  if (!response.ok) throw Error('Cabin finish calibration could not be loaded');
  const cameras = await response.json();
  const loader = new T.TextureLoader();
  const pairs = await Promise.all(
    rooms.map(async (id) => {
      const [detail, depth] = await Promise.all(
        ['detail', 'depth'].map((tag) => loader.loadAsync(base + id + '-' + tag + '.png')),
      );
      detail.colorSpace = T.NoColorSpace;
      detail.anisotropy = 4;
      depth.colorSpace = T.NoColorSpace;
      depth.minFilter = depth.magFilter = T.NearestFilter;
      depth.generateMipmaps = false;
      return [
        id,
        {
          detail,
          depth,
          projector: new T.Matrix4().fromArray(cameras[id].viewProjection).transpose(),
        },
      ];
    }),
  );
  await hardware;
  return Object.fromEntries(pairs);
}

export function fitMaterial(mesh, finish) {
  const source = mesh.material;
  for(let n=mesh;n;n=n.parent){
    if(source.name==='Pressure_Fabric'&&n.name==='shell_berth')return;
    if(/^(cloth_berth_|loom_service_|curtain_ring_|curtain_stile|prop_accelerometer|prop_accel_test|prop_capillary_)/.test(n.name))return;
  }
  if (
    !source.isMeshStandardMaterial ||
    source.transparent ||
    source.emissive?.getHex() ||
    /display|pixel|print|emitter|glaz|glass|stencil/i.test(source.name)
  )
    return;
  const material = source.clone(),
    projection = finish.projector.clone().multiply(mesh.matrixWorld);
  material.onBeforeCompile = (shader) => {
    shader.uniforms.uSurfaceProjector = { value: projection };
    shader.uniforms.uFinishDetail = { value: finish.detail };
    shader.uniforms.uFinishDepth = { value: finish.depth };
    shader.vertexShader = shader.vertexShader
      .replace(
        '#include <common>',
        '#include <common>\nuniform mat4 uSurfaceProjector; varying vec4 vSurfaceClip;',
      )
      .replace(
        '#include <begin_vertex>',
        '#include <begin_vertex>\nvSurfaceClip=uSurfaceProjector*vec4(position,1.);',
      );
    shader.fragmentShader = shader.fragmentShader
      .replace(
        '#include <common>',
        '#include <common>\nuniform sampler2D uFinishDetail, uFinishDepth; varying vec4 vSurfaceClip;',
      )
      .replace(
        '#include <map_fragment>',
        `#include <map_fragment>
        vec2 fitUV=vSurfaceClip.xy/max(.001,vSurfaceClip.w)*.5+.5;
        vec2 packedDepth=texture2D(uFinishDepth,clamp(fitUV,0.,1.)).rg;
        float surveyDepth=dot(floor(packedDepth*255.+.5),vec2(256.,1.))*.01;
        float rim=min(min(fitUV.x,1.-fitUV.x),min(fitUV.y,1.-fitUV.y));
        float tol=.019+.006*vSurfaceClip.w;
        float useFinish=.92*smoothstep(.002,.022,rim)*step(.04,vSurfaceClip.w)*step(.04,surveyDepth)*
          (1.-smoothstep(tol,tol+.035,abs(surveyDepth-vSurfaceClip.w)));
        vec3 finishLog=(texture2D(uFinishDetail,clamp(fitUV,0.,1.)).rgb*255.-128.)/82.;
        diffuseColor.rgb*=exp2(finishLog*useFinish);`,
      )
      .replace(
        '#include <roughnessmap_fragment>',
        '#include <roughnessmap_fragment>\nroughnessFactor=clamp(roughnessFactor-dot(finishLog,vec3(.012))*useFinish,.04,1.);',
      );
  };
  material.customProgramCacheKey = () => 'upwell_registered_finish_1';
  mesh.material = material;
}
