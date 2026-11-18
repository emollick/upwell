Shader "Upwell/Proof cell optical guard" {
    Properties { _Color("Edge tint",Color)=(.53,.72,.75,1) }
    SubShader {
        Tags {"Queue"="Transparent" "RenderType"="Transparent" "IgnoreProjector"="True"}
        ZWrite Off Cull Back Blend SrcAlpha OneMinusSrcAlpha
        Pass {
            Tags {"LightMode"="ForwardBase"}
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma target 3.0
            #include "UnityCG.cginc"
            #include "Lighting.cginc"
            struct Vary {float4 pos:SV_POSITION;float3 normal:TEXCOORD0;float3 view:TEXCOORD1;};
            Vary vert(appdata_base v){Vary o;o.pos=UnityObjectToClipPos(v.vertex);o.normal=UnityObjectToWorldNormal(v.normal);o.view=_WorldSpaceCameraPos-mul(unity_ObjectToWorld,v.vertex).xyz;return o;}
            float4 _Color;
            half4 frag(Vary i):SV_Target{
                float3 n=normalize(i.normal),v=normalize(i.view),refl=reflect(-v,n);
                float ndv=saturate(dot(n,v));
                float f=min(.59,.008+.992*pow(1-ndv,5));
                float absorption=.0018/max(.28,ndv),alpha=f+absorption;
                half3 reflected=DecodeHDR(UNITY_SAMPLE_TEXCUBE_LOD(unity_SpecCube0,refl,1.3),unity_SpecCube0_HDR);
                half3 highlight=_LightColor0.rgb*pow(saturate(dot(refl,normalize(_WorldSpaceLightPos0.xyz))),248)*.45;
                return half4(((reflected+highlight)*f+_Color.rgb*absorption)/alpha,alpha);
            }
            ENDCG
        }
    }
}
