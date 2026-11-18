Shader "Upwell/Bonded live readout"{
    Properties{_MainTex("Live pixels",2D)="black"{} _PanelGain("Panel luminance",Float)=.8}
    SubShader{Tags {"RenderType"="Opaque"} Pass{
        CGPROGRAM
        #pragma vertex vert
        #pragma fragment frag
        #pragma target 3.0
        #include "UnityCG.cginc"
        #include "CabinHardware.cginc"
        sampler2D _MainTex;half _PanelGain;struct v2f{float4 p:SV_POSITION;float2 uv:TEXCOORD0;float3 fragmentWorld:TEXCOORD1;float3 normal:TEXCOORD2;};
        v2f vert(appdata_base v){v2f o;o.p=UnityObjectToClipPos(v.vertex);o.uv=v.texcoord;o.fragmentWorld=mul(unity_ObjectToWorld,v.vertex).xyz;o.normal=UnityObjectToWorldNormal(v.normal);return o;}
        half4 frag(v2f i):SV_Target{return half4(CabinCover(tex2D(_MainTex,i.uv).rgb*_PanelGain+.002,i.fragmentWorld,i.normal,i.uv),1);}
        ENDCG
    }}
}
