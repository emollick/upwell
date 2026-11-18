#ifndef UPWELL_CABIN_HARDWARE_INCLUDED
#define UPWELL_CABIN_HARDWARE_INCLUDED
sampler2D _UpwellCabinContact, _UpwellJacketPrint;
float4x4 _CabinProject0,_CabinProject1,_CabinRest;
float4 _CabinTiles,_CabinLayer,_CabinRub;
float4 _CabinFieldSize;
half _CabinGlass;
inline float CabinVisibilityTap(float2 p,float2 tile,float depth,float tol){
    float2 uv=(tile*_CabinFieldSize.xy+clamp(p,0,_CabinFieldSize.xy-1)+.5)*_CabinFieldSize.zw;
    uv.y=1-uv.y;
    float3 observed=tex2D(_UpwellCabinContact,uv).rgb;
    float recorded=dot(floor(observed.gb*255+.5),float2(256,1))/8192;
    return (1-observed.r)*(1-smoothstep(tol,tol*2.15,abs(depth-recorded)));
}
inline float CabinSurvey(float3 proj,float2 tile){
    if(any(proj.xy<0)||any(proj.xy>1))return 0;
    float2 p=proj.xy*_CabinFieldSize.xy-.5,b=floor(p),f=frac(p);
    float tol=clamp(.004+fwidth(proj.z)*1.4,.004,.020);
    return lerp(lerp(CabinVisibilityTap(b,tile,proj.z,tol),CabinVisibilityTap(b+float2(1,0),tile,proj.z,tol),f.x),
        lerp(CabinVisibilityTap(b+float2(0,1),tile,proj.z,tol),CabinVisibilityTap(b+1,tile,proj.z,tol),f.x),f.y);
}
inline void CabinContact(float3 obj,float4 cable,float2 surfaceUV,inout half3 albedo,inout half smoothness,inout half visibility,inout half3 normalTS){
    if(_CabinLayer.x>.5){
        float a=CabinSurvey(mul(_CabinProject0,float4(obj,1)).xyz,_CabinTiles.xy);
        if(_CabinLayer.x>1.5)a=max(a,CabinSurvey(mul(_CabinProject1,float4(obj,1)).xyz,_CabinTiles.zw));
        visibility*=pow(max(.06,1-a),1.43);
    }
    if(_CabinLayer.y>.5){
        float3 p=mul(_CabinRest,float4(obj,1)).xyz;
        float3 d=(p-_CabinRub.xyz)*float3(8.2,10.1,8.2);float rub=_CabinRub.w*exp(-dot(d,d));
        float grain=dot(p,float3(.31,.89,.147))*2800;
        float scratch=sin(grain+2*sin(grain*.014))*exp(-1.3*abs(fwidth(grain)));
        float r=1-smoothness;
        r=_CabinLayer.y<1.5?r*.85+.042+scratch*.047-rub*.085:_CabinLayer.y<2.5?r*.87+.04-rub*.155:r-rub*.13;
        smoothness=1-clamp(r,.16,.94);albedo*=1-rub*(_CabinLayer.y>1.5&&_CabinLayer.y<2.5?.093:.025);
    }
    if(_CabinLayer.z>.5){
        float phase=atan2(cable.z,cable.y)/6.2831853+.5;
        float ink=tex2D(_UpwellJacketPrint,float2(cable.x/.213,1-(phase+_CabinLayer.z-1)*.5)).r;
        float ridge=smoothstep(.956,.999,dot(normalize(cable.yz+1e-6),float2(.832,-.554)));
        albedo*=_CabinLayer.z<1.5?float3(.77,.69,.59):float3(.53,.79,.77);
        albedo=lerp(albedo*(1-.08*ridge),_CabinLayer.z<1.5?float3(.042,.029,.019):float3(.026,.046,.061),ink*.84);
        float ribs=cable.x*4900+phase*18.85;
        smoothness=1-clamp(.44+.16*(1-smoothness)+.05*cos(ribs)*exp(-1.8*abs(fwidth(ribs)))-.052*ridge,.34,.72);
    }
    if(_CabinLayer.w>.5&&cable.w>.01){
        float phase=atan2(cable.z,cable.y)/6.2831853;
        float2 yarn=cable.x/.0078+phase*float2(8,-8),cut=cos(yarn*6.2831853)*exp(-2.2*abs(fwidth(yarn)));
        float course=dot(abs(cut),float2(.48,.52)),interlace=max(cut.x,cut.y),height=.00013*interlace*cable.w;
        albedo*=lerp(half3(1,1,1),half3(.36,.37,.34)*(.92+course*.16+interlace*.10),cable.w);
        smoothness=lerp(smoothness,.52-.13*course,cable.w);
        float2 dx=ddx(surfaceUV),dy=ddy(surfaceUV);float uvArea=dx.x*dy.y-dx.y*dy.x;
        if(abs(uvArea)>1e-9){
            float3 du=(ddx(obj)*dy.y-ddy(obj)*dx.y)/uvArea,dv=(ddy(obj)*dx.x-ddx(obj)*dy.x)/uvArea;
            float2 dh=float2(ddx(height)*dy.y-ddy(height)*dx.y,ddy(height)*dx.x-ddx(height)*dy.x)/uvArea;
            normalTS=normalize(normalTS-float3(dh/max(float2(length(du),length(dv)),.0001),0));
        }
    }
}
inline half3 CabinCover(half3 light,float3 fragmentWorld,float3 normal,float2 uv){
    if(_CabinGlass<.5)return light;
    float3 v=normalize(fragmentWorld-_WorldSpaceCameraPos),n=normalize(normal);
    if(dot(v,n)>0)n=-n;
    half4 observed=UNITY_SAMPLE_TEXCUBE_LOD(unity_SpecCube0,reflect(v,n),.5);
    half3 reflected=min(DecodeHDR(observed,unity_SpecCube0_HDR),3.8)*half3(.96,.99,1.025);
    half fresnel=.025+.72*pow(1-saturate(dot(-v,n)),5);
    float edge=min(min(uv.x,1-uv.x),min(uv.y,1-uv.y));
    return lerp(lerp(light,reflected,fresnel),half3(.011,.017,.016),.56*(1-smoothstep(0,max(.002,fwidth(edge)*1.3),edge)));
}
#endif
