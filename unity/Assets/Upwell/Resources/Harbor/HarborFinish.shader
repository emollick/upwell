Shader "Upwell/Marine daylight finish" {
    Properties {
        _MainTex ("Paint",2D)="white"{}
        _Color ("Paint tint",Color)=(1,1,1,1)
        _Metallic ("Metalness",Range(0,1))=0
        _Glossiness ("Smoothness",Range(0,1))=.4
        [Normal] _BumpMap ("Coating normal",2D)="bump"{}
        _BumpScale ("Normal strength",Float)=1
        [HDR] _EmissionColor ("Navigation light",Color)=(0,0,0,1)
    }
    SubShader {
        Tags {"RenderType"="Opaque"}
        LOD 240
        CGPROGRAM
        #pragma surface surf Standard fullforwardshadows addshadow
        #pragma target 3.0
        #include "UnityStandardUtils.cginc"
        #include "HarborSky.cginc"
        sampler2D _MainTex,_BumpMap;
        fixed4 _Color;
        half4 _EmissionColor;
        half _Glossiness,_Metallic,_BumpScale;
        struct Input {float2 uv_MainTex;float3 worldPos;float3 worldNormal;INTERNAL_DATA};
        void surf(Input i,inout SurfaceOutputStandard o){
            half3 paint=tex2D(_MainTex,i.uv_MainTex).rgb*_Color.rgb;
            o.Albedo=paint;o.Metallic=_Metallic;o.Smoothness=_Glossiness;o.Alpha=1;o.Occlusion=1;
            o.Normal=UnpackScaleNormal(tex2D(_BumpMap,i.uv_MainTex),_BumpScale);
            float3 n=normalize(WorldNormalVector(i,o.Normal)),v=normalize(_WorldSpaceCameraPos-i.worldPos);
            half3 sky=HarborIrradiance(n);
            half3 diffuse=paint*(1.-_Metallic)*sky*.73;
            float3 reflected=reflect(-v,n);
            half fresnel=pow(1.-saturate(dot(n,v)),5.);
            half3 f0=lerp(half3(.039,.039,.039),paint,_Metallic);
            half3 gloss=lerp(f0,1.,fresnel)*HarborFaces(reflected)*lerp(.34,.78,_Glossiness);
            o.Emission=_EmissionColor.rgb+_HarborLightReady*(diffuse+gloss);
        }
        ENDCG
    }
    Fallback "Standard"
}
