Shader "Upwell/Orbital structure" {
    Properties {
        _Color ("Surface tint", Color)=(1,1,1,1)
        _MainTex ("Colour and surface markings", 2D)="white"{}
        _Metallic ("Metalness", Range(0,1))=.4
        _Glossiness ("Smoothness", Range(0,1))=.52
        _EmissionMap ("Emitter texture", 2D)="white"{}
        [HDR] _EmissionColor ("Local lights", Color)=(0,0,0,1)
        _AsterBounce ("Diffuse irradiance from adjoining hull and collectors", Range(0,1))=.3
        [HideInInspector] _ValleyFinish("Interior finish",Float)=0
        [HideInInspector] _ValleyTime("Hydraulic time",Float)=0
    }
    SubShader {
        Tags {"RenderType"="Opaque"} LOD 250
        CGPROGRAM
        #pragma surface surf Standard fullforwardshadows addshadow vertex:PressureFace finalcolor:EnclosedColor
        #pragma target 3.0
        sampler2D _MainTex,_EmissionMap;fixed4 _Color;half4 _EmissionColor;
        half _Metallic,_Glossiness,_AsterBounce;
        float _ValleyFinish,_ValleyTime;
        struct Input {float2 uv_MainTex;float3 worldNormal;float3 landPosition;};
        void PressureFace(inout appdata_full v,out Input i){
            UNITY_INITIALIZE_OUTPUT(Input,i);
            i.landPosition=v.vertex.xyz*float3(-1.,1.,1.);
        }
        void EnclosedColor(Input i,SurfaceOutputStandard s,inout fixed4 c){
            if(_ValleyFinish>.5){
                #ifdef UNITY_PASS_FORWARDADD
                c.rgb=0;
                #else
                float3 q=i.landPosition;
                // Reuse Standard's normal interpolant; the lens's survey position
                // is the only extra interpolator on the WebGL2 forward pass.
                float3 n=normalize(mul(i.worldNormal,(float3x3)unity_ObjectToWorld))*float3(-1,1,1);
                float a=atan2(q.x,q.z),sector=floor(a/2.0943951+.5)*2.0943951;
                float3 radial=float3(sin(sector),0,cos(sector)),side=float3(cos(sector),0,-sin(sector));
                float3 key=normalize(-radial*.79+side*.64+float3(0,-.41,0));
                float wash=.78+.15*sin(q.y*.21+.64)+.059*cos(q.y*.49+a*2);
                float roof=saturate(dot(n,-normalize(float3(q.x,0,q.z)+float3(0,0,1.e-5))));
                float gate=.99-.17*smoothstep(6.3,7.23,length(q.xz))*(1-roof);
                float3 received=s.Albedo*(float3(.29,.34,.355)+float3(.87,.75,.55)*saturate(dot(n,key))*wash)*gate;
                if(_ValleyFinish==2){
                    float stream=.146*sin(q.y*.31+.26)+.055*sin(q.y*.72-.48);
                    float offset=a-sector-stream;
                    received*=1.-.13*exp(-abs(offset-.18)*50.)-.12*exp(-abs(abs(offset)-.060)*53.);
                }else if(_ValleyFinish==3){
                    float along=q.y*80.,across=(a-sector)*577.6;
                    float crest=across*1.7+along*.53,wind=across*.71-along*1.21;
                    float cap=sin(crest+_ValleyTime*2.7)*sin(wind+_ValleyTime*.8);
                    cap*=1.-smoothstep(1.,3.14,max(fwidth(crest),fwidth(wind)));
                    float wakes=.56+.20*sin(along*.095+across*.13)+.19*cap;
                    received=lerp(float3(.018,.064,.069),float3(.112,.212,.196),wakes*.85);
                    received+=float3(.021,.034,.030)*pow(max(cap,0.),4.);
                }else if(_ValleyFinish==4)received+=float3(.030,.051,.053)*(.45+.55*roof);
                else if(_ValleyFinish==5)received=float3(.76,.54,.28)*(.83+.12*cos(q.y*8.));
                else if(_ValleyFinish==6){
                    received=lerp(float3(.087,.119,.133),float3(.225,.243,.223),smoothstep(1.2,7.3,length(q.xz)));
                    received*=.95+.05*cos(a*48.);
                }
                c.rgb=received;
                #endif
            }
        }
        void surf(Input i,inout SurfaceOutputStandard o){
            half3 albedo=tex2D(_MainTex,i.uv_MainTex).rgb*_Color.rgb;
            half3 normal=normalize(i.worldNormal);
            half broad=.29+.41*saturate(dot(normal,normalize(half3(.47,.31,-.82))))+.30*(.5-.5*normal.y);
            o.Albedo=albedo;o.Metallic=_Metallic;o.Smoothness=_Glossiness;o.Alpha=1;
            o.Emission=tex2D(_EmissionMap,i.uv_MainTex).rgb*_EmissionColor.rgb+albedo*broad*_AsterBounce*half3(.81,.90,1);
        }
        ENDCG
    }
    FallBack "Standard"
}
