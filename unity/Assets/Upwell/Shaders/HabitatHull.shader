Shader "Upwell/Habitat structure and valleys" {
    Properties{_MainTex("Longitudinal survey",2D)="white"{} _RoughMap("Roughness",2D)="gray"{}}
    SubShader{Tags {"RenderType"="Opaque"}
        CGPROGRAM
        #pragma surface surf Standard fullforwardshadows addshadow
        #pragma target 3.0
        sampler2D _MainTex,_RoughMap;struct Input{float2 uv_MainTex;};
        void surf(Input i,inout SurfaceOutputStandard o){
            float2 uv=i.uv_MainTex;half3 albedo=tex2D(_MainTex,uv).rgb;half roughness=tex2D(_RoughMap,uv).r;
            float cell=frac(uv.x*3);float glazing=smoothstep(.008,.05,cell)*(1-smoothstep(.48,.56,cell));
            o.Albedo=albedo;o.Metallic=lerp(.45,.18,glazing);o.Smoothness=1-roughness;
            float strips=pow(saturate(cos(uv.y*6.283185*56)),27)*glazing;
            // Interior glazing exposes lit farms and galleries, independent of the sunlit exterior plates.
            o.Emission=albedo*(.075+.61*glazing)+glazing*float3(.006,.022,.011)+strips*float3(.095,.073,.040);
            o.Alpha=1;
        }
        ENDCG
    }Fallback "Standard"
}
