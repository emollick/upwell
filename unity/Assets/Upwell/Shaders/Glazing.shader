Shader "Upwell/Laminated glazing" {
    Properties { _Color("Edge tint",Color)=(.59,.75,.79,.05) _OpticalDepth("Optical depth",Range(0,.6))=.0014 _CabinFilm("Electrochromic coating",Float)=0 }
    SubShader {
        Tags { "Queue"="Transparent" "RenderType"="Transparent" }
        Blend SrcAlpha OneMinusSrcAlpha
        ZWrite Off
        Cull Off
        Pass { Tags {"LightMode"="ForwardBase"}
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma target 3.0
            #include "UnityCG.cginc"
            #include "Lighting.cginc"
            struct v2f {float4 pos:SV_POSITION; float3 view:TEXCOORD0; float3 n:TEXCOORD1;};
            fixed4 _Color;float _OpticalDepth,_UpwellSolarFilm,_CabinFilm;float4 _CabinGlassOrigin;
            sampler2D _UpwellGlassPanel,_UpwellGlassFeed;float _UpwellGlassPanelGain,_UpwellGlassPanelPage;float4 _UpwellPracticalState;
            float3 RoomRay(float3 pos,float3 ray){
                if(_CabinGlassOrigin.w<.5)return ray;
                float3 centre=_CabinGlassOrigin.xyz;
                float3 nearCorner=float3(-2.18,.025,centre.z-1.90),farCorner=float3(2.18,2.60,centre.z+1.90);
                float3 walls=lerp(nearCorner,farCorner,step(0,ray));
                float3 distanceToWall=(walls-pos)*(step(0,ray)*2-1)/max(abs(ray),.0001);
                return pos+ray*clamp(min(distanceToWall.x,min(distanceToWall.y,distanceToWall.z)),0,6)-centre;
            }
            // Coordinates here use the survey axes of the Blender source.
            float3 Diffuser(float3 p,float3 ray,float side){
                float3 n=float3(-side*.8,-.6,0),along=float3(0,0,side);
                float3 centre=float3(side*1.96,2.30,0)+n*.041;
                float facing=-dot(n,ray),t=dot(p-centre,n)/max(.001,facing);
                float3 hit=p+t*ray-centre;
                float station=hit.z< -3.80?-4.73:-2.87;
                hit.z-=station;
                float2 at=float2(dot(hit,along),dot(hit,cross(n,along)));
                float halfWidth=(station< -3.8 && side<0) ? .279 : .269;
                float2 excess=abs(at)-float2(halfWidth-.007,.0115);
                float edge=length(max(excess,0))+min(max(excess.x,excess.y),0)-.007;
                float soft=.003+.003*clamp(t,0,6);
                float band=max(.7*fwidth(edge),soft),core=1-smoothstep(-band,band,edge);
                float spread=max(0,edge)/soft,skirt=exp(-spread*spread*.20);
                float pitch=(halfWidth*2+.022)/9;
                float seam=abs(frac(at.x/pitch)-.5)*pitch;
                float seamAA=max(.0005,.7*fwidth(at.x));
                float web=1-.48*(1-smoothstep(.0009-seamAA,.0009+seamAA,seam))*step(abs(at.x),pitch*4);
                float housing=.012*(1-smoothstep(.023,.060,edge));
                float energy=(.90*core+.065*skirt)*web+housing;
                return float3(1.64,1.52,1.36)*step(.5,_UpwellPracticalState.x)*energy*step(.001,facing)*step(.01,t);
            }
            float3 Sources(float3 pos,float3 ray,float3 room){
                pos.z=-pos.z;ray.z=-ray.z;
                [unroll] for(int i=0;i<2;i++){
                    float side=i==0?-1:1;
                    room=max(room,Diffuser(pos,ray,side));
                }
                float3 n=normalize(float3(0,.58,.815)),u=float3(0,n.z,-n.y);
                float3 centre=float3(.716,1.198,-5.104)+n*.0606;
                float facing=-dot(n,ray),t=dot(pos-centre,n)/max(.001,facing);
                float3 hit=pos+t*ray-centre;
                float2 uv=float2(hit.x/.675,dot(hit,u)/.211)+.5;
                float2 aa=max(fwidth(uv),.001),mask=smoothstep(-aa,aa,min(uv,1-uv));
                if(facing>.001&&t>.01&&mask.x*mask.y>.001){
                    float3 ink=tex2D(_UpwellGlassPanel,saturate(uv)).rgb;
                    float2 feedUv=(_UpwellGlassPanelPage>.5&&_UpwellGlassPanelPage<1.5)?
                        (uv-float2(.034,.12))/float2(.934,.69):(uv-float2(.57,.44))/float2(.402,.343);
                    if(all(feedUv>=0)&&all(feedUv<=1))ink=tex2D(_UpwellGlassFeed,feedUv).rgb*.85;
                    room=lerp(room,ink*_UpwellGlassPanelGain*2.3,mask.x*mask.y);
                }
                return room;
            }
            v2f vert(appdata_base v) {v2f o; o.pos=UnityObjectToClipPos(v.vertex); o.n=UnityObjectToWorldNormal(v.normal); o.view=_WorldSpaceCameraPos-mul(unity_ObjectToWorld,v.vertex).xyz; return o;}
            fixed4 frag(v2f i):SV_Target {
                float rim=pow(1-saturate(abs(dot(normalize(i.view),normalize(i.n)))),4);
                float3 coating=lerp(float3(.20,.27,.30),_Color.rgb,saturate(rim+2.5*_OpticalDepth));
                if(_OpticalDepth>.08){
                    float3 n=normalize(i.n),v=normalize(i.view);if(dot(n,v)<0)n=-n;
                    float3 r=reflect(-v,n);half3 environment=DecodeHDR(UNITY_SAMPLE_TEXCUBE_LOD(unity_SpecCube0,r,1.2),unity_SpecCube0_HDR);
                    float glint=pow(saturate(dot(r,normalize(_WorldSpaceLightPos0.xyz))),167);
                    coating=_Color.rgb*.21+environment*(.60+rim*.32)+float3(.009,.048,.048)*(1-rim)+_LightColor0.rgb*glint*.53;
                }
                float film=_CabinFilm*_UpwellSolarFilm;
                if(_OpticalDepth<.015){
                    float3 v=normalize(i.view),n=normalize(i.n);if(dot(n,v)<0)n=-n;
                    float cosine=saturate(dot(v,n));
                    float3 reflected=reflect(-v,n),through=refract(-v,n,1./1.51);
                    float ct=max(.27,abs(dot(through,n)));
                    float3 pos=_WorldSpaceCameraPos-i.view;
                    float3 shear=.032*(through-n*dot(through,n))/ct;
                    half3 r0=DecodeHDR(UNITY_SAMPLE_TEXCUBE_LOD(unity_SpecCube0,RoomRay(pos,reflected),.12),unity_SpecCube0_HDR);
                    half3 r1=DecodeHDR(UNITY_SAMPLE_TEXCUBE_LOD(unity_SpecCube0,RoomRay(pos+shear,reflected),.58),unity_SpecCube0_HDR);
                    float rs=(cosine-1.51*ct)/(cosine+1.51*ct),rp=(1.51*cosine-ct)/(1.51*cosine+ct);
                    bool saloonPane=_CabinGlassOrigin.w>.5&&pos.z>1.90&&abs(n.y)<.30;
                    if(saloonPane&&_WorldSpaceCameraPos.z>1.90){
                        r0=Sources(pos,reflected,r0);r1=Sources(pos+shear,reflected,r1);
                    }
                    float faceReflectance=saloonPane?.022:.011;
                    float reflection=clamp(faceReflectance+.91*(.5*(rs*rs+rp*rp)-.0413),faceReflectance,.67);
                    float absorption=.0035/ct+.49*film;
                    float a=clamp(reflection+absorption,.006,.88);
                    return half4(((r0*.74+r1*half3(.238,.262,.267)*(1-.70*film))*reflection+half3(.23,.33,.34)*absorption*(1-.82*film))/a,a);
                }
                return float4(lerp(coating,float3(.014,.033,.043),film),_OpticalDepth+rim*.15+.55*film);
            }
            ENDCG
        }
    }
}
