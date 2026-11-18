using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;

namespace Upwell {
    /// <summary>Working vessels, mooring loads and wake paths in the anchor's surveyed water coordinates.</summary>
    public sealed class HarborFleet {
        const string Folder="Harbor/";
        readonly Transform root;
        readonly Transform[] boats=new Transform[6];
        readonly Dictionary<string,Material> materials=new Dictionary<string,Material>();
        readonly Vector3[] ropePoints=new Vector3[13];
        readonly LineRenderer[] springs=new LineRenderer[4];
        static readonly string[] ids={"tug","pilot","supply","line_berth","buoy","buoy"};
        static readonly float[] lengths={24.6f,11.9f,43.5f,32,2.1f,2.1f};
        static readonly float[] beams={9.1f,4.4f,10.6f,12,2.1f,2.1f};
        static readonly float[] responses={.72f,.95f,.87f,.72f,1.18f,1.13f};
        static readonly Vector3[] fairleads={new Vector3(-3.06483f,2.33264f,8.4f),new Vector3(-2.93376f,1.97834f,-9.73f),
            new Vector3(4.5f,2.12f,10.8f),new Vector3(4.5f,2.12f,-10.8f)};
        static readonly Vector3[] shores={new Vector3(18.63f,5.31f,12.05f),new Vector3(18.63f,5.31f,22.8f),
            new Vector3(-1.1f,3.48f,69.45f),new Vector3(-31.3f,3.48f,70.8f)};
        static readonly float[] sag={.44f,.59f,.56f,.46f};
        static readonly int[] shipId={Shader.PropertyToID("boatTug"),Shader.PropertyToID("boatPilot"),Shader.PropertyToID("boatSupply"),Shader.PropertyToID("boatBerth")};
        static readonly int[] trackId={Shader.PropertyToID("pilotHistory"),Shader.PropertyToID("supplyHistory")};
        static readonly int speedId=Shader.PropertyToID("harborSpeed");
        static readonly Vector3[] skyDirections={new Vector3(.89f,.45f,0),new Vector3(-.89f,.45f,0),Vector3.up,
            Vector3.down,new Vector3(0,.45f,.89f),new Vector3(0,.45f,-.89f)};
        readonly RenderTexture skyStrip,skySample;
        readonly Texture2D readback;
        double lightAt=-999;
        [Serializable] sealed class Palette {public Finish[] materials;}
        [Serializable] sealed class Finish {public string name,color,image,normal,emit;public float metal,rough,normalStrength,gain,alpha;}
        readonly struct Swell {
            public readonly float x,z,k,omega,h;
            public Swell(float x,float z,float length,float height){
                this.x=x;this.z=z;k=2*Mathf.PI/length;omega=Mathf.Sqrt(9.81f*k);h=height;
            }
        }
        static readonly Swell[] sea={new Swell(.86f,.51f,18.3f,.23f),new Swell(.68f,-.73f,8.7f,.10f),new Swell(.96f,-.27f,4.1f,.040f),
            new Swell(.40f,.916f,2.06f,.019f),new Swell(.78f,.626f,35.7f,.29f),new Swell(-.42f,.907f,12.3f,.075f),new Swell(.99f,-.14f,6.48f,.053f)};
        static float Water(float x,float z,float t){
            float warp=.51f*Mathf.Sin(.045f*x+.037f*z+.025f*t)+.33f*Mathf.Sin(-.019f*x+.026f*z),h=0;
            foreach(var w in sea)h+=w.h*Mathf.Sin(w.k*(w.x*x+w.z*z)-w.omega*t+warp);
            return h;
        }
        static float Soft(float x,float width){
            return x>20*width?x:width*Mathf.Log(1+Mathf.Exp(x/width));
        }
        static Vector4 Route(int id,float t){
            float x,z,dx,dz;
            if(id==1){
                float d=.58f*t+3.37f*(Soft(t-11,3.7f)-Soft(-11,3.7f));
                float turn=Soft(d-65,17)-Soft(-65,17),curve=1/(1+Mathf.Exp(-(d-65)/17));
                x=26+.026f*d+.53f*turn;z=-45-.996f*d+.105f*turn;dx=.026f+.53f*curve;dz=-.996f+.105f*curve;
            }else if(id==2){
                float angle=(t-28)*.0124f;
                x=-9+205*Mathf.Sin(angle);z=-131+57*(1-Mathf.Cos(angle))+24*Mathf.Sin(angle);
                dx=205*Mathf.Cos(angle);dz=57*Mathf.Sin(angle)+24*Mathf.Cos(angle);
            }else{
                bool tug=id==0,berth=id==3;float stationX=id==4?39.2f:68.1f,stationZ=id==4?-60.8f:-193.8f;
                float phase=tug?.52f:berth?2.8f:stationX*.07f;
                x=(tug?24.02f:berth?-16:stationX)+(tug?.095f:berth?.12f:.21f)*Mathf.Sin(.193f*t+phase);
                z=(tug?-17.5f:berth?-78.6f:stationZ)+(tug?.23f:berth?.17f:.24f)*Mathf.Sin(.109f*t+.6f*phase);
                float yaw=(tug?0:berth?1.73f:.37f)+(tug?.011f:berth?.009f:.07f)*Mathf.Sin(.123f*t+phase);
                dx=Mathf.Sin(yaw);dz=-Mathf.Cos(yaw);
            }
            float size=Mathf.Sqrt(dx*dx+dz*dz);return new Vector4(x,z,dx/size,dz/size);
        }
        static void Float(Transform boat,int id,Vector4 course,float t){
            float x=course.x,z=course.y,fx=course.z,fz=course.w,rx=-fz,rz=fx;
            float fore=.29f*lengths[id],side=.32f*beams[id];
            float f=Water(x+fore*fx,z+fore*fz,t),a=Water(x-fore*fx,z-fore*fz,t);
            float s=Water(x+side*rx,z+side*rz,t),p=Water(x-side*rx,z-side*rz,t);
            boat.localPosition=new Vector3(x,.16f*Water(x,z,t)+.21f*(f+a)+.21f*(s+p),-z);
            var forward=new Vector3(fx,responses[id]*(f-a)/(2*fore),-fz);
            var right=new Vector3(rx,responses[id]*(s-p)/(2*side),-rz);
            boat.localRotation=Quaternion.LookRotation(forward,Vector3.Cross(forward,right));
        }
        static Color ColorOf(string hex){ColorUtility.TryParseHtmlString(hex,out var c);return c;}
        void GetPalette(string name){
            var catalog=Resources.Load<TextAsset>(Folder+name);
            if(!catalog)throw new InvalidOperationException("Missing harbor finish catalog "+name);
            foreach(var f in JsonUtility.FromJson<Palette>(catalog.text).materials){
                var shader=f.alpha<1?Shader.Find("Standard"):Resources.Load<Shader>(Folder+"HarborFinish");
                var mat=new Material(shader){name=f.name};
                var c=ColorOf(f.color);c.a=f.alpha;mat.color=c;mat.SetFloat("_Metallic",f.metal);mat.SetFloat("_Glossiness",1-f.rough);
                if(!string.IsNullOrEmpty(f.image)){
                    var texture=Resources.Load<Texture2D>(Folder+f.image);mat.mainTexture=texture;
                    if(texture)texture.anisoLevel=6;
                }
                if(!string.IsNullOrEmpty(f.normal)){
                    mat.SetTexture("_BumpMap",Resources.Load<Texture2D>(Folder+f.normal));mat.SetFloat("_BumpScale",f.normalStrength);mat.EnableKeyword("_NORMALMAP");
                }
                if(f.gain>0){mat.EnableKeyword("_EMISSION");mat.SetColor("_EmissionColor",ColorOf(f.emit).linear*f.gain);}
                if(f.alpha<1){
                    mat.SetFloat("_Mode",3);mat.SetInt("_SrcBlend",(int)BlendMode.One);mat.SetInt("_DstBlend",(int)BlendMode.OneMinusSrcAlpha);
                    mat.SetInt("_ZWrite",0);mat.EnableKeyword("_ALPHAPREMULTIPLY_ON");mat.SetOverrideTag("RenderType","Transparent");mat.renderQueue=3000;
                }
                materials[f.name]=mat;
            }
        }
        static Transform Group(string name,Transform parent){
            var g=new GameObject(name);g.layer=ExteriorRig.ExteriorLayer;g.transform.SetParent(parent,false);return g.transform;
        }
        Transform Model(string id){
            var source=Resources.Load<GameObject>(Folder+id);
            if(!source)throw new InvalidOperationException("Missing Blender harbor model "+id);
            var boat=Group(id,root);
            var model=UnityEngine.Object.Instantiate(source,boat,false);model.name=id+" hull";
            foreach(var child in model.GetComponentsInChildren<Transform>(true))child.gameObject.layer=ExteriorRig.ExteriorLayer;
            // Establish the FBX's true physical bow using its exported survey marker.
            Transform bow=null;
            foreach(var child in model.GetComponentsInChildren<Transform>(true))if(child.name==id+"_bow"){bow=child;break;}
            if(bow){
                Vector3 axis=boat.InverseTransformPoint(bow.position);axis.y=0;
                if(axis.sqrMagnitude>.01f)model.transform.localRotation=Quaternion.FromToRotation(axis,Vector3.forward)*model.transform.localRotation;
            }else if(id=="line_berth"||id=="offshore_depot")model.transform.localRotation=Quaternion.Euler(0,180,0)*model.transform.localRotation;
            foreach(var renderer in model.GetComponentsInChildren<MeshRenderer>(true)){
                var slots=renderer.sharedMaterials;
                for(int k=0;k<slots.Length;k++)slots[k]=materials[slots[k].name.Replace(" (Instance)","")];
                renderer.sharedMaterials=slots;renderer.receiveShadows=true;renderer.reflectionProbeUsage=ReflectionProbeUsage.Off;
            }
            return boat;
        }
        void Cylinder(Vector3 at,float radius,float height,Material mat){
            var go=GameObject.CreatePrimitive(PrimitiveType.Cylinder);go.name="Mooring casting";go.layer=ExteriorRig.ExteriorLayer;
            go.transform.SetParent(root,false);go.transform.localPosition=at;go.transform.localScale=new Vector3(2*radius,height*.5f,2*radius);
            var coll=go.GetComponent<Collider>();coll.enabled=false;UnityEngine.Object.Destroy(coll);
            var r=go.GetComponent<MeshRenderer>();r.sharedMaterial=mat;r.reflectionProbeUsage=ReflectionProbeUsage.Off;
        }
        void MakeSprings(){
            var metal=materials["Harbor_Graphite"];var cap=materials["Harbor_Berth_Gantry"];
            for(int i=0;i<springs.Length;i++){
                Vector3 b=shores[i];bool berth=i>=2;
                if(berth){
                    foreach(var offset in new[]{new Vector2(-.43f,.22f),new Vector2(.43f,.22f),new Vector2(0,-.40f)})
                        Cylinder(new Vector3(b.x+offset.x,-.16f,b.z+offset.y),.24f,6.95f,metal);
                    Cylinder(b+Vector3.down*.39f,.77f,.54f,metal);Cylinder(b+Vector3.down*.15f,.63f,.15f,cap);
                }
                Cylinder(b+Vector3.down*.18f,berth?.26f:.32f,.4f,metal);Cylinder(b+Vector3.up*.035f,berth?.33f:.39f,.082f,cap);
                var line=Group(berth?"Berth bridle":"Tug spring",root).gameObject.AddComponent<LineRenderer>();
                line.sharedMaterial=materials["Harbor_Rope"];line.useWorldSpace=false;line.positionCount=ropePoints.Length;
                line.widthMultiplier=berth?.112f:.094f;line.generateLightingData=true;line.alignment=LineAlignment.View;
                line.shadowCastingMode=ShadowCastingMode.Off;line.receiveShadows=true;line.reflectionProbeUsage=ReflectionProbeUsage.Off;springs[i]=line;
            }
        }
        public HarborFleet(Transform anchor){
            root=Group("Working roadstead",anchor);root.localPosition=Vector3.down*7;
            var format=SystemInfo.SupportsRenderTextureFormat(RenderTextureFormat.ARGBHalf)?RenderTextureFormat.ARGBHalf:RenderTextureFormat.ARGB32;
            skyStrip=new RenderTexture(6,1,0,format,RenderTextureReadWrite.Linear){name="Roadstead hemispherical light",filterMode=FilterMode.Point,wrapMode=TextureWrapMode.Clamp};
            skySample=new RenderTexture(1,1,0,format,RenderTextureReadWrite.Linear){name="Harbor sky sample",filterMode=FilterMode.Point};
            skyStrip.Create();skySample.Create();
            if(SystemInfo.copyTextureSupport==CopyTextureSupport.None)readback=new Texture2D(6,1,TextureFormat.RGBA32,false,true){name="Roadstead diffuse sky",filterMode=FilterMode.Point,wrapMode=TextureWrapMode.Clamp};
            Shader.SetGlobalFloat("_HarborLightReady",0);
            GetPalette("finishes");GetPalette("berth-finishes");
            for(int i=0;i<boats.Length;i++)boats[i]=Model(ids[i]);
            var depot=Model("offshore_depot");depot.localPosition=new Vector3(-48,0,409);
            depot.localRotation=Quaternion.AngleAxis(-.25f*Mathf.Rad2Deg,Vector3.up);
            MakeSprings();
        }
        public void SampleDaylight(Material sky,double seconds,double altitude){
            if(altitude>=1.95){Shader.SetGlobalFloat("_HarborLightReady",0);lightAt=-999;return;}
            if(Math.Abs(seconds-lightAt)<.9)return;
            lightAt=seconds;
            // The probes sit above the water and look out past all quay geometry.
            // One sky ray per direction is sufficient for these low angular frequencies.
            var previous=RenderTexture.active;var eye=Shader.GetGlobalVector("_SkyEye");
            var forward=Shader.GetGlobalVector("_SkyForward");var right=Shader.GetGlobalVector("_SkyRight");var up=Shader.GetGlobalVector("_SkyUp");
            float samples=sky.GetFloat("_Samples"),height=sky.GetFloat("_HeightKm");
            try{
                sky.SetFloat("_HeightKm",.007f);sky.SetFloat("_Samples",32);
                Shader.SetGlobalVector("_SkyEye",new Vector3(18,3,75));Shader.SetGlobalVector("_SkyUp",Vector4.zero);Shader.SetGlobalVector("_SkyRight",Vector4.zero);
                for(int i=0;i<skyDirections.Length;i++){
                    Shader.SetGlobalVector("_SkyForward",skyDirections[i]);Graphics.Blit(null,skySample,sky,0);
                    if(readback){RenderTexture.active=skySample;readback.ReadPixels(new Rect(0,0,1,1),i,0,false);}
                    else Graphics.CopyTexture(skySample,0,0,0,0,1,1,skyStrip,0,0,i,0);
                }
                if(readback){readback.Apply(false,false);Shader.SetGlobalTexture("_HarborLight",readback);}
                else Shader.SetGlobalTexture("_HarborLight",skyStrip);
                Shader.SetGlobalFloat("_HarborLightReady",1);
            }finally{
                sky.SetFloat("_HeightKm",height);sky.SetFloat("_Samples",samples);RenderTexture.active=previous;
                Shader.SetGlobalVector("_SkyEye",eye);Shader.SetGlobalVector("_SkyForward",forward);Shader.SetGlobalVector("_SkyRight",right);Shader.SetGlobalVector("_SkyUp",up);
            }
        }
        public void Dispose(){
            skyStrip.Release();skySample.Release();UnityEngine.Object.Destroy(skyStrip);UnityEngine.Object.Destroy(skySample);
            if(readback)UnityEngine.Object.Destroy(readback);
            Shader.SetGlobalFloat("_HarborLightReady",0);
        }
        public float Update(double routeSeconds,double altitude){
            bool shown=altitude<1.95;
            if(root.gameObject.activeSelf!=shown)root.gameObject.SetActive(shown);
            if(!shown)return 0;
            float t=(float)(Math.Min(9,routeSeconds)+CarriageForces.At(altitude).ShipSeconds);
            Vector2 speeds=Vector2.zero;
            for(int i=0;i<boats.Length;i++){
                var course=Route(i,t);Float(boats[i],i,course,t);
                if(i<4)Shader.SetGlobalVector(shipId[i],course);
                if(i==1||i==2){
                    float dt=i==1?9:17,stern=i==1?5.68f:20.15f;
                    var a=Route(i,t-dt);var b=Route(i,t-2*dt);
                    Shader.SetGlobalVector(trackId[i-1],new Vector4(a.x-stern*a.z,a.y-stern*a.w,b.x-stern*b.z,b.y-stern*b.w));
                    a=Route(i,t-.1f);speeds[i-1]=10*new Vector2(course.x-a.x,course.y-a.y).magnitude;
                }
            }
            Shader.SetGlobalVector(speedId,new Vector4(speeds.x,speeds.y,0,0));
            for(int i=0;i<springs.Length;i++){
                var boat=boats[i<2?0:3];var a=boat.localPosition+boat.localRotation*fairleads[i];
                for(int j=0;j<ropePoints.Length;j++){
                    float u=j/(float)(ropePoints.Length-1);ropePoints[j]=Vector3.Lerp(a,shores[i],u)+Vector3.down*(4*sag[i]*u*(1-u));
                }
                springs[i].SetPositions(ropePoints);
            }
            return t;
        }
    }
}
