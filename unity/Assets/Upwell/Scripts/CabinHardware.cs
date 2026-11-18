using System;
using System.Collections.Generic;
using UnityEngine;

namespace Upwell {
    public sealed class CabinHardware:MonoBehaviour {
        [Serializable] class Survey { public string id; public float[] origin,right,up,forward,extent; public int[] tile; }
        [Serializable] class ShieldPath { public float[] xyz; }
        [Serializable] class Sheet { public int width,height,columns,rows; public Survey[] surveys; public ShieldPath[] shieldPaths; }
        struct Segment { public Vector3 start,axis,u,v;public float length,arc; }
        readonly List<Segment> braidLines=new List<Segment>();
        static readonly Matrix4x4 ToWeb=Matrix4x4.Scale(new Vector3(1,1,-1));
        static readonly HashSet<string> Omit=new HashSet<string>{"mug","capillary_cell","capillary_primer","accelerometer","accel_test","field_glasses","logbook","tool_roll","access_card","roller_shade","privacy_curtain"};
        static readonly Dictionary<string,Vector3> Grips=new Dictionary<string,Vector3>{
            {"ascent_lever",new Vector3(1.46f,1.235f,-5)},{"pilot_console",new Vector3(.83f,1.001f,-4.76f)},
            {"pressure_hatch",new Vector3(.49f,1.18f,1.81f)},{"card_reader",new Vector3(1.02f,1.34f,1.72f)},
            {"service_cabinet",new Vector3(1.69f,1.49f,4.10f)},{"grab_handle",new Vector3(-1.23f,1.34f,1)},
            {"lounge_seat",new Vector3(-1.38f,.89f,-3.51f)}
        };
        readonly Dictionary<string,Survey> tiles=new Dictionary<string,Survey>();
        TransitRide ride;Light rack,reading;FurnishingSurface fiber;TransitProp solarShade;Texture2D berthCover;
        static readonly int ApertureSky=Shader.PropertyToID("_UpwellApertureSky"),ApertureEarth=Shader.PropertyToID("_UpwellApertureEarth"),
            ApertureSun=Shader.PropertyToID("_UpwellApertureSun"),ApertureGain=Shader.PropertyToID("_UpwellApertureGain");
        static Vector3 V(float[] p)=>new Vector3(p[0],p[1],p[2]);
        static Vector3 U(float x,float y,float z)=>new Vector3(x,y,-z);
        static Matrix4x4 Project(Survey s) {
            var m=Matrix4x4.identity;Vector3 o=V(s.origin),a=V(s.right)/s.extent[0],b=-V(s.up)/s.extent[1],d=V(s.forward);
            m.SetRow(0,new Vector4(a.x,a.y,a.z,.5f-Vector3.Dot(a,o)));
            m.SetRow(1,new Vector4(b.x,b.y,b.z,.5f-Vector3.Dot(b,o)));
            m.SetRow(2,new Vector4(d.x,d.y,d.z,-Vector3.Dot(d,o)));return m;
        }
        static bool IsMetal(string n)=>n.Contains("Titanium")||n.Contains("Aluminum")||n.Contains("Anodized")||n.Contains("Graphite_Alloy");
        static int Surface(string n)=>IsMetal(n)?1:n.Contains("Rubber")||n.Contains("Grip")||n.StartsWith("Cable_")?2:
            n.Contains("Ceramic")||n.Contains("Composite")||n.StartsWith("Surface_")?3:0;
        public void Install(TransitRide owner) {
            ride=owner;
            var field=Resources.Load<Texture2D>("CabinContactField");var config=Resources.Load<TextAsset>("CabinContactSurvey");
            var ink=Resources.Load<Texture2D>("CabinJacketPrint");if(!field||!config||!ink)return;
            var sheet=JsonUtility.FromJson<Sheet>(config.text);
            foreach(var s in sheet.surveys)tiles.Add(s.id,s);
            foreach(var route in sheet.shieldPaths){
                var p=route.xyz;float arc=0;var u=Vector3.right;
                for(int i=0;i+5<p.Length;i+=3){
                    var a=U(p[i],p[i+1],p[i+2]);var delta=U(p[i+3],p[i+4],p[i+5])-a;
                    float length=delta.magnitude;if(length<.0001f)continue;var dir=delta/length;
                    u=Vector3.ProjectOnPlane(u,dir).normalized;
                    braidLines.Add(new Segment{start=a,axis=dir,u=u,v=-Vector3.Cross(dir,u),length=length,arc=arc});arc+=length;
                }
            }
            Shader.SetGlobalTexture("_UpwellCabinContact",field);Shader.SetGlobalTexture("_UpwellJacketPrint",ink);
            Shader.SetGlobalTexture("_UpwellApertures",Resources.Load<Texture2D>("CabinApertures"));
            berthCover=Resources.Load<Texture2D>("BerthCover");
            ride.props.TryGetValue("roller_shade",out solarShade);
            Shader.SetGlobalVector("_CabinFieldSize",new Vector4(sheet.width,sheet.height,1f/(sheet.columns*sheet.width),1f/(sheet.rows*sheet.height)));
            foreach(var region in FindObjectsByType<RegisteredFinish>(FindObjectsInactive.Include))
                foreach(var r in region.GetComponentsInChildren<MeshRenderer>(true)){RegisterAperture(r,region.room);Register(r,region.room);}
            GlandBank("Feeder compression nuts",1.8004f,6,new Color(.55f,.56f,.51f),.87f,.31f,
                new[]{new Vector2(.0180f,.0053f),new Vector2(.0215f,.0036f),new Vector2(.0215f,-.0053f),new Vector2(.0181f,-.0079f)});
            GlandBank("Terminal lock washers",1.8081f,24,new Color(.68f,.67f,.58f),.84f,.24f,
                new[]{new Vector2(.0191f,.0020f),new Vector2(.0205f,.0012f),new Vector2(.0205f,-.0011f),new Vector2(.0191f,-.0020f)});
            GlandBank("Terminal seals",1.7922f,20,new Color(.115f,.135f,.14f),.025f,.48f,
                new[]{new Vector2(.0179f,.0018f),new Vector2(.0186f,.0013f),new Vector2(.0189f,0),new Vector2(.0185f,-.0014f),new Vector2(.0176f,-.0020f)});
            GlandBank("Molded jacket boots",1.7648f,16,new Color(.115f,.135f,.14f),.025f,.48f,
                new[]{new Vector2(.0158f,.0154f),new Vector2(.0166f,.0140f),new Vector2(.0166f,.0115f),new Vector2(.0143f,.0108f),
                    new Vector2(.0142f,.0086f),new Vector2(.0157f,.0077f),new Vector2(.0150f,.0053f),new Vector2(.0130f,.0045f),
                    new Vector2(.0126f,.0017f),new Vector2(.0140f,.0010f),new Vector2(.0132f,-.0014f),new Vector2(.0118f,-.0025f),new Vector2(.0110f,-.0088f)});
            reading=TaskLight("Berth reading aperture",U(-1.976f,1.492f,-.839f),U(-1.61f,.94f,-.40f),new Color(1,.77f,.52f),2.34f,103,1.10f);
            rack=TaskLight("Recessed wiring inspection strip",U(1.868f,1.94f,3.36f),U(2.065f,1.32f,3.62f),new Color(1,.86f,.73f),2.15f,116,1.42f);
            if(ride.practicals.Length>=3){ride.practicals[1].intensity*=.53f;ride.practicals[2].intensity*=.70f;}
            UpdateLights();
        }
        void RegisterAperture(MeshRenderer r,string room){
            var mats=r.sharedMaterials;
            for(int i=0;i<mats.Length;i++){
                if(!mats[i])continue;string shader=mats[i].shader.name;
                if(shader!="Upwell/Carriage finish"&&shader!="Upwell/Woven textile"&&shader!="Upwell/Laminated glazing")continue;
                var block=new MaterialPropertyBlock();r.GetPropertyBlock(block,i);
                if(shader=="Upwell/Laminated glazing"){
                    int ix=room=="observation"?0:room=="berth"?1:2;
                    var probes=ride.exterior.roomReflections;
                    if(probes!=null&&ix<probes.Length&&probes[ix]){
                        var p=probes[ix].transform.position;block.SetVector("_CabinGlassOrigin",new Vector4(p.x,p.y,p.z,1));
                    }
                }else block.SetFloat("_CabinApertures",1);
                r.SetPropertyBlock(block,i);
            }
        }
        void Register(MeshRenderer r,string room) {
            var prop=r.GetComponentInParent<TransitProp>();string id=prop?prop.id:"";
            if(prop&&(prop.portable||Omit.Contains(id)))return;
            var fabric=r.GetComponentInParent<FurnishingSurface>();if(fabric&&!fabric.IsCable)return;
            if(fabric){if(fabric.partId=="loom_service_fiber")fiber=fabric;JacketCoordinates(r,fabric);}
            string first=id=="pressure_hatch"?"hatch":room=="berth"?"berth":room=="observation"?"seat":"rack";
            string second=first=="seat"?"deck":first=="rack"?"lock":null;
            bool travels=id=="service_cabinet"||id=="locker_drawer";
            var rest=ToWeb*r.localToWorldMatrix;var mats=r.sharedMaterials;
            for(int i=0;i<mats.Length;i++){
                var m=mats[i];if(!m)continue;string n=m.name,shader=m.shader.name;var block=new MaterialPropertyBlock();r.GetPropertyBlock(block,i);
                if(shader=="Upwell/Optical flight panel"||shader=="Upwell/Bonded live readout"){block.SetFloat("_CabinGlass",1);r.SetPropertyBlock(block,i);continue;}
                if(shader!="Upwell/Carriage finish")continue;
                if(fabric){
                    float type=n.StartsWith("Cable_Orange")?1:n.StartsWith("Cable_Cyan")?2:0;
                    if(type>0){block.SetVector("_CabinLayer",new Vector4(0,0,type,0));block.SetFloat("_Metallic",.015f);}
                }else{
                    var a=tiles[first];int count=travels?0:second==null?1:2;
                    var tile=new Vector4(a.tile[0],a.tile[1],0,0);block.SetMatrix("_CabinProject0",Project(a)*rest);
                    if(second!=null){var b=tiles[second];tile.z=b.tile[0];tile.w=b.tile[1];block.SetMatrix("_CabinProject1",Project(b)*rest);}
                    bool shield=room=="service"&&!prop&&n=="Technical_Twill"&&ShieldCoordinates(r,i);
                    if(room=="berth"&&!prop&&n=="Pressure_Fabric"&&berthCover){
                        // The cover atlas takes the roughness sampler on this
                        // slot, keeping the WebGL fragment sampler budget fixed.
                        block.SetTexture("_RoughMap",berthCover);block.SetFloat("_MappedRoughness",0);
                        block.SetFloat("_Roughness",.91f);block.SetFloat("_CabinSoftPanel",1);block.SetFloat("_FinishActive",0);
                    }
                    block.SetVector("_CabinTiles",tile);block.SetVector("_CabinLayer",new Vector4(count,Surface(n),0,shield?1:0));block.SetMatrix("_CabinRest",rest);
                    if(Grips.TryGetValue(id,out var g))block.SetVector("_CabinRub",new Vector4(g.x,g.y,g.z,1));
                }
                r.SetPropertyBlock(block,i);
            }
        }
        bool ShieldCoordinates(MeshRenderer renderer,int slot){
            var filter=renderer.GetComponent<MeshFilter>();if(!filter||!filter.sharedMesh||!filter.sharedMesh.isReadable)return false;
            var mesh=Instantiate(filter.sharedMesh);mesh.name=filter.sharedMesh.name+" · shield coordinates";filter.sharedMesh=mesh;owned.Add(mesh);
            var vertices=mesh.vertices;var coords=new Vector4[vertices.Length];var visited=new bool[vertices.Length];
            foreach(int i in mesh.GetIndices(slot)){
                if(visited[i])continue;visited[i]=true;
                var p=filter.transform.TransformPoint(vertices[i]);float best=.018f*.018f;
                foreach(var line in braidLines){
                    var offset=p-line.start;float t=Mathf.Clamp(Vector3.Dot(offset,line.axis),0,line.length);
                    var radial=offset-line.axis*t;float d=radial.sqrMagnitude;if(d>=best)continue;best=d;radial.Normalize();
                    coords[i]=new Vector4(line.arc+t,Vector3.Dot(radial,line.u),Vector3.Dot(radial,line.v),1);
                }
            }
            mesh.SetUVs(2,new List<Vector4>(coords));return true;
        }
        static void JacketCoordinates(MeshRenderer renderer,FurnishingSurface f) {
            if(f.rest==null||f.rest.Length<3)return;
            f.Sample(.5f,0); // Establish the deformable surface's private runtime mesh.
            var filter=renderer.GetComponent<MeshFilter>();if(!filter||!filter.sharedMesh||!filter.sharedMesh.isReadable)return;
            var mesh=filter.sharedMesh;if(mesh.HasVertexAttribute(UnityEngine.Rendering.VertexAttribute.TexCoord2))return;
            var rest=f.rest;int count=rest.Length-1;var d=new float[count+1];var u=new Vector3[count];var v=new Vector3[count];var basis=Vector3.right;
            for(int j=0;j<count;j++){
                var axis=rest[j+1]-rest[j];d[j+1]=d[j]+axis.magnitude;axis.Normalize();basis=Vector3.ProjectOnPlane(basis,axis).normalized;
                u[j]=basis;v[j]=Vector3.Cross(axis,basis);
            }
            var from=f.transform.worldToLocalMatrix*filter.transform.localToWorldMatrix;
            var coords=new List<Vector3>(mesh.vertexCount);
            foreach(var vertex in mesh.vertices){
                var p=from.MultiplyPoint3x4(vertex);float best=float.MaxValue,k=0;int index=0;var radial=Vector3.right;
                for(int j=0;j<count;j++){
                    var segment=rest[j+1]-rest[j];float along=Mathf.Clamp01(Vector3.Dot(p-rest[j],segment)/Mathf.Max(1e-10f,segment.sqrMagnitude));
                    var dist=p-rest[j]-along*segment;if(dist.sqrMagnitude<best){best=dist.sqrMagnitude;index=j;k=along;radial=dist.normalized;}
                }
                coords.Add(new Vector3(Mathf.Lerp(d[index],d[index+1],k),Vector3.Dot(radial,u[index]),Vector3.Dot(radial,v[index])));
            }
            mesh.SetUVs(2,coords);
        }
        public float FiberBendMM() {
            if(!fiber||fiber.rest.Length<9)return 0;
            int n=fiber.rest.Length;float least=float.MaxValue;
            for(int i=4;i<n-4;i++){
                Vector3 a=fiber.Sample((float)(i-3)/(n-1),0),b=fiber.Sample((float)i/(n-1),0),c=fiber.Sample((float)(i+3)/(n-1),0);
                float den=2*Vector3.Cross(b-a,c-b).magnitude;
                if(den>1e-9f)least=Mathf.Min(least,(b-a).magnitude*(c-b).magnitude*(c-a).magnitude/den);
            }
            return Mathf.Round(least*1000);
        }
        readonly List<UnityEngine.Object> owned=new List<UnityEngine.Object>();
        void GlandBank(string label,float y,int sides,Color tint,float metal,float rough,Vector2[] contour) {
            var vertices=new List<Vector3>();var normals=new List<Vector3>();var colors=new List<Color>();var tris=new List<int>();var uv=new List<Vector2>();
            for(int j=0;j<15;j++){
                var center=U(1.992f,y,3.029f+j/3*.25f+(j%3-1)*.052f);float scale=j%3==1&&y<1.78f?.86f:1;
                for(int k=0;k+1<contour.Length;k++)for(int side=0;side<sides;side++){
                    var top=contour[k];var bottom=contour[k+1];float slope=(bottom.x-top.x)/(top.y-bottom.y);
                    int start=vertices.Count;
                    for(int vertex=0;vertex<4;vertex++){
                        bool last=vertex>=2;var row=vertex==0||vertex==3?top:bottom;
                        float t=(float)(side+(last?1:0))/sides,theta=t*2*Mathf.PI+j*.87f;
                        float normalTheta=sides==6?((side+.5f)/sides)*2*Mathf.PI+j*.87f:theta;
                        vertices.Add(center+new Vector3(Mathf.Cos(theta)*row.x*scale,row.y,Mathf.Sin(theta)*row.x*scale));
                        normals.Add(new Vector3(Mathf.Cos(normalTheta),slope,Mathf.Sin(normalTheta)).normalized);uv.Add(new Vector2(t,row.y*34));colors.Add(Color.white);
                    }
                    tris.Add(start);tris.Add(start+3);tris.Add(start+2);tris.Add(start);tris.Add(start+2);tris.Add(start+1);
                }
            }
            var mesh=new Mesh{name=label};mesh.SetVertices(vertices);mesh.SetNormals(normals);mesh.SetColors(colors);mesh.SetUVs(0,uv);mesh.SetTriangles(tris,0);mesh.RecalculateBounds();
            var mat=new Material(Shader.Find("Upwell/Carriage finish")){name=label};mat.SetColor("_Color",tint);mat.SetFloat("_Metallic",metal);mat.SetFloat("_Roughness",rough);
            var g=new GameObject(label);g.transform.SetParent(transform,false);g.AddComponent<MeshFilter>().sharedMesh=mesh;g.AddComponent<MeshRenderer>().sharedMaterial=mat;
            owned.Add(mesh);owned.Add(mat);
        }
        Light TaskLight(string label,Vector3 pos,Vector3 target,Color color,float range,float angle,float power) {
            var g=new GameObject(label);g.transform.SetParent(transform,false);g.transform.position=pos;g.transform.forward=(target-pos).normalized;
            var light=g.AddComponent<Light>();light.type=LightType.Spot;light.spotAngle=angle;light.innerSpotAngle=angle*.35f;light.color=color;
            light.range=range;light.intensity=power;light.shadows=LightShadows.Soft;light.shadowBias=.008f;light.shadowNormalBias=.012f;light.shadowNearPlane=.055f;
            light.shadowResolution=UnityEngine.Rendering.LightShadowResolution.Medium;return light;
        }
        void UpdateLights(){if(!rack||!reading||!ride||ride.practicals.Length<3)return;reading.enabled=ride.practicals[1].enabled;rack.enabled=ride.practicals[2].enabled;}
        static float Ramp(float low,float high,float value)=>Mathf.SmoothStep(0,1,Mathf.InverseLerp(low,high,value));
        void UpdateDaylight(){
            if(!ride||!ride.exterior||!ride.exterior.sun)return;
            var ext=ride.exterior;float km=ride.Altitude;
            var dir=-ext.sun.transform.forward;float beam=ext.CloudTransmission,solar=ext.SolarVisibility*beam;
            float air=(1-Ramp(12,145,km))*Ramp(-.12f,.32f,dir.y);
            float disk=6371/(6371+Mathf.Max(0,km));disk=1-Mathf.Sqrt(Mathf.Max(0,1-disk*disk));
            float angle=Mathf.Acos(Mathf.Clamp(dir.y,-1,1)),phase=(Mathf.Sin(angle)+(Mathf.PI-angle)*Mathf.Cos(angle))/Mathf.PI;
            float ground=disk*phase;
            float terminal=Mathf.Max(1-Ramp(.017f,.064f,km),1-Ramp(12,70,(float)((AscentRoute.Terminal-ride.PreciseAltitude)*1000)));
            float transmission=1-.72f*terminal;
            var sky=Vector3.Lerp(new Vector3(.45f,.64f,1),new Vector3(.94f,.95f,.93f),1-beam);
            sky*=air*(1.75f+1.58f*(1-beam))*transmission;
            sky+=new Vector3(.39f,.56f,.77f)*(1.20f*ground*transmission);
            var earth=Vector3.Lerp(new Vector3(.39f,.54f,.69f),new Vector3(.84f,.89f,.92f),1-beam)*(2.7f*ground*transmission);
            var sun=Vector3.Lerp(new Vector3(1,.79f,.55f),new Vector3(1,.94f,.84f),Ramp(.04f,.43f,dir.y))*(solar*(.18f+1.4f*air)*transmission);
            float film=solarShade?solarShade.Position:0;if(ride.systems&&ride.systems.Film)film=1;
            Shader.SetGlobalVector(ApertureSky,new Vector4(sky.x,sky.y,sky.z,.29f*air));
            Shader.SetGlobalVector(ApertureEarth,earth);Shader.SetGlobalVector(ApertureSun,sun);
            Shader.SetGlobalVector(ApertureGain,new Vector4(Mathf.Max(0,dir.x),Mathf.Max(0,-dir.x),Mathf.Max(0,dir.z),1-.82f*film));
            // The original aperture lamps still catch textile sheen and polished
            // hardware. Diffuse transfer supplies the extended-window component.
            if(ext.windowBounce!=null)foreach(var light in ext.windowBounce)if(light)light.intensity*=.49f;
        }
        void LateUpdate(){UpdateLights();UpdateDaylight();}
        void OnDestroy(){foreach(var item in owned)if(item)Destroy(item);}
    }
}
