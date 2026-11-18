import * as T from 'three';
import {harborWater} from './harbor-water.js';

const wellMotion=`float wellFootprint(vec2 p){
  return (1.-smoothstep(3.35,4.06,abs(p.x)))*(1.-smoothstep(6.76,7.55,abs(p.y-.11)));
}
vec3 wellWave(vec2 p,float t){
  // Transverse and longitudinal oscillations of the seven by fourteen metre wet well.
  float a=.887*p.x,b=.443*(p.y-.11),c=cos(2.94*t+.09*p.y),s=sin(2.08*t-.07*p.x);
  return vec3(.145*cos(a)*c+.086*cos(b)*s,-.129*sin(a)*c,-.038*sin(b)*s);
}`;


// Short gravity waves and capillary ripples are evaluated in dock coordinates.
// The mesh descends with the dock. Distant water belongs to the planet shader.
export function createAnchorSea(fleet){
  const geom=new T.PlaneGeometry(2,2,144,144);geom.rotateX(-Math.PI/2);
  const positions=geom.attributes.position;
  const radius=1150;
  const warp=x=>Math.sign(x)*(Math.abs(x)*.025+Math.abs(x)**2.75*.975)*radius;
  for(let i=0;i<positions.count;i++)positions.setXYZ(i,warp(positions.getX(i)),0,warp(positions.getZ(i)));
  positions.needsUpdate=true;geom.computeBoundingSphere();
  const uniforms={clock:{value:0},solar:{value:new T.Vector3(1,.15,-.2)},solarPower:{value:1},
    skyEnvironment:{value:null},skyBlue:{value:new T.Color(.24,.46,.66)},
    boatTug:{value:fleet.vessels[0]},boatPilot:{value:fleet.vessels[1]},boatSupply:{value:fleet.vessels[2]},
    boatBerth:{value:fleet.vessels[3]},pilotHistory:{value:fleet.trails[0]},supplyHistory:{value:fleet.trails[1]},harborSpeed:{value:fleet.speeds}};
  const mat=new T.ShaderMaterial({
    uniforms,transparent:true,depthWrite:false,side:T.FrontSide,
    vertexShader:`uniform float clock;varying vec3 pWorld;varying vec2 slope;varying float crestHeight;
      ${wellMotion}
      void swell(in vec2 p, in vec2 dir, in float lengthM, in float height, inout float y, inout vec2 derivative){
        float k=6.2831853/lengthM, phase=k*dot(p,dir)-sqrt(9.81*k)*clock;
        phase+=.51*sin(dot(p,vec2(.045,.037))+.025*clock)+.33*sin(dot(p,vec2(-.019,.026)));
        y+=height*sin(phase);derivative+=dir*(k*height)*cos(phase);
      }
      void main(){vec3 p=position;float y=0.;slope=vec2(0.);
        swell(p.xz,vec2(.86,.51),18.3,.23,y,slope);swell(p.xz,vec2(.68,-.73),8.7,.10,y,slope);
        swell(p.xz,vec2(.96,-.27),4.1,.040,y,slope);swell(p.xz,vec2(.40,.916),2.06,.019,y,slope);
        swell(p.xz,vec2(.78,.626),35.7,.29,y,slope);swell(p.xz,vec2(-.42,.907),12.3,.075,y,slope);
        swell(p.xz,vec2(.99,-.14),6.48,.053,y,slope);
        float well=wellFootprint(p.xz);if(well>.001)y=mix(y,.38*y+wellWave(p.xz,clock).x,well);
        crestHeight=y;p.y+=y;pWorld=(modelMatrix*vec4(p,1.)).xyz;gl_Position=projectionMatrix*viewMatrix*vec4(pWorld,1.);}`,
    fragmentShader:`uniform float clock,solarPower;uniform vec3 solar,skyBlue;uniform samplerCube skyEnvironment;varying vec3 pWorld;varying vec2 slope;varying float crestHeight;
      ${wellMotion}
      vec3 quayReflection(vec3 sky,vec2 p,vec3 ray,float elevation){
  if(abs(p.x)>3.55||abs(p.y-.11)>7.08)return sky;
  vec2 travel=(vec2(3.55,7.08)-sign(ray.xz)*vec2(p.x,p.y-.11))/max(abs(ray.xz),vec2(.0005));
  float t=min(travel.x,travel.y),height=elevation+t*ray.y;
  if(height>6.79)return sky;
  vec2 hit=p+t*ray.xz;float along=travel.x<travel.y?hit.y:hit.x;
  float wet=smoothstep(.38,2.53,height),seam=smoothstep(.035,.08,abs(fract((along+.45)/3.17)-.5));
  vec3 concrete=mix(vec3(.021,.032,.031),vec3(.115,.133,.123),wet)*(.78+.22*seam);
  return mix(concrete,sky,smoothstep(6.24,6.79,height));
}
      float hashSea(vec2 p){vec3 q=fract(vec3(p.xyx)*.1031);q+=dot(q,q.yzx+33.33);return fract((q.x+q.y)*q.z);}
      float swellNoise(vec2 p){
        vec2 i=floor(p),f=fract(p);f=f*f*(3.-2.*f);
        return mix(mix(hashSea(i),hashSea(i+vec2(1,0)),f.x),mix(hashSea(i+vec2(0,1)),hashSea(i+vec2(1)),f.x),f.y);
      }
      ${harborWater}
      float dockDistance(vec2 p){
        // Cross-section of the two surveyed concrete caissons and their end
        // aprons at the waterline. The central guide well remains flooded.
        vec2 sides=abs(vec2(abs(p.x)-10.42,p.y+11.))-vec2(6.875,20.10);
        vec2 front=abs(p-vec2(0.,-19.03))-vec2(3.725,12.06);
        vec2 aft=abs(p-vec2(0.,9.80))-vec2(3.725,2.605);
        float a=length(max(sides,0.))+min(max(sides.x,sides.y),0.);
        float b=length(max(front,0.))+min(max(front.x,front.y),0.);
        float c=length(max(aft,0.))+min(max(aft.x,aft.y),0.);
        return min(a,min(b,c));
      }
      vec3 waterDetail(vec3 body,vec3 lit,vec2 p,vec2 slope,float elevation,vec3 sun,float direct,float t,float footprint){
        // A crest has a shorter path through the dyed water. Breakers leave
        // short windrows and attach a discontinuous lace of wash to the pier.
        float folds=swellNoise(p*.14+vec2(-.12*t,.04*t));
        float crest=smoothstep(.14,.70,elevation+.43*folds-.22);
        float litSlope=clamp(.48+dot(slope,sun.xz)*2.15+crest*.36,0.,1.);
        lit+=body*(.12+.61*direct)*litSlope+vec3(.0015,.008,.009)*crest;
        float local=1.-smoothstep(95.,145.,length(p));
        float windFace=dot(slope,vec2(.88,.47));
        float lip=1.-smoothstep(.045,.175,abs(elevation-(.30+.18*folds)));
        float mask=lip*smoothstep(.09,.25,windFace)*smoothstep(.44,.68,folds);
        float foam=.0,shade=1.;
        if(local>.001){
          float wall=dockDistance(p);
          vec2 boat=(p-vec2(-22.4,-18.8))/vec2(1.22,3.02);
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
            lit=mix(lit,lit*vec3(.68,.78,.76),sheltered*(1.-.72*runup));
          }
          float height=7.-elevation;
          vec2 intercept=p+sun.xz*height/max(sun.y,.055);
          shade=mix(.72,1.,smoothstep(-.8,2.8,dockDistance(intercept)));
        }
        float textureScale=1.-smoothstep(.08,.40,footprint);
        float streak=swellNoise(vec2(dot(p,vec2(.89,.46))*.47-t*.10,dot(p,vec2(-.46,.89))*1.61+.07*t));
        float cells=swellNoise(p*3.94+vec2(-.135*t,.16*t)+3.4*folds);
        float lace=smoothstep(.30,.63,streak+textureScale*(.42*cells-.19));
        float bubbles=clamp((.24*mask+foam)*lace,0.,.78);
        vec3 foamLight=mix(vec3(.22,.33,.34),vec3(.66,.72,.67),min(1.,.23+.79*direct*shade));
        return mix(lit*mix(1.,shade,.18),foamLight,bubbles);
      }
      vec2 packet(vec2 x,vec2 dir,float span,float amp,float offset,float pix){
        // Independent, overlapping trains of waves. Each train carries a
        // different phase, period and direction and fades before the next one.
        float reach=span*3.7;
        vec2 coord=x/reach+vec2(offset,-.47*offset),base=floor(coord),f=fract(coord);
        vec2 blend=f*f*(3.-2.*f),gradient=vec2(0.);
        for(int j=0;j<2;j++)for(int i=0;i<2;i++){
          vec2 corner=vec2(float(i),float(j)),key=base+corner;
          float h=hashSea(key+vec2(19.2,8.7)),angle=(hashSea(key+27.3)-.5)*1.06;
          vec2 heading=normalize(dir+vec2(-dir.y,dir.x)*angle);
          float k=6.2831853/(span*(.72+.61*h));
          float phase=k*dot((f-corner)*reach,heading)-sqrt(9.81*k)*clock+6.2831853*hashSea(key-3.7);
          float weight=mix(1.-blend.x,blend.x,corner.x)*mix(1.-blend.y,blend.y,corner.y);
          gradient+=heading*(weight*k*amp*(.53+.97*h)*cos(phase)*exp(-.32*k*k*pix*pix));
        }
        return gradient;
      }
      void main(){vec3 V=normalize(cameraPosition-pWorld);float distanceM=length(cameraPosition-pWorld);
        vec2 x=pWorld.xz;float pix=max(length(dFdx(x)),length(dFdy(x)));
        vec2 s=packet(x,vec2(.86,.51),18.3,.23,3.7,pix)+packet(x,vec2(.68,-.73),8.7,.116,17.6,pix)
          +packet(x,vec2(.96,-.27),4.1,.055,44.3,pix)+packet(x,vec2(.40,.916),2.06,.028,8.2,pix)
          +packet(x,vec2(.78,.626),35.7,.29,27.5,pix)+packet(x,vec2(-.42,.907),12.3,.10,13.2,pix)
          +packet(x,vec2(.99,-.14),.68,.0083,32.8,pix);
        float well=wellFootprint(x);if(well>.001)s=mix(s,.38*s+wellWave(x,clock).yz,well);
        float wakes=0.,hullShade=1.,eddies=swellNoise(x*.49+vec2(-.17,.11)*clock);
        harborWave(x,clock,pix,eddies,s,wakes);
        vec3 N=normalize(vec3(-s.x,1.,-s.y));
        float nv=max(.001,dot(N,V)),f=.022+.978*pow(1.-nv,5.);
        vec3 reflected=reflect(-V,N);reflected.y=max(.015,reflected.y);
        float spread=.025+.035*swellNoise(x/47.+8.);
        vec3 sky=.46*textureCube(skyEnvironment,reflected,2.0).rgb
          +.27*textureCube(skyEnvironment,normalize(reflected+vec3(spread,.013,-.7*spread)),2.0).rgb
          +.27*textureCube(skyEnvironment,normalize(reflected+vec3(-spread,.013,.7*spread)),2.0).rgb;
        if(well>.001)sky=quayReflection(sky,x,reflected,crestHeight);
        harborContact(x,reflected,pix,eddies,sky,hullShade,wakes);
        float waterMass=swellNoise(x/124.+vec2(4.,-.03*clock))*.69+.31*swellNoise(x/43.+7.);
        vec3 body=mix(vec3(.012,.041,.052),vec3(.022,.066,.079),waterMass);
        float nh=max(0.,dot(N,normalize(V+solar)));float a2=.0038;
        float D=a2/(3.14159265*pow(max(.001,nh*nh*(a2-1.)+1.),2.));
        vec3 col=mix(body,sky,f)+vec3(1.0,.78,.49)*min(4.,D*.028)*solarPower;
        col=waterDetail(body,col,x,s,crestHeight,solar,solarPower,clock,pix);
        col=mix(col*hullShade,mix(vec3(.26,.365,.36),vec3(.66,.74,.70),solarPower),
          clamp(wakes,0.,.86));
        float alpha=(1.-smoothstep(620.,1120.,distanceM))*(1.-smoothstep(800.,1300.,cameraPosition.y-pWorld.y));
        gl_FragColor=vec4(col,alpha);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }`,
  });
  const mesh=new T.Mesh(geom,mat);mesh.name='Equatorial Atlantic surface';mesh.renderOrder=2;
  return {mesh,setEnvironment(map){uniforms.skyEnvironment.value=map;},update(m,time,beam){const metres=m.km*1000;mesh.visible=metres<1180;
    if(!mesh.visible)return;mesh.position.y=-7-metres;uniforms.clock.value=time;uniforms.solar.value.fromArray(m.sunDirection);uniforms.solarPower.value=beam;
  }};
}
