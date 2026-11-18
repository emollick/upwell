import * as T from 'three';

// Work on display-referred color after the passenger lens and tone curve.
// Sampling HDR values here would spread a sunlit steel glint into dark trim.
const edgeResolve=`uniform sampler2D picture,depthMap;uniform vec2 size;varying vec2 at;
float luma(vec3 c){return dot(c,vec3(.2126,.7152,.0722));}
void main(){
  vec2 d=1./size,dx=vec2(d.x,0.),dy=vec2(0.,d.y);
  vec3 center=texture2D(picture,at).rgb;gl_FragColor=vec4(center,1.);
  float z=texture2D(depthMap,at).r;
  if(z>.999999&&min(min(texture2D(depthMap,at-dx).r,texture2D(depthMap,at+dx).r),
                    min(texture2D(depthMap,at-dy).r,texture2D(depthMap,at+dy).r))>.999999)return;
  float nw=luma(texture2D(picture,at-dx+dy).rgb),ne=luma(texture2D(picture,at+d).rgb);
  float sw=luma(texture2D(picture,at-d).rgb),se=luma(texture2D(picture,at+dx-dy).rgb);
  float m=luma(center),lo=min(m,min(min(nw,ne),min(sw,se))),hi=max(m,max(max(nw,ne),max(sw,se)));
  if(hi-lo<max(.030,hi*.125))return;
  float n=luma(texture2D(picture,at+dy).rgb),s=luma(texture2D(picture,at-dy).rgb);
  float e=luma(texture2D(picture,at+dx).rgb),w=luma(texture2D(picture,at-dx).rgb);
  float mid=(lo+hi)*.5;
  float bright=step(mid,m)+step(mid,nw)+step(mid,ne)+step(mid,sw)+step(mid,se)+step(mid,n)+step(mid,s)+step(mid,e)+step(mid,w);
  if(bright<2.5||bright>6.5)return;
  // Texture north is +Y. Rotate the luminance gradient to follow the seam.
  vec2 tangent=vec2(sw+se-nw-ne,ne+se-nw-sw);
  float reduction=max(.008,(nw+ne+sw+se)*.03125);
  vec2 along=clamp(tangent/(min(abs(tangent.x),abs(tangent.y))+reduction),-6.,6.)*d;
  vec3 inner=.5*(texture2D(picture,at-along/6.).rgb+texture2D(picture,at+along/6.).rgb);
  vec3 outer=inner*.5+.25*(texture2D(picture,at-.5*along).rgb+texture2D(picture,at+.5*along).rgb);
  float result=luma(outer);gl_FragColor=vec4(result<lo||result>hi?inner:outer,1.);
}`;

