import * as T from 'three';

// Look through the actual shallow vessel. Its rear scale and wick are
// rendered under the current cabin lights into a small linear-radiance
// target; rays refract through the current three-dimensional liquid boundary
// before sampling that target. The protective glass and housing are separate.
export class CapillaryOptics {
  constructor(world, fixture, survey, physics) {
    this.world=world; this.physics=physics;
    const {radius, depth}=physics;
    const origin=new T.Vector3(...survey.center), right=new T.Vector3(...survey.right);
    const up=new T.Vector3(...survey.up), normal=new T.Vector3(...survey.normal);
    const basis=new T.Matrix4().makeBasis(right,up,normal);
    this.localLightBasis=new T.Matrix3().setFromMatrix4(basis).transpose();this.sunRay=new T.Vector3();
    this.group=new T.Group(); this.group.name='Sealed galley fluid volume';
    this.group.position.copy(origin); this.group.quaternion.setFromRotationMatrix(basis);
    world.scene.add(this.group); this.group.updateMatrixWorld(true);
    const resolution=world.softwareGpu?256:512;
    this.backing=new T.WebGLRenderTarget(resolution,resolution,{
      type:world.r.extensions.has('EXT_color_buffer_float')?T.HalfFloatType:T.UnsignedByteType,
      minFilter:T.LinearFilter,magFilter:T.LinearFilter,depthBuffer:true,stencilBuffer:false,
    });
    this.backing.texture.colorSpace=T.LinearSRGBColorSpace;
    this.camera=new T.OrthographicCamera(-radius,radius,radius,-radius,.0003,.14);
    this.camera.position.copy(origin).addScaledVector(normal,depth*.5-.0004);
    this.camera.up.copy(up);this.camera.lookAt(origin.clone().addScaledVector(normal,-depth));
    this.camera.layers.set(2); this.camera.updateMatrixWorld();
    this.backingMeshes=[];
    fixture.traverse(n=>{
      if(!n.isMesh||n.material.transparent||n.userData.isGlass||/glass|lens|glazing/i.test(n.material.name))return;
      for(let p=n;p;p=p.parent)if(!p.visible)return;
      n.layers.enable(2);this.backingMeshes.push(n);
    });
    world.scene.traverse(n=>{if(n.isLight)n.layers.enable(2);});
    const uniforms={
      backplate:{value:this.backing.texture},roomRadiance:{value:null},useRoom:{value:false},
      eye:{value:new T.Vector3()},toWorld:{value:new T.Matrix3().setFromMatrix4(basis)},
      keyLight:{value:new T.Vector3(0,.3,1)},keyEnergy:{value:.25},
      cellRadius:{value:radius},halfDepth:{value:depth/(radius*2)},coreRadius:{value:physics.coreRadius},
      coreDepth:{value:physics.coreDepth},gasCenter:{value:new T.Vector2()},gasRadii:{value:physics.radii},
    };
    this.material=new T.ShaderMaterial({name:'Wetted sight cell / optical path',uniforms,
      vertexShader:`varying vec2 surface;uniform float cellRadius;
        void main(){surface=position.xy/cellRadius;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}`,
      fragmentShader:`precision highp float;
        uniform sampler2D backplate;uniform samplerCube roomRadiance;uniform bool useRoom;
        uniform vec3 eye,keyLight;uniform mat3 toWorld;uniform float keyEnergy,cellRadius,halfDepth,coreRadius,coreDepth;
        uniform vec2 gasCenter;uniform float gasRadii[9];varying vec2 surface;
        float bubbleRadius(float z){
          float s=clamp((z/(halfDepth*coreDepth)*.5+.5)*8.,0.,8.);
          int a=min(7,int(floor(s)));return mix(gasRadii[a],gasRadii[a+1],s-float(a));
        }
        vec3 reflectedLight(vec3 direction){
          if(useRoom)return textureCube(roomRadiance,toWorld*direction).rgb;
          return vec3(.19,.22,.23)*(.65+.35*max(0.,direction.y));
        }
        void main(){
          if(dot(surface,surface)>.9999)discard;
          vec3 ray=normalize(vec3(surface,halfDepth)-eye);
          if(ray.z>=-.0001)discard;
          vec3 waterRay=refract(ray,vec3(0.,0.,1.),1./1.333);
          vec2 airSlope=ray.xy/(-ray.z),waterSlope=waterRay.xy/(-waterRay.z);
          float dz=2.*halfDepth/20.,antialias=clamp(.85*length(fwidth(surface)),.001,.038);
          float wetLength=.00032,lastWet=1.,minDistance=40.,rim=0.,strongest=0.,internal=0.;
          vec2 at=surface,bend=vec2(0.);vec3 interfaceNormal=vec3(0.,1.,0.);
          for(int i=0;i<20;i++){
            float z=halfDepth-(float(i)+.5)*dz;
            vec2 sampleAt=at+(mix(airSlope,waterSlope,lastWet)+bend)*dz*.5;
            vec2 delta=sampleAt/coreRadius-gasCenter;
            float d=length(delta)-bubbleRadius(z);
            float wet=smoothstep(-antialias,antialias,d);
            if(length(sampleAt)>=coreRadius||abs(z)>=halfDepth*coreDepth)wet=1.;
            float dr=(bubbleRadius(z+dz*.30)-bubbleRadius(z-dz*.30))/(dz*.60);
            vec3 n=normalize(vec3(delta/max(.00001,length(delta)),-dr*coreRadius));
            if(abs(d)<minDistance){minDistance=abs(d);interfaceNormal=n;}
            if(i>0&&abs(wet-lastWet)>.32){
              vec3 entering=normalize(vec3(mix(airSlope,waterSlope,lastWet)+bend,-1.));
              n=faceforward(n,entering,n);
              vec3 transmitted=refract(entering,n,lastWet>.5?1.333:1./1.333);
              if(dot(transmitted,transmitted)<.001)internal=1.;
              if(transmitted.z<-.08){
                bend=clamp(transmitted.xy/(-transmitted.z)-mix(airSlope,waterSlope,wet),vec2(-1.65),vec2(1.65));
              }
              strongest=max(strongest,.020+.98*pow(1.-abs(dot(n,entering)),5.));
            }
            vec2 slope=mix(airSlope,waterSlope,wet)+bend;
            wetLength+=wet*dz*cellRadius*sqrt(1.+dot(slope,slope));
            at+=slope*dz;lastWet=wet;
            rim=max(rim,smoothstep(.994,1.012,length(at)));
          }
          float edge=1.-smoothstep(antialias*.45,.016+antialias,minDistance);
          vec2 lookup=at+interfaceNormal.xy*edge*.020;
          if(length(lookup)>.997)lookup=normalize(lookup)*.997;
          vec2 uv=.5+.5*lookup,dispersion=bend*(.0011*edge);
          vec3 rear=vec3(texture2D(backplate,uv+dispersion).r,texture2D(backplate,uv).g,texture2D(backplate,uv-dispersion).b);
          // Dilute tracer absorbs red light along the optical path. The
          // room and the engraved scale remain visible through the water.
          vec3 transmission=exp(-wetLength*vec3(54.,16.,12.5));
          vec3 col=rear*transmission+vec3(.020,.095,.082)*(1.-transmission);
          // The curved shoulder diverts light onto the physical rear graticule.
          // Its bright and shadowed bands travel with the meniscus, even when
          // the passenger stays still. Broad source angles soften the focus.
          vec2 lampAt=lookup-keyLight.xy*halfDepth*.50/max(.42,abs(keyLight.z));
          vec2 fromGas=lampAt/coreRadius-gasCenter;
          float wall=length(fromGas)-gasRadii[4];
          float shoulder=clamp(gasRadii[4]-gasRadii[1],.017,.086);
          float band=max(.009,antialias*1.5);
          float toward=.32+.68*smoothstep(-.25,.90,dot(normalize(fromGas+vec2(.00001)),normalize(keyLight.xy+vec2(.0001))));
          float focusDist=(wall-shoulder*.37)/(band+.16*shoulder),shadeDist=(wall+shoulder*.44)/(band+.50*shoulder);
          float focus=exp(-focusDist*focusDist),penumbra=exp(-shadeDist*shadeDist);
          col*=1.+keyEnergy*toward*(.43*focus-.19*penumbra);
          col=mix(col,vec3(.026,.058,.055)+rear*.14,rim*.81);
          vec3 n=faceforward(interfaceNormal,ray,interfaceNormal);
          float fresnel=.0204+.9796*pow(1.-abs(dot(n,ray)),5.);
          vec3 room=reflectedLight(reflect(ray,n));
          vec3 inner=mix(room,vec3(.016,.033,.031),.46+.22*max(0.,-n.y));
          col=mix(col,mix(room,inner,internal),min(.91,edge*(.36+.53*fresnel)+.52*strongest+.42*internal));
          float line=exp(-minDistance/(.002+antialias*.46));
          col+=vec3(.52,.69,.64)*line*(.09+.48*fresnel);
          col+=vec3(1.,.96,.88)*edge*keyEnergy*.11*pow(max(0.,dot(reflect(ray,n),keyLight)),72.);
          vec3 windowNormal=normalize(vec3(.073*surface,1.));
          float film=.031+.969*pow(1.-abs(dot(windowNormal,ray)),5.);
          col=mix(col,reflectedLight(reflect(ray,windowNormal)),film);
          gl_FragColor=vec4(max(vec3(.0001),col),1.);
          #include <tonemapping_fragment>
          #include <colorspace_fragment>
        }`,
    });
    const face=new T.Mesh(new T.PlaneGeometry(2*radius,2*radius),this.material);
    face.name='Finite-depth liquid and trapped gas';face.position.z=depth*.5-.0003;
    face.onBeforeRender=(r,s,camera)=>{
      camera.getWorldPosition(uniforms.eye.value);this.group.worldToLocal(uniforms.eye.value).multiplyScalar(1/radius);
      const probe=this.world.photometry.localProbe,valid=this.world.photometry.filteredScene&&r.getRenderTarget()!==probe;
      uniforms.roomRadiance.value=valid?probe.texture:null;uniforms.useRoom.value=!!valid;
    };
    this.group.add(face);this.lastCapture=-Infinity;this.key='';
  }
  update(state, time) {
    const u=this.material.uniforms;u.gasCenter.value.set(this.physics.cx,this.physics.cy);
    const light=this.world.photometry;
    if(light){
      const power=Math.min(1,light.sun.intensity*.23);
      const sun=this.sunRay.copy(light.solar).applyMatrix3(this.localLightBasis);
      const incident=power*Math.max(0,sun.z);
      u.keyLight.value.set(.23,.39,1).addScaledVector(sun,2.4*incident).normalize();
      u.keyEnergy.value=.11+(state.berthLight?.31:0)+.52*incident;
    }
    const key=[state.berthLight,state.lamps,state.shade,state.curtain].join('/');
    if(this.lastCapture!==-Infinity&&(state.room!=='berth'||(time>=this.lastCapture&&time-this.lastCapture<1.25&&this.key===key)))return;
    const {r,scene}=this.world,old=r.getRenderTarget(),face=r.getActiveCubeFace(),mip=r.getActiveMipmapLevel(),shadows=r.shadowMap.autoUpdate;
    r.shadowMap.autoUpdate=false;r.setRenderTarget(this.backing);r.clear(true,true,true);r.render(scene,this.camera);
    r.setRenderTarget(old,face,mip);r.shadowMap.autoUpdate=shadows;
    this.lastCapture=time;this.key=key;
  }
}
