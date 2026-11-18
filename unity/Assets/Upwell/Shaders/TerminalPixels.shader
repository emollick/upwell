Shader "Upwell/Terminal status"{
    Properties{_MainTex("Terminal atlas",2D)="black"{}}
    SubShader{Tags {"RenderType"="Opaque"} Pass{
        CGPROGRAM
        #pragma vertex vert
        #pragma fragment frag
        #include "UnityCG.cginc"
        sampler2D _MainTex,_UpwellAnchor,_UpwellAster,_UpwellScada,_UpwellScope;float _UpwellTerminalLive;
        struct v2f{float4 p:SV_POSITION;float2 uv:TEXCOORD0;};v2f vert(appdata_base v){v2f o;o.p=UnityObjectToClipPos(v.vertex);o.uv=v.texcoord;return o;}
        half4 frag(v2f i):SV_Target{float2 p=float2(i.uv.x,1-i.uv.y)*2048;half3 c=tex2D(_MainTex,i.uv).rgb;
            if(_UpwellTerminalLive>.5&&p.y>=951&&p.y<=1252){int k=(int)clamp(floor(p.x/510),0,3);float start=k==0?11:k==1?520:k==2?1029:1538;
                float2 q=float2((p.x-start)/490,1-(p.y-951)/301);
                if(q.x>=0&&q.x<=1)c=k==0?tex2D(_UpwellAnchor,q).rgb:k==1?tex2D(_UpwellAster,q).rgb:k==2?tex2D(_UpwellScada,q).rgb:tex2D(_UpwellScope,q).rgb;}
            return half4(c*1.15,1);}
        ENDCG
    }}
}
