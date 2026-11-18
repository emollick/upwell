Shader "Upwell/Aster close structural members" {
    Properties {
        _Color ("Tint",Color)=(1,1,1,1)
        _MainTex ("Finish",2D)="white"{}
        _Metallic ("Metalness",Range(0,1))=.5
        _Glossiness ("Smoothness",Range(0,1))=.5
        _AsterBounce ("Reflected valley light",Range(0,1))=.4
    }
    SubShader {
        Tags {"Queue"="Transparent-10" "RenderType"="Transparent"}
        CGPROGRAM
        #pragma target 3.0
        #pragma surface surf Standard alpha:fade fullforwardshadows vertex:nearVertex
        sampler2D _MainTex;fixed4 _Color;half _Metallic,_Glossiness,_AsterBounce;
        struct Input {float2 uv_MainTex;float3 worldNormal;float nearWeight;};
        void nearVertex(inout appdata_full v,out Input o){
            UNITY_INITIALIZE_OUTPUT(Input,o);
            float unit=length(mul((float3x3)unity_ObjectToWorld,float3(1,0,0)));
            float footprint=.5*_ScreenParams.y*abs(UNITY_MATRIX_P._m11)*unit/max(.01,-UnityObjectToViewPos(float3(0,0,0)).z);
            o.nearWeight=smoothstep(2.8,4.6,footprint*v.texcoord1.x);
            if(o.nearWeight<.001)v.vertex.xyz=0;
        }
        void surf(Input i,inout SurfaceOutputStandard o){
            clip(i.nearWeight-.001);half3 n=normalize(i.worldNormal),c=tex2D(_MainTex,i.uv_MainTex).rgb*_Color.rgb;
            float broad=.29+.41*saturate(dot(n,normalize(half3(.47,.31,-.82))))+.30*(.5-.5*n.y);
            o.Albedo=c;o.Metallic=_Metallic;o.Smoothness=_Glossiness;o.Emission=c*broad*_AsterBounce*half3(.81,.90,1);o.Alpha=i.nearWeight;
        }
        ENDCG
    }
    Fallback "Standard"
}
