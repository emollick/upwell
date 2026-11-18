Shader "Upwell/Backlit proof scale" {
    Properties {
        _MainTex("Registered scale printing",2D)="white"{}
        _DialLume("Dial phosphor registration",2D)="black"{}
        _Color("Print tint",Color)=(1,1,1,1)
        _Metallic("Metallic coating",Range(0,1))=.17
        _Roughness("Print roughness",Range(0,1))=.54
    }
    SubShader {
        Tags {"RenderType"="Opaque"}
        CGPROGRAM
        #pragma surface surf Standard fullforwardshadows addshadow
        #pragma target 3.0
        sampler2D _MainTex,_DialLume;half4 _Color;half _Metallic,_Roughness;
        struct Input {float2 uv_MainTex;};
        void surf(Input i,inout SurfaceOutputStandard o){
            half3 ink=tex2D(_MainTex,i.uv_MainTex).rgb*_Color.rgb;
            half lume=tex2D(_DialLume,i.uv_MainTex).r;
            o.Albedo=ink;o.Metallic=_Metallic;o.Smoothness=1-_Roughness;o.Alpha=1;
            o.Emission=ink*lume*half3(.105,.099,.088);
        }
        ENDCG
    }
    FallBack "Standard"
}
