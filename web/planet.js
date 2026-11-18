import * as T from 'three';
import {loadStarCatalog,loadGalacticLight,adaptStellarEye,STELLAR_GLSL} from './stellar-sky.js';
import {loadWeatherNoise,marineOrganization,WEATHER_GLSL,WEATHER_DEFAULTS} from './weather-density.js';

// No cloud photographs or view panoramas. Distances km; +X east,+Y up,+Z north.
export async function createPlanetSky(){
  const [day,night,broadCloud,regional,data,carMask,catalogue,galaxy]=await Promise.all([
    new T.TextureLoader().loadAsync(new URL('./assets/planet/earth-day.webp',import.meta.url).href),
    new T.TextureLoader().loadAsync(new URL('./assets/planet/earth-night.webp',import.meta.url).href),
    new T.TextureLoader().loadAsync(new URL('./assets/planet/earth-cloud-density.webp',import.meta.url).href),
    new T.TextureLoader().loadAsync(new URL('./assets/planet/atlantic-weather.png',import.meta.url).href),loadWeatherNoise(),
    new T.TextureLoader().loadAsync(new URL('./assets/planet/car-sun-mask.png',import.meta.url).href),loadStarCatalog(),loadGalacticLight()]);
  day.colorSpace=T.SRGBColorSpace;day.wrapS=T.RepeatWrapping;day.anisotropy=8;
  night.colorSpace=T.SRGBColorSpace;night.wrapS=T.RepeatWrapping;night.anisotropy=4;
  broadCloud.colorSpace=T.NoColorSpace;broadCloud.wrapS=T.RepeatWrapping;
  regional.colorSpace=T.NoColorSpace;regional.minFilter=T.LinearMipMapLinearFilter;regional.anisotropy=4;
  const noise=new T.Data3DTexture(data,64,64,64);
  noise.format=T.RGBAFormat;noise.type=T.UnsignedByteType;noise.magFilter=T.LinearFilter;
  noise.minFilter=T.LinearMipmapLinearFilter;noise.generateMipmaps=true;
  noise.wrapS=noise.wrapT=noise.wrapR=T.RepeatWrapping;noise.unpackAlignment=1;noise.needsUpdate=true;
  const cells=new T.DataTexture(marineOrganization(),256,256,T.RGBAFormat);
  cells.wrapS=cells.wrapT=T.RepeatWrapping;cells.magFilter=T.LinearFilter;cells.minFilter=T.LinearMipmapLinearFilter;cells.generateMipmaps=true;cells.needsUpdate=true;
  const uniforms={dayMap:{value:day},nightMap:{value:night},broadCloudMap:{value:broadCloud},regionalMap:{value:regional},noiseVolume:{value:noise},marineCells:{value:cells},oceanSky:{value:null},hasOceanSky:{value:false},altitudeKm:{value:0},weatherTime:{value:0},
    coverage:{value:.58},evolution:{value:.5},weatherLod:{value:0},solarAtCar:{value:1},carMask:{value:carMask},wind:{value:new T.Vector2(.018,.007)},
    sunDirection:{value:new T.Vector3(-.6,.72,.35).normalize()},longitude:{value:-36*Math.PI/180}};
  const material=new T.ShaderMaterial({glslVersion:T.GLSL3,uniforms,side:T.BackSide,depthTest:false,depthWrite:false,toneMapped:true,
    vertexShader:/*glsl*/`
      out vec3 vDirection;
      void main(){vDirection=position;vec4 p=projectionMatrix*vec4(mat3(viewMatrix)*position,1.);gl_Position=p.xyww;}
    `,
    fragmentShader:/*glsl*/`
      precision highp float;
      in vec3 vDirection;
      out vec4 fragColor;
      #define gl_FragColor fragColor
      uniform sampler2D dayMap,nightMap,carMask;
      uniform samplerCube oceanSky;uniform bool hasOceanSky;
      uniform float altitudeKm,longitude,solarAtCar;
      uniform vec3 sunDirection;
      const float PI=3.14159265359,R=6371.;
      const vec3 betaR=vec3(.0058,.0135,.0331),betaM=vec3(.015,.014,.013),betaO3=vec3(.00065,.001881,.000085);
      ${WEATHER_GLSL}
      vec2 sphere(vec3 ro,vec3 rd,float radius){float b=dot(ro,rd),c=dot(ro,ro)-radius*radius,h=b*b-c;
        if(h<0.)return vec2(-1.);h=sqrt(h);return vec2(-b-h,-b+h);}
      vec2 uvEarth(vec3 n){vec3 up=vec3(cos(longitude),0.,sin(longitude)),east=vec3(-sin(longitude),0.,cos(longitude));
        vec3 p=n.x*east+n.y*up+vec3(0.,n.z,0.);return vec2(atan(p.z,p.x)/(2.*PI)+.5,asin(clamp(p.y,-1.,1.))/PI+.5);}
      float sunVisible(vec3 p){float h=max(0.,length(p)-R),mu=dot(normalize(p),sunDirection),dip=acos(clamp(R/(R+h),0.,1.));
        return smoothstep(-.00465,.00465,asin(clamp(mu,-1.,1.))+dip);}
      float hg(float mu,float g){return .07957747*(1.-g*g)/pow(max(.015,1.+g*g-2.*g*mu),1.5);}
      float starTransmission(vec3 d,vec3 aim,vec3 sun,float height,vec3 air,float solarVisible){
        float litSky=dot(air,vec3(.2126,.7152,.0722)),adapt=1./(1.+170.*litSky);
        float glare=1.-.975*pow(max(0.,dot(d,sun)),24.)*solarVisible;
        float dip=sqrt(max(0.,1.-pow(6371./(6371.+max(height,0.)),2.)));
        // Bright Earth or the sun elsewhere in the same lens raises the
        // observer's exposure floor even when this particular ray sees space.
        float earthInView=(1.-smoothstep(-.27,.31,aim.y+dip))*smoothstep(-.13,.23,sun.y);
        float sunInView=smoothstep(.69,.975,dot(aim,sun))*solarVisible;
        float lensGain=1./(1.+.78*earthInView+1.12*sunInView);
        return adapt*adapt*glare*lensGain*smoothstep(.002,.082,d.y+dip);
      }
// Average unresolved capillary waves, while keeping longer groups of swell
// and wind roughness where a pixel still covers part of a crest. Positions are km.
vec3 coastalSlopes(vec2 p,float footprint,float t){
  vec2 windUnit=vec2(.86,.51),crossWind=vec2(-.51,.86);
  vec2 uv=vec2(dot(p,windUnit),dot(p,crossWind));
  vec4 groups=fieldNoise(vec3(uv.x/3.7-.00047*t,.39,uv.y/2.0+.21));
  vec4 windField=fieldNoise(vec3(uv.x/13.2+.41,.71,uv.y/6.8+.00024*t));
  float cap=exp(-.19*pow(86.2*footprint,2.));
  float swell=cap*cos(86.2*uv.x-.93*t+4.3*groups.r);
  vec2 tilt=windUnit*(.047*swell)+.16*(groups.rg-.50)*(1.-smoothstep(.09,.65,footprint))
            +.066*(windField.gb-.50)*(1.-smoothstep(.65,2.8,footprint));
  return vec3(tilt,clamp(.47+.68*(windField.r-.50)+.48*(groups.g-.5),.23,.79));
}
      vec3 ground(vec3 ro,vec3 d,float t){
        vec3 n=normalize(ro+d*t),albedo=texture(dayMap,uvEarth(n)).rgb;
        float nl=max(dot(n,sunDirection),0.);vec3 color=albedo*(nl*.96+.0015);
        vec3 intercepted=normalize(n+sunDirection*(5./R)/max(.14,dot(n,sunDirection)))*R;
        vec4 obs=regionalColumn(intercepted);
        float cover=mix(broadCloudDensity(intercepted),1.-exp(-obs.x*.19),obs.w);
        float nearby=(1.-smoothstep(150.,410.,t*R))*(1.-smoothstep(38.,155.,altitudeKm))*smoothstep(.055,.21,nl);
        if(nearby>.002){
          const float layer[5]=float[5](1.43,2.71,5.78,7.94,10.68);
          const float width[5]=float[5](1.15,1.48,2.12,2.34,2.40);
          vec3 surface=n*R,drift=vec3(wind.x*weatherTime,R,wind.y*weatherTime);
          float depth=0.,secant=1./max(.08,nl);
          for(int i=0;i<5;i++){
            vec3 at=surface+sunDirection*(layer[i]*secant);
            depth+=width[i]*localCloud(at-drift,length(at)-R,.62);
          }
          cover=mix(cover,1.-exp(-.90*secant*depth),nearby);
        }
        color*=1.-.48*cover;
        vec3 night=texture(nightMap,uvEarth(n)).rgb;
        // Recorded city-light geography, emitted only on the night hemisphere.
        // Suppress the source's dim photographic land/ocean base.
        float lights=max(0.,max(night.r,night.g)-.025);
        color+=vec3(1.,.62,.28)*lights*.55*(1.-smoothstep(-.12,.025,dot(n,sunDirection)));
        float water=smoothstep(.003,.035,albedo.b-max(albedo.r,albedo.g*.72));
        // At orbital footprints the pixel contains many waves. Integrate their
        // slope distribution instead of sampling one ray against a moving crest.
        float nv=max(.001,dot(n,-d));
        vec3 sunGlint=vec3(0.);
        if(nl>.0001&&water>.001){
          vec3 halfV=normalize(sunDirection-d);float nh=max(.001,dot(n,halfV)),vh=max(.001,dot(-d,halfV));
          vec3 east=normalize(cross(abs(n.z)<.99?vec3(0.,0.,1.):vec3(0.,1.,0.),n));
          vec3 windward=east*.895+cross(n,east)*.446;
          vec2 slope=vec2(dot(halfV,windward),dot(halfV,cross(n,windward)))/nh;
          float density=exp(-.5*dot(slope*slope,vec2(47.,72.)))*9.26/max(.0001,nh*nh*nh*nh);
          float mask=min(1.,2.*nh*min(nv,nl)/vh),f=.0204+.9796*pow(1.-vh,5.);
          vec3 solar=exp(-(betaR*8.+betaM*.85)/max(.045,nl+.016));
          sunGlint=solar*water*(1.-.92*cover)*density*mask*f*.74/nv;
        }
        // Continue the filmed water surface out to the geometric horizon. A
        // grazing ray sees sky reflected off water even in the cloud shadow.
        float localOcean=(1.-smoothstep(12.,38.,altitudeKm))*(1.-smoothstep(.15,.30,length(n.xz)))*step(.9,n.y);
        if(localOcean>.001){
          vec2 oceanKm=n.xz*R;float footprint=max(length(dFdx(oceanKm)),length(dFdy(oceanKm)));
          vec3 groups=coastalSlopes(oceanKm,footprint,weatherTime);
          vec3 waveNormal=normalize(n+vec3(groups.x,0.,groups.y));
          float viewCos=max(.006,mix(dot(n,-d),dot(waveNormal,-d),.61));vec3 reflected=reflect(d,waveNormal);
          reflected.y=max(.009,reflected.y)+.075*groups.z;reflected=normalize(reflected);
          float toward=clamp(dot(reflected,sunDirection)*.5+.5,0.,1.);
          float clouds=noiseC(reflected*1.95+vec3(weatherTime*.00013,.24,.53),0);
          vec3 sky=mix(vec3(.23,.38,.53),vec3(.58,.62,.61),smoothstep(.26,.72,clouds));
          sky+=vec3(.17,.102,.053)*pow(toward,5.);
          if(hasOceanSky){
            sky=textureLod(oceanSky,reflected,.70+2.1*groups.z).rgb;
          }
          // A rough ocean pixel reflects a cone. Resolve the broad part of the
          // same marine field beneath its base rather than a binary pencil ray.
          vec3 meanRay=reflect(d,n);meanRay.y=max(.02,meanRay.y)+.105*groups.z;meanRay=normalize(meanRay);
          vec3 cloudFoot=n*R+meanRay*(1.82/max(.05,dot(n,meanRay)))-vec3(wind.x*weatherTime,R,wind.y*weatherTime);
          vec4 cell=fieldNoise(cloudFoot/16.);float rounded=.60*cell.r+.40*cell.g;
          float broad=fieldNoise(vec3(cloudFoot.x/26.,.37,cloudFoot.z/26.)).a;
          float overcast=smoothstep(.28,.70,.56*rounded+.44*broad);
          float day=smoothstep(-.11,.14,sunDirection.y),f=.024+.976*pow(1.-viewCos,5.);
          vec3 clear=vec3(.159,.219,.267)+vec3(.17,.13,.075)*pow(toward,7.);
          vec3 cloud=vec3(.305,.304,.277)+vec3(.18,.137,.068)*pow(toward,4.);
          vec3 localReflection=mix(clear,cloud,overcast)*(.50+.69*groups.z)*(.12+.88*day);
          sky=mix(sky,localReflection,.54*(1.-smoothstep(14.,32.,altitudeKm)));
          vec3 liquid=mix(vec3(.017,.052,.067)*(.13+.87*day)*(1.-.54*cover),sky,f);
          color=mix(color,liquid,localOcean);
        }
        return color+sunGlint;
      }
      // The same curved, exponentially stratified air path attenuates sea,
      // sky and cloud radiance. Exact homogeneous-step integration prevents
      // the bright horizon overshoot of beta*distance at high optical depth.
      void airStep(vec3 p,vec3 d,float distanceKm,out vec3 transmission,out vec3 inscatter){
        float h=max(0.,(length(p)-1.)*R),dr=exp(-h/8.),dm=exp(-h/.85);
        float mu=dot(d,sunDirection),lightMu=dot(normalize(p),sunDirection);
        float phaseR=.0596831*(1.+mu*mu),phaseM=hg(mu,.72);
        float ozone=max(0.,1.-abs(h-25.)/15.);
        float ozoneAbove=h<25.?15.-max(0.,h-10.)*ozone*.5:max(0.,40.-h)*ozone*.5;
        float sunPath=1./max(.045,lightMu+.065);
        vec3 sunlight=exp(-(betaR*dr*8.+betaM*dm*.85+betaO3*ozoneAbove)*sunPath)*sunVisible(p*R);
        vec3 extinction=betaR*dr+betaM*dm+betaO3*ozone;
        transmission=exp(-extinction*distanceKm);
        vec3 source=(betaR*dr*phaseR+betaM*dm*phaseM)*sunlight*6.;
        // Diffuse marine aerosol is lit by the whole sky, including beneath clouds.
        source+=betaM*dm*vec3(.10,.135,.17)*smoothstep(-.12,.2,sunDirection.y);
        inscatter=(1.-transmission)*source/max(extinction,vec3(.0000001));
      }
      float emittingSpan(vec3 ro,vec3 d,float a,float b){
        if(b<=a)return 0.;vec3 n=normalize(ro+d*((a+b)*.5));
        float night=1.-smoothstep(-.23,-.025,dot(n,sunDirection));
        float swell=.91+.065*sin(dot(n,vec3(40.,-26.,54.))+weatherTime*.0014)
                        +.035*sin(dot(n,vec3(-122.,138.,164.))-weatherTime*.002);
        return (b-a)*R*night*swell;
      }
      float emittingShell(vec3 ro,vec3 d,float stop,float lo,float hi){
        vec2 outer=sphere(ro,d,1.+hi/R);float a=max(outer.x,0.),b=min(stop,outer.y);
        if(b<=a)return 0.;vec2 inner=sphere(ro,d,1.+lo/R);
        if(inner.y<=a||inner.x>=b)return emittingSpan(ro,d,a,b);
        return emittingSpan(ro,d,a,min(b,inner.x))+emittingSpan(ro,d,max(a,inner.y),b);
      }
      vec3 nightAir(vec3 ro,vec3 d,float stop){
        if(altitudeKm<50.&&sunDirection.y>-.02)return vec3(0.);
        // Edge-on columns in the narrow green oxygen band and broader, fainter
        // red thermosphere. Both Earth and the back half of the shell occlude correctly.
        float green=emittingShell(ro,d,stop,88.,105.);
        float red=emittingShell(ro,d,stop,182.,306.);
        return vec3(.000015,.000034,.000012)*green+vec3(.0000025,.00000055,.0000007)*red;
      }
      vec3 atmosphere(vec3 ro,vec3 d,float stop,vec3 background,out vec3 transmission){
        transmission=vec3(1.);vec2 hit=sphere(ro,d,1.+120./R);if(hit.y<=0.)return background;
        float a=max(hit.x,0.),b=min(hit.y,stop);if(b<=a)return background;
        vec3 scatter=vec3(0.);
        for(int i=0;i<20;i++){
          float u=float(i)/20.,v=(float(i)+1.)/20.;
          // Near-ground rays need dense integration in the first kilometre.
          float bend=1.-smoothstep(5.,40.,altitudeKm);
          float ta=mix(u,u*u,bend),tb=mix(v,v*v,bend);
          vec3 p=ro+d*(a+(ta+tb)*.5*(b-a)),tr,ins;
          airStep(p,d,(tb-ta)*(b-a)*R,tr,ins);
          scatter+=transmission*ins;transmission*=tr;
        }return background*transmission+scatter;
      }
      // Analytic path through the broad, optically thick part of an updraft.
      // The resolved four-kilometre shadow ray has already integrated its near face.
      float distantCore(vec3 at,vec3 dir,vec3 center,vec3 reciprocalAxes){
        vec3 x=(at-center)*reciprocalAxes,w=dir*reciprocalAxes;
        float a=dot(w,w),b=dot(x,w),closest=dot(x,x)-b*b/a;
        if(closest>=1.)return 0.;
        float halfChord=sqrt((1.-closest)/a),t=-b/a;
        float chord=max(0.,min(95.,t+halfChord)-max(4.25,t-halfChord));
        return (1.-exp(-.69*chord))*smoothstep(0.,.23,1.-closest);
      }
      float updraftShadow(vec3 parcel,vec3 solar,float h){
        if(h>15.1||max(abs(parcel.x),abs(parcel.z))>105.)return 0.;
        vec3 at=vec3(.72*parcel.x-.69*parcel.z,.69*parcel.x+.72*parcel.z,h);
        vec3 dir=vec3(.72*solar.x-.69*solar.z,.69*solar.x+.72*solar.z,solar.y);
        float nearTower=distantCore(at,dir,vec3(10.25,1.92,6.78),vec3(.249,.318,.198));
        float farTower=distantCore(at,dir,vec3(8.66,-16.85,6.76),vec3(.238,.294,.198));
        float anvil=distantCore(at,dir,vec3(20.,4.23,11.08),vec3(.111,.38,2.24));
        float original=2.16*max(max(nearTower,farTower),.48*anvil)*(1.-smoothstep(11.4,12.2,h));
        vec3 weatherAt=vec3(.974*(parcel.x+7.)-.227*(parcel.z+25.),.227*(parcel.x+7.)+.974*(parcel.z+25.),h);
        vec3 weatherDir=vec3(.974*solar.x-.227*solar.z,.227*solar.x+.974*solar.z,solar.y);
        float squall=distantCore(weatherAt,weatherDir,vec3(-6.2,-4.1,7.85),vec3(.13,.43,.164));
        float rainHead=distantCore(weatherAt,weatherDir,vec3(2.,-1.65,3.42),vec3(.091,.35,.62));
        float ice=distantCore(weatherAt,weatherDir,vec3(4.7,-3.3,12.71),vec3(.078,.25,.95));
        return original+2.9*max(squall,max(.61*rainHead,.74*ice));
      }
      float cloudSunDepth(vec3 p,float localDensity){
        // Integrate a continuous extinction profile. Assigning an entire long
        // terminal interval to one distant probe repeats a bank's rim in its shadow.
        float footprint=densityFilterKm;densityFilterKm=max(footprint,.42);
        float a=cloudDensity(p+sunDirection*.74);densityFilterKm=max(footprint,.86);
        float b=cloudDensity(p+sunDirection*2.05);densityFilterKm=max(footprint,1.46);
        float c=cloudDensity(p+sunDirection*4.25);densityFilterKm=footprint;
        vec3 parcel=p-vec3(wind.x*weatherTime,R,wind.y*weatherTime);
        return .37*(localDensity+a)+.655*(a+b)+1.10*(b+c)+(1.-weatherLod)*updraftShadow(parcel,sunDirection,length(p)-R);
      }
vec3 glorySpectrum(float angle){
  vec3 radius=vec3(.064,.054,.046),inner=(angle-radius)/.012,outer=(angle-1.88*radius)/.019;
  return .21*exp(-inner*inner)+.028*exp(-outer*outer)+vec3(.041)*exp(-angle*angle/.00055);
}
float carShadow(vec3 cloudFromCar,vec3 sun){
  float behind=-dot(cloudFromCar,sun);
  if(behind<4.||behind>3900.)return 0.;
  vec3 sideways=normalize(vec3(-sun.z,0.,sun.x)),vertical=cross(sideways,sun);
  vec3 halfHull=vec3(2.38,1.54,5.94);
  vec2 halfExtent=vec2(dot(abs(sideways),halfHull),dot(abs(vertical),halfHull));
  vec2 projected=vec2(dot(cloudFromCar,sideways),dot(cloudFromCar,vertical));
  vec2 offset=abs(projected)-halfExtent+.64;
  float boundary=length(max(offset,vec2(0.)))+min(max(offset.x,offset.y),0.)-.64;
  float penumbra=max(.38,.00465*behind);
  vec2 uv=projected/vec2(24.,12.)+.5;
  if(min(uv.x,uv.y)>0.&&max(uv.x,uv.y)<1.){
    float surveyed=dot(sun,vec3(.9652923,.1580617,-.2079117));
    float blend=smoothstep(.981,.999,surveyed)*(1.-smoothstep(620.,1250.,behind));
    boundary=mix(boundary,(textureLod(carMask,uv,0.).a-.5)*12.,blend);
  }
  float filling=min(1.,(4.*halfExtent.x*halfExtent.y)/(3.14159*penumbra*penumbra));
  return filling*(1.-smoothstep(-penumbra,penumbra,boundary));
}
      vec4 cloudVolume(vec3 ro,vec3 d,float groundT){
        vec2 outer=sphere(ro,d,1.+16.15/R);if(outer.y<=0.)return vec4(0.,0.,0.,1.);
        float start=max(0.,outer.x)*R,end=min(outer.y,groundT)*R;vec2 inner=sphere(ro,d,1.+.04/R);
        if(length(ro)<1.+.04/R)start=max(start,inner.y*R);else if(inner.x>0.)end=min(end,inner.x*R);
        if(altitudeKm<30.)end=min(end,start+320.);
        if(end<=start)return vec4(0.,0.,0.,1.);
        float count=mix(192.,48.,smoothstep(90.,900.,altitudeKm));
        float span=end-start,nearBias=1.-smoothstep(80.,500.,altitudeKm);
        // Intervals have a common physical origin and scale across neighboring
        // rays. Changing the far intersection at the horizon cannot move a nearby sample.
        float marchSpan=mix(span,max(320.,span),1.-smoothstep(28.,75.,altitudeKm));
        float ratio=exp(log(1.+marchSpan/3.4)/count),advance=3.4*(ratio-1.),cursor=start;
        vec3 radiance=vec3(0.);float trans=1.;
        vec3 airTrans;vec3 airScatter=atmosphere(ro,d,start/R,vec3(0.),airTrans);
        float mu=dot(d,sunDirection),phase=.58+.70*hg(mu,.70)+.17*hg(mu,-.28);
        float antiAngle=acos(clamp(-mu,-1.,1.));
        int maxParts=altitudeKm>.45&&altitudeKm<73.?3:1,cells=0,pending=0;
        float prior=cloudDensity(ro*R+d*start),farDensity=0.,subLength=0.;
        for(int i=0;i<576;i++){
          if(trans<.008||cursor>=end||(float(cells)>=count&&pending==0))break;
          float ds,rightDensity;
          if(pending>0){
            ds=min(end-cursor,subLength);densityFilterKm=ds;
            rightDensity=pending==1?farDensity:cloudDensity(ro*R+d*(cursor+ds));pending--;
          }else{
            float whole=min(end-cursor,mix(span/count,advance,nearBias));advance*=ratio;cells++;
            int parts=int(clamp(ceil(whole/.10),1.,float(maxParts)));
            densityFilterKm=whole/float(parts);farDensity=cloudDensity(ro*R+d*(cursor+whole));
            bool occupied=max(prior,farDensity)>.0008;
            if(!occupied&&parts>1&&whole>.8&&cursor-start<65.)occupied=cloudDensity(ro*R+d*(cursor+.5*whole))>.003;
            if(!occupied)parts=1;
            subLength=whole/float(parts);ds=subLength;pending=parts-1;densityFilterKm=ds;
            rightDensity=pending>0?cloudDensity(ro*R+d*(cursor+ds)):farDensity;
          }
          // Between two observed densities, integrate extinction and find the
          // point at which half of this cell's scattered light reaches the eye.
          float cellTau=.5*(prior+rightDensity)*ds,median=-log(.5+.5*exp(-cellTau));
          float rad=max(0.,prior*prior+2.*(rightDensity-prior)*median/max(ds,.00001));
          float at=cellTau>.00004?clamp(2.*median/max(.00001,ds*(prior+sqrt(rad))),0.,1.):.5;
          vec3 p=ro*R+d*(cursor+at*ds);float density=mix(prior,rightDensity,at);prior=rightDensity;
          vec3 stepTrans,stepScatter;airStep(ro+d*((cursor+.5*ds)/R),d,ds,stepTrans,stepScatter);cursor+=ds;
          vec3 sampleAir=airScatter+airTrans*stepScatter*.5;
          vec3 sampleTrans=airTrans*sqrt(stepTrans);
          airScatter+=airTrans*stepScatter;airTrans*=stepTrans;
          if(cellTau<.00005)continue;
          float alpha=1.-exp(-cellTau),tau=cloudSunDepth(p,density),h=length(p)-R;
          float localSun=max(dot(normalize(p),sunDirection),0.);
          float direct=exp(-tau)*sunVisible(p)*mix(1.,localSun,weatherLod);
          float rangeKm=cursor-(1.-at)*ds;
          // Toward backscatter the eye is on the solar path. Its measured
          // sunlight and the integrated foreground give the near bank's beam.
          float nearBeam=(1.-smoothstep(.55,2.8,rangeKm))*smoothstep(.60,.94,-mu)*smoothstep(.44,.91,solarAtCar);
          direct=mix(direct,solarAtCar*trans,nearBeam);
          float layerTop=h<4.?smoothstep(.72,3.1,h):smoothstep(4.3,11.,h);
          float skyLight=.016+(.047+.114*layerTop)*smoothstep(-.15,.35,sunDirection.y);
          float multiple=(.24*exp(-.29*tau)+.047*exp(-.078*tau))*(1.-exp(-1.35*density));
          float escape=exp(-.43*tau),rim=smoothstep(.16,.91,mu)*escape*(1.-exp(-1.72*density));
          vec3 ambient=vec3(.46,.64,.91)*skyLight*mix(.44,1.,escape),sunlight=vec3(1.,.955,.885);
          if(tau>.45&&weatherLod<.99){
            // Indirect light can enter the shaded flank above a shelf, or from
            // the open sky to its side. Integrate the actual cloudy path in each direction.
            vec3 up=normalize(p),tangent=sunDirection-up*dot(up,sunDirection);
            vec3 openSky=normalize(up*.88-tangent*.72);
            float footprint=densityFilterKm;densityFilterKm=max(footprint,.63);
            float overhead=cloudDensity(p+up*1.19);
            densityFilterKm=max(footprint,1.13);float leeward=cloudDensity(p+openSky*3.06);
            densityFilterKm=footprint;
            float skyAccess=.54*exp(-.76*(.40*density+1.10*overhead))+.46*exp(-.62*(.37*density+1.64*leeward));
            float secondBounce=(.018+.249*smoothstep(.22,.78,skyAccess))*(.42+.58*layerTop)*(1.-escape)*(1.-weatherLod)*smoothstep(-.09,.22,localSun);
            ambient+=vec3(.54,.707,.96)*secondBounce;
          }
          ambient*=mix(1.,.04+.96*localSun,weatherLod);
          float sunAir=exp(-max(0.,h)/8.);
          sunlight*=exp(-betaR*sunAir*8./max(.06,dot(normalize(p),sunDirection)+.08));
          float sunPath=sunVisible(p)*mix(1.,localSun,weatherLod);
          vec3 light=ambient+sunlight*(direct*phase*1.57+(multiple+.60*rim)*sunPath);
          // Water droplets return sunlight toward the observer. The finite
          // solar disc softens the projected silhouette with increasing range.
          if(mu<-.989&&h<8.6&&solarAtCar>.12){
            float liquid=(1.-smoothstep(5.0,8.6,h))*smoothstep(.028,.15,rangeKm)*(1.-smoothstep(14.,30.,rangeKm));
            float shade=carShadow(cameraPosition-vec3(0.,1.54,0.)+d*(rangeKm*1000.),sunDirection);
            vec3 parcel=p-vec3(wind.x*weatherTime,R,wind.y*weatherTime);
            float dropSize=.87+.18*smoothstep(.30,3.9,density)+.22*(noiseC(parcel/1.4,0)-.5);
            vec3 glory=glorySpectrum(antiAngle*dropSize);
            light+=sunlight*liquid*(solarAtCar*trans*glory*(1.-shade)-vec3(.82*shade*direct*phase*1.57));
          }
          light=light*sampleTrans+sampleAir;
          radiance+=trans*alpha*light;trans*=1.-alpha;
        }return vec4(radiance,trans*smoothstep(.008,.031,trans));
      }
      void main(){
        vec3 d=normalize(vDirection),ro=vec3(0.,1.+altitudeKm/R,0.)+cameraPosition*(.001/R);
        vec2 earth=sphere(ro,d,1.);float groundT=earth.x>0.?earth.x:1.e5;
        if(altitudeKm<.015&&d.y<0.)groundT=max(.0000002,earth.x);
        vec3 color=vec3(.000008,.000012,.000020);
        if(groundT<1.e4)color=ground(ro,d,groundT);
        else{float glint=pow(max(dot(d,sunDirection),0.),1800.)*.10;
          color+=vec3(.85,.64,.38)*glint*sunVisible(ro*R);}
        vec3 airTransmission;color=atmosphere(ro,d,groundT,color,airTransmission);
        vec3 airGlow=nightAir(ro,d,groundT);
        float sunUp=sunVisible(ro*R),solarCone=step(.99942,dot(d,sunDirection));
        vec3 aim=-vec3(viewMatrix[0][2],viewMatrix[1][2],viewMatrix[2][2]);
        float sensitivity=mix(starTransmission(d,aim,sunDirection,altitudeKm,color+airGlow,sunUp),sunUp,solarCone);
        float skyExposure=groundT>1.e4?dot(airTransmission,vec3(.2126,.7152,.0722))*sensitivity:0.;
        vec4 volume=cloudVolume(ro,d,groundT);
        if(altitudeKm>65.&&groundT<1.e4&&volume.a<.995){
          vec3 n=normalize(ro+d*groundT);float night=1.-smoothstep(-.17,.00,dot(n,sunDirection));
          if(night>.001){
            // An unresolved city lights the underside of the overcast above it.
            // Two map footprints separate a city core from its diffuse hinterland.
            vec2 uv=uvEarth(n);float metropolis=.68*textureLod(nightMap,uv,1.8).r+.32*textureLod(nightMap,uv,3.7).r;
            vec3 downlight=vec3(.00085,.0015,.00155);
            volume.rgb+=(1.-volume.a)*night*(downlight+vec3(.46,.235,.089)*max(0.,metropolis-.003));
          }
        }
        color=volume.rgb+volume.a*color+airGlow*mix(volume.a*airTransmission,vec3(1.),smoothstep(55.,160.,altitudeKm));
        gl_FragColor=vec4(max(color,vec3(0.)),skyExposure*volume.a);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }
    `});
  // Trace the actual 3-D medium at half linear resolution, then reconstruct its
  // radiance. This is a live per-camera volume pass, not a stored sky image.
  const volumeScene=new T.Scene(),volumeMesh=new T.Mesh(new T.SphereGeometry(1,32,20),material);
  volumeMesh.frustumCulled=false;volumeMesh.layers.enableAll();volumeScene.add(volumeMesh);
  const targets=new Map();let targetClock=0;
  function targetFor(width,height){
    const key=width+'x'+height;let item=targets.get(key);
    if(!item){
      item={target:new T.WebGLRenderTarget(width,height,{type:T.HalfFloatType,depthBuffer:false,stencilBuffer:false}),used:0};targets.set(key,item);
      if(targets.size>8){let oldest;for(const [k,v] of targets)if(k!==key&&(!oldest||v.used<oldest[1].used))oldest=[k,v];
        oldest[1].target.dispose();targets.delete(oldest[0]);}
    }item.used=++targetClock;return item.target;
  }
  const display=new T.ShaderMaterial({side:T.BackSide,depthTest:false,depthWrite:false,toneMapped:true,
    uniforms:{sunDirection:uniforms.sunDirection,starCatalogue:{value:catalogue},galacticLight:{value:galaxy},siderealBasis:{value:new T.Vector2(1,0)},stellarEye:{value:.15},radiance:{value:null},viewport:{value:new T.Vector4(0,0,1,1)}},
    vertexShader:'varying vec3 vRay;void main(){vRay=position;vec4 p=projectionMatrix*vec4(mat3(viewMatrix)*position,1.);gl_Position=p.xyww;}',
    fragmentShader:`uniform sampler2D radiance;uniform vec4 viewport;uniform vec3 sunDirection;varying vec3 vRay;
      ${STELLAR_GLSL}
      void main(){
        vec2 uv=(gl_FragCoord.xy-viewport.xy)/viewport.zw;vec4 traced=texture2D(radiance,uv);
        vec3 d=normalize(vRay);float mu=dot(d,sunDirection),angle=length(cross(d,sunDirection));
        float px=max(.000035,.64*fwidth(angle));
        float disc=mu>0.?1.-smoothstep(.00465-px,.00465+px,angle):0.;
        float limb=.63+.37*sqrt(max(0.,1.-pow(angle/.00465,2.)));
        vec3 points=mu>.99942?vec3(14.,12.,9.)*disc*limb:catalogueLight(d);
        gl_FragColor=vec4(traced.rgb+traced.a*points,1.);
      #include <tonemapping_fragment>
      #include <colorspace_fragment>
      }`});
  const mesh=new T.Mesh(new T.SphereGeometry(1,32,20),display);mesh.name='Earth_Volumetric_Weather';mesh.frustumCulled=false;mesh.renderOrder=-1000;
  const savedViewport=new T.Vector4(),physicalViewport=new T.Vector4(),savedScissor=new T.Vector4();
  let eyeAdaptation=.15;
  mesh.onBeforeRender=(renderer,scene,camera)=>{
    const previous=renderer.getRenderTarget(),face=renderer.getActiveCubeFace(),mip=renderer.getActiveMipmapLevel();
    const autoClear=renderer.autoClear,scissorTest=renderer.getScissorTest();
    renderer.getViewport(savedViewport);renderer.getCurrentViewport(physicalViewport);renderer.getScissor(savedScissor);
    display.uniforms.viewport.value.copy(physicalViewport);
    display.uniforms.stellarEye.value=camera.userData.passengerEye?eyeAdaptation:.86;
    const scale=uniforms.altitudeKm.value>1000?.85:.5;
    const width=Math.max(16,Math.ceil(physicalViewport.z*scale)),height=Math.max(16,Math.ceil(physicalViewport.w*scale));
    const target=targetFor(width,height);display.uniforms.radiance.value=target.texture;
    renderer.autoClear=true;renderer.setScissorTest(false);renderer.setRenderTarget(target);
    renderer.render(volumeScene,camera);
    renderer.setRenderTarget(previous,face,mip);
    // setViewport always applies renderer pixel ratio in r169, even for RTs.
    // Restore the measured physical viewport, including a CubeCamera face.
    renderer.setViewport(physicalViewport.clone().divideScalar(renderer.getPixelRatio()));renderer.setScissor(savedScissor);
    renderer.setScissorTest(scissorTest);renderer.autoClear=autoClear;
  };
  return {mesh,setOceanSky(t){uniforms.oceanSky.value=t;uniforms.hasOceanSky.value=!!t;},update(state,metrics,time=0,beam=1,dt=0){
    const km=Number(metrics?.km??metrics?.altitudeKm??state?.altitudeKm??0);
    uniforms.altitudeKm.value=Number.isFinite(km)?Math.max(0,km):0;uniforms.weatherTime.value=Number(metrics?.weatherSeconds??time)||0;
    uniforms.solarAtCar.value=beam*(metrics?.sunVisible??1);
    const sidereal=2.8*Math.PI/12+(metrics?.forces?.shipSeconds??0)*7.292115e-5;
    display.uniforms.siderealBasis.value.set(Math.cos(sidereal),Math.sin(sidereal));
    if(state&&metrics?.sunDirection)eyeAdaptation=adaptStellarEye(eyeAdaptation,state,metrics,dt);
    uniforms.weatherLod.value=T.MathUtils.smoothstep(Math.max(0,km),30,285);
    const w=metrics?.weather??WEATHER_DEFAULTS;
    uniforms.coverage.value=T.MathUtils.clamp(w.coverage??.58,0,1);uniforms.evolution.value=T.MathUtils.clamp(w.evolution??.5,0,1);
    uniforms.wind.value.fromArray(w.wind??[.018,.007]);if(metrics?.sunDirection)uniforms.sunDirection.value.fromArray(metrics.sunDirection).normalize();
  },dispose(){mesh.geometry.dispose();volumeMesh.geometry.dispose();material.dispose();display.dispose();for(const item of targets.values())item.target.dispose();targets.clear();day.dispose();night.dispose();broadCloud.dispose();regional.dispose();carMask.dispose();catalogue.dispose();galaxy.dispose();noise.dispose();cells.dispose();}};
}
