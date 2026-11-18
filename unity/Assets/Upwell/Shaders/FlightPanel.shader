Shader "Upwell/Optical flight panel" {
    Properties { _MainTex("Telemetry",2D)="black"{} _Feed("Selected exterior camera",2D)="black"{} _PanelGain("Panel luminance",Float)=.8 _Page("Page",Float)=0 }
    SubShader {
        Tags { "RenderType"="Opaque" }
        Pass {
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma target 3.0
            #include "UnityCG.cginc"
            #include "CabinHardware.cginc"
            sampler2D _MainTex,_Feed;float _Page,_PanelGain;
            struct v2f {float4 pos:SV_POSITION;float2 uv:TEXCOORD0;float3 fragmentWorld:TEXCOORD1;float3 normal:TEXCOORD2;};
            v2f vert(appdata_base v){v2f o;o.pos=UnityObjectToClipPos(v.vertex);o.uv=v.texcoord;o.fragmentWorld=mul(unity_ObjectToWorld,v.vertex).xyz;o.normal=UnityObjectToWorldNormal(v.normal);return o;}
            half4 frag(v2f i):SV_Target{
                float2 u=(i.uv-float2(.57,.44))/float2(.402,.343);
                if(_Page>.5&&_Page<1.5)u=(i.uv-float2(.034,.12))/float2(.934,.69);
                half3 c=tex2D(_MainTex,i.uv).rgb;
                if(all(u>=0)&&all(u<=1))c=tex2D(_Feed,u).rgb*.85;
                float rowPhase=i.uv.y*1400.;
                float rowContrast=1.-smoothstep(1.,3.14,fwidth(rowPhase));
                return half4(CabinCover(c*(.98+.02*rowContrast*cos(rowPhase))*_PanelGain,i.fragmentWorld,i.normal,i.uv),1);
            }
            ENDCG
        }
    }
}
