Shader "Upwell/Moving atmosphere and Earth" {
    Properties {
        _Albedo("Geographic surface",2D)="gray"{} _Night("Black Marble lights",2D)="black"{} _Broad("Initial regional density",2D)="gray"{} _Atlantic("GOES optical depth and cloud tops",2D)="black"{}
        _NoiseField("Advected density field",3D)=""{} _MarineCells("Marine cell organization",2D)="gray"{} _SunLocal("Local sun",Vector)=(1,.2,.2,0)
        _HeightKm("Camera deck altitude km",Float)=0 _WeatherSeconds("Weather time",Float)=0
        _Samples("Volume steps",Float)=24
        _CarSunMask("Measured carriage silhouette",2D)="white"{}
    }
    SubShader { Tags {"Queue"="Background" "RenderType"="Background" "PreviewType"="Skybox"} Cull Off ZWrite Off
        Pass {
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma target 3.5
            #include "UnityCG.cginc"
            #include "CloudField.cginc"
            sampler2D _Albedo,_Night,_CarSunMask;float4 _SunLocal;
            float _Samples,_SurveyMode,_UpwellSolarPower;
            float4 _SkyForward,_SkyRight,_SkyUp,_SkyEye;
            #define R 6371.0
            #define Rayleigh float3(.0058,.01345,.0313)
            struct v2f {float4 pos:SV_POSITION;float4 screen:TEXCOORD0;};
            v2f vert(appdata_base v){v2f o;o.pos=UnityObjectToClipPos(v.vertex);o.screen=ComputeScreenPos(o.pos);return o;}
            float HeightAt(float3 p){
                // Avoid catastrophic cancellation where the 6371 km sphere meets a metre-scale camera.
                return (dot(p.xz,p.xz)+p.y*(2*R+p.y))/(length(p+float3(0,R,0))+R);
            }
            float2 Arc(float3 p,float3 d,float shell){
                float3 q=p*(1.0/6371.0);
                float height=shell*(1.0/6371.0);
                float closest=-dot(q+float3(0,1,0),d);
                float norm=dot(q.xz,q.xz)+(q.y-height)*(2.0+q.y+height);
                float discriminant=closest*closest-norm;
                if(discriminant<0)return float2(-1,-1);
                float width=sqrt(discriminant);
                float entry=closest-width,exitDistance=closest+width;
                if(closest>0)entry=norm/max(1e-9,exitDistance);
                return 6371.0*float2(entry,exitDistance);
            }
            float2 Geo(float3 radial){
                const float cs=.809016994,sn=-.58778525;
                float gx=cs*radial.y-sn*radial.x,gz=sn*radial.y+cs*radial.x;
                return float2(frac(.5+atan2(gz,gx)*.15915494),.5+asin(clamp(radial.z,-1,1))*.31830989);
            }
            float SunSeen(float3 radial,float h,float3 sun){
                float horizon=-sqrt(saturate(1-pow(R/(R+max(0,h)),2)));
                return smoothstep(horizon-.005,horizon+.006,dot(radial,sun));
            }
            float3 SunFilter(float3 radial,float h,float3 sun){
                float mu=dot(radial,sun),mass=1/max(.047,mu+.06);
                return exp(-mass*(Rayleigh*8.0*exp(-max(h,0)/8.0)+.0055*1.35*exp(-max(h,0)/1.35)));
            }
            float Hash(float2 a){float3 p=frac(float3(a.xyx)*.1031);p+=dot(p,p.yzx+33.33);return frac((p.x+p.y)*p.z);}
      float starTransmission(float3 d,float3 aim,float3 sun,float height,float3 air,float solarVisible){
        float litSky=dot(air,float3(.2126,.7152,.0722)),adapt=1./(1.+170.*litSky);
        float glare=1.-.975*pow(max(0.,dot(d,sun)),24.)*solarVisible;
        float dip=sqrt(max(0.,1.-pow(6371./(6371.+max(height,0.)),2.)));
        // Bright Earth or the sun elsewhere in the same lens raises the
        // observer's exposure floor even when this particular ray sees space.
        float earthInView=(1.-smoothstep(-.27,.31,aim.y+dip))*smoothstep(-.13,.23,sun.y);
        float sunInView=smoothstep(.69,.975,dot(aim,sun))*solarVisible;
        float lensGain=1./(1.+.78*earthInView+1.12*sunInView);
        return adapt*adapt*glare*lensGain*smoothstep(.002,.082,d.y+dip);
      }
            float3 Space(float3 d,float3 sun){
                float aureole=.10*pow(saturate(dot(d,sun)),1800);
                return float3(.00005,.00007,.00014)+float3(.85,.64,.38)*aureole;
            }
// Average unresolved capillary waves, while keeping longer groups of swell
// and wind roughness where a pixel still covers part of a crest. Positions are km.
float3 coastalSlopes(float2 p,float footprint,float t){
  float2 windUnit=float2(.86,.51),crossWind=float2(-.51,.86);
  float2 uv=float2(dot(p,windUnit),dot(p,crossWind));
  float4 groups=fieldNoise(float3(uv.x/3.7-.00047*t,.39,uv.y/2.0+.21));
  float4 windField=fieldNoise(float3(uv.x/13.2+.41,.71,uv.y/6.8+.00024*t));
  float cap=exp(-.19*pow(86.2*footprint,2.));
  float swell=cap*cos(86.2*uv.x-.93*t+4.3*groups.r);
  float2 tilt=windUnit*(.047*swell)+.16*(groups.rg-.50)*(1.-smoothstep(.09,.65,footprint))
            +.066*(windField.gb-.50)*(1.-smoothstep(.65,2.8,footprint));
  return float3(tilt,clamp(.47+.68*(windField.r-.50)+.48*(groups.g-.5),.23,.79));
}
            float3 Surface(float3 p,float3 d,float3 sun,float dist) {
                float3 n=normalize(p+float3(0,R,0));float2 uv=Geo(n);
                float3 albedo=tex2Dlod(_Albedo,float4(uv,0,max(0,log2(max(1,dist*.0018))))).rgb;
                float water=smoothstep(.002,.025,albedo.b-max(albedo.r,albedo.g*.72));
                // The launch patch is open equatorial Atlantic; black BMNG ocean texels carry no shore class.
                water=max(water,1-smoothstep(310,500,length(p.xz)));
                albedo=lerp(albedo,max(albedo,float3(.005,.025,.073)),water);
                float lit=max(0,dot(n,sun)),nv=max(.001,dot(n,-d));
                float3 direct=SunFilter(n,0,sun)*SunSeen(n,0,sun);
                float3 intercepted=normalize(n+sun*(5./R)/max(.14,dot(n,sun)))*R;
                float4 observed=regionalColumn(intercepted);
                float clouds=lerp(broadCloudDensity(intercepted),1.-exp(-observed.x*.19),observed.w);
                float nearby=(1.-smoothstep(150.,410.,dist))*(1.-smoothstep(38.,155.,_HeightKm))*smoothstep(.055,.21,lit);
                if(nearby>.002){
                    const float layer[5]={1.43,2.71,5.78,7.94,10.68};
                    const float width[5]={1.15,1.48,2.12,2.34,2.40};
                    float3 drift=float3(wind.x*_WeatherSeconds,0,wind.y*_WeatherSeconds);
                    float depth=0,secant=1./max(.08,lit);
                    [loop] for(int i=0;i<5;i++){
                        float3 at=p+sun*(layer[i]*secant);
                        depth+=width[i]*localCloud(at-drift,HeightAt(at),.62);
                    }
                    clouds=lerp(clouds,1.-exp(-.90*secant*depth),nearby);
                }
                float3 city=tex2Dlod(_Night,float4(uv,0,max(0,log2(max(1,dist*.0018))))).rgb;
                float fixtures=max(0,max(city.r,city.g)-.025)*(1-smoothstep(-.12,.025,dot(n,sun)));
                float3 litSurface=albedo*(float3(.042,.058,.087)+direct*(.19+1.7*lit)*(1-.48*clouds));
                if(_HeightKm<32&&water>.001){
                    float2 oceanKm=p.xz;float footprint=max(length(ddx(oceanKm)),length(ddy(oceanKm)));
                    float3 groups=coastalSlopes(oceanKm,footprint,_WeatherSeconds);
                    float3 waveNormal=normalize(n+float3(groups.x,0,groups.y)),reflected=reflect(d,waveNormal);
                    reflected.y=max(.009,reflected.y)+.075*groups.z;reflected=normalize(reflected);
                    float toward=saturate(dot(reflected,sun)*.5+.5);
                    float3 meanRay=reflect(d,n);meanRay.y=max(.02,meanRay.y)+.105*groups.z;meanRay=normalize(meanRay);
                    float3 cloudFoot=p+meanRay*(1.82/max(.05,dot(n,meanRay)))-float3(.018*_WeatherSeconds,0,.007*_WeatherSeconds);
                    float4 cell=fieldNoise(cloudFoot/16.);float rounded=.60*cell.r+.40*cell.g;
                    float broad=fieldNoise(float3(cloudFoot.x/26.,.37,cloudFoot.z/26.)).a;
                    float overcast=smoothstep(.28,.70,.56*rounded+.44*broad);
                    float3 clearSky=float3(.159,.219,.267)+float3(.17,.13,.075)*pow(toward,7.);
                    float3 cloudSky=float3(.305,.304,.277)+float3(.18,.137,.068)*pow(toward,4.);
                    float day=smoothstep(-.11,.14,dot(n,sun));
                    float3 localReflection=lerp(clearSky,cloudSky,overcast)*(.50+.69*groups.z)*(.12+.88*day);
                    float fresnel=.024+.976*pow(1-saturate(lerp(dot(n,-d),dot(waveNormal,-d),.61)),5.);
                    float3 liquid=lerp(float3(.017,.052,.067)*(.13+.87*day)*(1.-.54*clouds),localReflection,fresnel);
                    litSurface=lerp(litSurface,liquid,water*(1-smoothstep(14.,32.,_HeightKm)));
                }
                if(lit>.0001&&water>.001){
                    float3 halfV=normalize(sun-d);float nh=max(.001,dot(n,halfV)),vh=max(.001,dot(-d,halfV));
                    float3 east=normalize(cross(abs(n.z)<.99?float3(0,0,1):float3(0,1,0),n));
                    float3 windward=east*.895+cross(n,east)*.446;
                    float2 slope=float2(dot(halfV,windward),dot(halfV,cross(n,windward)))/nh;
                    float density=exp(-.5*dot(slope*slope,float2(47,72)))*9.26/max(.0001,nh*nh*nh*nh);
                    float masking=min(1.,2.*nh*min(nv,lit)/vh),f=.0204+.9796*pow(1.-vh,5.);
                    litSurface+=direct*water*(1-.92*clouds)*density*masking*f*.74/nv;
                }
                return litSurface+float3(.55,.34,.15)*fixtures;
            }
            float3 SkyAir(float3 p,float3 d,float3 sun,float t0,float t1,float3 beyond,out float3 airTransmission){
                airTransmission=1;if(t1<=t0)return beyond;
                float3 radiance=0,trans=1;float span=t1-t0;float cs=dot(d,sun);
                float rayPhase=.05968*(1+cs*cs),g=.74;
                float miePhase=.07958*(1-g*g)/pow(max(.015,1+g*g-2*g*cs),1.5);
                [unroll] for(int j=0;j<8;j++){
                    float u0=j/8.0,u1=(j+1)/8.0;
                    // Bias samples toward the observer inside the air column.
                    bool low=HeightAt(p)<65;float v0=low?u0*u0:u0,v1=low?u1*u1:u1;
                    float step=(v1-v0)*span;float3 q=p+d*(t0+.5*(v0+v1)*span);float h=max(0,HeightAt(q));
                    float3 normal=normalize(q+float3(0,R,0));float a=exp(-h/8),b=exp(-h/1.35);
                    float ozone=max(0,1-abs(h-25)/15);float3 extinction=Rayleigh*a+.0055*b+float3(.00065,.001881,.000085)*ozone,attenuation=exp(-extinction*step);
                    float3 incident=SunFilter(normal,h,sun)*SunSeen(normal,h,sun);
                    float3 source=(Rayleigh*a*rayPhase+.0044*b*miePhase)*incident*9.0+
                        Rayleigh*a*float3(.043,.072,.12)*(.30+.70*saturate(normal.y));
                    radiance+=trans*(1-attenuation)*source/max(extinction,.000001);trans*=attenuation;
                }airTransmission=trans;return beyond*trans+radiance;
            }
            float EmittingSpan(float3 p,float3 d,float3 sun,float a,float b){
                if(b<=a)return 0;float3 n=normalize(p+float3(0,R,0)+d*((a+b)*.5));
                float night=1-smoothstep(-.23,-.025,dot(n,sun));
                float swell=.91+.065*sin(dot(n,float3(40,-26,54))+_WeatherSeconds*.0014)
                               +.035*sin(dot(n,float3(-122,138,164))-_WeatherSeconds*.002);
                return (b-a)*night*swell;
            }
            float EmittingShell(float3 p,float3 d,float3 sun,float stop,float lo,float hi){
                float2 outer=Arc(p,d,hi);float a=max(outer.x,0),b=min(stop,outer.y);
                if(b<=a)return 0;float2 inner=Arc(p,d,lo);
                if(inner.y<=a||inner.x>=b)return EmittingSpan(p,d,sun,a,b);
                return EmittingSpan(p,d,sun,a,min(b,inner.x))+EmittingSpan(p,d,sun,max(a,inner.y),b);
            }
            float3 Nightglow(float3 p,float3 d,float3 sun,float stop) {
                if(_HeightKm<50&&sun.y>-.02)return 0;
                float green=EmittingShell(p,d,sun,stop,88,105),red=EmittingShell(p,d,sun,stop,182,306);
                return float3(.000015,.000034,.000012)*green+float3(.0000025,.00000055,.0000007)*red;
            }
            // Analytic path through the broad, optically thick part of an updraft.
            // The resolved four-kilometre shadow ray has already integrated its near face.
            float distantCore(float3 at,float3 dir,float3 center,float3 reciprocalAxes){
              float3 x=(at-center)*reciprocalAxes,w=dir*reciprocalAxes;
              float a=dot(w,w),b=dot(x,w),closest=dot(x,x)-b*b/a;
              if(closest>=1.)return 0.;
              float halfChord=sqrt((1.-closest)/a),t=-b/a;
              float chord=max(0.,min(95.,t+halfChord)-max(4.25,t-halfChord));
              return (1.-exp(-.69*chord))*smoothstep(0.,.23,1.-closest);
            }
            float updraftShadow(float3 parcel,float3 solar,float h){
              if(h>15.1||max(abs(parcel.x),abs(parcel.z))>105.)return 0.;
              float3 at=float3(.72*parcel.x-.69*parcel.z,.69*parcel.x+.72*parcel.z,h);
              float3 dir=float3(.72*solar.x-.69*solar.z,.69*solar.x+.72*solar.z,solar.y);
              float nearTower=distantCore(at,dir,float3(10.25,1.92,6.78),float3(.249,.318,.198));
              float farTower=distantCore(at,dir,float3(8.66,-16.85,6.76),float3(.238,.294,.198));
              float anvil=distantCore(at,dir,float3(20.,4.23,11.08),float3(.111,.38,2.24));
              float original=2.16*max(max(nearTower,farTower),.48*anvil)*(1.-smoothstep(11.4,12.2,h));
              float3 weatherAt=float3(.974*(parcel.x+7.)-.227*(parcel.z+25.),.227*(parcel.x+7.)+.974*(parcel.z+25.),h);
              float3 weatherDir=float3(.974*solar.x-.227*solar.z,.227*solar.x+.974*solar.z,solar.y);
              float squall=distantCore(weatherAt,weatherDir,float3(-6.2,-4.1,7.85),float3(.13,.43,.164));
              float rainHead=distantCore(weatherAt,weatherDir,float3(2.,-1.65,3.42),float3(.091,.35,.62));
              float ice=distantCore(weatherAt,weatherDir,float3(4.7,-3.3,12.71),float3(.078,.25,.95));
              return original+2.9*max(squall,max(.61*rainHead,.74*ice));
            }
            float AlongDensity(float3 p,float3 d,float distanceKm,float lod,float footprint){
                float3 q=p+d*distanceKm;return DensityAt(q,HeightAt(q),lod,footprint);
            }
float3 glorySpectrum(float angle){
  float3 radius=float3(.064,.054,.046),inner=(angle-radius)/.012,outer=(angle-1.88*radius)/.019;
  return .21*exp(-inner*inner)+.028*exp(-outer*outer)+float3(.041,.041,.041)*exp(-angle*angle/.00055);
}
float carShadow(float3 cloudFromCar,float3 sun){
  float behind=-dot(cloudFromCar,sun);
  if(behind<4.||behind>3900.)return 0.;
  float3 sideways=normalize(float3(-sun.z,0.,sun.x)),vertical=cross(sideways,sun);
  float3 halfHull=float3(2.38,1.54,5.94);
  float2 halfExtent=float2(dot(abs(sideways),halfHull),dot(abs(vertical),halfHull));
  float2 projected=float2(dot(cloudFromCar,sideways),dot(cloudFromCar,vertical));
  float2 offset=abs(projected)-halfExtent+.64;
  float boundary=length(max(offset,float2(0.,0.)))+min(max(offset.x,offset.y),0.)-.64;
  float penumbra=max(.38,.00465*behind);
  float2 uv=projected/float2(24.,12.)+.5;
  if(min(uv.x,uv.y)>0.&&max(uv.x,uv.y)<1.){
    float surveyed=dot(sun,float3(.9652923,.1580617,-.2079117));
    float blend=smoothstep(.981,.999,surveyed)*(1.-smoothstep(620.,1250.,behind));
    boundary=lerp(boundary,(tex2Dlod(_CarSunMask,float4(uv,0,0)).a-.5)*12.,blend);
  }
  float filling=min(1.,(4.*halfExtent.x*halfExtent.y)/(3.14159*penumbra*penumbra));
  return filling*(1.-smoothstep(-penumbra,penumbra,boundary));
}
            float3 Clouds(float3 p,float3 d,float3 sun,float start,float end,float3 sky,out float mistTransmission){
                mistTransmission=1;if(end<=start)return sky;
                float span=end-start,h0=HeightAt(p),trans=1;float3 light=0;
                int count=(int)clamp(_Samples,16,146);
                // Sparse terrain-sized columns at orbital distances retain a global forecast distribution.
                float remote=smoothstep(35,220,h0);
                count=(int)lerp(count,32,smoothstep(90,900,h0));
                float mu=dot(d,sun);
                float antiAngle=acos(clamp(-mu,-1.,1.));
                // Shared physical intervals stop neighbouring rays from crawling
                // across the same cloud face as the planet intersection changes.
                float marchSpan=lerp(span,max(295.,span),1.-smoothstep(28.,75.,h0));
                float ratio=exp(log(1+marchSpan/3.4)/count),advance=3.4*(ratio-1),cursor=start;
                int maxParts=h0>.45&&h0<73?(_Samples>=72?3:_Samples>=40?2:1):1,cells=0,pending=0;
                float prior=AlongDensity(p,d,start,remote,.04),farDensity=0,subLength=0,lod=remote;
                [loop] for(int i=0;i<438;i++){
                    if(trans<.025||cursor>=end||(cells>=count&&pending==0))break;
                    float step,rightDensity;
                    if(pending>0){
                        step=min(end-cursor,subLength);
                        rightDensity=pending==1?farDensity:AlongDensity(p,d,cursor+step,lod,step);pending--;
                    }else{
                        float whole=min(end-cursor,lerp(advance,span/count,remote));advance*=ratio;cells++;
                        int parts=(int)clamp(ceil(whole/.10),1.,(float)maxParts);
                        float footprint=whole/parts;farDensity=AlongDensity(p,d,cursor+whole,lod,footprint);
                        bool occupied=max(prior,farDensity)>.0008;
                        if(!occupied&&parts>1&&whole>.8&&cursor-start<65.)occupied=AlongDensity(p,d,cursor+.5*whole,lod,footprint)>.003;
                        if(!occupied)parts=1;
                        subLength=whole/parts;step=subLength;pending=parts-1;
                        rightDensity=pending>0?AlongDensity(p,d,cursor+step,lod,step):farDensity;
                    }
                    float cellTau=.57*(prior+rightDensity)*min(step,22.),median=-log(.5+.5*exp(-cellTau));
                    float physical=.57*2.*min(step,22.);
                    float rad=max(0.,prior*prior+2.*(rightDensity-prior)*median/max(physical,.00001));
                    float at=cellTau>.00004?saturate(2.*median/max(.00001,physical*(prior+sqrt(rad)))):.5;
                    float t=cursor+at*step,rho=lerp(prior,rightDensity,at);prior=rightDensity;cursor+=step;
                    if(cellTau<.00005)continue;
                    float3 q=p+d*t;float h=HeightAt(q);
                    float3 normal=normalize(q+float3(0,R,0));
                    float a=1-exp(-cellTau);
                    float direct=SunSeen(normal,h,sun);float3 tint=SunFilter(normal,h,sun);
                    float3 p1=q+sun*.74,p2=q+sun*2.05,p3=q+sun*4.25;
                    float sunA=DensityAt(p1,HeightAt(p1),lod,max(step,.42)),sunB=DensityAt(p2,HeightAt(p2),lod,max(step,.86));
                    float shadow=.37*(rho+sunA)+.655*(sunA+sunB);
                    if(_Samples>=72)shadow+=1.10*(sunB+DensityAt(p3,HeightAt(p3),lod,max(step,1.46)));
                    else shadow+=.74*sunB;
                    shadow+=(1.-remote)*updraftShadow(q-float3(wind.x*weatherTime,0.,wind.y*weatherTime),sun,h);
                    float solarIncidence=saturate(dot(normal,sun)),day=saturate(dot(normal,sun)*2.3+.21);
                    float edge=pow(saturate(mu),14);
                    float layerTop=h<4?smoothstep(.72,3.1,h):smoothstep(4.3,11.,h);
                    float escape=exp(-.43*shadow),rim=smoothstep(.16,.91,mu)*escape*(1-exp(-1.72*rho));
                    float3 ambient=float3(.46,.64,.91)*(.019+(.059+.134*layerTop)*day)*lerp(.44,1,escape)*lerp(1,.04+.96*solarIncidence,remote);
                    if(shadow>.45&&remote<.99){
                        float3 openSky=normalize(normal*.88-(sun-normal*dot(normal,sun))*.72);
                        float3 zenithPoint=q+normal*1.19,sidePoint=q+openSky*3.06;
                        float overhead=DensityAt(zenithPoint,HeightAt(zenithPoint),lod,max(step,.63));
                        float leeward=_Samples>=40?DensityAt(sidePoint,HeightAt(sidePoint),lod,max(step,1.13)):overhead;
                        float skyAccess=.54*exp(-.76*(.40*rho+1.10*overhead))+.46*exp(-.62*(.37*rho+1.64*leeward));
                        float secondBounce=(.018+.249*smoothstep(.22,.78,skyAccess))*(.42+.58*layerTop)*(1.-escape)*(1.-remote)*smoothstep(-.09,.22,solarIncidence);
                        ambient+=float3(.54,.707,.96)*secondBounce;
                    }
                    float multiple=(.24*exp(-.29*shadow)+.047*exp(-.078*shadow))*(1-exp(-1.35*rho));
                    float nearBeam=(1.-smoothstep(.55,2.8,t))*smoothstep(.60,.94,-mu)*smoothstep(.44,.91,_UpwellSolarPower);
                    float directPath=lerp(exp(-shadow),_UpwellSolarPower*trans,nearBeam);
                    float3 c=ambient+tint*direct*lerp(1,solarIncidence,remote)*(directPath*(.95+.73*edge)+multiple+.60*rim);
                    if(mu<-.989&&h<8.6&&_UpwellSolarPower>.12){
                        float liquid=(1.-smoothstep(5.,8.6,h))*smoothstep(.028,.15,t)*(1.-smoothstep(14.,30.,t));
                        float3 fromCar=float3(_SkyEye.x,_SkyEye.y-1.54,-_SkyEye.z)+d*(t*1000.);
                        float shade=carShadow(fromCar,sun),surfaceLight=direct*directPath*(.95+.73*edge);
                        float3 parcel=q-float3(wind.x*weatherTime,0.,wind.y*weatherTime);
                        float dropSize=.87+.18*smoothstep(.30,3.9,rho)+.22*(noiseC(parcel/1.4,0)-.5);
                        float3 glory=glorySpectrum(antiAngle*dropSize);
                        c+=tint*liquid*(_UpwellSolarPower*trans*glory*(1.-shade)-.82*shade*surfaceLight);
                    }
                    // Distinct distant layers receive the same aerial perspective as the lower air column.
                    float fog=1-exp(-min(400,t)*.0024*exp(-min(h,h0)/9));
                    c=lerp(c,sky,fog*.53);light+=trans*a*c;trans*=1-a;
                }mistTransmission=trans*smoothstep(.025,.065,trans);return light+mistTransmission*sky;
            }
            float4 frag(v2f i):SV_Target{
                float2 screen=i.screen.xy/i.screen.w*2-1;
                float3 d=normalize(_SkyForward.xyz+screen.x*_SkyRight.xyz+screen.y*_SkyUp.xyz);d.z=-d.z;
                float3 sun=normalize(float3(_SunLocal.x,_SunLocal.y,-_SunLocal.z));
                float3 p=float3(_SkyEye.x*.001,_HeightKm+_SkyEye.y*.001,-_SkyEye.z*.001);
                p.y=max(p.y,.0002);
                float2 hit=Arc(p,d,0);float ground=hit.x>=0?hit.x:1e9;bool land=hit.x>=0;
                if(_SurveyMode>.5&&_SurveyMode<1.5)return float4(d*.5+.5,1);
                if(_SurveyMode>=1.5&&_SurveyMode<2.5)return float4(land?1:0,saturate(hit.x/30000),saturate(-d.y),1);
                if(_SurveyMode>=2.5){float2 geo=Geo(normalize(p+d*ground+float3(0,R,0)));return float4(land?tex2Dlod(_Albedo,float4(geo,0,1)).rgb:0,1);}
                float3 far=land?Surface(p+d*ground,d,sun,ground):Space(d,sun);
                float2 atmosphere=Arc(p,d,100),cloudBounds=Arc(p,d,16.15);float3 sky=far,airTransmission=1;
                if(atmosphere.y>0)sky=SkyAir(p,d,sun,max(0,atmosphere.x),min(atmosphere.y,ground),far,airTransmission);
                float3 airGlow=Nightglow(p,d,sun,ground);
                float sunUp=SunSeen(normalize(p+float3(0,R,0)),_HeightKm,sun);
                float3 aim=normalize(float3(_SkyForward.x,_SkyForward.y,-_SkyForward.z));
                float sensitivity=lerp(starTransmission(d,aim,sun,_HeightKm,sky+airGlow,sunUp),sunUp,step(.99942,dot(d,sun)));
                float exposed=land?0:dot(airTransmission,float3(.2126,.7152,.0722))*sensitivity;
                float mistTransmission=1;
                if(cloudBounds.y>0){
                    float first=max(0,cloudBounds.x),last=min(cloudBounds.y,ground);
                    if(_HeightKm<30)last=min(last,first+295);
                    // Discard the clear gap between camera and cloud base on upward-looking ground rays.
                    float2 baseHit=Arc(p,d,.04);
                    if(HeightAt(p)<.04&&baseHit.y>=0)first=max(first,baseHit.y);
                    sky=Clouds(p,d,sun,first,last,sky,mistTransmission);
                }
                if(_HeightKm>65&&land&&mistTransmission<.995){
                    float3 radial=normalize(p+d*ground+float3(0,R,0));float night=1-smoothstep(-.17,0.,dot(radial,sun));
                    if(night>.001){float2 uv=Geo(radial);
                        float metropolis=.68*tex2Dlod(_Night,float4(uv,0,1.8)).r+.32*tex2Dlod(_Night,float4(uv,0,3.7)).r;
                        sky+=(1-mistTransmission)*night*(float3(.00085,.0015,.00155)+float3(.46,.235,.089)*max(0,metropolis-.003));
                    }
                }
                sky+=airGlow*lerp(mistTransmission*airTransmission,float3(1,1,1),smoothstep(55,160,_HeightKm));
                return float4(max(sky,0),exposed*mistTransmission);
            }
            ENDCG
        }
    }
}
