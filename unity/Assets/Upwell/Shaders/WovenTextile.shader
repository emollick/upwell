Shader "Upwell/Woven textile" {
    Properties {
        _MainTex("Yarn colour",2D)="white"{}
        _RoughMap("Measured roughness",2D)="white"{}
        [Normal] _BumpMap("Woven relief",2D)="bump"{}
        _Roughness("Fiber roughness",Range(0,1))=.9
        _MappedRoughness("Roughness texture",Range(0,1))=1
        _NormalStrength("Weave depth",Range(0,1))=.72
    }
    SubShader {
        Tags {"RenderType"="Opaque"} Cull Off
        CGPROGRAM
        #pragma surface surf Woven fullforwardshadows addshadow
        #pragma target 3.0
        #include "UnityStandardUtils.cginc"
        #include "UnityGlobalIllumination.cginc"
        #include "CabinDaylight.cginc"
        sampler2D _MainTex,_RoughMap,_BumpMap;half _Roughness,_MappedRoughness,_NormalStrength;
        struct Input {float2 uv_MainTex;float3 viewDir;float3 worldPos;float3 worldNormal;INTERNAL_DATA float4 color:COLOR;fixed facing:VFACE;};
        half4 LightingWoven(SurfaceOutput s,half3 view,UnityGI gi){
            half nl=dot(s.Normal,gi.light.dir),ndv=saturate(dot(s.Normal,view)),ndl=saturate(nl);
            // Diffuse multiple scattering among yarns lifts the dark side of each fold.
            // This lobe has no metal or polished dielectric environment reflection.
            half wrap=saturate((nl+.32)/1.32);
            half diffuse=.68*ndl+.32*wrap;
            half fibreSheen=.023*pow(1-ndv,3.)*sqrt(max(0.,diffuse))*(.4+.6*s.Specular);
            half3 outgoing=s.Albedo*(gi.indirect.diffuse+gi.light.color*diffuse);
            return half4(outgoing+gi.light.color*fibreSheen,1);
        }
        void LightingWoven_GI(SurfaceOutput s,UnityGIInput data,inout UnityGI gi){
            gi=UnityGlobalIllumination(data,s.Gloss,s.Normal);
        }
        void surf(Input i,inout SurfaceOutput o){
            half3 fibre=UnpackScaleNormal(tex2D(_BumpMap,i.uv_MainTex),_NormalStrength);
            if(i.facing<0)fibre=-fibre;
            o.Normal=fibre;
            half graze=1-saturate(abs(dot(normalize(i.viewDir),fibre)));
            half ao=saturate(i.color.r);
            o.Albedo=tex2D(_MainTex,i.uv_MainTex).rgb*lerp(.82,1,ao)*(1+.085*graze*graze);
            half roughness=lerp(_Roughness,tex2D(_RoughMap,i.uv_MainTex).r,_MappedRoughness);
            o.Specular=1-roughness;
            o.Gloss=lerp(.54,1,ao);
            half ambientFactor=1;
            half3 apertureLight=CabinDaylight(i.worldPos,WorldNormalVector(i,o.Normal),ambientFactor);
            o.Emission=o.Albedo*apertureLight*o.Gloss;o.Gloss*=ambientFactor;
            o.Alpha=1;
        }
        ENDCG
    }
    Fallback "Diffuse"
}
