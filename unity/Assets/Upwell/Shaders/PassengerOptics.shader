Shader "Hidden/Upwell/Passenger optics" {
    Properties { _MainTex("Camera frame",2D)="white"{} }
    SubShader { Cull Off ZWrite Off ZTest Always
        Pass {
            CGPROGRAM
            #pragma vertex vert_img
            #pragma fragment frag
            #pragma target 3.0
            #include "UnityCG.cginc"
            sampler2D _MainTex, _CameraDepthNormalsTexture;
            UNITY_DECLARE_DEPTH_TEXTURE(_CameraDepthTexture);
            float4 _MainTex_TexelSize;float _FocusDistance,_UpwellSimplifiedOptics,_UpwellContactShading;
            float Eye(float2 uv){return LinearEyeDepth(SAMPLE_DEPTH_TEXTURE(_CameraDepthTexture,uv));}
            float3 Position(float2 uv,float d){return float3((uv*2-1)*d/float2(UNITY_MATRIX_P._m00,UNITY_MATRIX_P._m11),-d);}
            half4 frag(v2f_img i):SV_Target{
                float2 uv=i.uv;half3 scene=tex2D(_MainTex,uv).rgb;
                float2 du=uv;
                #if UNITY_UV_STARTS_AT_TOP
                if(_MainTex_TexelSize.y<0)du.y=1-du.y;
                #endif
                float depth=100,oc=0;
                if(_UpwellSimplifiedOptics<.5&&(_FocusDistance>0||_UpwellContactShading>.5))depth=Eye(du);
                if(_FocusDistance>0&&_UpwellSimplifiedOptics<.5){
                    float blur=saturate((depth-_FocusDistance-.10)/max(depth,.03))*2.55;
                    float2 off=abs(_MainTex_TexelSize.xy)*blur;
                    scene=(scene*4+tex2D(_MainTex,uv+off).rgb+tex2D(_MainTex,uv-off).rgb+tex2D(_MainTex,uv+float2(off.x,-off.y)).rgb+tex2D(_MainTex,uv+float2(-off.x,off.y)).rgb)*.125;
                }
                if(depth<10 && _UpwellContactShading>.5){
                    float unused;float3 n;DecodeDepthNormal(tex2D(_CameraDepthNormalsTexture,du),unused,n);
                    float3 at=Position(du,depth);float2 radius=float2(UNITY_MATRIX_P._m00,UNITY_MATRIX_P._m11)*.075/max(depth,.2);
                    const float2 taps[10]={float2(1,0),float2(.32,.95),float2(-.81,.59),float2(-.81,-.59),float2(.31,-.95),float2(.36,.18),float2(-.06,.41),float2(-.37,.11),float2(-.25,-.34),float2(.23,-.31)};
                    [unroll] for(int k=0;k<10;k++){
                        float2 q=du+taps[k]*radius;float3 delta=Position(q,Eye(q))-at;
                        float dist=length(delta);oc+=saturate((dot(n,delta)-.009)/(dist+.006))*saturate(1-dist/.25);
                    }
                }
                scene*=1-min(.35,oc*.13);
                // A bounded photographic shoulder preserves the painted instrument and broad sunlit ceramic highlights.
                half3 exposed=max(scene*.87,0);
                scene=saturate((exposed*(2.51*exposed+.03))/(exposed*(2.43*exposed+.59)+.14));
                float2 c=uv-.5;scene*=1-.075*dot(c,c);
                return half4(scene,1);
            }
            ENDCG
        }
    }
}
