Shader "Upwell/Screen printed stencil" {
    Properties { _MainTex("Ink mask",2D)="white"{} _Cutoff("Cutout",Range(0,1))=.34 }
    SubShader { Tags {"Queue"="AlphaTest" "RenderType"="TransparentCutout"} Offset -1,-1
        CGPROGRAM
        #pragma surface surf Standard alphatest:_Cutoff addshadow fullforwardshadows
        #pragma target 3.0
        sampler2D _MainTex;struct Input{float2 uv_MainTex;};
        void surf(Input i,inout SurfaceOutputStandard o){fixed4 c=tex2D(_MainTex,i.uv_MainTex);o.Albedo=c.rgb;o.Alpha=c.a;o.Smoothness=.34;o.Metallic=.09;}
        ENDCG
    }
}
