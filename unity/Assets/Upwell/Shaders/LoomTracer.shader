Shader "Upwell/Loom witness fibre"{
    Properties{_MainTex("Fibre coordinates",2D)="white"{} _Color("Fibre",Color)=(.1,.14,.14,1) _Pulse("Diagnostic pulse",Float)=-2 _TraceInk("Colour",Color)=(.3,.8,1,1)}
    SubShader{Tags {"RenderType"="Opaque"} Cull Off
        CGPROGRAM
        #pragma surface surf Standard fullforwardshadows
        half4 _Color,_TraceInk;float _Pulse;sampler2D _MainTex;struct Input{float2 uv_MainTex;};
        void surf(Input i,inout SurfaceOutputStandard o){float wave=saturate(1-abs(i.uv_MainTex.x-_Pulse)*8);
            o.Albedo=_Color.rgb;o.Emission=_TraceInk.rgb*wave*2.8;o.Smoothness=.52;o.Metallic=.18;o.Alpha=1;}
        ENDCG
    }
}
