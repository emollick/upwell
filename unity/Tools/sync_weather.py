"""Convert the shared scalar weather expressions to Unity's HLSL sampler syntax."""
import re

def sync_weather(project):
    source=(project.parent/"web/weather-density.js").read_text(encoding="utf-8")
    glsl=source.split("export const WEATHER_GLSL=",1)[1].split("`",2)[1]
    field=glsl[glsl.index("float broadCloudDensity("):]
    for src,dst in (("vec4","float4"),("vec3","float3"),("vec2","float2"),("fract(","frac("),("atan(e.z,e.x)","atan2(e.z,e.x)"),("atan(n.x,n.y)","atan2(n.x,n.y)"),("mix(","lerp("),("float4(0.)","float4(0,0,0,0)"),("weatherLod","unresolved")):field=field.replace(src,dst)
    field=field.replace("textureLod(broadCloudMap,float2(frac(uv.x),clamp(uv.y,.001,.999)),0.)","tex2Dlod(_Broad,float4(frac(uv.x),clamp(uv.y,.001,.999),0,0))")
    field=field.replace("textureLod(noiseVolume,frac(p),0.)","Noise4(p)")
    field=field.replace("textureLod(marineCells,","MarineCell(")
    field=field.replace("textureLod(regionalMap,uv,footprint)","tex2Dlod(_Atlantic,float4(uv,0,footprint))")
    field=field.replace("float cloudDensity(float3 p){","float DensityAt(float3 local,float h,float unresolved,float footprintKm){\n  float3 p=local+float3(0,6371.,0);")
    field=field.replace("localCloud(q,h,densityFilterKm)","localCloud(q,h,footprintKm)")
    field=field.replace("float h=length(p)-6371.;","")
    field=field.replace("p-float3(wind.x*weatherTime,6371.,wind.y*weatherTime)","local-float3(wind.x*weatherTime,0.,wind.y*weatherTime)")
    field=re.sub(r"  float unresolved=[^;]+;\n","",field)
    header="""#ifndef UPWELL_CLOUD_FIELD
#define UPWELL_CLOUD_FIELD
sampler3D _NoiseField; sampler2D _Broad,_Atlantic,_MarineCells; float _WeatherSeconds,_HeightKm;
#define altitudeKm _HeightKm
#define weatherTime _WeatherSeconds
#define wind float2(.018,.007)
#define coverage .58
#define evolution .5
#define longitude (-.6283185307)
float4 Noise4(float3 p){return tex3Dlod(_NoiseField,float4(p,0));}
float4 MarineCell(float2 uv,float lod){return tex2Dlod(_MarineCells,float4(uv,0,lod));}
"""
    result=header+field.strip()+"\n#endif\n";path=project/"Assets/Upwell/Shaders/CloudField.cginc"
    if not path.exists() or path.read_text(encoding="utf-8")!=result:path.write_text(result,encoding="utf-8")
