Shader "Upwell/Running guide finish" {
    Properties {
        _MainTex ("Surface",2D)="white" {}
        _Color ("Tint",Color)=(1,1,1,1)
        _RoughMap ("Roughness",2D)="white" {}
        _Roughness ("Roughness",Range(0,1))=.42
        _MappedRoughness ("Mapped roughness",Range(0,1))=0
        [Normal] _BumpMap ("Normal",2D)="bump" {}
        _NormalStrength ("Normal depth",Range(0,1))=.3
        _Metallic ("Metallic",Range(0,1))=.7
        _GuideMean ("Average measured reflectance",Color)=(.5,.5,.5,1)
        _GuideKind ("Guide material",Float)=0
        _GuideRadius ("Contact roller radius",Float)=1
    }
    SubShader {
        Tags {"RenderType"="Opaque"}
        CGPROGRAM
        #pragma target 3.0
        #pragma surface surf Standard fullforwardshadows addshadow vertex:GuideVertex
        #include "UnityStandardUtils.cginc"
        sampler2D _MainTex,_RoughMap,_BumpMap;
        fixed4 _Color,_GuideMean;
        half _Roughness,_MappedRoughness,_NormalStrength,_Metallic;
        float _GuideKind,_GuideRadius,_UpwellGuideShutter;
        struct Input {float2 uv_MainTex;float3 guideP;float3 guideN;float4 color:COLOR;};
        void GuideVertex(inout appdata_full v,out Input o){
            UNITY_INITIALIZE_OUTPUT(Input,o);o.guideP=v.vertex.xyz;o.guideN=v.normal;
            if(_GuideKind==3 && length(v.vertex.xy)>.012 && abs(v.vertex.z)>.030){
                float2 axis=normalize(v.vertex.xy);
                v.normal=normalize(float3(axis*dot(axis,v.normal.xy),v.normal.z));
            }
        }
        float Wave(float phase,float smear){
            return cos(6.2831853*phase)*(1-smoothstep(.16,.82,fwidth(phase)+smear));
        }
        void surf(Input i,inout SurfaceOutputStandard o){
            float3 p=i.guideP;
            float3 color=tex2D(_MainTex,i.uv_MainTex).rgb*_Color.rgb;
            float roughness=lerp(_Roughness,tex2D(_RoughMap,i.uv_MainTex).r,_MappedRoughness);
            float shutter=_UpwellGuideShutter,normalWeight=1,metal=_Metallic;
            if(_GuideKind==1){
                float fiber=Wave(p.z*267,0);
                float tape=.6*Wave(p.z*94+.2,0)+.4*Wave(p.z*157,0);
                float binder=.5*(Wave(p.z*114+p.y*57,shutter*57)+Wave(p.z*111-p.y*57,shutter*57));
                float blur=smoothstep(.003,.11,shutter);
                color=lerp(color,_GuideMean.rgb,blur*.85)*(.79+.087*tape+.058*fiber+.049*binder);
                roughness=lerp(roughness,.53,.52+blur*.36)+fiber*.026+tape*.030+binder*.021;
                metal*=.48;
                normalWeight=lerp(.68,.085,blur);
            }else if(_GuideKind==2){
                float isRail=step(abs(abs(p.z)-.485),.065)*step(-.012,p.x);
                float nz=abs(normalize(i.guideN).z),aa=min(.23,fwidth(nz));
                float track=(1-smoothstep(.12-aa,.39+aa,nz))*isRail;
                float grain=Wave(p.z*491,0),blur=smoothstep(.003,.105,shutter);
                color=lerp(color,_GuideMean.rgb,blur*.81)*lerp(.73,1.13,track)*(1+.019*grain);
                roughness=lerp(lerp(.44,.29,track),roughness,.19*(1-blur))+.019*grain;
                normalWeight=lerp(.61,.10,blur);
            }else if(_GuideKind==3){
                float r=length(p.xy);
                if(abs(p.z)<.026 && r<_GuideRadius*.818 && shutter/_GuideRadius>.24)clip(-1);
                float face=step(_GuideRadius*.25,r)*step(.030,abs(p.z));
                float lathe=Wave(r*470,0),norm=r/_GuideRadius,aa=min(.025,fwidth(norm));
                float groove=1-smoothstep(.004,.012+aa,abs(norm-.863));
                float land=smoothstep(.545-aa,.565+aa,norm)*(1-smoothstep(.834-aa,.852+aa,norm));
                float turn=face*(.76+.20*smoothstep(0,.11,shutter));
                color=lerp(color,_GuideMean.rgb,turn)*(1+face*(-.18+.090*land-.30*groove+lathe*.022));
                roughness=lerp(roughness,.46-.102*land+.085*groove+lathe*.014,turn);
                normalWeight=1-turn*.91;
            }else if(_GuideKind==4 && shutter/_GuideRadius>.24)clip(-1);
            half ao=saturate(i.color.r);
            o.Albedo=color*lerp(.74,1,ao);o.Metallic=metal;o.Smoothness=1-saturate(roughness);
            o.Normal=UnpackScaleNormal(tex2D(_BumpMap,i.uv_MainTex),_NormalStrength*normalWeight);
            o.Occlusion=lerp(.45,1,ao);o.Alpha=1;
        }
        ENDCG
    }
    Fallback "Standard"
}
