using System;
using UnityEngine;

namespace Upwell {
    // This CPU sample uses the same field and optical path as the sky volume.
    public sealed class WeatherOptics {
        readonly Color32[] cube;
        readonly byte[] organization;
        public readonly Texture2D MarineCells;
        public WeatherOptics(Texture3D texture){
            cube=texture.GetPixels32();organization=Resources.Load<TextAsset>("MarineOrganization").bytes;
            MarineCells=new Texture2D(256,256,TextureFormat.RGBA32,true,true);
            MarineCells.name="Atlantic open and closed cell fractions";MarineCells.wrapMode=TextureWrapMode.Repeat;MarineCells.filterMode=FilterMode.Trilinear;
            MarineCells.SetPixelData(organization,0);MarineCells.Apply(true,true);
        }
        Vector4 MarineTex(float u,float v){
            float x=Mathf.Repeat(u,1)*256-.5f,y=Mathf.Repeat(v,1)*256-.5f;
            int ix=Mathf.FloorToInt(x),iy=Mathf.FloorToInt(y);float fx=x-ix,fy=y-iy;
            var values=Vector4.zero;
            for(int b=0;b<2;b++)for(int a=0;a<2;a++){
                int i=(((iy+b)&255)*256+((ix+a)&255))*4;float w=(a==1?fx:1-fx)*(b==1?fy:1-fy)/255f;
                values+=new Vector4(organization[i],organization[i+1],organization[i+2],organization[i+3])*w;
            }return values;
        }
        static float S(float a,float b,float x){float u=Mathf.Clamp01((x-a)/(b-a));return u*u*(3-2*u);}
        float Read(Vector3 uv,int c){
            uv=uv*64-Vector3.one*.5f;int x=Mathf.FloorToInt(uv.x),y=Mathf.FloorToInt(uv.y),z=Mathf.FloorToInt(uv.z);float fx=uv.x-x,fy=uv.y-y,fz=uv.z-z,v=0;
            for(int k=0;k<2;k++)for(int j=0;j<2;j++)for(int i=0;i<2;i++){
                var p=cube[(((z+k)&63)*64+((y+j)&63))*64+((x+i)&63)];float b=c==0?p.r:c==1?p.g:c==2?p.b:p.a;
                v+=b*(i==1?fx:1-fx)*(j==1?fy:1-fy)*(k==1?fz:1-fz);
            }return v/255;
        }
        // A sinuous dry slot separates the moist marine streets from the sheared
        // storm flank. The coordinates follow the moving air mass.
        static float drySlot(float u,float v){
          float center=-1.5f+1.7f*Mathf.Sin(.115f*u+.55f)+2.2f*Mathf.Sin(.045f*u-.75f);
          float broadening=1.0f+.85f*S(9.0f,34.0f,u);
          return (1.0f-S(1.20f*broadening,4.90f*broadening,Mathf.Abs(v-center)))*(1.0f-S(27.0f,65.0f,Mathf.Abs(u-8.0f)));
        }
        static float thermal(float x,float y,float z){return 1.0f-x*x-y*y-z*z;}
        // A sloping intrusion of dry air intersects the edge of the marine bank.
        // All coordinates move with the air parcel. Distances are kilometres.
        float sunbreak(float x,float z,float h,float baseDensity){
          if(h>12.0f||x< -15.0f||x>53.0f||z< -27.0f||z>12.0f)return baseDensity;
          x+=3.20f;
          z+=1.25f;
          float along=.978f*x-.209f*z;
          float across=.209f*x+.978f*z;
          float bend=.44f*Mathf.Sin(.15f*along+.4f)+.19f*Mathf.Sin(.31f*along);
          float span=S(-2.0f,1.4f,along)*(1.0f-S(39.0f,49.0f,along));
          float core=1.0f-S(1.48f,4.20f,Mathf.Abs(across-bend));
          float centre=3.15f+.163f*along+.10f*Mathf.Sin(.27f*along)+.07f*Mathf.Sin(across*.7f);
          float intrusion=span*core*(1.0f-S(.43f,1.15f,Mathf.Abs(h-centre)));
          float density=baseDensity*(1.0f-intrusion);
          if(along< -8.0f||along>.75f||Mathf.Abs(across)>6.3f||h<1.8f||h>4.1f)return density;
          float eddy=.57f*Read(new Vector3(x,h,z)/3.7f,0)+.43f*Read(new Vector3(x,h,z)/.94f,2);
          float lip=-.17f+.16f*Mathf.Sin(2.17f*across)+.59f*(eddy-.5f);
          float fringe=S(-7.8f,-4.8f,along)*(1.0f-S(lip-.14f,lip+.16f,along));
          fringe*=1.0f-S(2.0f,6.1f,Mathf.Abs(across+.37f*Mathf.Sin(1.2f*along)));
          float floorH=2.38f+.14f*Mathf.Sin(.82f*across+.4f*along)+.22f*(eddy-.5f);
          float topH=3.12f+.18f*Mathf.Sin(.92f*across-.50f*along)+.34f*(eddy-.5f)
                      +.16f*Mathf.Sin(4.6f*across+1.2f*along)+.10f*Mathf.Sin(6.1f*along-3.2f*across);
          float hydro=S(floorH-.16f,floorH+.16f,h)*(1.0f-S(topH-.16f,topH+.15f,h));
          return Mathf.Max(density,fringe*hydro*(2.75f+2.65f*eddy));
        }
        // Horizontal humidity belongs to a parcel, including where the ray crosses its roof.
        static float openBasin(float u,float v,float bend,float fold){
          float sound=thermal((u+2.8f+7.2f*bend)*.052f,(v-21.4f-7.8f*fold-2.7f*bend)*.126f,0.0f);
          float inlet=thermal((u-40.0f-5.6f*fold)*.058f,(v+16.8f-8.3f*bend)*.116f,0.0f);
          return S(-.22f,.62f,Mathf.Max(sound,inlet));
        }
        static float marineRaft(float u,float v,float h,float slot,float cover,float column,float shore,float ridge,float grain,float fraction,float draft,float breakup,float moisture,float upstream){
          float bend=column-.50f,fold=shore-.47f;
          float distortion=5.4f*(breakup-.50f)+3.2f*(ridge-.55f)+2.6f*(grain-.50f);
          float raggedSlot=drySlot(u+3.4f*fold,v+distortion);
          float basin=openBasin(u+4.1f*(breakup-.5f),v+distortion,bend,fold);
          float humidity=.46f+.85f*(fraction-.55f)+.42f*bend+.28f*fold+.25f*(moisture-.50f)+.17f*(ridge-.52f)+.12f*(cover-.72f)-.39f*raggedSlot-.31f*basin-.09f*slot;
          humidity+=.18f*S(.55f,.78f,moisture)*(1.0f-.86f*raggedSlot)*(1.0f-.70f*basin)-.31f*(1.0f-S(.26f,.46f,moisture));
          float edge=S(.22f,.60f,humidity+.29f*(grain-.48f)+.20f*(breakup-.50f));
          float floorH=.89f+.38f*bend+.12f*fold+.145f*(ridge-.5f)+.16f*(breakup-.5f)+.19f*(1.0f-edge);
          float roof=floorH+.24f+edge*(.43f+.76f*column+.51f*ridge+1.36f*draft)+.61f*(grain-.48f);
          float profile=S(floorH-.12f,floorH+.135f,h)*(1.0f-S(roof-.24f,roof+.19f,h));
          float wispH=floorH+.63f+.61f*draft+.31f*ridge+.29f*(breakup-.50f);
          float torn=S(.12f,.48f,upstream-fraction)*S(.31f,.77f,upstream);
          float wisp=torn*S(wispH-.39f,wispH-.08f,h)*(1.0f-S(wispH+.03f,wispH+.27f,h));
          float mixing=.22f+.78f*S(.20f,.72f,grain+.37f*edge+.24f*(breakup-.50f));
          return Mathf.Max(edge*edge*profile*(.96f+1.57f*edge+.55f*ridge)*mixing,.075f*wisp);
        }
        static float stratiformShield(float u,float v,float h,float slot,float cover,float column,float shore,float grain,float curl,float fraction,float draft,float breakup,float moisture,float upstream){
          float bend=column-.50f,fold=shore-.47f;
          float distortion=6.8f*(breakup-.5f)+4.2f*(grain-.5f)+3.7f*(fraction-.57f);
          float inlet=openBasin(u+4.7f*(moisture-.5f),v+distortion,bend,fold);
          float raggedSlot=drySlot(u+5.2f*fold,v+.75f*distortion);
          float front=Mathf.Abs(v+3.2f-8.3f*bend-5.7f*fold);
          float wing=S(2.4f,9.8f,front);
          float humidity=.36f+.90f*(moisture-.49f)+.71f*(fraction-.56f)+.44f*bend+.29f*fold+.25f*(wing-.50f)+.12f*(cover-.72f)-.33f*raggedSlot-.28f*inlet-.08f*slot;
          humidity+=.29f*S(.56f,.80f,moisture)*(1.0f-.85f*raggedSlot)*(1.0f-.75f*inlet)-.40f*(1.0f-S(.27f,.45f,moisture));
          // Upstream of the deep convection, entrainment erodes the lid from above.
          // The thinning slope and its cloudy filaments extend into the ocean lead.
          float along=u+.26f*v+2.8f*fold+1.46f*(breakup-.5f);
          float seam=Mathf.Abs(v-(2.55f+.22f*u+4.34f*fold+3.83f*(breakup-.5f)+2.1f*(grain-.50f)));
          float dryMix=S(-27.0f,-6.0f,along)*(1.0f-S(.3f,16.0f,along))*(1.0f-S(2.75f,12.15f,seam));
          humidity-=dryMix*(.66f+.49f*S(5.05f,8.63f,h));
          float mass=S(.265f,.65f,humidity+.24f*(grain-.50f)+.21f*(breakup-.50f));
          float floorH=4.87f+1.22f*column+.44f*fold+.38f*(wing-.5f)+.34f*(breakup-.50f)+.78f*(1.0f-mass);
          float roof=floorH+.21f+mass*(.61f+1.06f*column+.41f*wing+2.32f*draft)+.89f*(grain-.50f)+.46f*(curl-.48f);
          roof-=1.31f*dryMix*(.51f+.49f*breakup);
          float profile=S(floorH-.23f,floorH+.32f,h)*(1.0f-S(roof-.34f,roof+.24f,h));
          float wispH=floorH+.52f+.79f*moisture+.77f*draft+.48f*(grain-.50f)+.33f*(breakup-.50f);
          float torn=S(.12f,.51f,upstream-fraction)*S(.36f,.77f,upstream)*(.16f+.84f*S(.26f,.75f,breakup));
          float wisp=torn*S(wispH-.59f,wispH-.11f,h)*(1.0f-S(wispH+.06f,wispH+.38f,h));
          return Mathf.Max(mass*mass*profile*(.78f+1.34f*mass),.118f*wisp);
        }
        static float stormCrown(float u,float v,float h,float shape,float curl,float erosion){
          if(u < -13.0f||u > 52.0f||v < -27.0f||v > 25.0f)return 0.0f;
          // The inflow rolls a cleft into the west face of the rising column; the
          // flanking roll stays attached to the core and curls around the opening.
          float gullyU=u-7.19f-.46f*(h-8.55f)-1.34f*(shape-.5f)-.68f*(erosion-.5f);
          float gullyV=v+.03f-.26f*(h-8.55f)+1.28f*(curl-.50f);
          float gully=thermal(gullyU*.45f,gullyV*.66f,(h-8.91f)*.264f);
          float drag=.12f*(h-5.0f)+1.13f*S(9.5f,12.0f,h);
          u-=drag+1.51f*(curl-.5f);v-=.48f*drag+2.17f*(shape-.5f)+.74f*(erosion-.5f);
          float rootA=thermal((u-8.70f)*.136f,(v-1.75f)*.257f,(h-4.31f)*.306f);
          float rootB=thermal((u-8.14f)*.135f,(v+16.90f)*.225f,(h-4.42f)*.298f);
          float roll=.78f*(curl-.50f)+.51f*(erosion-.50f);
          float shoulder=thermal((u-9.7f+1.52f*roll)*.224f,(v-1.30f-1.74f*roll-.20f*(h-7.4f))*.304f,(h-8.55f)*.215f);
          float turret=thermal((u-12.3f)*.36f,(v-1.88f)*.40f,(h-10.28f)*.315f);
          float flank=thermal((u-6.2f)*.147f,(v+8.8f)*.239f,(h-6.55f)*.41f);
          float farCore=thermal((u-8.5f)*.195f,(v+17.25f)*.25f,(h-8.72f)*.223f);
          float farTurret=thermal((u-7.0f)*.35f,(v+17.85f)*.40f,(h-10.76f)*.378f);
          float scud=thermal((u+2.25f)*.22f,(v+4.70f)*.78f,(h-7.80f-.26f*(v+4.6f))*1.09f);
          float plumeU=u-11.8f;
          float driftV=2.35f+.202f*plumeU+1.55f*(curl-.48f)+.064f*plumeU*(shape-.50f);
          float reach=S(-6.0f,3.0f,plumeU)*(1.0f-S(16.0f,36.0f,plumeU+6.8f*(shape-.47f)));
          float halfWidth=2.0f+.158f*Mathf.Max(0.0f,plumeU)+2.35f*(shape-.46f);
          float fringe=1.0f-S(halfWidth-.81f,halfWidth+1.34f,Mathf.Abs(v-driftV));
          float roof=11.34f+.020f*plumeU+.38f*(shape-.5f)+.25f*(curl-.50f);
          float thickness=.26f+.73f*(1.0f-S(2.0f,29.0f,plumeU));
          float iceFan=reach*fringe*S(roof-thickness-.19f,roof-thickness+.22f,h)*(1.0f-S(roof-.06f,roof+.32f,h));
          float lift=Mathf.Max(Mathf.Max(rootA,rootB),Mathf.Max(Mathf.Max(shoulder,turret),Mathf.Max(flank,Mathf.Max(farCore,farTurret))));
          lift=Mathf.Max(lift,.61f*scud-.15f);
          lift-=.97f*S(-.45f,.88f,gully);
          float rolledShoulder=thermal((u-7.69f-.31f*(h-8.6f))*.43f,(v-1.03f+.29f*(h-8.6f))*.74f,(h-8.8f)*.33f);
          lift=Mathf.Max(lift,.75f*rolledShoulder-.16f);
          float scallop=(.88f*(shape-.50f)+.54f*(curl-.51f)+.33f*(erosion-.50f))*(.46f+.54f*S(4.3f,8.8f,h));
          float column=S(-.085f,.47f,lift+scallop)*S(1.28f,1.87f,h)*(1.74f+.72f*shape+.75f*curl+.63f*erosion);
          return Mathf.Max(column,iceFan*(.59f+.79f*(1.0f-S(6.0f,29.0f,plumeU))));
        }
        // A shelf at the leading edge of a marine squall line, with precipitation
        // reaching down behind it and ice spreading downwind from the updraft.
        float squallLine(float x,float z,float h,float density,float widthKm){
          if(x < -45.0f||x>45.0f||z < -53.0f||z>4.0f||h>16.15f)return density;
          float along=(x+7.0f)*.974f-(z+25.0f)*.227f;
          float across=(z+25.0f)*.974f+(x+7.0f)*.227f;
          float range=S(-36.0f,-23.0f,along)*(1.0f-S(23.0f,40.0f,along));
          if(range<=0.0f||across < -20.0f||across>27.0f)return density;
          float frontBow=2.7f*Mathf.Sin(.086f*along+.52f)+1.1f*Mathf.Sin(.163f*along-.42f);
          float distanceFromFront=across-frontBow;
          var billows=new Vector3(along/32.0f+.39f,h/19.0f+.28f,across/17.0f+.62f);
          float eddy=Mathf.Lerp(Read(billows,0),.5f,S(.8f,3.0f,widthKm))-.5f;
          float ridge=Mathf.Lerp(Read(billows,1),.5f,S(1.4f,5.5f,widthKm))-.5f;
          float depth=distanceFromFront+.93f*eddy+.69f*ridge;
          // Subsidence ahead of the front clears a winding lead in both lower decks.
          float opening=S(2.5f,7.4f,depth)*(1.0f-S(13.0f,23.0f,depth))
                       *S(-27.0f,-12.0f,along)*(1.0f-S(4.3f,11.0f,h));
          density*=1.0f-.96f*range*opening;
          float wet=0.0f;
          if(h<5.3f){
            float shelfEdge=5.55f+.35f*Mathf.Sin(.61f*along)+.19f*Mathf.Sin(1.32f*along-.3f)+1.09f*ridge;
            float overlap=1.0f-S(shelfEdge-.55f,shelfEdge+.38f,depth);
            float wedge=S(-6.2f,-2.7f,depth)*overlap;
            float shelfBase=1.14f+.145f*depth+.52f*eddy+.18f*Mathf.Sin(.46f*along+.62f*depth);
            float roof=3.84f-.264f*Mathf.Max(0.0f,depth)+.42f*ridge+.36f*eddy;
            wet=wedge*S(shelfBase-.22f,shelfBase+.22f,h)*(1.0f-S(roof-.27f,roof+.33f,h))
                *(.95f+.46f*ridge+.67f*eddy);
            float rainAxis=-2.2f+.37f*h+.68f*ridge;
            float shaft=1.0f-S(1.25f,4.10f,Mathf.Abs(depth-rainAxis));
            float streak=Read(new Vector3((along-.32f*h)/15.0f+.39f,h/43.0f+.21f,(depth-.20f*h)/19.0f+.17f),0);
            float showers=(.10f+.92f*S(.30f,.72f,streak))*(1.0f-S(2.9f,4.55f,h));
            wet=Mathf.Max(wet,shaft*showers*S(-26.0f,-11.0f,along)*(1.0f-S(3.0f,16.0f,along)));
          }
          if(h>2.3f){
            var folds=new Vector3((along-.24f*h)/9.3f+.19f,h/8.2f+.55f,(depth+.19f*h)/7.7f+.29f);
            float roll=(.57f*Read(folds,0)+.43f*Read(folds,2)-.5f)*(1.0f-S(.45f,2.4f,widthKm));
            float lift=Mathf.Exp(-.014f*(along+6.0f)*(along+6.0f))+.55f*Mathf.Exp(-.026f*(along-5.0f)*(along-5.0f));
            float fan=S(10.3f,14.3f,h);
            float coreDepth=depth+1.15f+.158f*h-1.16f*eddy-.53f*ridge;
            float bulb=3.16f*Mathf.Exp(-.17f*(along+5.0f-.61f*(h-10.0f))*(along+5.0f-.61f*(h-10.0f))-.054f*(h-9.9f)*(h-9.9f));
            float halfWidth=1.85f+1.01f*lift+bulb+1.47f*roll+1.24f*eddy+(1.0f-S(2.4f,6.2f,h))*1.28f;
            float column=1.0f-S(halfWidth-1.15f,halfWidth+.58f,Mathf.Abs(coreDepth));
            float roof=5.87f+8.64f*Mathf.Min(1.0f,lift)+2.45f*eddy+1.28f*ridge+1.24f*roll;
            float updraft=column*S(2.3f,3.65f,h)*(1.0f-S(roof-.79f,roof+.45f,h));
            wet=Mathf.Max(wet,updraft*(1.51f+.39f*eddy+.44f*ridge));
            if(fan>.001f){
              float drift=along+4.0f;
              float width=2.62f+.12f*Mathf.Max(0.0f,drift)+1.88f*eddy;
              float radius=Mathf.Abs(coreDepth-.13f*drift-.026f*drift*ridge);
              float span=S(-8.0f,-1.7f,drift)*(1.0f-S(12.0f,30.0f,drift+7.2f*ridge+2.9f*roll));
              var grain=new Vector3((drift+.71f*coreDepth)/58.0f+.27f,(h-.02f*drift)/6.0f+.48f,(coreDepth-.14f*drift)/13.0f+.71f);
              float strands=Mathf.Lerp(.64f*Read(grain,0)+.36f*Read(grain,2),.52f,S(.46f,2.2f,widthKm));
              float fringe=1.0f-S(width-1.9f,width+1.15f,radius-3.5f*(strands-.5f));
              float cap=13.06f+.021f*drift+.26f*Mathf.Sin(.115f*drift)+.89f*eddy+.63f*ridge+.83f*roll;
              float fall=.42f+1.16f*(1.0f-S(-1.0f,24.0f,drift))+.72f*(strands-.5f);
              float ice=S(cap-fall-.48f,cap-fall+.48f,h)*(1.0f-S(cap-.28f,cap+.24f,h));
              wet=Mathf.Max(wet,span*fringe*ice*(.09f+.88f*S(.35f,.72f,strands)));
              // A short turret breaks through the stable sheet at its feeding end.
              float turret=thermal((along+5.15f+.99f*eddy)*.28f,(coreDepth-1.62f-1.41f*ridge)*.38f,(h-14.08f)*.599f);
              wet=Mathf.Max(wet,1.78f*S(-.13f,.42f,turret+1.50f*roll+.72f*eddy));
            }
          }
          return Mathf.Max(density,range*wet);
        }
        public float Density(Vector3 enu,float t){
            float h=(float)((enu.x*(double)enu.x+enu.z*(double)enu.z+enu.y*(12742.0+enu.y))/(Math.Sqrt(enu.x*(double)enu.x+enu.z*(double)enu.z+Math.Pow(6371.0+enu.y,2))+6371.0));
            if(h<.04f||h>16.15f)return 0;Vector3 q=enu-new Vector3(.018f*t,0,.007f*t);
            float cover=S(.26f,.68f,.64f*Read(q/7600,3)+.36f*Read(q/1900,0)+.052f),den=0;
            float frontU=.72f*q.x-.69f*q.z,frontV=.69f*q.x+.72f*q.z,slot=drySlot(frontU,frontV);
            var airMass=new Vector3(frontU/123f+.34f,.37f,frontV/99f+.61f);
            float column=Read(airMass,3),shore=.58f*Read(airMass,0)+.42f*Read(airMass,1);
            float airX=(frontU-(h-1.5f)*.49f)/146f+.418f,airY=(frontV-(h-1.5f)*.25f)/131f+.583f;
            var field=MarineTex(airX,airY);float upstream=MarineTex(airX-.030f,airY-.011f).x;
            if(h<4.28f){
                var rows=new Vector3((frontU-2.8f*(shore-.48f))/56f+.41f,.19f,(frontV+6.7f*(column-.5f))/23f+.27f);
                float ridge=S(.24f,.74f,.61f*Read(rows,0)+.39f*Read(rows,1));
                float grain=.65f*Read(q/12.4f,0)+.35f*Read(q/12.4f,1);
                den=marineRaft(frontU,frontV,h,slot,cover,column,shore,ridge,grain,field.x,field.y,field.z,field.w,upstream);
            }
            if(h>1.28f&&h<13.54f){
                float cap=S(8.4f,10.65f,h);
                var shear=new Vector3(q.x-(h-6f)*(.28f+1.05f*cap),q.y*(1f+.45f*cap),q.z*(1f+.23f*cap));
                float shape=.62f*Read(shear/30f,0)+.38f*Read(shear/30f,1);
                float curl=Read(q/6.2f+new Vector3(0,t*.000185f,t*.00024f),2);
                float erosion=.61f*curl+.39f*Read(q/1.4f+new Vector3(curl*.19f,0,-curl*.15f),0);
                float stratiform=stratiformShield(frontU,frontV,h,slot,cover,column,shore,shape,curl,field.x,field.y,field.z,field.w,upstream);
                den=Mathf.Max(den,Mathf.Max(stratiform,stormCrown(frontU,frontV,h,shape,curl,erosion)));
            }
            if(h>10.75f){
                float u=q.x+.47f*q.z,v=q.z-.47f*q.x;
                var gust=new Vector3(u/72+.16f,.29f,v/81+.40f);float bend=Read(gust,0)-.5f,fold=Read(gust,1)-.5f;
                float lane=v+9.6f*bend+4.2f*fold+(12.5f-h)*(.75f+.45f*fold)+.08f*u*bend;
                float bank=Read(new Vector3(u/91+.31f,.07f+h/31,lane/59),3);
                float fibre=Read(new Vector3(u/47+.26f*bend+t*.000025f,.30f+h/9+.42f*fold,lane/10.8f+.18f*Read(gust,2)),0);
                float crossFibre=Read(new Vector3((u+.23f*v)/34+.72f*fold,h/14+.311f,(v-.31f*u)/16-.42f*bend),0);
                float filament=S(.38f,.70f,.55f*fibre+.45f*crossFibre),iceBase=11.02f+.69f*fold+.39f*bend;
                float veil=S(iceBase-.27f,iceBase+.66f,h)*(1-S(iceBase+1.34f,iceBase+2.22f,h));
                float plume=S(-.16f,.76f,thermal((frontU-16)*.089f,(frontV-6.2f)*.145f,(h-12.43f)*1.62f));
                den+=(S(.41f,.73f,bank)*veil*.042f+plume*.051f)*(.12f+.88f*filament);
            }
            float background=h<.65f?0:sunbreak(q.x,q.z,h,den);
            return squallLine(q.x,q.z,h,background,0);
        }
        public static float Visibility(double height, Vector3 sun){
            return S(-.00465f,.00465f,(float)(Math.Asin(Math.Max(-1,Math.Min(1,sun.y)))+Math.Acos(6371/(6371+Math.Max(0,height)))));
        }
        public float Transmission(double km,float t,Vector3 sun){
            if(Visibility(km,sun)<.01f)return .10f;
            double b=(6371+km)*sun.y,c=(km-16.15)*(12742+km+16.15),dis=b*b-c;if(dis<=0)return 1;
            double root=Math.Sqrt(dis),start=Math.Max(0,-b-root),end=Math.Min(-b+root,start+400);if(end<=start)return 1;
            float dx=(float)(end-start)/28,depth=0;Vector3 dir=new Vector3(sun.x,sun.y,-sun.z),ro=new Vector3(0,(float)km,0);
            for(int i=0;i<28;i++)depth+=Density(ro+dir*((float)start+(i+.5f)*dx),t)*dx;
            return Mathf.Clamp(Mathf.Exp(-depth),.1f,1);
        }
    }
}
