Shader "Hidden/Upwell/Presentation FXAA" {
    Properties { _MainTex ("Scene",2D) = "black" {} }
    SubShader { Cull Off ZWrite Off ZTest Always
        Pass {
            CGPROGRAM
            #pragma vertex vert_img
            #pragma fragment FilterEdges
            #pragma target 3.0
            #include "UnityCG.cginc"
            sampler2D _MainTex;
            float4 _MainTex_TexelSize;
            float Luma(float3 color){return sqrt(max(0,dot(color,float3(.299,.587,.114))));}
            float4 FilterEdges(v2f_img i):SV_Target {
                float2 p=i.uv, d=abs(_MainTex_TexelSize.xy);
                float4 original=tex2D(_MainTex,p);
                float m=Luma(original.rgb);
                float nw=Luma(tex2D(_MainTex,p+float2(-d.x,d.y)).rgb),ne=Luma(tex2D(_MainTex,p+d).rgb);
                float sw=Luma(tex2D(_MainTex,p-d).rgb),se=Luma(tex2D(_MainTex,p+float2(d.x,-d.y)).rgb);
                float lo=min(m,min(min(nw,ne),min(sw,se))),hi=max(m,max(max(nw,ne),max(sw,se)));
                if(hi-lo<max(.032,hi*.105))return original;
                float n=Luma(tex2D(_MainTex,p+float2(0,d.y)).rgb),s=Luma(tex2D(_MainTex,p-float2(0,d.y)).rgb);
                float e=Luma(tex2D(_MainTex,p+float2(d.x,0)).rgb),w=Luma(tex2D(_MainTex,p-float2(d.x,0)).rgb);
                float mid=(lo+hi)*.5;
                float bright=step(mid,m)+step(mid,nw)+step(mid,ne)+step(mid,sw)+step(mid,se)+step(mid,n)+step(mid,s)+step(mid,e)+step(mid,w);
                if(bright<2.5 || bright>6.5)return original; // An unresolved star or dark pinhole keeps its original footprint.
                float2 direction=float2(sw+se-nw-ne,ne+se-nw-sw);
                float reduction=max((nw+ne+sw+se)*.03125,.0078125);
                direction=clamp(direction/(min(abs(direction.x),abs(direction.y))+reduction),-8,8)*d;
                float3 inner=.5*(tex2D(_MainTex,p+direction/6).rgb+tex2D(_MainTex,p-direction/6).rgb);
                float3 outer=inner*.5+.25*(tex2D(_MainTex,p+direction*.5).rgb+tex2D(_MainTex,p-direction*.5).rgb);
                float l=Luma(outer);
                return float4(l<lo || l>hi ? inner : outer,original.a);
            }
            ENDCG
        }
    }
    Fallback Off
}
