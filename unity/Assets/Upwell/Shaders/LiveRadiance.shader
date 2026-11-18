Shader "Upwell/Live exterior radiance" {
    Properties{
        _Radiance("Current camera's traced radiance",2D)="black"{}
        [NoScaleOffset] _StarCatalogue("Measured star positions",2D)="black"{}
        [NoScaleOffset] _GalacticLight("Pioneer Galactic photometry",2D)="black"{}
        [HideInInspector] _SiderealBasis("Sidereal basis",Vector)=(1,0,0,0)
        [HideInInspector] _StellarEye("Stellar sensitivity",Float)=.15
    }
    SubShader{Tags {"Queue"="Background" "RenderType"="Background" "PreviewType"="Skybox"} Cull Off ZWrite Off
        Pass {
        CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma target 3.0
            #include "UnityCG.cginc"
            sampler2D _Radiance;struct v2f{float4 pos:SV_POSITION;float4 screen:TEXCOORD0;};
            v2f vert(appdata_base v){v2f o;o.pos=UnityObjectToClipPos(v.vertex);o.screen=ComputeScreenPos(o.pos);return o;}
            float4 _SkyForward,_SkyRight,_SkyUp,_UpwellSun;
sampler2D _StarCatalogue;
sampler2D _GalacticLight;
float2 _SiderealBasis;
float _StellarEye;
float3 catalogueLight(float3 ray){
  // Local equatorial frame (+X east,+Y zenith,+Z north) to J2000 directions.
  float3 dir=float3(dot(ray.xy,float2(-_SiderealBasis.y,_SiderealBasis.x)),dot(ray.xy,_SiderealBasis),ray.z);
  float3 a=abs(dir);float2 uv;float face,major;
  if(a.x>=a.y&&a.x>=a.z){face=dir.x>=0.?0.:1.;major=a.x;uv=dir.yz;}
  else if(a.y>=a.z){face=dir.y>=0.?2.:3.;major=a.y;uv=dir.zx;}
  else{face=dir.z>=0.?4.:5.;major=a.z;uv=dir.xy;}
  float2 grid=(uv/major*.5+.5)*64.,tile=clamp(floor(grid),0.,63.);
  float2 pixel=clamp(float2(length(float2(ddx(grid.x),ddy(grid.x))),length(float2(ddx(grid.y),ddy(grid.y)))),.003,.30);
  float2 cellCentre=float2(tile.x*16.+.5,tile.y+64.*face+.5),local=grid-tile;
  float3 gal=float3(dot(dir,float3(-.05487556,-.87343709,-.48383502)),
                    dot(dir,float3(.49410943,-.44482963,.74698224)),dot(dir,float3(-.86766615,-.19807637,.45598378)));
  float2 bands=tex2Dlod(_GalacticLight,float4(atan2(gal.y,gal.x)/6.2831853,asin(clamp(gal.z,-1.,1.))/3.14159265+.5,0,0)).rg;
  bands=bands*bands*float2(768.,1536.);
  float adapted=smoothstep(.15,.95,_StellarEye);
  float diffuse=max(0.,dot(bands,float2(.72,.2016))-28.)*.000074*adapted*adapted;
  float3 light=float3(.96,1.,1.055)*diffuse;
  [loop] for(int i=0;i<16;i++){
    float4 entry=tex2Dlod(_StarCatalogue,float4((cellCentre+float2(float(i),0.))/float2(1024.,384.),0,0));
    if(entry.b<.001)break;
    float magnitude=(entry.b*255.-1.)*(8./254.)-1.5;
    float visible=smoothstep(-.55,.55,lerp(3.60,6.58,_StellarEye)-magnitude);
    if(visible<=0.)break;
    float2 delta=(local-(entry.rg*1.6-.30))/pixel;
    float square=dot(delta,delta);
    // The unresolved source is sampled at the final display size. A narrow core
    // and an optical skirt soften the brightest stars without diffraction spikes.
    float core=exp(-1.26*square),skirt=exp(-.23*square);
    float energy=.79*exp2(-1.02*magnitude);
    float radiance=energy*(core+.048*skirt)*visible*lerp(.48,1.,_StellarEye);
    float bv=entry.a*2.6-.4;
    float3 cool=lerp(float3(.65,.79,1.),float3(1.,.98,.94),smoothstep(-.3,.58,bv));
    float3 colour=lerp(cool,float3(1.,.63,.42),smoothstep(.58,1.85,bv));
    light+=radiance*lerp(float3(1.,1.,1.),colour,1.-.66*smoothstep(0.,3.,magnitude));
  }
  return light;
}
            half4 frag(v2f i):SV_Target{
                float2 uv=i.screen.xy/i.screen.w,screen=uv*2-1;
                float3 dir=normalize(_SkyForward.xyz+screen.x*_SkyRight.xyz+screen.y*_SkyUp.xyz);
                dir.z=-dir.z;
                float4 traced=tex2D(_Radiance,uv);
                float3 sun=normalize(float3(_UpwellSun.x,_UpwellSun.y,-_UpwellSun.z));
                float mu=dot(dir,sun),angle=length(cross(dir,sun)),px=max(.000035,.64*fwidth(angle));
                float disc=mu>0?1.-smoothstep(.00465-px,.00465+px,angle):0;
                float limb=.63+.37*sqrt(max(0,1.-pow(angle/.00465,2.)));
                float3 stars=catalogueLight(dir);
                float3 points=mu>.99942?float3(14,12,9)*disc*limb:stars;
                return half4(traced.rgb+traced.a*points,1);
            }
            ENDCG
        }
    }
}
