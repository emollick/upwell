// Six broad directional radiances traced through the actual maritime sky.
// Opposite faces blend by projected area, approximating a hemispherical integral.
#ifndef UPWELL_HARBOR_SKY
#define UPWELL_HARBOR_SKY
sampler2D _HarborLight;
float _HarborLightReady;
inline half3 HarborFaces(float3 n){
    float3 w=n*n;
    half3 x=tex2Dlod(_HarborLight,float4((n.x>0?.5:1.5)/6.,.5,0,0)).rgb;
    half3 y=tex2Dlod(_HarborLight,float4((n.y>0?2.5:3.5)/6.,.5,0,0)).rgb;
    half3 z=tex2Dlod(_HarborLight,float4((n.z>0?4.5:5.5)/6.,.5,0,0)).rgb;
    return w.x*x+w.y*y+w.z*z;
}
inline half3 HarborIrradiance(float3 n){
    // A vertical hull side sees sky over the upper half of its incident hemisphere.
    float3 bent=normalize(float3(n.x*.76,n.y+.41,n.z*.76));
    return HarborFaces(bent);
}
#endif
