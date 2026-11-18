Shader "Upwell/Aster member area coverage" {
    SubShader {
        Tags { "Queue"="Transparent-20" "RenderType"="Transparent" }
        Cull Off ZWrite Off Blend SrcAlpha OneMinusSrcAlpha
        Pass {
            Tags { "LightMode"="ForwardBase" }
            CGPROGRAM
            #pragma target 3.0
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile_fwdbase
            #include "UnityCG.cginc"
            #include "Lighting.cginc"
            #include "UnityPBSLighting.cginc"
            struct Input {
                float4 vertex:POSITION;float3 other:TEXCOORD0;float3 sectionU:TEXCOORD1;float3 sectionV:TEXCOORD2;
                float2 corner:TEXCOORD3;float3 finish:TEXCOORD4;float4 color:COLOR;
            };
            struct Varyings {
                float4 pos:SV_POSITION;float4 screen:TEXCOORD0;float4 beam:TEXCOORD1;float4 section:TEXCOORD2;
                half3 front:TEXCOORD3;half3 side:TEXCOORD4;half4 tint:COLOR0;half3 finish:TEXCOORD5;float3 toward:TEXCOORD6;
                half4 faceU:TEXCOORD7;half3 faceV:TEXCOORD8;
            };
            float2 Pixel(float4 p){float4 uv=ComputeScreenPos(p);return uv.xy/uv.w*_ScreenParams.xy;}
            Varyings vert(Input v) {
                Varyings o;
                float3 va=UnityObjectToViewPos(v.vertex.xyz),vb=UnityObjectToViewPos(v.other),mid=(va+vb)*.5;
                float2 pa=Pixel(mul(UNITY_MATRIX_P,float4(va,1))),pb=Pixel(mul(UNITY_MATRIX_P,float4(vb,1)));
                float len=max(.002,length(pb-pa));float2 d=(pb-pa)/len,across=float2(-d.y,d.x);
                float3 vu=mul((float3x3)UNITY_MATRIX_MV,v.sectionU),vv=mul((float3x3)UNITY_MATRIX_MV,v.sectionV);
                float2 pm=Pixel(mul(UNITY_MATRIX_P,float4(mid,1)));
                float2 hu=Pixel(mul(UNITY_MATRIX_P,float4(mid+vu,1)))-pm;
                float2 hv=Pixel(mul(UNITY_MATRIX_P,float4(mid+vv,1)))-pm;
                float2 section=float2(dot(hu,across),dot(hv,across));
                float r=lerp(length(section),abs(section.x)+abs(section.y),v.finish.z);
                float2 pixel=lerp(pa,pb,v.corner.x)+d*(v.corner.x*2-1)*.86+across*v.corner.y*(r+.86);
                float3 axis=normalize(vb-va),toward=normalize(-mid);
                float3 front=normalize(toward-axis*dot(toward,axis)+.000001),lateral=normalize(cross(axis,front));
                float2 projected=Pixel(mul(UNITY_MATRIX_P,float4(mid+lateral,1)))-pm;if(dot(projected,across)<0)lateral=-lateral;
                float3 pos=lerp(va,vb,v.corner.x)+front*max(length(vu),length(vv))*.53;
                o.pos=mul(UNITY_MATRIX_P,float4(pos,1));o.pos.xy=(pixel/_ScreenParams.xy*2-1)*o.pos.w*float2(1,_ProjectionParams.x);
                o.screen=ComputeScreenPos(o.pos);o.beam=float4(pa,d);
                float unit=length(mul((float3x3)unity_ObjectToWorld,float3(1,0,0)));
                float pixelsPerUnit=.5*_ScreenParams.y*abs(UNITY_MATRIX_P._m11)*unit/max(.01,-UnityObjectToViewPos(float3(0,0,0)).z);
                float widthPixels=2*max(length(v.sectionU),length(v.sectionV))*pixelsPerUnit;
                if(widthPixels>=5.1)o.pos=float4(2,2,1,1);
                float fu=dot(vu,toward)>=0?1:-1,fv=dot(vv,toward)>=0?1:-1;
                o.section=float4(len,r,widthPixels,section.x*fu);o.front=front;o.side=lateral;o.tint=v.color;o.finish=v.finish;
                o.faceU=half4(normalize(vu)*fu,abs(section.y));o.faceV=normalize(vv)*fv;
                o.toward=mul((float3x3)UNITY_MATRIX_I_V,toward);
                return o;
            }
            float Cdf(float x,float2 n){
                float2 a=abs(n)*.5;float hi=max(a.x,a.y),lo=min(a.x,a.y);
                if(lo<.002)return saturate(.5+x/(2*max(.001,hi)));
                float q=abs(x),tail=max(0,hi+lo-q);
                float v=q<hi-lo?.5+q/(2*hi):1-tail*tail/(8*hi*lo);
                return x<0?1-v:v;
            }
            half3 SectionLight(half3 viewNormal,half3 eye,half3 tint,half3 diffuse,half3 spec,half complement,half roughness){
                half3 normal=normalize(mul((float3x3)UNITY_MATRIX_I_V,viewNormal));
                UnityLight sun;sun.color=_LightColor0.rgb;sun.dir=normalize(_WorldSpaceLightPos0.xyz);sun.ndotl=saturate(dot(normal,sun.dir));
                UnityIndirect indirect;indirect.diffuse=max(0,ShadeSH9(half4(normal,1)));
                Unity_GlossyEnvironmentData env=UnityGlossyEnvironmentSetup(1-roughness,eye,normal,spec);
                indirect.specular=Unity_GlossyEnvironment(UNITY_PASS_TEXCUBE(unity_SpecCube0),unity_SpecCube0_HDR,env);
                half3 result=UNITY_BRDF_PBS(diffuse,spec,complement,1-roughness,normal,eye,sun,indirect).rgb;
                half broad=.29+.41*saturate(dot(normal,normalize(half3(.47,.31,-.82))))+.30*(.5-.5*normal.y);
                return result+tint*broad*.40*half3(.81,.90,1);
            }
            fixed4 frag(Varyings i):SV_Target {
                float2 q=i.screen.xy/i.screen.w*_ScreenParams.xy-i.beam.xy,d=i.beam.zw,n=float2(-d.y,d.x);
                float x=dot(q,d),y=dot(q,n),r=i.section.y;
                float width=Cdf(y+r,n)-Cdf(y-r,n);
                float covered=width*(Cdf(x,d)-Cdf(x-i.section.x,d));
                float opacity=covered*(1-smoothstep(3.7,5.1,i.section.z));clip(opacity-.0015);
                float off=clamp(y/max(r,.001),-.96,.96),part=max(width,.00001);
                half3 nr=normalize(i.front*sqrt(1-off*off)+i.side*off);
                half3 a=normalize(i.front*.70-i.side*.715),b=i.front,c=normalize(i.front*.70+i.side*.715);
                float left=(Cdf(y+r,n)-Cdf(y+r*.3333,n))/part,right=(Cdf(y-r*.3333,n)-Cdf(y-r,n))/part;
                half3 weights=half3(left,max(0,1-left-right),right);
                if(i.finish.z>.5){
                    float t=y-i.section.w,w=i.faceU.w,uf=saturate((Cdf(t+w,n)-Cdf(t-w,n))/part);
                    weights=half3(uf,0,1-uf);a=i.faceU.xyz;c=i.faceV;
                }else{
                    float resolved=smoothstep(1.75,4.2,r);
                    a=normalize(lerp(a,nr,resolved));b=normalize(lerp(b,nr,resolved));c=normalize(lerp(c,nr,resolved));
                }
                half3 eye=normalize(i.toward),tint=i.tint.rgb,spec;
                half oneMinusReflectivity;half3 diffuse=DiffuseAndSpecularFromMetallic(tint,i.finish.x,spec,oneMinusReflectivity);
                half3 result=SectionLight(a,eye,tint,diffuse,spec,oneMinusReflectivity,i.finish.y)*weights.x+
                             SectionLight(b,eye,tint,diffuse,spec,oneMinusReflectivity,i.finish.y)*weights.y+
                             SectionLight(c,eye,tint,diffuse,spec,oneMinusReflectivity,i.finish.y)*weights.z;
                return half4(result,opacity);
            }
            ENDCG
        }
    }
    Fallback Off
}
