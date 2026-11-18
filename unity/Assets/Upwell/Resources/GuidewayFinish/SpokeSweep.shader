Shader "Upwell/Contact roller exposure" {
    Properties { _GuideRadius ("Contact radius",Float)=.214 }
    SubShader {
        Tags {"Queue"="Transparent" "RenderType"="Transparent"}
        Cull Off ZWrite Off
        CGPROGRAM
        #pragma target 3.0
        #pragma surface surf Standard alpha:fade vertex:GuideVertex
        float _GuideRadius,_UpwellGuideShutter;
        struct Input{float3 guideP;float4 color:COLOR;fixed facing:VFACE;};
        void GuideVertex(inout appdata_full v,out Input o){UNITY_INITIALIZE_OUTPUT(Input,o);o.guideP=v.vertex.xyz;}
        float Integral(float cycle,float duty){return floor(cycle)*duty+min(frac(cycle),duty);}
        void surf(Input i,inout SurfaceOutputStandard o){
            float radius=length(i.guideP.xy),tick=step(.018,abs(i.guideP.z)),n=lerp(6,3,tick);
            float duty=clamp(lerp(.020,.019,tick)*n/(6.2831853*max(.015,radius)),.015,.68);
            float phase=atan2(i.guideP.y,i.guideP.x)*n/6.2831853+.5*duty;
            float shutter=max(fwidth(phase),_UpwellGuideShutter*n/(_GuideRadius*6.2831853));
            float cover=(Integral(phase+.5*shutter,duty)-Integral(phase-.5*shutter,duty))/max(.001,shutter);
            o.Alpha=lerp(cover,duty,smoothstep(1.5,3.5,shutter));clip(o.Alpha-.004);
            o.Albedo=i.color.rgb;o.Metallic=.65;o.Smoothness=.58;o.Normal=float3(0,0,i.facing<0?-1:1);
        }
        ENDCG
    }
    Fallback Off
}
