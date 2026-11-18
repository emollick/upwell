#ifndef UPWELL_CABIN_DAYLIGHT_INCLUDED
#define UPWELL_CABIN_DAYLIGHT_INCLUDED
sampler2D _UpwellApertures;
float4 _UpwellApertureSky,_UpwellApertureEarth,_UpwellApertureSun,_UpwellApertureGain;
float _CabinApertures;
inline float2 ApertureUV(float2 xy,float sliceIndex){
    float2 tile=float2(fmod(sliceIndex,12),floor(sliceIndex/12));
    float2 uv=(tile*float2(36,24)+xy+.5)/float2(432,192);
    return float2(uv.x,1-uv.y);
}
inline half3 CabinDaylight(float3 positionWS,float3 normalWS,inout half ambientFactor){
    if(_CabinApertures<.5)return 0;
    float3 n=normalize(normalWS)*float3(1,1,-1);
    float3 p=positionWS*float3(1,1,-1);
    float3 q=saturate((p+n*.084-float3(-2.27,-.08,-5.83))/float3(4.54,2.83,11.66))*float3(35,23,95);
    float sliceIndex=floor(q.z);
    half4 field=lerp(tex2D(_UpwellApertures,ApertureUV(q.xy,sliceIndex)),tex2D(_UpwellApertures,ApertureUV(q.xy,min(95,sliceIndex+1))),q.z-sliceIndex);
    field*=field;
    bool fore=p.z< -1.90;
    float3 east=float3(2.18,fore?1.76:1.85,fore?-3.80:.03)-p;
    float3 west=float3(-2.18,fore?1.76:1.68,fore?-3.80:3.68)-p;
    float3 front=float3(0,1.59,-5.67)-p,floorPort=float3(0,-.132,-3.80)-p;
    half4 cosine=half4(dot(n,normalize(east)),dot(n,normalize(west)),dot(n,normalize(front)),dot(n,normalize(floorPort)));
    // A finite patch also lights a surface that is edge-on to its centre.
    half4 flux=field*saturate(cosine+.25*field*(1-abs(cosine)));
    flux.z*=_UpwellApertureGain.w;
    ambientFactor=1-_UpwellApertureSky.a*(1-saturate(dot(field,half4(2,2,2,2))));
    return _UpwellApertureSky.rgb*(flux.x+flux.y+flux.z)+_UpwellApertureEarth.rgb*flux.w
         +_UpwellApertureSun.rgb*dot(flux.xyz,_UpwellApertureGain.xyz);
}
#endif
