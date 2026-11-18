Shader "Upwell/Carriage finish" {
    Properties {
        _MainTex ("Surface", 2D) = "white" {}
        _Color ("Base tint", Color) = (1,1,1,1)
        _Metallic ("Metallic", Range(0,1)) = 0.15
        _Roughness ("Roughness", Range(0,1)) = 0.45
        _RoughMap ("Roughness map", 2D) = "white" {}
        _MappedRoughness ("Mapped roughness", Range(0,1)) = 0
        [Normal] _BumpMap ("Normal", 2D) = "bump" {}
        _NormalStrength ("Normal depth", Range(0,1)) = 0.58
        _Emission ("Emission", Range(0,5)) = 0
        _Instrument ("Display", Range(0,1)) = 0
        [HideInInspector] _OpalCircuit ("Switched diffuser circuits",Float)=0
        _Weave ("Textile weave", Range(0,1)) = 0
        _DisplayTint ("Display tint", Color) = (1,1,1,1)
        [HideInInspector] _FinishActive("Registered finish",Float)=0
        [HideInInspector] _FinishEligible("Surface accepts registration",Float)=1
        [HideInInspector] _FinishMap("Registered detail",2D)="grey"{}
        [HideInInspector] _FinishDepth("Registered surface depth",2D)="black"{}
        [HideInInspector] _Cull("Face culling",Float)=2
    }
    SubShader {
        Tags { "RenderType"="Opaque" }
        Cull [_Cull]
        LOD 300
        CGPROGRAM
        #pragma surface surf Standard fullforwardshadows addshadow vertex:HardwareVertex
        #pragma target 3.0
        #include "UnityStandardUtils.cginc"
        #include "CabinHardware.cginc"
        #include "CabinDaylight.cginc"
        sampler2D _MainTex, _RoughMap, _BumpMap;
        sampler2D _FinishMap, _FinishDepth;
        float4x4 _RestProjector;float _FinishActive,_UpwellFinishWeight;
        fixed4 _Color, _DisplayTint;
        half _Metallic, _Roughness, _MappedRoughness, _NormalStrength, _Emission, _Instrument, _Weave;
        half _OpalCircuit;float4 _UpwellPracticalState,_UpwellRepeater;
        half _CabinSoftPanel;
        struct Input { float2 uv_MainTex; float4 color : COLOR; float3 worldPos; float3 worldNormal; INTERNAL_DATA float4 cableMetric; fixed facing:VFACE; };
        void HardwareVertex(inout appdata_full v,out Input o){UNITY_INITIALIZE_OUTPUT(Input,o);o.cableMetric=v.texcoord2;}
        void surf (Input i, inout SurfaceOutputStandard o) {
            fixed3 color = tex2D(_MainTex, i.uv_MainTex).rgb * _Color.rgb;
            half ao = saturate(i.color.r);
            color *= lerp(1, _DisplayTint.rgb, _Instrument);
            o.Albedo = color * lerp(.74, 1, ao);
            o.Metallic = _Metallic;
            o.Smoothness = 1 - lerp(_Roughness, tex2D(_RoughMap,i.uv_MainTex).r, _MappedRoughness);
            o.Normal = UnpackScaleNormal(tex2D(_BumpMap,i.uv_MainTex), _NormalStrength);
            float3 p=mul(unity_WorldToObject,float4(i.worldPos,1)).xyz;
            float2 loom=float2(dot(p,float3(618,164,383)),dot(p,float3(117,593,421)));
            float2 phase=loom*6.2831853;float2 filter=saturate(1-fwidth(loom)*.85);
            half relief=dot(cos(phase)*filter,float2(.54,.46));
            o.Albedo*=1+_Weave*relief*.17;
            o.Normal=normalize(o.Normal+float3(sin(phase)*filter*_Weave*.085,0));
            o.Normal*=i.facing<0?-1:1;
            o.Smoothness=saturate(o.Smoothness-_Weave*.11);
            if(_FinishActive>.5 && _UpwellFinishWeight>.001) {
                float4 cp=mul(_RestProjector,float4(p,1));
                float2 uv=.5+.5*cp.xy/max(.001,cp.w);
                if(cp.w>.01 && all(uv>0) && all(uv<1)) {
                    float2 bytes=floor(tex2D(_FinishDepth,uv).rg*255+.5);
                    float meters=dot(bytes,float2(2.56,.01));
                    float tolerance=.022+.0095*cp.w;
                    float weight=meters>.001?(1-smoothstep(tolerance,tolerance*1.72,abs(meters-cp.w)))*_UpwellFinishWeight:0;
                    float3 logGain=clamp((tex2D(_FinishMap,uv).rgb*255-128)/82,-1.2,1.2);
                    o.Albedo*=exp2(logGain*weight);
                    o.Smoothness=saturate(o.Smoothness+dot(logGain,float3(.3333,.3333,.3333))*.035*weight);
                }
            }
            o.Occlusion = lerp(.45, 1, ao);
            CabinContact(p,i.cableMetric,i.uv_MainTex,o.Albedo,o.Smoothness,o.Occlusion,o.Normal);
            if(_CabinSoftPanel>.5){
                float3 rest=mul(_CabinRest,float4(p,1)).xyz;
                float2 piece=clamp(floor((rest.zy-float2(-.965,1.275))/float2(.48,.374)+.5),0,float2(4,1));
                float2 centre=float2(-.965,1.275)+piece*float2(.48,.374);
                float2 cut=clamp(.5-(rest.zy-centre)/float2(.465,.353),.0014,.9986);
                float pattern=piece.x==3&&piece.y==0?5:fmod(piece.x*3+piece.y*2,5);
                float2 uvCut=(float2(fmod(pattern,3),floor(pattern/3))+cut)/float2(3,2);
                half4 pad=tex2D(_RoughMap,float2(uvCut.x,1-uvCut.y));
                pad.a=saturate((pad.a-.502)*2.008);
                half faceWeight=smoothstep(-2.135,-2.098,rest.x);
                o.Albedo=half3(.063,.091,.099)*lerp(.74,1,ao)*lerp(half3(1,1,1),half3(1.13,1.11,1.07)*(pad.b/.67),faceWeight);
                o.Albedo=lerp(o.Albedo,half3(.238,.251,.219),pad.a*faceWeight);
                float2 ds=2*pad.rg-1;float3 slope=float3(0,-ds.y,ds.x)*faceWeight;
                float3 ts=WorldNormalVector(i,float3(1,0,0)),bs=WorldNormalVector(i,float3(0,1,0)),ns=WorldNormalVector(i,float3(0,0,1));
                o.Normal=normalize(half3(0,0,1)+float3(dot(slope,ts),dot(slope,bs),dot(slope,ns)));
            }
            half circuit=1;
            if(_OpalCircuit>.5&&_OpalCircuit<1.5){
                float3 p=i.worldPos;
                if(p.z>1.92&&p.z<5.84&&p.y>2.14)circuit=_UpwellPracticalState.x;
                if(p.x>1.83&&p.x<2.27&&p.y>1.92&&p.y<2.04&&p.z< -2.95&&p.z> -4.18)circuit=_UpwellPracticalState.z;
            }else if(_OpalCircuit>1.5&&i.worldPos.x>.633&&i.worldPos.x<.8&&i.worldPos.z>4.90&&i.worldPos.z<5.19&&i.worldPos.y>1.08&&i.worldPos.y<1.22){
                float x=i.worldPos.x;
                circuit=x<.673?_UpwellRepeater.x:x<.715?_UpwellRepeater.y:x<.758?_UpwellRepeater.z:_UpwellRepeater.w;
            }
            half ambientFactor=1;
            half3 apertureLight=CabinDaylight(i.worldPos,WorldNormalVector(i,o.Normal),ambientFactor);
            o.Emission = color * _Emission * circuit+o.Albedo*(1-o.Metallic)*apertureLight*o.Occlusion;
            o.Occlusion*=ambientFactor;
            o.Alpha = 1;
        }
        ENDCG
    }
    Fallback "Standard"
}
