// Positions and historical wake centres use the same metre survey as the pier.
// Each powered vessel supplies two older stern positions, so the wash follows
// its turns after the hull has moved on. All sub-pixel wavelets are filtered.
export const harborWater=`
uniform vec4 boatTug,boatPilot,boatSupply,boatBerth,pilotHistory,supplyHistory;
uniform vec2 harborSpeed;
float hwHull(vec2 dl,vec2 f,vec2 size,out float along,out float across){
  along=dot(dl,f);across=dot(dl,vec2(-f.y,f.x));
  float tip=clamp(along/size.x,-1.,1.);
  float halfBeam=size.y*sqrt(max(.018,1.-tip*tip))*(1.-.28*max(tip,0.)*max(tip,0.));
  return max(abs(across)-halfBeam,abs(along)-size.x);
}
void hwWake(vec2 p,vec4 boat,vec4 history,float speed,float breadth,float halfLength,
  float t,float footprint,float folds,inout vec2 gradient,inout float white){
  vec2 dl=p-boat.xy;
  float along,across,edge=hwHull(dl,boat.zw,vec2(halfLength,breadth),along,across);
  vec2 stern=boat.xy-boat.zw*halfLength;
  float span=length(history.xy-stern);
  if(span<.15||dot(dl,dl)>64000.)return;
  vec2 seg=normalize(stern-history.xy),older=normalize(history.xy-history.zw+vec2(.00001,.00001));
  float behind=dot(stern-p,seg);
  float turn=smoothstep(.7*span,1.3*span,behind);
  vec2 f=normalize(mix(seg,older,turn)),crossdir=vec2(-f.y,f.x);
  vec2 stem=mix(stern,history.xy+older*span,turn);
  float b=dot(stem-p,f),a=dot(p-stem,crossdir),dist=abs(a);
  float life=.55+12.*speed+1.6*halfLength;
  if(b>life*1.8||b< -2.4*halfLength||dist>breadth+max(0.,b+2.*halfLength)*.38+7.)return;
  float live=1.-smoothstep(.82*life,1.65*life,b);
  float wash=smoothstep(.4,3.,speed)*live;
  float aft=max(b,0.),outer=max(0.,b+1.8*halfLength);
  float amp=clamp((speed-.25)/3.,0.,1.);
  float attenuation=exp(-aft/(.78*life));
  float jolt=(folds-.5)*(.29+aft*.025);
  // Divergent branches open at the deep-water Kelvin half angle. Faster
  // launches lay fine curved crests and bubbly twin jet streaks inside it.
  float arm=dist-(.49*breadth+.327*outer+jolt);
  float halfWidth=.36+.037*outer+.35*breadth;
  float field=exp(-arm*arm/(halfWidth*halfWidth))*live;
  float lambda=max(1.05,speed*speed*.175+.18*breadth);
  float filterWidth=1./(1.+3.*footprint*footprint/(lambda*lambda));
  float phase=6.283185*(arm/lambda-.0045*outer+.12*(folds-.5));
  float crest=cos(phase);
  vec2 crossSlope=sign(a)*crossdir+.327*f;
  gradient+=.13*amp*field*crest*crossSlope*filterWidth;
  float acrossStern=breadth*(.66+.18*exp(-aft*.1)),jetWidth=.25+.023*aft+.12*breadth;
  float offset=dist-acrossStern-jolt;
  float jets=exp(-offset*offset/(jetWidth*jetWidth))+.26*exp(-a*a/(4.*jetWidth*jetWidth));
  float washBreak=.38+.62*smoothstep(.25,.79,folds);
  float trail=wash*attenuation*smoothstep(-.5,1.2,b)*jets*washBreak;
  float shattered=field*(.16+.33*max(0.,crest)*filterWidth)*washBreak;
  float bow=smoothstep(.47*halfLength,.83*halfLength,along)*(1.-smoothstep(.93*halfLength,1.14*halfLength,along));
  bow*=exp(-edge*edge/(.25+.03*breadth))*(.4+.6*folds);
  white=max(white,amp*(.73*trail+.48*shattered+.81*bow));
}
void hwContact(vec2 p,vec3 ray,vec4 boat,vec2 size,float hullHeight,float superLength,float superBeam,float top,
  vec3 sideColor,vec3 houseColor,float footprint,float noise,inout vec3 sky,inout float shadow,inout float foam){
  vec2 d=p-boat.xy;float along,across,edge=hwHull(d,boat.zw,size,along,across);
  float radius=size.x+2.;
  if(dot(d,d)<radius*radius){
    float nearHull=1.-smoothstep(.10,.86+.85*noise,max(edge,0.));
    foam=max(foam,nearHull*(.19+.37*noise));
    shadow=min(shadow,1.-.29*exp(-max(0.,edge)/(.45+.25*size.y)));
  }
  // Intersect the reflected ray with two raised sections of hull. Their
  // union breaks with the real rippled water normal instead of a flat decal.
  float elev=max(.045,ray.y),blur=.38+min(2.3,footprint*.65);
  vec2 mid=d+ray.xz*(.52*hullHeight/elev);
  float h=hwHull(mid,boat.zw,size,along,across);
  float hull=(1.-smoothstep(-blur,blur,h));
  vec2 bridge=d+ray.xz*((hullHeight+.43*(top-hullHeight))/elev)-boat.zw*(size.x*.19);
  float sh=hwHull(bridge,boat.zw,vec2(superLength,superBeam),along,across);
  float house=1.-smoothstep(-1.35*blur,1.35*blur,sh);
  float amount=(.51+.25*noise)*(1.-smoothstep(.64,1.,ray.y));
  sky=mix(sky,houseColor,amount*house);sky=mix(sky,sideColor,amount*hull);
}
void harborWave(vec2 p,float t,float footprint,float folds,inout vec2 gradient,inout float foam){
  if(abs(p.x)>380.||p.y>19.||p.y< -650.)return;
  hwWake(p,boatPilot,pilotHistory,harborSpeed.x,2.17,5.68,t,footprint,folds,gradient,foam);
  hwWake(p,boatSupply,supplyHistory,harborSpeed.y,5.20,20.15,t,footprint,folds,gradient,foam);
}
void harborContact(vec2 p,vec3 ray,float footprint,float noise,inout vec3 sky,inout float shadow,inout float foam){
  if(abs(p.x)>375.||p.y>110.||p.y< -650.)return;
  hwContact(p,ray,boatTug,vec2(12.15,4.52),2.45,5.1,3.35,7.0,
    vec3(.044,.046,.041),vec3(.32,.34,.286),footprint,noise,sky,shadow,foam);
  hwContact(p,ray,boatPilot,vec2(5.91,2.12),1.48,2.91,1.65,3.8,
    vec3(.037,.067,.071),vec3(.56,.19,.046),footprint,noise,sky,shadow,foam);
  hwContact(p,ray,boatSupply,vec2(21.72,5.18),3.85,7.2,4.25,10.2,
    vec3(.030,.082,.131),vec3(.45,.45,.35),footprint,noise,sky,shadow,foam);
  hwContact(p,ray,boatBerth,vec2(16.,6.05),2.0,4.0,2.46,5.0,
    vec3(.041,.070,.073),vec3(.25,.24,.168),footprint,noise,sky,shadow,foam);
}`;
