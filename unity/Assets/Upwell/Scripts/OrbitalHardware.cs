using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;

namespace Upwell {
    /// <summary>Mount the same Blender orbital assemblies as the browser carriage.</summary>
    public sealed class OrbitalHardware {
        internal static readonly string[] CarIds=Array.ConvertAll(AscentRoute.Services,s=>s.Car);
        const string Folder="OrbitalHardware/";
        [Serializable] class Finishes {public Finish[] materials;}
        [Serializable] class Finish {public string name,color,image,emit;public float metal,rough,gain,alpha;}
        readonly Dictionary<string,Material> finishes=new Dictionary<string,Material>();
        readonly Dictionary<string,Material> assigned=new Dictionary<string,Material>();
        readonly Dictionary<string,Texture2D> textures=new Dictionary<string,Texture2D>();
        readonly List<Material> finishOrder=new List<Material>();
        readonly List<Transform> wheels=new List<Transform>();
        readonly Material[] labels=new Material[AscentRoute.Services.Length];
        readonly Transform spin,train,passenger,common,freight,tender,scanner,inspection,relayGimbal;
        readonly MeshRenderer placard;
        float parkedTime;

        public Transform Rotor{get{return spin;}}
        public Transform Train{get{return train;}}
        public Transform Scanner{get{return scanner;}}
        public Transform HabitatRelay {get;private set;}
        readonly Transform axialDatum;
        Material valleyWater;
        static int InteriorFinish(string key){
            switch(key){
                case "Aster_Timber":case "Aster_Building":case "Aster_Roof":case "Aster_PaleStone":return 1;
                case "Aster_Soil":return 2;
                case "Aster_Water":return 3;
                case "Aster_Greenhouse":case "Aster_TowerGlass":case "Aster_WindowBank":return 4;
                case "Aster_LitWindow":return 5;
                case "Aster_Liner":return 6;
                default:return 0;
            }
        }
        static readonly Vector3 galleryRadial=new Vector3(-Mathf.Sin(-.70f),0,Mathf.Cos(-.70f));
        public void AimValleyCamera(Camera camera){
            var eye=axialDatum.TransformPoint(Vector3.down*16.1f+galleryRadial*1.58f);
            var forward=axialDatum.TransformDirection(Vector3.up*.888f+galleryRadial*.46f);
            var up=axialDatum.TransformDirection(Vector3.up*.46f-galleryRadial*.888f);
            camera.transform.SetPositionAndRotation(eye,Quaternion.LookRotation(forward,up));
            camera.fieldOfView=54;camera.nearClipPlane=.16f;
        }
        static Color Rgb(string value){Color c;ColorUtility.TryParseHtmlString(value,out c);return c;}
        static Transform Group(Transform parent,string name){
            var node=new GameObject(name).transform;node.SetParent(parent,false);node.gameObject.layer=ExteriorRig.ExteriorLayer;return node;
        }
        static Transform Child(Transform parent,string name){
            foreach(var child in parent.GetComponentsInChildren<Transform>(true))if(child.name==name)return child;
            throw new InvalidOperationException("Missing Blender orbital part "+name);
        }
        Material Resolve(Material original,string assembly){
            Material result;string key=original.name.Replace(" (Instance)",""),slot=assembly+"/"+key;
            if(assigned.TryGetValue(slot,out result))return result;
            if(!finishes.TryGetValue(key,out result))throw new InvalidOperationException("Missing orbital finish "+key);
            if(result.HasProperty("_AsterBounce")){
                result=new Material(result);result.name=key;
                float reflected=assembly=="CounterCar"||assembly=="CounterFleet"?.25f:.16f;
                if(assembly=="AsterReach")reflected=key=="Aster_Mirror"?.135f:key=="Aster_Radiator"?.23f:key=="Aster_Frame"?.34f:.43f;
                result.SetFloat("_AsterBounce",result.GetColor("_EmissionColor").maxColorComponent>0?0:reflected);
                if(assembly=="AsterReach"){
                    result.SetFloat("_ValleyFinish",InteriorFinish(key));
                    if(key=="Aster_Water")valleyWater=result;
                }
            }
            assigned[slot]=result;return result;
        }
        Transform Model(string name,Transform parent){
            var source=Resources.Load<GameObject>(Folder+name);
            if(!source)throw new InvalidOperationException("Orbital source mesh unavailable: "+name);
            var model=UnityEngine.Object.Instantiate(source,parent,false);model.name=name;
            // Blender's exported FBX feeds Unity's -X reflection. The
            // carriage survey uses +X to starboard and mirrors Z from glTF.
            model.transform.localRotation=Quaternion.Euler(0,180,0);
            foreach(var tr in model.GetComponentsInChildren<Transform>(true))tr.gameObject.layer=ExteriorRig.ExteriorLayer;
            foreach(var renderer in model.GetComponentsInChildren<MeshRenderer>(true)){
                var slots=renderer.sharedMaterials;for(int i=0;i<slots.Length;i++)slots[i]=Resolve(slots[i],name);
                renderer.sharedMaterials=slots;renderer.receiveShadows=true;
            }
            return model.transform;
        }
        static void DisableLegacy(Transform root){
            foreach(var renderer in root.GetComponentsInChildren<MeshRenderer>(true))renderer.enabled=false;
        }
        void MakeMaterials(){
            var definitions=Resources.Load<TextAsset>(Folder+"finishes");
            if(!definitions)throw new InvalidOperationException("Orbital finish survey unavailable.");
            var standard=Shader.Find("Standard");var structure=Resources.Load<Shader>(Folder+"OrbitalFinish");
            var survey=JsonUtility.FromJson<Finishes>(definitions.text);
            foreach(var f in survey.materials){
                var mat=new Material(f.alpha<1||!structure?standard:structure){name=f.name};var tint=Rgb(f.color);tint.a=f.alpha;mat.color=tint;
                mat.SetFloat("_Metallic",f.metal);mat.SetFloat("_Glossiness",1-f.rough);
                if(!string.IsNullOrEmpty(f.image)){
                    Texture2D image;if(!textures.TryGetValue(f.image,out image)){
                        image=Resources.Load<Texture2D>(Folder+f.image);
                        if(!image)throw new InvalidOperationException("Missing orbital map "+f.image);
                        image.anisoLevel=8;textures[f.image]=image;
                    }
                    mat.mainTexture=image;
                }
                if(f.gain>0){mat.EnableKeyword("_EMISSION");mat.SetColor("_EmissionColor",Rgb(f.emit).linear*f.gain);
                    if(f.name=="Aster_Soil")mat.SetTexture("_EmissionMap",mat.mainTexture);}
                if(f.alpha<1){
                    mat.SetFloat("_Mode",3);mat.SetInt("_SrcBlend",(int)BlendMode.One);mat.SetInt("_DstBlend",(int)BlendMode.OneMinusSrcAlpha);
                    mat.SetInt("_ZWrite",0);mat.EnableKeyword("_ALPHAPREMULTIPLY_ON");mat.SetOverrideTag("RenderType","Transparent");mat.renderQueue=3000;
                }
                finishes.Add(f.name,mat);finishOrder.Add(mat);
            }
        }
        public OrbitalHardware(Transform habitat,Transform other,Transform station) {
            MakeMaterials();DisableLegacy(habitat);DisableLegacy(other);
            var anchor=Group(habitat,"Counter-rotating axle datum");
            anchor.localRotation=Quaternion.Euler(90,0,0);anchor.localScale=Vector3.one*(80f/315f);
            Transform assembly=Model("AsterReach",anchor);axialDatum=assembly;spin=Group(assembly,"Valley bearings");
            Child(assembly,"rotating_habitat").SetParent(spin,true);
            var members=Child(assembly,"pressure_members");members.SetParent(spin,true);
            spin.gameObject.AddComponent<HabitatMembers>().Mount(members,finishOrder);
            train=Child(assembly,"maintenance_train");train.SetParent(spin,true);
            var car=Model("CounterCar",other);passenger=Child(car,"counter_body");Child(car,"counter_freight").gameObject.SetActive(false);
            var workFleet=Model("CounterFleet",other);common=Child(workFleet,"counter_common_bogie");
            freight=Child(workFleet,"counter_freight_carrier");tender=Child(workFleet,"counter_inspection_tender");
            var wheel=Child(car,"counter_wheels");
            foreach(float y in new[]{-2.5f,2.46f})foreach(float z in new[]{-.47f,.50f}){
                var mounted=UnityEngine.Object.Instantiate(wheel,other,false);mounted.name="Contact wheel";
                mounted.localPosition=new Vector3(-1.28f,y,z);wheels.Add(mounted);
            }
            wheel.gameObject.SetActive(false);
            var plate=GameObject.CreatePrimitive(PrimitiveType.Quad);plate.name="Vehicle registration plate";
            UnityEngine.Object.Destroy(plate.GetComponent<Collider>());plate.transform.SetParent(other,false);plate.layer=ExteriorRig.ExteriorLayer;
            plate.transform.localPosition=new Vector3(0,1.70f,-1.359f);plate.transform.localScale=new Vector3(1.04f,.262f,1);placard=plate.GetComponent<MeshRenderer>();
            // Each passing car carries a permanent, legible vehicle ID.
            int n=0;foreach(string id in CarIds){
                var mat=new Material(finishes["Aster_Mark"]);var tex=Resources.Load<Texture2D>(Folder+"registration-"+id);
                if(tex)mat.mainTexture=tex;
                labels[n++]=mat;
            }
            var receiver=Model("Receiver",station);
            var basePlate=Child(receiver,"survey_head");var head=Child(receiver,"survey_gimbal");inspection=Child(receiver,"receiver_carriage");
            var scope=Group(station,"Arrival range finder");scope.localPosition=new Vector3(1.48f,1.02f,6.76f);
            scanner=Group(scope,"Range finder trunnion");scanner.localPosition=Vector3.up*.244f;
            basePlate.SetParent(scope,false);head.SetParent(scanner,false);head.localPosition=Vector3.down*.244f;
            basePlate.localRotation=Quaternion.Euler(0,180,0);
            inspection.SetParent(station,false);inspection.localPosition=new Vector3(-6.12f,.073f,11);
            inspection.localRotation=Quaternion.Euler(0,180,0);
            var track=Child(receiver,"receiver_track");track.SetParent(station,false);track.localPosition=new Vector3(-6.12f,.048f,12.6f);track.localRotation=Quaternion.Euler(0,180,0);
            // The outer gallery's physical instrument has a clear line of
            // sight beyond the last hoop. Its entrance pupil is the feed eye.
            var datum=new Vector3(-5.14f,4.64f,26.85f);
            var direction=(new Vector3(1060,988,7900)-datum).normalized;
            var relay=Group(station,"Aster outboard optical relay");
            relay.localPosition=datum-direction*.291f-Vector3.up*.244f;
            relay.localRotation=Quaternion.LookRotation(new Vector3(direction.x,0,direction.z));
            var stand=GameObject.CreatePrimitive(PrimitiveType.Cylinder);stand.name="Relay pedestal";stand.layer=ExteriorRig.ExteriorLayer;
            UnityEngine.Object.Destroy(stand.GetComponent<Collider>());stand.transform.SetParent(relay,false);
            float height=relay.localPosition.y-3.86f;stand.transform.localScale=new Vector3(.27f,height*.5f,.27f);
            stand.transform.localPosition=Vector3.down*(height*.5f);stand.GetComponent<MeshRenderer>().sharedMaterial=finishes["Aster_Frame"];
            var fork=UnityEngine.Object.Instantiate(basePlate,relay,false);fork.localPosition=Vector3.zero;fork.localRotation=Quaternion.identity;
            relayGimbal=Group(relay,"Habitat line of sight");relayGimbal.localPosition=Vector3.up*.244f;
            var telescope=UnityEngine.Object.Instantiate(head,relayGimbal,false);telescope.localPosition=Vector3.down*.244f;telescope.localRotation=Quaternion.identity;
            HabitatRelay=Group(relayGimbal,"Optical entrance pupil");HabitatRelay.localPosition=Vector3.forward*.291f;
            var stationRig=station.GetComponent<StationRig>();
            if(stationRig&&stationRig.lights!=null)foreach(var l in stationRig.lights){
                if(!l)continue;
                if(l.name.Contains("booth")||l.name.Contains("gallery"))l.intensity*=.58f;
                if(l.name.Contains("underdeck"))l.intensity*=.72f;
            }
        }
        public void Update(double seconds,double shipSeconds,double remaining,float dt,AscentRoute.CounterCar contact){
            parkedTime=seconds>=360?parkedTime+Mathf.Clamp(dt,0,.15f):0;float t=(float)seconds+parkedTime;
            double physicalTime=shipSeconds+parkedTime;
            if(valleyWater)valleyWater.SetFloat("_ValleyTime",(float)(physicalTime%(20*Math.PI)));
            spin.localRotation=Quaternion.AngleAxis(-(float)((1.12+physicalTime*.125)%(2*Math.PI))*Mathf.Rad2Deg,Vector3.up);
            // Fourteen seconds at each platform, 78 seconds of smooth acceleration and braking.
            double service=(physicalTime+46)%184;bool outward=service<92;
            double leg=Math.Max(0,Math.Min(1,((outward?service:service-92)-14)/78));
            double transit=.5-.5*Math.Cos(Math.PI*leg);
            train.localPosition=new Vector3(0,(float)(-11.4+18.7*(outward?transit:1-transit)),0);
            train.localRotation=Quaternion.Euler(0,-10.31f,0);
            if(contact.InRange){string kind=contact.Service.Kind;
                passenger.gameObject.SetActive(kind=="passenger");common.gameObject.SetActive(kind!="passenger");
                freight.gameObject.SetActive(kind=="freight");tender.gameObject.SetActive(kind=="tender");placard.sharedMaterial=labels[contact.Index];
                float ang=(float)((contact.Altitude*1000/.269)%(Math.PI*2))*Mathf.Rad2Deg;
                foreach(var wheel in wheels)wheel.localRotation=Quaternion.AngleAxis(ang,Vector3.forward);}
            if(remaining<2200){
                float look=1-Mathf.Clamp01((float)remaining/100);
                float depression=Mathf.Min(.94f,Mathf.Atan2((float)remaining+.48f,5.7f))*Mathf.Rad2Deg;
                scanner.localRotation=Quaternion.Euler(depression,180+Mathf.Rad2Deg*(.51f-.91f*look-.035f*Mathf.Sin(t*.82f)),0);
                inspection.localPosition=new Vector3(-6.12f,.073f,12.6f-Mathf.Sin(t*.058f)*.98f);
                relayGimbal.LookAt(new Vector3(1060,988+(float)remaining,7900),Vector3.up);
            }
        }
    }
}
