Shader "Upwell/Sealed capillary fluid" {
    SubShader {
        Tags { "Queue"="Transparent-35" "RenderType"="Transparent" "IgnoreProjector"="True" }
        GrabPass { "_UpwellCellBackground" }
        Pass {
            Tags { "LightMode"="ForwardBase" }
            Cull Back ZWrite Off ZTest LEqual
            CGPROGRAM
            #pragma target 3.0
            #pragma vertex vert
            #pragma fragment frag
            #include "UnityCG.cginc"
            #include "Lighting.cginc"
            sampler2D _UpwellCellBackground;
            float4 _CellCenter, _CellRight, _CellUp, _CellFront, _Chamber, _GasCenter;
            float4 _UpwellSun,_UpwellPracticalState;float _UpwellSolarPower;
            float _Radii[9];
            struct VertexOutput { float4 position:SV_POSITION;float3 world:TEXCOORD0;float4 grab:TEXCOORD1; };
            VertexOutput vert(appdata_base v) {
                VertexOutput o;
                o.position=UnityObjectToClipPos(v.vertex);
                o.world=mul(unity_ObjectToWorld,v.vertex).xyz;
                o.grab=ComputeGrabScreenPos(o.position);
                return o;
            }
            float3 inCell(float3 v) {
                return float3(dot(v,_CellRight.xyz),dot(v,_CellUp.xyz),dot(v,_CellFront.xyz));
            }
            half4 frag(VertexOutput input):SV_Target {
                float3 direction=normalize(input.world-_WorldSpaceCameraPos), ray=inCell(direction);
                float3 origin=inCell(_WorldSpaceCameraPos-_CellCenter.xyz);
                float radius=_Chamber.x, halfDepth=.5*_Chamber.y;
                float A=dot(ray.xy,ray.xy), B=dot(origin.xy,ray.xy), C=dot(origin.xy,origin.xy)-radius*radius;
                float entry=0, exitDistance=1e5;
                if(A>.000001) {
                    float discriminant=B*B-A*C;clip(discriminant);
                    float s=sqrt(max(0,discriminant));
                    entry=max(entry,(-B-s)/A);exitDistance=min(exitDistance,(-B+s)/A);
                } else {clip(-C);}
                if(abs(ray.z)>.00001) {
                    float2 t=(float2(-halfDepth,halfDepth)-origin.z)/ray.z;
                    entry=max(entry,min(t.x,t.y));exitDistance=min(exitDistance,max(t.x,t.y));
                } else {clip(halfDepth-abs(origin.z));}
                float lengthM=exitDistance-entry;clip(lengthM-.00001);
                float water=.00032,closest=100,lastWet=1,boundary=0,internal=0,rimWall=0;
                float3 interfaceN=_CellFront.xyz;float3 first=origin+ray*entry;
                float2 at=first.xy,bend=0;float travelSign=ray.z<0?-1:1;
                float dz=lengthM*max(.001,abs(ray.z))/20.;
                float3 throughWater=refract(ray,float3(0,0,-travelSign),1./1.333);
                float2 airSlope=ray.xy/max(.001,abs(ray.z)),wetSlope=throughWater.xy/max(.001,abs(throughWater.z));
                float antialias=clamp(.85*length(fwidth(first.xy/radius)),.001,.038);
                [loop]for(int i=0;i<20;i++) {
                    float3 pos=float3(at+(lerp(airSlope,wetSlope,lastWet)+bend)*dz*.5,first.z+travelSign*dz*(i+.5));
                    float z=pos.z/(halfDepth*_Chamber.w);float2 plane=pos.xy/(radius*_Chamber.z);
                    float zCell=saturate(.5+.5*z)*8.;int layer=clamp((int)zCell,0,7);
                    float2 radial=plane-_GasCenter.xy;
                    float r=lerp(_Radii[layer],_Radii[layer+1],zCell-layer);
                    float sd=length(radial)-r;
                    float wet=smoothstep(-antialias,antialias,sd);
                    if(abs(z)>=1.||dot(plane,plane)>=1.)wet=1;
                    float2 d=radial/max(.0001,length(radial));
                    float slope=-4.*(_Radii[layer+1]-_Radii[layer])*(radius*_Chamber.z)/(halfDepth*_Chamber.w);
                    float3 normal=normalize(float3(d,slope));
                    if(abs(sd)<closest) {
                        closest=abs(sd);
                        interfaceN=normal.x*_CellRight.xyz+normal.y*_CellUp.xyz+normal.z*_CellFront.xyz;
                    }
                    if(i>0&&abs(wet-lastWet)>.30){
                        float3 incoming=normalize(float3(lerp(airSlope,wetSlope,lastWet)+bend,travelSign));
                        float3 facing=dot(normal,incoming)<0?normal:-normal;
                        float3 transmitted=refract(incoming,facing,lastWet>.5?1.333:1./1.333);
                        if(dot(transmitted,transmitted)<.001)internal=1;
                        if(transmitted.z*travelSign>.08)bend=clamp(transmitted.xy/abs(transmitted.z)-lerp(airSlope,wetSlope,wet),-.80,.80);
                        boundary=max(boundary,abs(wet-lastWet)*pow(1-saturate(abs(dot(facing,incoming))),2.));
                    }
                    float2 stepSlope=lerp(airSlope,wetSlope,wet)+bend;
                    water+=wet*dz*sqrt(1.+dot(stepSlope,stepSlope));
                    at+=stepSlope*dz;lastWet=wet;
                    rimWall=max(rimWall,smoothstep(.991,1.012,length(at)/radius));
                }
                float3 transmission=exp(-water*float3(54.,16.,12.5));
                float edge=1.-smoothstep(antialias*.45,.019+antialias,closest);
                float2 lookup=at+float2(dot(interfaceN,_CellRight.xyz),dot(interfaceN,_CellUp.xyz))*edge*.002;
                lookup*=min(1.,radius*.997/max(.00001,length(lookup)));
                float3 rear=_CellCenter.xyz+_CellRight.xyz*lookup.x+_CellUp.xyz*lookup.y+_CellFront.xyz*(first.z+20*travelSign*dz);
                float4 screen=ComputeGrabScreenPos(UnityWorldToClipPos(rear));float2 uv=screen.xy/screen.w;
                float2 disperse=bend*.0006*edge;
                half3 background=half3(tex2D(_UpwellCellBackground,uv+disperse).r,tex2D(_UpwellCellBackground,uv).g,tex2D(_UpwellCellBackground,uv-disperse).b);
                half3 radiance=background*transmission+float3(.020,.095,.082)*(1-transmission);
                float3 solar=inCell(_UpwellSun.xyz);
                float incident=saturate(_UpwellSolarPower)*max(0,solar.z);
                float3 keyLight=normalize(float3(.23,.39,1)+2.4*incident*solar);
                float keyEnergy=.11+.31*saturate(_UpwellPracticalState.y)+.52*incident;
                float2 fromGas=(lookup/radius-keyLight.xy*halfDepth/radius*.50/max(.42,abs(keyLight.z)))/_Chamber.z-_GasCenter.xy;
                float wall=length(fromGas)-_Radii[4],shoulder=clamp(_Radii[4]-_Radii[1],.017,.086);
                float band=max(.009,antialias*1.5);
                float toward=.32+.68*smoothstep(-.25,.90,dot(normalize(fromGas+.00001),normalize(keyLight.xy+.0001)));
                float focalDist=(wall-shoulder*.37)/(band+.16*shoulder),shadeDist=(wall+shoulder*.44)/(band+.50*shoulder);
                radiance*=1+keyEnergy*toward*(.43*exp(-focalDist*focalDist)-.19*exp(-shadeDist*shadeDist));
                radiance=lerp(radiance,float3(.026,.058,.055)+background*.14,rimWall*.81);
                float3 n=dot(interfaceN,-direction)<0?-interfaceN:interfaceN;
                float3 reflected=reflect(direction,n);
                half3 env=DecodeHDR(UNITY_SAMPLE_TEXCUBE_LOD(unity_SpecCube0,reflected,1.),unity_SpecCube0_HDR);
                float spec=pow(saturate(dot(reflected,normalize(_WorldSpaceLightPos0.xyz))),52.);
                float fresnel=.02+.98*pow(1-saturate(dot(n,-direction)),5.);
                float3 environment=lerp(env,lerp(env,float3(.016,.033,.031),.46+.22*max(0,-dot(n,_CellUp.xyz))),internal);
                radiance=lerp(radiance,environment,min(.91,edge*(.36+.53*fresnel)+.52*boundary+.42*internal));
                float contactHighlight=exp(-closest/(.002+antialias*.46));
                radiance+=contactHighlight*(float3(.52,.69,.64)*(.09+.48*fresnel)+.15*_LightColor0.rgb*spec);
                return half4(radiance,1);
            }
            ENDCG
        }
    }
}
