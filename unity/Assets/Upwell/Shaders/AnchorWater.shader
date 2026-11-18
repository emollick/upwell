Shader "Upwell/Equatorial Atlantic" {
    SubShader{ Tags {"Queue"="Transparent" "RenderType"="Transparent"} ZWrite Off Cull Off Blend SrcAlpha OneMinusSrcAlpha
        Pass{
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma target 3.0
            #include "UnityCG.cginc"
            #include "HarborWater.cginc"
            float4 _UpwellSun,_SkyForward,_SkyUp,_SkyRight;float _UpwellSolarPower,_UpwellWaterTime;
            sampler2D _UpwellCurrentSky;
float wellFootprint(float2 p){
  return (1.-smoothstep(3.35,4.06,abs(p.x)))*(1.-smoothstep(6.76,7.55,abs(p.y-.11)));
}
float3 wellWave(float2 p,float t){
  // Transverse and longitudinal oscillations of the seven by fourteen metre wet well.
  float a=.887*p.x,b=.443*(p.y-.11),c=cos(2.94*t+.09*p.y),s=sin(2.08*t-.07*p.x);
  return float3(.145*cos(a)*c+.086*cos(b)*s,-.129*sin(a)*c,-.038*sin(b)*s);
}
float3 quayReflection(float3 sky,float2 p,float3 ray,float elevation){
  if(abs(p.x)>3.55||abs(p.y-.11)>7.08)return sky;
  float2 travel=(float2(3.55,7.08)-sign(ray.xz)*float2(p.x,p.y-.11))/max(abs(ray.xz),float2(.0005,.0005));
  float t=min(travel.x,travel.y),height=elevation+t*ray.y;
  if(height>6.79)return sky;
  float2 hit=p+t*ray.xz;float along=travel.x<travel.y?hit.y:hit.x;
  float wet=smoothstep(.38,2.53,height),seam=smoothstep(.035,.08,abs(frac((along+.45)/3.17)-.5));
  float3 concrete=lerp(float3(.021,.032,.031),float3(.115,.133,.123),wet)*(.78+.22*seam);
  return lerp(concrete,sky,smoothstep(6.24,6.79,height));
}
            struct v2f{float4 pos:SV_POSITION;float3 world:TEXCOORD0;float2 wave:TEXCOORD1;float crestHeight:TEXCOORD2;};
            void Swell(float2 x,float2 d,float period,float amp,inout float h,inout float2 slope){
                float k=6.283185/period,phase=k*dot(x,d)-sqrt(9.81*k)*_UpwellWaterTime+.51*sin(dot(x,float2(.045,.037))+.025*_UpwellWaterTime)+.33*sin(dot(x,float2(-.019,.026)));
                h+=amp*sin(phase);slope+=d*k*amp*cos(phase);
            }
            v2f vert(appdata_base v){v2f o;float3 p=v.vertex.xyz;float h=0;float2 slope=0;float2 basin=float2(p.x,-p.z);
                Swell(basin,float2(.86,.51),18.3,.23,h,slope);Swell(basin,float2(.68,-.73),8.7,.10,h,slope);Swell(basin,float2(.96,-.27),4.1,.04,h,slope);Swell(basin,float2(.4,.916),2.06,.019,h,slope);Swell(basin,float2(.78,.626),35.7,.29,h,slope);Swell(basin,float2(-.42,.907),12.3,.075,h,slope);Swell(basin,float2(.99,-.14),6.48,.053,h,slope);p.y=h;o.crestHeight=h;
                float well=wellFootprint(basin);
                if(well>.001){p.y=lerp(h,.38*h+wellWave(basin,_UpwellWaterTime).x,well);o.crestHeight=p.y;}
                o.pos=UnityObjectToClipPos(float4(p,1));o.world=mul(unity_ObjectToWorld,float4(p,1)).xyz;o.wave=slope;return o;}
            float HashSea(float2 p){float3 q=frac(p.xyx*.1031);q+=dot(q,q.yzx+33.33);return frac((q.x+q.y)*q.z);}
            float SeaNoise(float2 p){
                float2 cell=floor(p),f=frac(p);f=f*f*(3-2*f);
                return lerp(lerp(HashSea(cell),HashSea(cell+float2(1,0)),f.x),lerp(HashSea(cell+float2(0,1)),HashSea(cell+1),f.x),f.y);
            }
      float dockDistance(float2 p){
        // Cross-section of the two surveyed concrete caissons and their end
        // aprons at the waterline. The central guide well remains flooded.
        float2 sides=abs(float2(abs(p.x)-10.42,p.y+11.))-float2(6.875,20.10);
        float2 front=abs(p-float2(0.,-19.03))-float2(3.725,12.06);
        float2 aft=abs(p-float2(0.,9.80))-float2(3.725,2.605);
        float a=length(max(sides,0.))+min(max(sides.x,sides.y),0.);
        float b=length(max(front,0.))+min(max(front.x,front.y),0.);
        float c=length(max(aft,0.))+min(max(aft.x,aft.y),0.);
        return min(a,min(b,c));
      }
      float3 waterDetail(float3 body,float3 lit,float2 p,float2 slope,float elevation,float3 sun,float direct,float t,float footprint){
        // A crest has a shorter path through the dyed water. Breakers leave
        // short windrows and attach a discontinuous lace of wash to the pier.
        float folds=SeaNoise(p*.14+float2(-.12*t,.04*t));
        float crest=smoothstep(.14,.70,elevation+.43*folds-.22);
        float litSlope=clamp(.48+dot(slope,sun.xz)*2.15+crest*.36,0.,1.);
        lit+=body*(.12+.61*direct)*litSlope+float3(.0015,.008,.009)*crest;
        float local=1.-smoothstep(95.,145.,length(p));
        float windFace=dot(slope,float2(.88,.47));
        float lip=1.-smoothstep(.045,.175,abs(elevation-(.30+.18*folds)));
        float mask=lip*smoothstep(.09,.25,windFace)*smoothstep(.44,.68,folds);
        float foam=.0,shade=1.;
        if(local>.001){
          float wall=dockDistance(p);
          float2 boat=(p-float2(-22.4,-18.8))/float2(1.22,3.02);
          float hull=(length(boat)-1.)*1.32;
          float nearest=max(0.,min(wall,hull));
          float reach=.18+.67*folds+.39*max(0.,elevation);
          foam=(1.-smoothstep(.09,reach,nearest))*(.34+.46*crest)*local;
          float sheltered=wellFootprint(p);
          if(sheltered>.001){
            float slosh=wellWave(p,t).x;
            float runup=smoothstep(-.13,.18,slosh+.15*elevation);
            float distanceToFace=max(wall,0.),reach=.27+1.10*runup;
            float backwash=.5+.5*cos(5.2*distanceToFace-1.83*t+.53*p.y+3.3*folds);
            float plume=(1.-smoothstep(.04,reach,distanceToFace))*(.20+.63*runup);
            plume+=.27*backwash*(1.-smoothstep(.40,1.65,distanceToFace))*smoothstep(.32,.77,folds);
            foam=max(foam,sheltered*plume);
            lit=lerp(lit,lit*float3(.68,.78,.76),sheltered*(1.-.72*runup));
          }
          float height=7.-elevation;
          float2 intercept=p+sun.xz*height/max(sun.y,.055);
          shade=lerp(.72,1.,smoothstep(-.8,2.8,dockDistance(intercept)));
        }
        float textureScale=1.-smoothstep(.08,.40,footprint);
        float streak=SeaNoise(float2(dot(p,float2(.89,.46))*.47-t*.10,dot(p,float2(-.46,.89))*1.61+.07*t));
        float cells=SeaNoise(p*3.94+float2(-.135*t,.16*t)+3.4*folds);
        float lace=smoothstep(.30,.63,streak+textureScale*(.42*cells-.19));
        float bubbles=clamp((.24*mask+foam)*lace,0.,.78);
        float3 foamLight=lerp(float3(.22,.33,.34),float3(.66,.72,.67),min(1.,.23+.79*direct*shade));
        return lerp(lit*lerp(1.,shade,.18),foamLight,bubbles);
      }
            float2 Packet(float2 p,float2 direction,float span,float amp,float offset,float footprint){
                float k=6.283185/span;
                float2 crossWind=float2(-direction.y,direction.x);
                float2 coord=float2(dot(p,direction)/(4.1*span),dot(p,crossWind)/(2.3*span))+.013*_UpwellWaterTime+offset;
                float2 base=floor(coord),weight=frac(coord);weight=weight*weight*(3-2*weight);float2 result=0;
                [unroll]for(int y=0;y<2;y++)[unroll]for(int x=0;x<2;x++){
                    float2 seed=base+float2(x,y);float noise=HashSea(seed+.29);
                    float2 dir=normalize(direction+crossWind*(noise-.5)*1.6);
                    float phase=k*dot(p,dir)-sqrt(9.81*k)*_UpwellWaterTime+HashSea(seed+8.31)*6.283185;
                    float blend=(x==0?1-weight.x:weight.x)*(y==0?1-weight.y:weight.y);
                    result+=dir*blend*(.30+HashSea(seed+19.84))*cos(phase);
                }return result*k*amp*exp(-.29*k*k*footprint*footprint);
            }
            half4 frag(v2f i):SV_Target{float3 view=normalize(_WorldSpaceCameraPos-i.world);float d=distance(_WorldSpaceCameraPos,i.world);float t=_UpwellWaterTime;
                float2 p=i.world.xz;float extent=max(length(ddx(p)),length(ddy(p)));
                float2 s=Packet(p,float2(.86,.51),18.3,.23,3.7,extent)+Packet(p,float2(.68,-.73),8.7,.116,17.6,extent)
                    +Packet(p,float2(.96,-.27),4.1,.055,44.3,extent)+Packet(p,float2(.40,.916),2.06,.028,8.2,extent)
                    +Packet(p,float2(.78,.626),35.7,.29,27.5,extent)+Packet(p,float2(-.42,.907),12.3,.10,13.2,extent)
                    +Packet(p,float2(.99,-.14),.68,.0083,32.8,extent);
                float2 basin=float2(p.x,-p.y);float well=wellFootprint(basin);
                if(well>.001){float2 mode=wellWave(basin,t).yz;s=lerp(s,.38*s+float2(mode.x,-mode.y),well);}
                float wakes=0,hullShade=1,eddies=SeaNoise(basin*.49+float2(-.17,.11)*t);
                float2 wakeSlope=0;harborWave(basin,t,extent,eddies,wakeSlope,wakes);s+=float2(wakeSlope.x,-wakeSlope.y);
                float3 n=normalize(float3(-s.x,1,-s.y));float f=.022+.978*pow(1-saturate(dot(n,view)),5);
                float3 reflection=reflect(-view,n);reflection.y=max(.009,reflection.y);float sky=saturate(reflection.y);
                float z=dot(reflection,_SkyForward.xyz);
                float2 ray=.5+.5*float2(dot(reflection,_SkyRight.xyz)/dot(_SkyRight.xyz,_SkyRight.xyz),dot(reflection,_SkyUp.xyz)/dot(_SkyUp.xyz,_SkyUp.xyz))/max(.001,z);
                float2 edge=saturate(min(ray,1-ray)*14);float capture=z>0?min(edge.x,edge.y):0;
                float3 environment=lerp(lerp(float3(.42,.48,.51),float3(.14,.30,.53),sky),tex2D(_UpwellCurrentSky,saturate(ray)).rgb,.77*capture);
                if(well>.001)environment=quayReflection(environment,basin,float3(reflection.x,reflection.y,-reflection.z),i.crestHeight);
                harborContact(basin,float3(reflection.x,reflection.y,-reflection.z),extent,eddies,environment,hullShade,wakes);
                float mass=.69*SeaNoise(p/124+float2(4,-.03*t))+.31*SeaNoise(p/43+7);
                float3 body=lerp(float3(.012,.041,.052),float3(.022,.066,.079),mass);
                float nh=saturate(dot(n,normalize(view+_UpwellSun.xyz)));float a=.0038;float disc=a/(3.1416*pow(max(.001,nh*nh*(a-1)+1),2));
                float3 lit=lerp(body,environment,f)+float3(1,.74,.46)*min(3,disc*.029)*_UpwellSolarPower;
                lit=waterDetail(body,lit,float2(p.x,-p.y),float2(s.x,-s.y),i.crestHeight,float3(_UpwellSun.x,_UpwellSun.y,-_UpwellSun.z),_UpwellSolarPower,t,extent);
                lit=lerp(lit*hullShade,lerp(float3(.26,.365,.36),float3(.66,.74,.70),_UpwellSolarPower),clamp(wakes,0.,.86));
                return float4(lit,(1-smoothstep(620,1110,d))*(1-smoothstep(800,1270,_WorldSpaceCameraPos.y-i.world.y)));}
            ENDCG
        }
    }
}
