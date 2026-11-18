using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.SceneManagement;

namespace Upwell.Editor {
    public static class CarriageProject {
        const string Root="Assets/Upwell", Models=Root+"/SourceModels", Mats=Root+"/Materials", ScenePath=Root+"/Car07.unity";
        [Serializable] class Plan {public Part[] parts;public Finish[] materials,terminalMaterials,guideMaterials;public Projection[] cameras;public Station[] stations;public Flex[] flex;public Attachment[] mechanisms;public Guide guide;public Switch[] switches;public Bench apparatus;public Furnish[] furnishings;public TextureAlias[] textureAliases;}
        [Serializable] class TextureAlias {public string path,source;}
        [Serializable] class Furnish {public string id,room,file,parentId,kind;public float[] webPivot,u,v,rest,open,lower,upper;public float radius,maxOffset;public bool uvInverted;public int[] pinned,belts;public Fitting[] hardware;}
        [Serializable] class Fitting {public string id;public float u;}
        [Serializable] class Bench {public Gauge accelerometer;public Vessel capillary;public InstrumentPart[] parts;}
        [Serializable] class InstrumentPart {public string id,node,file,room,parentId;public float[] webPivot,parentLocalPivot;}
        [Serializable] class Gauge {public string id,node,massNode,testId;public float[] restCenter,testAxis;public float metersPerG,referenceG,testTravel;public Spring[] springs;}
        [Serializable] class Spring {public string node;public float[] fixedEnd,restMovingEnd;public float restLength,coilRadius;public int fixedEndSign,turns;}
        [Serializable] class Vessel {public string id,node,primerId;public float[] center,right,up,normal,primerAxis;public float radius,depth,primerTravel;public string[] standInNodes;}
        [Serializable] class Switch{public string id,kind;public float[] axis;public float amount;public int stops;}
        [Serializable] class Guide{public float repeatHeight,splicePeriod;public Part[] parts;public Roller[] rollers;public Placement[] placements;}
        [Serializable] class Roller{public string node;public float[] pivot;public float radius,sign;}
        [Serializable] class Placement{public string id;public float[] position;}
        [Serializable] class Flex {public string id,parentId,file,kind,material;public float[] points,widthGuide;public int[] pinned;public float limit,support,width,thickness;public bool hasSupport;}
        [Serializable] class Attachment {public string id,parentId,file,axis,label;public float[] parentLocalPivot;public float amount;public int detents;}
        [Serializable] class Station {public string station;public Part[] parts;public Fixture[] lights;}
        [Serializable] class Fixture {public string id;public float[] position,target,color;public float power,size;}
        [Serializable] class Projection {public string room;public float[] viewProjection;}
        [Serializable] class Part {public string id,room,file,title,action;public float[] pivot,focus,low,high,reference;public Motion animation;}
        [Serializable] class Motion {public string kind,axis;public float amount,phaseDelay;}
        [Serializable] class Finish {public string name,baseColor,roughnessMap,normal,family;public int[] rgb;public float metallic,roughness,alpha,emission;public bool alphaFromMap;}
        static Vector3 U(float[] a)=>new Vector3(a[0],a[1],-a[2]);
        static Vector3[] Triplets(float[] values){var result=new Vector3[values.Length/3];for(int n=0;n<result.Length;n++)result[n]=new Vector3(values[n*3],values[n*3+1],-values[n*3+2]);return result;}
        static Dictionary<string,string> textureAliases;
        static Texture Tex(string path)=>AssetDatabase.LoadAssetAtPath<Texture2D>(textureAliases!=null&&textureAliases.TryGetValue(path,out var canonical)?canonical:path);
        static T Asset<T>(T instance,string path) where T:UnityEngine.Object {
            var existing=AssetDatabase.LoadAssetAtPath<T>(path);
            if(existing){EditorUtility.CopySerialized(instance,existing);UnityEngine.Object.DestroyImmediate(instance);EditorUtility.SetDirty(existing);return existing;}
            AssetDatabase.CreateAsset(instance,path);return instance;
        }
        static Material Surface(Finish a,string folder=Models+"/Textures") {
            bool coatedDisplay=a.name=="Display_Phosphor"||a.name=="Handheld_Display";bool pixels=a.name.StartsWith("Pixels_"),trace=a.name.StartsWith("Trace_"),terminal=a.name=="Terminal_Display";
            bool weave=a.name=="Curtain_Acoustic"||a.name=="Quilt_Lining"||a.name=="Quilt_Ripstop"||a.name=="Berth_Bias_Tape";
            var shader=Shader.Find(weave?"Upwell/Woven textile":a.name=="Nav_Active_Pixels"?"Upwell/Optical flight panel":terminal?"Upwell/Terminal status":pixels?"Upwell/Bonded live readout":trace?"Upwell/Loom witness fibre":coatedDisplay?"Upwell/Coated instrument glass":a.alphaFromMap?"Upwell/Screen printed stencil":a.alpha<.5?"Upwell/Laminated glazing":"Upwell/Carriage finish");
            if(!shader||!shader.isSupported)throw new Exception("Shader unavailable: "+a.name);
            var mat=new Material(shader){name=a.name};
            if(weave){
                mat.mainTexture=Tex(folder+"/"+a.baseColor);mat.SetFloat("_Roughness",a.roughness);
                if(!string.IsNullOrEmpty(a.roughnessMap))mat.SetTexture("_RoughMap",Tex(folder+"/"+a.roughnessMap));else mat.SetFloat("_MappedRoughness",0);
                if(!string.IsNullOrEmpty(a.normal))mat.SetTexture("_BumpMap",Tex(folder+"/"+a.normal));
            }
            else if(a.name=="Nav_Active_Pixels"||a.alphaFromMap||coatedDisplay||pixels||terminal){mat.mainTexture=Tex(folder+"/"+a.baseColor);if(coatedDisplay)mat.SetFloat("_Emission",a.emission);}
            else if(trace){mat.SetColor("_Color",new Color(.19f,.24f,.25f));mat.SetColor("_TraceInk",a.name.EndsWith("Power")?new Color(1,.45f,.13f):a.name.EndsWith("Fiber")?new Color(.16f,1,.98f):a.name.EndsWith("Seal")?new Color(.30f,.68f,1):new Color(.89f,.87f,.59f));}
            else {
                Color c=new Color(a.rgb[0]/255f,a.rgb[1]/255f,a.rgb[2]/255f);
                mat.SetColor("_Color",!string.IsNullOrEmpty(a.baseColor)?Color.white:c);
                if(a.alpha<.5f)mat.SetFloat("_OpticalDepth",a.name=="Optical_Laminate"?a.alpha:.0014f);
                if(a.alpha<.5f)mat.SetFloat("_CabinFilm",a.name=="Surface_window"?1:0);
                if(a.alpha>=.5){
                    if(!string.IsNullOrEmpty(a.baseColor))mat.SetTexture("_MainTex",Tex(folder+"/"+a.baseColor));
                    if(!string.IsNullOrEmpty(a.roughnessMap)){mat.SetTexture("_RoughMap",Tex(folder+"/"+a.roughnessMap));mat.SetFloat("_MappedRoughness",1);}
                    if(!string.IsNullOrEmpty(a.normal))mat.SetTexture("_BumpMap",Tex(folder+"/"+a.normal));
                    mat.SetFloat("_NormalStrength",a.family=="metal"||a.name=="Titanium"||a.name=="Aluminum"||a.name=="Graphite_Alloy"?.30f:.53f);
                    mat.SetFloat("_Roughness",a.roughness);mat.SetFloat("_Metallic",a.metallic);mat.SetFloat("_Emission",a.emission);mat.SetFloat("_Instrument",a.name=="Display_Phosphor"?1:0);
                    bool cloth=a.family=="fabric"||a.name=="Technical_Twill"||a.name=="Aramid_Webbing"||a.name=="Pressure_Fabric"||a.name=="Restraint_Webbing";
                    mat.SetFloat("_Weave",cloth?1:0);mat.SetFloat("_OpalCircuit",a.name=="Opal_Emitter"?1:a.name=="Blue_Emitter"?2:0);
                    if(a.name=="Service_Print"){mat.SetFloat("_Metallic",.025f);mat.SetFloat("_Roughness",.60f);}
                    mat.SetFloat("_Cull",cloth||a.name=="Harness_Grip"?0:2);
                    bool plain=a.family=="glass"||a.name=="Smoked_Display"||a.name=="Carriage_Print"||a.name=="Paper"||a.emission>0;
                    mat.SetFloat("_FinishEligible",plain?0:1);
                }
            }return Asset(mat,Mats+"/"+a.name+".mat");
        }
        static GameObject New(string s,Transform parent=null){var g=new GameObject(s);if(parent)g.transform.SetParent(parent,false);return g;}
        static Bounds GetBounds(Transform root){
            bool first=true;var bounds=new Bounds();foreach(var mf in root.GetComponentsInChildren<MeshFilter>()){
                if(!mf.sharedMesh)continue;var b=mf.sharedMesh.bounds;
                for(int i=0;i<8;i++){var corner=b.center+Vector3.Scale(b.extents,new Vector3((i&1)==0?-1:1,(i&2)==0?-1:1,(i&4)==0?-1:1));Vector3 v=mf.transform.TransformPoint(corner);if(first){bounds=new Bounds(v,Vector3.zero);first=false;}else bounds.Encapsulate(v);}
            }return bounds;
        }
        static Bounds Expected(Part part){var a=U(part.low)-U(part.pivot);var b=U(part.high)-U(part.pivot);var bound=new Bounds(a,Vector3.zero);bound.Encapsulate(b);return bound;}
        static (Quaternion rot,Vector3 scale) ModelBasis(Plan plan) {
            var probes=new List<(Bounds got,Bounds want)>();
            foreach(var e in plan.parts){var prefab=AssetDatabase.LoadAssetAtPath<GameObject>(Models+"/"+e.file);if(!prefab)throw new Exception("Missing model "+e.file);probes.Add((GetBounds(prefab.transform),Expected(e)));}
            var obs=probes[0];float unit=obs.want.size.magnitude/obs.got.size.magnitude;
            if(Mathf.Abs(unit-1)<.002f)unit=1;
            float min=float.MaxValue;Quaternion rot=Quaternion.identity;Vector3 scale=Vector3.one;float worst=99;
            foreach(var forward in new[]{Vector3.forward,Vector3.back,Vector3.right,Vector3.left,Vector3.up,Vector3.down})
            foreach(var up in new[]{Vector3.forward,Vector3.back,Vector3.right,Vector3.left,Vector3.up,Vector3.down}){
                if(Mathf.Abs(Vector3.Dot(forward,up))>.5f)continue;
                var q=Quaternion.LookRotation(forward,up);foreach(int sign in new[]{1,-1}){
                    var k=new Vector3(unit*sign,unit,unit);float score=0,maximum=0;
                    foreach(var pair in probes){var c=q*Vector3.Scale(pair.got.center,k);var z=q*Vector3.Scale(pair.got.size,k);z=new Vector3(Mathf.Abs(z.x),Mathf.Abs(z.y),Mathf.Abs(z.z));
                        float err=(c-pair.want.center).magnitude+(z-pair.want.size).magnitude;score+=err*err;maximum=Mathf.Max(maximum,err);}
                    if(score<min){min=score;rot=q;scale=k;worst=maximum;}
                }
            }
            Debug.Log("UPWELL basis "+rot.eulerAngles+" scale "+scale+" maximum aggregate bounds error "+worst.ToString("F5")+" m");
            if(worst>.12f)throw new Exception("FBX basis does not match the room survey: "+worst);
            return(rot,scale);
        }
        static Light LightAt(Transform owner,string name,LightType type,Vector3 position,Vector3 aim,Color tint,float intensity,float range,bool shadows){
            var g=New(name,owner);g.transform.position=position;g.transform.rotation=Quaternion.LookRotation(aim);
            var l=g.AddComponent<Light>();l.type=type;l.color=tint;l.intensity=intensity;l.range=range;l.shadows=shadows?LightShadows.Soft:LightShadows.None;l.shadowStrength=.76f;l.shadowBias=.012f;l.shadowNormalBias=.06f;l.shadowNearPlane=.017f;l.renderMode=LightRenderMode.ForcePixel;l.cullingMask=~(1<<Passenger.InspectionLayer);return l;
        }
        static GameObject Barrier(Transform parent,string name,Vector3 center,Vector3 size){var go=New(name,parent);go.transform.localPosition=center;go.AddComponent<BoxCollider>().size=size;return go;}
        static Dictionary<string,Material> SourceMaterials(Plan plan){var outp=new Dictionary<string,Material>();foreach(var s in plan.materials)outp[s.name]=Surface(s);return outp;}
        static Material Hardware(string n,Color c,float metal,float smooth,float emissive=0){
            var m=new Material(Shader.Find("Standard")){name=n,color=c};m.SetFloat("_Metallic",metal);m.SetFloat("_Glossiness",smooth);if(emissive>0){m.EnableKeyword("_EMISSION");m.SetColor("_EmissionColor",c*emissive);}
            return Asset(m,Mats+"/"+n+".mat");
        }
        static Texture3D WeatherVolume(){
            var bytes=AssetDatabase.LoadAssetAtPath<TextAsset>(Root+"/Environment/CloudNoise.bytes");
            if(!bytes||bytes.bytes.Length!=64*64*64*4)throw new Exception("Missing 64³ weather density field.");
            string path=Root+"/Environment/WeatherNoise.asset";var texture=AssetDatabase.LoadAssetAtPath<Texture3D>(path);
            if(!texture){texture=new Texture3D(64,64,64,TextureFormat.RGBA32,false){name="Periodic cloud density field"};AssetDatabase.CreateAsset(texture,path);}
            texture.wrapMode=TextureWrapMode.Repeat;texture.filterMode=FilterMode.Bilinear;texture.SetPixelData(bytes.bytes,0);texture.Apply(false,false);EditorUtility.SetDirty(texture);return texture;
        }
        static StationRig AssembleStation(Transform parent,Station info,Dictionary<string,Material> materials){
            var root=New(info.station=="anchor"?"Equatorial Anchor · launch bay":"Aster Reach · receiving bay",parent);
            var station=root.AddComponent<StationRig>();station.receiving=info.station=="aster";
            var moving=new List<StationRig.Mechanism>();
            foreach(var e in info.parts){
                var pivot=New(e.id,root.transform);pivot.transform.localPosition=U(e.pivot);
                var source=AssetDatabase.LoadAssetAtPath<GameObject>(Root+"/Terminals/"+e.file);if(!source)throw new Exception("Missing station fabrication "+e.file);
                Bounds got=GetBounds(source.transform),want=Expected(e);
                if((got.center-want.center).magnitude+(got.size-want.size).magnitude>.16f)throw new Exception("Unaligned station FBX "+e.id+" vs "+want);
                var geometry=UnityEngine.Object.Instantiate(source,pivot.transform,false);geometry.name=e.id+" mesh";
                bool vertexCheck=false;var expectedVertex=U(e.reference);
                foreach(var mf in geometry.GetComponentsInChildren<MeshFilter>()){
                    if(!vertexCheck){foreach(var v in mf.sharedMesh.vertices)if((pivot.transform.InverseTransformPoint(mf.transform.TransformPoint(v))-expectedVertex).sqrMagnitude<.0016f){vertexCheck=true;break;}}
                    var r=mf.GetComponent<MeshRenderer>();r.gameObject.layer=ExteriorRig.ExteriorLayer;
                    r.sharedMaterials=r.sharedMaterials.Select(m=>materials[m.name.Replace(" (Instance)","")]).ToArray();
                    r.shadowCastingMode=ShadowCastingMode.On;r.receiveShadows=true;
                }
                if(!vertexCheck)throw new Exception("Asymmetric survey point absent in "+e.id);
                var a=e.animation;if(a==null||string.IsNullOrEmpty(a.kind))continue;
                Vector3 axis=a.axis=="x"?Vector3.right:a.axis=="y"?Vector3.up:Vector3.forward;
                if(a.kind=="translate"&&a.axis=="z"||a.kind!="translate"&&a.axis!="z")axis=-axis;
                moving.Add(new StationRig.Mechanism{part=pivot.transform,id=e.id,kind=a.kind,axis=axis,home=pivot.transform.localPosition,rest=pivot.transform.localRotation,amount=a.amount,delay=a.phaseDelay});
            }
            station.actuators=moving.ToArray();var lights=new List<Light>();
            foreach(var f in info.lights){var pos=U(f.position);var aim=U(f.target)-pos;
                var light=LightAt(root.transform,f.id,LightType.Spot,pos,aim,new Color(f.color[0],f.color[1],f.color[2]),Mathf.Clamp(f.power/107f,1.4f,10),Mathf.Max(8,aim.magnitude*2.9f),true);
                light.spotAngle=85;light.innerSpotAngle=39;light.shadowStrength=.84f;lights.Add(light);}
            station.lights=lights.ToArray();station.SetState(0,0);Debug.Log("UPWELL station "+info.station+" imported "+info.parts.Length+" measured FBXs and "+lights.Count+" fixture-matched lights.");
            return station;
        }
        [MenuItem("Upwell/Assemble carriage")]
        public static void Assemble(){
            var text=AssetDatabase.LoadAssetAtPath<TextAsset>(Models+"/UnityLayout.json");if(!text)throw new Exception("Missing prepared source manifest.");
            var plan=JsonUtility.FromJson<Plan>(text.text);if(plan.parts.Length<27||plan.switches==null||plan.switches.Length!=20)throw new Exception("Missing room or switch fabrication");
            if(!AssetDatabase.IsValidFolder(Mats))AssetDatabase.CreateFolder(Root,"Materials");
            PlayerSettings.companyName="Upwell";PlayerSettings.productName="Upwell — Car 07";PlayerSettings.colorSpace=ColorSpace.Linear;
            PlayerSettings.defaultScreenWidth=1600; PlayerSettings.defaultScreenHeight=900;PlayerSettings.fullScreenMode=FullScreenMode.Windowed; PlayerSettings.defaultIsNativeResolution=false;
            PlayerSettings.SetScriptingBackend(NamedBuildTarget.Standalone,ScriptingImplementation.Mono2x);
            textureAliases=plan.textureAliases?.ToDictionary(a=>a.path,a=>a.source);var materials=SourceMaterials(plan);var basis=ModelBasis(plan);
            var scene=EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);var root=New("Upwell · Car 07");
            var rooms=new Dictionary<string,Transform>();var mapped=new Dictionary<string,TransitProp>();Transform impeller=null;
            var switches=plan.switches.ToDictionary(q=>q.id,q=>q);
            foreach(var entry in plan.parts) {
                if(!rooms.TryGetValue(entry.room,out var room))rooms[entry.room]=room=New(entry.room,root.transform).transform;
                var owner=New(entry.title,room);owner.transform.position=U(entry.pivot);
                var source=AssetDatabase.LoadAssetAtPath<GameObject>(Models+"/"+entry.file);
                var geometry=UnityEngine.Object.Instantiate(source,owner.transform,false);geometry.name=Path.GetFileNameWithoutExtension(entry.file);
                var correction=New("Fabrication basis",owner.transform).transform;geometry.transform.SetParent(correction,false);correction.localRotation=basis.rot;correction.localScale=basis.scale;
                foreach(var mf in geometry.GetComponentsInChildren<MeshFilter>()){
                    mf.gameObject.layer=entry.id=="shell"?Passenger.ShellRay:Passenger.PropRay;var ren=mf.GetComponent<MeshRenderer>();
                    var names=ren.sharedMaterials.Select(m=>m?m.name.Replace(" (Instance)",""):"").ToArray();
                    foreach(var n in names)if(!materials.ContainsKey(n))throw new Exception(entry.file+" unknown FBX finish '"+n+"'");
                    ren.sharedMaterials=names.Select(n=>materials[n]).ToArray();ren.shadowCastingMode=ShadowCastingMode.On;ren.receiveShadows=true;
                    var c=mf.gameObject.AddComponent<MeshCollider>();c.sharedMesh=mf.sharedMesh;
                }
                if(entry.id=="shell")continue;
                if(entry.id=="blower_rotor"){impeller=owner.transform;continue;}
                var prop=owner.AddComponent<TransitProp>();prop.id=entry.id;prop.room=entry.room;prop.title=entry.title;prop.action=entry.action;
                prop.localFocus=U(entry.focus)-U(entry.pivot);
                prop.portable=new[]{"field_glasses","mug","tool_roll","logbook","access_card"}.Contains(entry.id);
                if(prop.portable)correction.gameObject.AddComponent<EquipmentMount>();
                if(entry.animation!=null&&!string.IsNullOrEmpty(entry.animation.kind)){
                    prop.motion=entry.animation.kind;prop.amount=entry.animation.amount;
                    Vector3 axis=entry.animation.axis=="x"?Vector3.right:entry.animation.axis=="y"?Vector3.up:Vector3.forward;
                    if(prop.motion=="translate"&&entry.animation.axis=="z"||prop.motion=="rotate"&&entry.animation.axis!="z")axis=-axis;
                    prop.motionAxis=axis;
                }
                if(switches.TryGetValue(entry.id,out var sw)){prop.panelControl=true;prop.motion=sw.kind;prop.motionAxis=U(sw.axis)*(sw.kind=="rotate"?-1:1);prop.amount=sw.amount;
                    prop.neutral=entry.id=="panel_gain"?.50f:entry.id=="camera_focus"?.25f:entry.id=="cabin_lights"||entry.id=="vent_fan"?1:0;}
                if(entry.id=="accel_test"||entry.id=="capillary_primer")prop.panelControl=true;
                if(entry.id=="locker_drawer"||entry.id=="pressure_hatch"||entry.id=="service_cabinet"){
                    var carriage=owner.AddComponent<Rigidbody>();carriage.useGravity=false;carriage.isKinematic=true;
                    carriage.interpolation=RigidbodyInterpolation.Interpolate;carriage.collisionDetectionMode=CollisionDetectionMode.ContinuousSpeculative;
                }
                var b=Expected(entry);if(new[]{"bunk","lounge_seat","pressure_hatch","pilot_console"}.Contains(entry.id)){
                    var hullProxy=Barrier(owner.transform,"Physical envelope",b.center,b.size);
                    if(entry.id=="bunk")hullProxy.layer=15; // Personal clearance, above the actual mattress colliders.
                }
                if(prop.portable||prop.panelControl||new[]{"ascent_lever","card_reader","breaker","grab_handle"}.Contains(entry.id)){
                    var hit=New("Hand reach",owner.transform);hit.layer=Passenger.PropRay;var c=hit.AddComponent<BoxCollider>();c.isTrigger=true;c.center=b.center;c.size=Vector3.Max(b.size,Vector3.one*.052f);
                }
                mapped.Add(entry.id,prop);
            }
            if(plan.flex==null||plan.flex.Length!=7||plan.mechanisms==null||plan.mechanisms.Length!=4)throw new Exception("Missing compliant or operable equipment geometry");
            GameObject Accessory(string name,string file,Transform pivot){
                var asset=AssetDatabase.LoadAssetAtPath<GameObject>(Models+"/"+file);if(!asset)throw new Exception("Missing accessory "+file);
                var mesh=UnityEngine.Object.Instantiate(asset,pivot,false);mesh.name=name;
                foreach(var r in mesh.GetComponentsInChildren<MeshRenderer>()){r.gameObject.layer=Passenger.PropRay;r.sharedMaterials=r.sharedMaterials.Select(m=>materials[m.name.Replace(" (Instance)","")]).ToArray();r.shadowCastingMode=ShadowCastingMode.On;r.receiveShadows=true;}
                return mesh;
            }
            foreach(var f in plan.flex){
                var parent=mapped[f.parentId].transform;var go=Accessory(f.id,f.file,parent);var mf=go.GetComponentInChildren<MeshFilter>();var strip=mf.gameObject.AddComponent<FlexibleTail>();
                strip.partId=f.id;strip.limit=f.limit;strip.pinned=f.pinned;strip.hasSupport=f.hasSupport;strip.support=f.support;strip.source=mf.sharedMesh;
                strip.width=f.width;strip.thickness=f.thickness;strip.widthGuide=U(f.widthGuide);strip.roundCord=f.kind=="cord";strip.strandMaterial=materials[f.material];
                strip.rest=new Vector3[f.points.Length/3];for(int j=0;j<strip.rest.Length;j++){var p=new Vector3(f.points[3*j],f.points[3*j+1],-f.points[3*j+2]);strip.rest[j]=mf.transform.InverseTransformPoint(parent.TransformPoint(p));}
            }
            foreach(var a in plan.mechanisms){
                var pivot=New(a.id,mapped[a.parentId].transform);pivot.transform.localPosition=U(a.parentLocalPivot);Accessory(a.id+" hardware",a.file,pivot.transform);
                var m=pivot.AddComponent<HandMechanism>();m.partId=a.id;m.label=a.label;m.detents=a.detents;m.angle=a.amount;m.axis=a.axis=="z"?Vector3.forward:a.axis=="y"?Vector3.down:Vector3.left;
            }
            if(plan.cameras!=null)foreach(var spec in plan.cameras) {
                if(spec.viewProjection==null||spec.viewProjection.Length!=16)throw new Exception("Invalid projection "+spec.room);
                Matrix4x4 matrix=Matrix4x4.zero;for(int i=0;i<16;i++)matrix[i/4,i%4]=spec.viewProjection[i];
                var fit=rooms[spec.room].gameObject.AddComponent<RegisteredFinish>();fit.room=spec.room;fit.webToClip=matrix;
                fit.detail=Tex(Root+"/Finish/"+spec.room+"-detail.png") as Texture2D;fit.depth=Tex(Root+"/Finish/"+spec.room+"-depth.png") as Texture2D;
                if(!fit.detail||!fit.depth)throw new Exception("Missing registered finish "+spec.room);
            }
            Debug.Log("UPWELL registered finish layers: "+(plan.cameras==null?0:plan.cameras.Length));
            var hull=New("Crew movement envelope",root.transform).transform;
            Barrier(hull,"Deck",new Vector3(0,-.095f,0),new Vector3(4.44f,.21f,11.55f));
            foreach(int sign in new[]{-1,1}){
                Barrier(hull,"Side",new Vector3(sign*2.24f,1.34f,0),new Vector3(.19f,2.7f,11.50f));
                Barrier(hull,"End",new Vector3(0,1.33f,sign*5.73f),new Vector3(4.48f,2.7f,.18f));
                foreach(float z in new[]{-1.9f,1.9f})Barrier(hull,"Partition",new Vector3(sign*1.51f,1.34f,z),new Vector3(1.63f,2.7f,.14f));
            }
            var env=New("Aster Reach exterior",root.transform).AddComponent<ExteriorRig>();
            env.liveRadiance=Shader.Find("Upwell/Live exterior radiance");
            if(plan.stations==null||plan.stations.Length!=2)throw new Exception("Both fabricated terminal bays are required.");
            foreach(var stock in plan.terminalMaterials)materials[stock.name]=Surface(stock,Root+"/Terminals/Textures");
            foreach(var st in plan.stations){var rig=AssembleStation(env.transform,st,materials);if(rig.receiving)env.arrivalBay=rig;else env.anchorBay=rig;}
            var water=New("Atlantic surface",env.anchorBay.transform);water.layer=ExteriorRig.ExteriorLayer;water.transform.localPosition=Vector3.down*7;
            int grid=112;var patch=new Vector3[(grid+1)*(grid+1)];var triangles=new int[grid*grid*6];int ti=0;
            float Distribution(int i){float t=2f*i/grid-1;return Mathf.Sign(t)*(Mathf.Abs(t)*.025f+Mathf.Pow(Mathf.Abs(t),2.75f)*.975f)*1150;}
            for(int y=0;y<=grid;y++)for(int x=0;x<=grid;x++){int a=y*(grid+1)+x;patch[a]=new Vector3(Distribution(x),0,Distribution(y));if(x<grid&&y<grid){triangles[ti++]=a;triangles[ti++]=a+grid+1;triangles[ti++]=a+1;triangles[ti++]=a+1;triangles[ti++]=a+grid+1;triangles[ti++]=a+grid+2;}}
            var ocean=new Mesh{name="Atlantic gravity waves"};ocean.vertices=patch;ocean.triangles=triangles;ocean.RecalculateBounds();water.AddComponent<MeshFilter>().sharedMesh=Asset(ocean,Root+"/Environment/AnchorWater.asset");
            var surf=water.AddComponent<MeshRenderer>();surf.sharedMaterial=Asset(new Material(Shader.Find("Upwell/Equatorial Atlantic")),Mats+"/AtlanticWater.mat");surf.shadowCastingMode=ShadowCastingMode.Off;
            if(plan.guide==null||plan.guide.parts.Length!=11)throw new Exception("Missing original guideway kit.");
            foreach(var s in plan.guideMaterials)materials[s.name]=Surface(s,Root+"/Guideway/Textures");
            var guide=New("Ribbon guideways",env.transform).AddComponent<GuidewayRig>();env.guideway=guide;
            var library=New("Guideway source parts",guide.transform);var sourceParts=new Dictionary<string,GameObject>();
            foreach(var p in plan.guide.parts){
                var prefab=AssetDatabase.LoadAssetAtPath<GameObject>(Root+"/Guideway/"+p.file);if(!prefab)throw new Exception("Missing guideway part "+p.file);
                var g=UnityEngine.Object.Instantiate(prefab,library.transform,false);g.name=p.id;
                foreach(var r in g.GetComponentsInChildren<MeshRenderer>()){r.gameObject.layer=ExteriorRig.ExteriorLayer;r.sharedMaterials=r.sharedMaterials.Select(m=>materials[m.name.Replace(" (Instance)","")]).ToArray();
                    r.shadowCastingMode=ShadowCastingMode.On;r.receiveShadows=true;foreach(var m in r.sharedMaterials)m.enableInstancing=true;}
                sourceParts[p.id]=g;
            }
            library.SetActive(false);guide.span=sourceParts["load_span"];guide.splice=sourceParts["splice"];guide.bogie=sourceParts["bogie"];guide.tow=materials["Tow_Carbon"];guide.rail=materials["Titanium"];
            guide.repeat=plan.guide.repeatHeight;guide.spliceEvery=plan.guide.splicePeriod;guide.lanes=plan.guide.placements.Select(s=>U(s.position)).ToArray();
            guide.rollers=plan.guide.rollers.Select(w=>new GuidewayRig.Roller{id=w.node,mesh=sourceParts[w.node],pivot=U(w.pivot),radius=w.radius,sign=w.sign}).ToArray();
            env.reflectionKernels=new[]{"Hidden/CubeCopy","Hidden/CubeBlur","Hidden/CubeBlend"}.Select(Shader.Find).Where(s=>s).ToArray();
            var sky=new Material(Shader.Find("Upwell/Moving atmosphere and Earth")){name="Orbital atmosphere"};
            sky.SetTexture("_Albedo",Tex(Root+"/Environment/EarthAlbedo.jpg"));sky.SetTexture("_Night",Tex(Root+"/Environment/EarthNight.jpg"));sky.SetTexture("_Broad",Tex(Root+"/Environment/EarthWeatherClimatology.jpg"));sky.SetTexture("_NoiseField",WeatherVolume());sky.SetVector("_SunLocal",AscentRoute.Sun(0));
            sky.SetTexture("_Atlantic",Tex(Root+"/Environment/AtlanticWeather.png"));
            if(!sky.GetTexture("_Albedo")||!sky.GetTexture("_Night")||!sky.GetTexture("_Atlantic"))throw new Exception("Missing geographic Earth or regional weather assets.");
            RenderSettings.skybox=Asset(sky,Mats+"/RouteSky.mat");
            RenderSettings.ambientMode=AmbientMode.Trilight;RenderSettings.ambientSkyColor=new Color(.22f,.29f,.34f);RenderSettings.ambientEquatorColor=new Color(.14f,.17f,.20f);RenderSettings.ambientGroundColor=new Color(.09f,.10f,.11f);RenderSettings.reflectionIntensity=.81f;
            env.graphite=Hardware("Orbital carbon",new Color(.12f,.15f,.17f),.59f,.48f);env.titanium=Hardware("Orbital titanium",new Color(.59f,.63f,.65f),.76f,.57f);
            env.pearl=Hardware("Orbital ceramic",new Color(.79f,.82f,.82f),.28f,.49f);env.glass=Hardware("Orbital glazing",new Color(.19f,.29f,.35f),.62f,.90f);
            env.amber=Hardware("Inspection ceramic",new Color(.87f,.38f,.13f),.48f,.53f);env.beacon=Hardware("Terminal beacon",new Color(.84f,.90f,.99f),.12f,.55f,2);
            env.rangePaint=Hardware("Capture flood body",new Color(.56f,.61f,.64f),.54f,.49f);env.rangeLamp=Hardware("Capture apron worklight",new Color(.68f,.87f,1),.12f,.48f,3.2f);
            var hab=New("Aster Reach rotating cylinder",env.transform);hab.layer=ExteriorRig.ExteriorLayer;hab.transform.position=new Vector3(15,4.8f,48);hab.transform.rotation=Quaternion.Euler(-14,64,-7);
            // The physical FBX settlement, its moving valley and optical coatings are installed by OrbitalHardware.
            env.habitat=hab.transform;
            env.sun=LightAt(env.transform,"Direct solar illumination",LightType.Directional,Vector3.zero,-AscentRoute.Sun(0),Color.white,2.7f,500,true);env.sun.shadowStrength=.95f;env.sun.shadowResolution=LightShadowResolution.VeryHigh;RenderSettings.sun=env.sun;
            env.windowBounce=new Light[4];
            env.windowBounce[0]=LightAt(root.transform,"Earth irradiance · forward window",LightType.Spot,new Vector3(-.55f,1.94f,5.51f),new Vector3(.1f,-.08f,-1),new Color(.77f,.90f,1),1,5.5f,true);
            env.windowBounce[1]=LightAt(root.transform,"Earth irradiance · berth port",LightType.Spot,new Vector3(2.16f,1.84f,-.03f),new Vector3(-1,-.16f,0),new Color(.77f,.90f,1),.70f,4.15f,true);
            env.windowBounce[2]=LightAt(root.transform,"Earth irradiance · service port",LightType.Spot,new Vector3(-2.14f,1.69f,-3.68f),new Vector3(1,-.13f,0),new Color(.77f,.90f,1),.64f,3.75f,true);
            env.windowBounce[3]=LightAt(root.transform,"Earth irradiance · deck port",LightType.Spot,new Vector3(0,.075f,3.80f),Vector3.up,new Color(.68f,.83f,1),.48f,3.6f,true);
            foreach(var aperture in env.windowBounce){aperture.spotAngle=119;aperture.innerSpotAngle=69;aperture.shadowStrength=.64f;}
            var ride=root.AddComponent<TransitRide>();ride.exterior=env;ride.practicals=new Light[3];env.roomReflections=new ReflectionProbe[3];
            if(!AssetDatabase.LoadAssetAtPath<GameObject>(Root+"/Resources/Fracture/FractureCartridge.fbx"))throw new InvalidOperationException("The shared fracture cartridge FBX is required for the service bay.");
            ride.fracture=New("Ceramic proof bench",rooms["service"]).AddComponent<FractureCartridge>();ride.fracture.ride=ride;
            var systems=root.AddComponent<CabinSystems>();systems.ride=ride;systems.fanRotor=impeller;ride.systems=systems;
            if(plan.apparatus?.parts!=null&&plan.apparatus.parts.Length>0){
                var apparatus=plan.apparatus;var gauge=apparatus.accelerometer;var vessel=apparatus.capillary;
                var experiments=root.AddComponent<CabinExperiments>();experiments.ride=ride;ride.experiments=experiments;
                experiments.metresPerG=gauge.metersPerG;experiments.referenceG=gauge.referenceG;
                Transform GaugePart(string node,float[] position){
                    var spec=apparatus.parts.FirstOrDefault(part=>part.node==node||part.id==node);
                    if(spec==null||string.IsNullOrEmpty(spec.file))throw new Exception("Missing surveyed component "+node);
                    var pivot=New(node,mapped[gauge.id].transform).transform;pivot.position=U(position);
                    Accessory(node+" fabrication",spec.file,pivot);return pivot;
                }
                experiments.proofMass=GaugePart(gauge.massNode,gauge.restCenter);
                foreach(var spring in gauge.springs){
                    var piece=GaugePart(spring.node,spring.fixedEnd);var fixedEnd=U(spring.fixedEnd);var movingEnd=U(spring.restMovingEnd);
                    var wire=piece.gameObject.AddComponent<ProofSpring>();wire.restLength=spring.restLength;wire.sign=movingEnd.y>fixedEnd.y?1:-1;
                    wire.turns=spring.turns>0?spring.turns:wire.sign<0?7:5;wire.coilRadius=spring.coilRadius>0?spring.coilRadius:.0092f;
                    if(fixedEnd.y>movingEnd.y){
                        experiments.upperWire=wire;experiments.upperSpring=piece;experiments.upperFixed=fixedEnd;experiments.upperMoving=movingEnd;experiments.upperLength=spring.restLength;
                    }else{
                        experiments.lowerWire=wire;experiments.lowerSpring=piece;experiments.lowerFixed=fixedEnd;experiments.lowerMoving=movingEnd;experiments.lowerLength=spring.restLength;
                    }
                }
                var test=mapped[gauge.testId];test.motion="press";test.motionAxis=U(gauge.testAxis);test.amount=gauge.testTravel;
                var lampPosition=new Vector3(-.73f,1.445f,5.17f);var lampDirection=new Vector3(-.75f,1.25f,5.215f)-lampPosition;
                experiments.scaleLamp=LightAt(mapped[gauge.id].transform,"Louvered scale light",LightType.Spot,lampPosition,lampDirection,new Color(1,.95f,.85f),1.45f,.52f,true);
                experiments.scaleLamp.spotAngle=74;experiments.scaleLamp.innerSpotAngle=43;experiments.scaleLamp.shadowNearPlane=.005f;experiments.scaleLamp.shadowBias=.006f;
                var lens=GameObject.CreatePrimitive(PrimitiveType.Cube);lens.name="Recessed scale-light diffuser";lens.transform.SetParent(experiments.scaleLamp.transform,false);
                lens.transform.localPosition=new Vector3(0,0,-.002f);lens.transform.localScale=new Vector3(.077f,.004f,.004f);UnityEngine.Object.DestroyImmediate(lens.GetComponent<Collider>());
                var lensRenderer=lens.GetComponent<MeshRenderer>();lensRenderer.sharedMaterial=Hardware("Scale illuminator lens",new Color(.98f,.94f,.80f),.04f,.36f,1.25f);lensRenderer.shadowCastingMode=ShadowCastingMode.Off;
                var primer=mapped[vessel.primerId];primer.motion="press";primer.motionAxis=U(vessel.primerAxis);primer.amount=vessel.primerTravel;
                var chamber=mapped[vessel.id];var fluid=chamber.gameObject.AddComponent<CapillaryCell>();experiments.fluid=fluid;
                fluid.radius=vessel.radius;fluid.depth=vessel.depth;fluid.center=U(vessel.center);
                fluid.right=U(vessel.right).normalized;fluid.up=U(vessel.up).normalized;fluid.front=U(vessel.normal).normalized;
                var body=GameObject.CreatePrimitive(PrimitiveType.Cube);body.name="Sealed liquid volume";body.transform.SetParent(chamber.transform,false);
                body.transform.position=fluid.center;body.transform.rotation=Quaternion.LookRotation(fluid.front,fluid.up);
                body.transform.localScale=new Vector3(vessel.radius*2,vessel.radius*2,vessel.depth);
                UnityEngine.Object.DestroyImmediate(body.GetComponent<Collider>());var optical=body.GetComponent<MeshRenderer>();fluid.volume=optical;
                optical.shadowCastingMode=ShadowCastingMode.Off;optical.receiveShadows=false;
                var shader=Shader.Find("Upwell/Sealed capillary fluid");if(!shader)throw new Exception("Missing liquid chamber optics.");
                optical.sharedMaterial=Asset(new Material(shader),Mats+"/Sealed capillary water.mat");
            }
            if(plan.furnishings!=null&&plan.furnishings.Length>0){
                var fittings=new Dictionary<string,Transform>();var moving=new Dictionary<string,FurnishingSurface>();
                foreach(var part in plan.furnishings){
                    var control=mapped[part.parentId=="shell"?"service_cabinet":part.parentId];
                    var pivot=New(part.id,part.kind=="curtainHardware"?control.transform:rooms[part.room]);
                    pivot.transform.position=U(part.webPivot);
                    var geometry=Accessory(part.id+" fabrication",part.file,pivot.transform);
                    if(part.kind=="curtainHardware"){
                        fittings[part.id]=pivot.transform;
                        foreach(var mf in geometry.GetComponentsInChildren<MeshFilter>()){var c=mf.gameObject.AddComponent<MeshCollider>();c.sharedMesh=mf.sharedMesh;}
                        if(part.id=="curtain_stile"){
                            var leading=pivot.AddComponent<CurtainHandle>();leading.control=control;
                            var grip=New("Black handle grip",pivot.transform);grip.layer=Passenger.PropRay;
                            var touch=grip.AddComponent<BoxCollider>();touch.isTrigger=true;touch.center=leading.gripCenter;touch.size=new Vector3(.043f,.199f,.064f);
                        }
                        continue;
                    }
                    var surface=pivot.AddComponent<FurnishingSurface>();surface.partId=part.id;surface.ride=ride;surface.control=control;
                    surface.type=part.kind=="quilt"?FurnishingSurface.FabricType.Quilt:part.kind=="curtain"?FurnishingSurface.FabricType.Curtain:FurnishingSurface.FabricType.Cable;
                    surface.rest=Triplets(part.rest);surface.extended=Triplets(part.open);surface.u=part.u;surface.v=part.v;
                    surface.pinned=part.pinned;surface.beltRows=part.belts;surface.radius=part.radius;surface.cableTravel=part.maxOffset;surface.flipBindingV=part.uvInverted;
                    if(part.lower!=null&&part.lower.Length==3){var a=U(part.lower);var b=U(part.upper);surface.hasClearance=true;surface.clearanceMin=Vector3.Min(a,b);surface.clearanceMax=Vector3.Max(a,b);}
                    moving[part.id]=surface;
                }
                foreach(var part in plan.furnishings.Where(p=>p.hardware!=null&&p.hardware.Length>0)){
                    moving[part.id].runners=part.hardware.Select(f=>fittings[f.id]).ToArray();
                    moving[part.id].runnerWeights=part.hardware.Select(f=>f.u).ToArray();
                }
                moving["cloth_berth_curtain"].quilt=moving["cloth_berth_quilt"];
                mapped["privacy_curtain"].motion="";
            }
            systems.portFixture=LightAt(root.transform,"Port saloon ceiling practical",LightType.Spot,new Vector3(-1.60f,2.41f,3.72f),new Vector3(.65f,-1,.01f),new Color(.96f,.975f,1),1.32f,4.15f,true);
            systems.portFixture.spotAngle=116;systems.portFixture.innerSpotAngle=72;
            for(int i=0;i<3;i++){
                float z=(1-i)*3.8f;float side=i==1?-1:1;var light=LightAt(root.transform,"Recessed practical "+i,LightType.Spot,new Vector3(side*1.64f,2.38f,z),new Vector3(-side*.61f,-.95f,.08f),new Color(1,.971f,.94f),2.35f,4.55f,true);light.spotAngle=117;light.innerSpotAngle=61;ride.practicals[i]=light;
                var probeGo=New("Laminated cabin reflections "+i,root.transform);probeGo.transform.position=new Vector3(0,1.37f,z);
                var probe=probeGo.AddComponent<ReflectionProbe>();probe.mode=ReflectionProbeMode.Realtime;probe.refreshMode=ReflectionProbeRefreshMode.ViaScripting;
                probe.timeSlicingMode=ReflectionProbeTimeSlicingMode.IndividualFaces;probe.boxProjection=true;probe.size=new Vector3(4.43f,2.67f,3.88f);probe.resolution=128;probe.nearClipPlane=.075f;probe.farClipPlane=16000;probe.cullingMask=~(1<<Passenger.InspectionLayer);probe.intensity=.78f;env.roomReflections[i]=probe;
            }
            AudioClip Audio(string clip)=>AssetDatabase.LoadAssetAtPath<AudioClip>(Root+"/Audio/"+clip+".wav");
            ride.motor=Audio("Traction");ride.relay=Audio("Relay");ride.runner=Audio("Runner");ride.latch=Audio("Latch");ride.keyscan=Audio("Keyscan");ride.dispatch=Enumerable.Range(0,AscentRoute.Stages.Length).Select(i=>Audio("Dispatch"+i)).ToArray();
            ride.passengerPass=Audio("PassengerPass");ride.freightPass=Audio("FreightPass");
            systems.fanSound=Audio("Circulation");
            var player=New("Passenger");player.layer=Passenger.PassengerLayer;player.transform.position=new Vector3(1.30f,.032f,2.24f);player.transform.rotation=Quaternion.Euler(0,-36f,0);var cc=player.AddComponent<CharacterController>();cc.height=1.70f;cc.radius=.22f;cc.center=new Vector3(0,.85f,0);cc.stepOffset=.14f;cc.skinWidth=.016f;
            var eyeGo=New("Passenger eye",player.transform);eyeGo.tag="MainCamera";eyeGo.transform.localPosition=new Vector3(0,1.55f,0);var camera=eyeGo.AddComponent<Camera>();camera.nearClipPlane=.025f;camera.farClipPlane=26000;camera.fieldOfView=66;camera.allowHDR=true;camera.allowMSAA=false;camera.cullingMask=~(1<<Passenger.InspectionLayer);eyeGo.AddComponent<AudioListener>();
            var passenger=player.AddComponent<Passenger>();passenger.ride=ride;passenger.eye=camera;
            Barrier(hull,"Pressure ceiling",new Vector3(0,2.73f,0),new Vector3(4.45f,.16f,11.55f));
            eyeGo.AddComponent<PassengerOptics>().optics=Shader.Find("Hidden/Upwell/Passenger optics");
            player.AddComponent<RideVerification>();
            QualitySettings.pixelLightCount=8;QualitySettings.shadows=ShadowQuality.All;QualitySettings.shadowDistance=90;QualitySettings.shadowCascades=4;QualitySettings.shadowCascade4Split=new Vector3(.069f,.20f,.46f);QualitySettings.antiAliasing=0;
            EditorBuildSettings.scenes=new[]{new EditorBuildSettingsScene(ScenePath,true)};
            EditorSceneManager.SaveScene(scene,ScenePath);AssetDatabase.SaveAssets();Debug.Log("UPWELL assembled "+mapped.Count+" controls in "+rooms.Count+" rooms.");
        }
        [MenuItem("Upwell/Build Windows player")]
        public static void BuildWindows(){
            Assemble();Directory.CreateDirectory("Build");
            var report=BuildPipeline.BuildPlayer(new BuildPlayerOptions{scenes=new[]{ScenePath},locationPathName="Build/Upwell.exe",target=BuildTarget.StandaloneWindows64,options=BuildOptions.None});
            if(report.summary.result!=BuildResult.Succeeded)throw new Exception("Windows build failed: "+report.summary.result);
            Debug.Log("UPWELL Windows player complete.");
        }
        [MenuItem("Upwell/Build WebGL player")]
        public static void BuildWebGL(){ExportWeb(false);}
        public static void BuildWebCheck(){ExportWeb(true);}
        static void ExportWeb(bool probe){
            Assemble();PlayerSettings.WebGL.compressionFormat=probe?WebGLCompressionFormat.Disabled:WebGLCompressionFormat.Brotli;PlayerSettings.WebGL.decompressionFallback=!probe;
            PlayerSettings.WebGL.threadsSupport=false;PlayerSettings.WebGL.dataCaching=true;PlayerSettings.WebGL.template="PROJECT:Upwell";
            PlayerSettings.SetIl2CppCodeGeneration(NamedBuildTarget.WebGL,Il2CppCodeGeneration.OptimizeSize);
            string destination=probe?Path.GetFullPath(Path.Combine(Application.dataPath,"..","..","source",".export-cache","cartridge-web-probe","unity")):Path.GetFullPath(Path.Combine(Application.dataPath,"..","..","web","unity"));Directory.CreateDirectory(destination);
            var report=BuildPipeline.BuildPlayer(new BuildPlayerOptions{scenes=new[]{ScenePath},locationPathName=destination,target=BuildTarget.WebGL,options=BuildOptions.None});
            if(report.summary.result!=BuildResult.Succeeded)throw new Exception("WebGL build failed: "+report.summary.result);
            Debug.Log("UPWELL WebGL player complete.");
        }
    }
}
