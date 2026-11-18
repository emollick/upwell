import * as T from 'three';

// The two optical interfaces return slightly different rays to the cabin.
// The apparent separation grows with angle and vanishes straight through.
export function laminatedPane(mesh,source,world){
  const uniforms={radiance:{value:null},probeReady:{value:false},origin:{value:new T.Vector3()},film:{value:0},
    practical:{value:1},panel:{value:null},panelFeed:{value:null},panelGain:{value:0},panelCamera:{value:0},tint:{value:new T.Color(.23,.33,.34)}};
  const material=new T.ShaderMaterial({name:source.name,uniforms,transparent:true,depthWrite:false,side:source.side,
    vertexShader:`#include <common>
      varying vec3 point,face;
      void main(){vec4 p=modelMatrix*vec4(position,1.);point=p.xyz;face=inverseTransformDirection(normalMatrix*normal,viewMatrix);
        gl_Position=projectionMatrix*viewMatrix*p;}`,
    fragmentShader:`varying vec3 point,face;uniform samplerCube radiance;uniform bool probeReady;
      uniform float film,practical,panelGain,panelCamera;uniform sampler2D panel,panelFeed;uniform vec3 tint,origin;
      vec3 roomRay(vec3 p,vec3 ray){
        vec3 nearCorner=vec3(-2.18,.025,origin.z-1.90),farCorner=vec3(2.18,2.60,origin.z+1.90);
        vec3 walls=mix(nearCorner,farCorner,step(vec3(0.),ray));
        vec3 hit=(walls-p)*(step(vec3(0.),ray)*2.-1.)/max(abs(ray),vec3(.0001));
        return p+ray*clamp(min(hit.x,min(hit.y,hit.z)),0.,6.)-origin;
      }
      // Surveyed emitting faces from the Blender saloon. Their 37 mm width falls
      // below the room probe's angular resolution from across the compartment.
      vec3 diffuser(vec3 p,vec3 ray,float side){
        vec3 n=vec3(-side*.8,-.6,0.),along=vec3(0.,0.,side);
        vec3 centre=vec3(side*1.96,2.30,0.)+n*.041;
        float facing=-dot(n,ray);
        float t=dot(p-centre,n)/max(.001,facing);
        vec3 hit=p+t*ray-centre;
        float station=hit.z< -3.80?-4.73:-2.87;
        hit.z-=station;
        vec2 at=vec2(dot(hit,along),dot(hit,cross(n,along)));
        // The eight narrow spacers are flush with the actual opal face.
        float halfWidth=station< -3.8&&side<0.?.279:.269;
        vec2 excess=abs(at)-vec2(halfWidth-.007,.0115);
        float edge=length(max(excess,0.))+min(max(excess.x,excess.y),0.)-.007;
        // Project the angular blur of a distant, slightly defocused lamp
        // into the fixture plane. Its outer housing catches weaker spill.
        float soft=.003+.003*clamp(t,0.,6.);
        float band=max(.7*fwidth(edge),soft),core=1.-smoothstep(-band,band,edge);
        float spread=max(0.,edge)/soft,skirt=exp(-spread*spread*.20);
        float pitch=(halfWidth*2.+.022)/9.;
        float seam=abs(fract(at.x/pitch)-.5)*pitch;
        float seamAA=max(.0005,.7*fwidth(at.x));
        float web=1.-.48*(1.-smoothstep(.0009-seamAA,.0009+seamAA,seam))*step(abs(at.x),pitch*4.);
        float housing=.012*(1.-smoothstep(.023,.060,edge));
        float energy=(.90*core+.065*skirt)*web+housing;
        return vec3(1.64,1.52,1.36)*practical*energy*step(.001,facing)*step(.01,t);
      }
      vec3 sources(vec3 p,vec3 ray,vec3 room){
        // Each plane contains two distinct light housings.
        for(int i=0;i<2;i++){
          float side=i==0?-1.:1.;
          room=max(room,diffuser(p,ray,side));
        }
        vec3 n=normalize(vec3(0.,.58,.815)),u=vec3(0.,n.z,-n.y);
        vec3 centre=vec3(.716,1.198,-5.104)+n*.0606;
        float facing=-dot(n,ray),t=dot(p-centre,n)/max(.001,facing);
        vec3 hit=p+ray*t-centre;
        vec2 uv=vec2(hit.x/.675,-dot(hit,u)/.211)+.5;
        vec2 aa=max(fwidth(uv),vec2(.001));
        vec2 mask=smoothstep(-aa,aa,min(uv,1.-uv));
        if(facing>.001&&t>.01&&mask.x*mask.y>.001){
          vec4 ink=texture2D(panel,clamp(uv,0.,1.));
          vec3 pixels=ink.rgb;
          if(panelCamera>.5&&ink.a<1.){
            vec2 feedUv=vec2(uv.x,.5+(.5-uv.y)*.65625);
            pixels=mix(texture2D(panelFeed,feedUv).rgb,ink.rgb,ink.a);
          }
          room=mix(room,pixels*panelGain*2.3,mask.x*mask.y);
        }
        return room;
      }
      void main(){
        vec3 v=normalize(cameraPosition-point),n=faceforward(normalize(face),-v,normalize(face));
        float incidence=clamp(dot(n,v),.001,1.);
        vec3 first=reflect(-v,n),transmitted=refract(-v,n,1./1.51);
        float ct=max(.27,abs(dot(n,transmitted)));
        vec3 shear=.032*(transmitted-n*dot(transmitted,n))/ct;
        vec3 r=probeReady?textureCube(radiance,roomRay(point,first)).rgb:vec3(.18,.22,.22);
        vec3 back=probeReady?textureCube(radiance,roomRay(point+shear,first)).rgb:r;
        float rs=(incidence-1.51*ct)/(incidence+1.51*ct),rp=(1.51*incidence-ct)/(1.51*incidence+ct);
        bool saloonPane=point.z< -1.90&&abs(n.y)<.30;
        if(probeReady&&saloonPane&&cameraPosition.z< -1.90){
          r=sources(point,first,r);back=sources(point+shear,first,back);
        }
        float coating=saloonPane?.022:.011;
        float reflection=clamp(coating+.91*(.5*(rs*rs+rp*rp)-.0413),coating,.67);
        float path=1./ct;
        float absorption=.0035*path+.49*film;
        float alpha=clamp(reflection+absorption,.006,.88);
        vec3 bounced=(r*.74+back*vec3(.238,.262,.267)*(1.-.70*film))*reflection;
        gl_FragColor=vec4((bounced+tint*absorption*(1.-.82*film))/alpha,alpha);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }`});
  mesh.onBeforeRender=r=>{
    const lighting=world.photometry;if(!lighting)return;
    const probe=lighting.localProbe,valid=!!lighting.filteredScene&&r.getRenderTarget()!==probe;
    uniforms.probeReady.value=valid;uniforms.radiance.value=valid?probe.texture:null;
    uniforms.origin.value.copy(lighting.cubeCamera.position);
    uniforms.practical.value=world.rideState?.lamps?1:0;
    const display=world.instruments;
    uniforms.panel.value=display.tex;uniforms.panelGain.value=display.gain;
    uniforms.panelCamera.value=display.material.uniforms.cameraOn.value;
    uniforms.panelFeed.value=r.getRenderTarget()===display.target?null:display.target.texture;
    uniforms.film.value=source.name==='Surface_window'&&world.base.roller_shade?world.base.roller_shade.v:0;
  };
  return material;
}
