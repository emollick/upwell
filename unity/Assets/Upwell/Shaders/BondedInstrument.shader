Shader "Upwell/Coated instrument glass" {
    Properties { _MainTex("Instrument",2D)="black"{} _Emission("Panel output",Range(0,3))=.58 }
    SubShader { Tags {"RenderType"="Opaque"}
        CGPROGRAM
        #pragma surface surf StandardSpecular fullforwardshadows addshadow
        #pragma target 3.0
        sampler2D _MainTex;half _Emission;struct Input {float2 uv_MainTex;};
        void surf(Input i,inout SurfaceOutputStandardSpecular o){
            half3 ink=tex2D(_MainTex,i.uv_MainTex).rgb;o.Albedo=ink*.52;o.Emission=ink*_Emission;
            o.Specular=half3(.006,.009,.012);o.Smoothness=.47;o.Alpha=1;
        }
        ENDCG
    }Fallback "Diffuse"
}