// Render the actual cabin and the item through one lens. Depth isolates the
// object at hand distance while leaving moving light and reflections intact.
export class PassengerOptics {
  constructor(renderer,softwareGpu=false){
    this.renderer=renderer;
    this.enabled=renderer.extensions.has('EXT_color_buffer_float');
    const gl=renderer.getContext();
    this.aaModes=[['auto','Automatic']];
    if(!this.enabled){this.activeAA=gl.getContextAttributes()?.antialias?'Browser multisampling':'Off';return;}
    const samplesFor=format=>Array.from(gl.getInternalformatParameter(gl.RENDERBUFFER,format,gl.SAMPLES)||[]);
    const depth=samplesFor(gl.DEPTH_COMPONENT24);
    const supported=samplesFor(gl.RGBA16F).filter(n=>[2,4,8].includes(n)&&depth.includes(n)).sort((a,b)=>a-b);
    this.aaModes.push(['off','Off'],['fxaa','FXAA'],...supported.map(n=>['msaa'+n,n+'× MSAA']));
    const samples=softwareGpu?0:Math.max(0,...supported.filter(n=>n<=4));
    this.autoAA=samples?'msaa'+samples:softwareGpu?'off':'fxaa';
    this.target=new T.WebGLRenderTarget(1,1,{type:T.HalfFloatType,depthBuffer:true,
      depthTexture:new T.DepthTexture(1,1,T.UnsignedIntType),samples,stencilBuffer:false});
    this.target.texture.colorSpace=T.LinearSRGBColorSpace;
    const u={radiance:{value:this.target.texture},depthMap:{value:this.target.depthTexture},
      size:{value:new T.Vector2()},invProjection:{value:new T.Matrix4()},nearFar:{value:new T.Vector2()},
      focus:{value:0},band:{value:0},focusStrength:{value:1},encodeDisplay:{value:false},toneMappingExposure:{value:1}};
    this.uniforms=u;
    this.material=new T.ShaderMaterial({uniforms:u,depthTest:false,depthWrite:false,
      vertexShader:'varying vec2 at;void main(){at=uv;gl_Position=vec4(position.xy,0.,1.);}',
      fragmentShader:`uniform sampler2D radiance,depthMap;uniform vec2 size,nearFar;uniform float focus,band,focusStrength;uniform bool encodeDisplay;
      #ifndef TONE_MAPPING
      #include <tonemapping_pars_fragment>
      #endif
      uniform mat4 invProjection;varying vec2 at;
      float zmetres(float z){return nearFar.x*nearFar.y/(nearFar.y-z*(nearFar.y-nearFar.x));}
      vec3 viewPos(vec2 uv,float z){vec4 p=invProjection*vec4(uv*2.-1.,z*2.-1.,1.);return p.xyz/p.w;}
      void main(){vec2 px=1./size;
        float z=texture2D(depthMap,at).x,linearZ=zmetres(z);
        vec3 color=texture2D(radiance,at).rgb;
        if(z<.999999&&linearZ<13.) {
          vec3 p=viewPos(at,z),normal=normalize(cross(dFdx(p),dFdy(p)));
          float occ=0.;
          for(int i=0;i<8;i++){
            float angle=float(i)*2.3999632;float radius=clamp(size.y*.042/max(linearZ,.08),3.,38.)*(.34+.66*float(i+1)/8.);
            vec2 uv=at+vec2(cos(angle),sin(angle))*px*radius;
            vec3 d=viewPos(uv,texture2D(depthMap,uv).x)-p;float dist=length(d);
            occ+=max(0.,dot(normal,d)/max(.001,dist)-.17)*(1.-smoothstep(.015,.18,dist));
          }
          color*=1.-min(.29,occ*.098);
        }
        if(focus>0.) {
          float blur=focusStrength*clamp((abs(linearZ-focus)-band)/max(linearZ,.04),0.,1.)*min(9.,size.y*.010);
          if(blur>.3){vec3 sum=color;float weight=1.;
            for(int i=0;i<14;i++){float j=float(i)+.5,angle=j*2.3999632;
              vec2 uv=at+vec2(cos(angle),sin(angle))*sqrt(j/14.)*blur*px;
              float depth=zmetres(texture2D(depthMap,uv).x);
              float w=depth>focus+band||linearZ<focus+band?1.:.025;
              sum+=texture2D(radiance,uv).rgb*w;weight+=w;
            }color=sum/weight;}
        }
        vec3 halo=vec3(0.);
        for(int i=0;i<4;i++){float a=float(i)*1.5707963+.36;
          vec3 c=texture2D(radiance,at+vec2(cos(a),sin(a))*px*3.2).rgb;
          halo+=max(vec3(0.),c-vec3(2.9));}
        color+=min(vec3(.25),halo*.013);
        if(encodeDisplay){gl_FragColor=sRGBTransferOETF(vec4(ACESFilmicToneMapping(color),1.));return;}
        gl_FragColor=vec4(color,1.);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }`});
    this.scene=new T.Scene();const quad=new T.Mesh(new T.PlaneGeometry(2,2),this.material);
    quad.frustumCulled=false;this.quad=quad;this.scene.add(quad);this.camera=new T.Camera();
    this.displayTarget=new T.WebGLRenderTarget(1,1,{depthBuffer:false,stencilBuffer:false});
    this.edgeMaterial=new T.ShaderMaterial({depthTest:false,depthWrite:false,toneMapped:false,
      uniforms:{picture:{value:this.displayTarget.texture},size:u.size,depthMap:u.depthMap},vertexShader:this.material.vertexShader,fragmentShader:edgeResolve});
    this.setAA('auto');
  }
  setAA(mode){
    if(!this.enabled)return;
    const choice=mode==='auto'?this.autoAA:mode;
    const samples=choice.startsWith('msaa')?Number(choice.slice(4)):0;
    if(this.target.samples!==samples){
      // Attachments have immutable sample counts once allocated by WebGL.
      this.target.dispose();this.target.samples=samples;
    }
    this.fxaa=choice==='fxaa';
    this.activeAA=this.aaModes.find(([id])=>id===choice)[1];
  }
  render(scene,camera,inspection){
    const r=this.renderer;r.setRenderTarget(null);
    if(!this.enabled){r.clear();r.render(scene,camera);return;}
    r.getDrawingBufferSize(this.uniforms.size.value);
    const {x,y}=this.uniforms.size.value;
    if(this.target.width!==x||this.target.height!==y)this.target.setSize(x,y);
    this.uniforms.invProjection.value.copy(camera.projectionMatrixInverse);
    this.uniforms.nearFar.value.set(camera.near,camera.far);
    this.uniforms.focus.value=inspection?.distance??0;this.uniforms.band.value=inspection?.focusBand??0;
    this.uniforms.focusStrength.value=1-(inspection?.carryBlend??0);
    r.setRenderTarget(this.target);r.clear();r.render(scene,camera);
    this.uniforms.encodeDisplay.value=this.fxaa;this.uniforms.toneMappingExposure.value=r.toneMappingExposure;
    if(this.fxaa){
      if(this.displayTarget.width!==x||this.displayTarget.height!==y)this.displayTarget.setSize(x,y);
      r.setRenderTarget(this.displayTarget);r.clear();r.render(this.scene,this.camera);
      this.quad.material=this.edgeMaterial;
    }
    r.setRenderTarget(null);r.clear();r.render(this.scene,this.camera);
    this.quad.material=this.material;
  }
}
