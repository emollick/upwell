using System;
using System.Collections.Generic;
using UnityEngine;

namespace Upwell {
    // The fixed indicator body is keyed to the shaft. Only the rim of the
    // handwheel turns with the operator. Its needle follows the receiving jaws.
    public sealed class CollarFeedback {
        readonly TransitRide ride;
        readonly Transform pointer;
        readonly Quaternion pointerHome;
        readonly AudioSource wheel, rail;
        readonly Dictionary<string,AudioClip> clips=new Dictionary<string,AudioClip>();
        readonly Dictionary<string,Material> finishes=new Dictionary<string,Material>();
        static readonly string[] turns={"CenterJaws","DrawCollar","LockCollar"};
        static readonly Dictionary<string,string> impactNames=new Dictionary<string,string>{
            {"mug","VesselImpact"},{"logbook","FolioImpact"},{"access_card","KeycardImpact"},
            {"field_glasses","OpticsImpact"},{"tool_roll","WalletImpact"}
        };
        double lastSeconds=double.NaN,lastTravel;
        long lastJoint;
        bool seated;
        public float NeedleAngle {get;private set;}

        public CollarFeedback(TransitRide ride) {
            this.ride=ride;
            var hub=new GameObject("Clamp screw travel indicator").transform;
            hub.SetParent(ride.transform,false);
            hub.position=new Vector3(0,1.27f,-5.346f);
            var model=UnityEngine.Object.Instantiate(Resources.Load<GameObject>("Docking/ClampIndicator"),hub,false);
            model.transform.localRotation=Quaternion.Euler(0,180,0);
            foreach(var part in model.GetComponentsInChildren<Transform>()){
                if(part.name=="clamp_gauge_needle")pointer=part;
            }
            if(!pointer)throw new InvalidOperationException("Missing clamp travel pointer");
            pointer.SetParent(hub,true);pointerHome=pointer.localRotation;
            foreach(var renderer in hub.GetComponentsInChildren<Renderer>()){
                var slots=renderer.sharedMaterials;
                for(int i=0;i<slots.Length;i++){
                    string key=slots[i].name.Replace(" (Instance)","");
                    if(!finishes.TryGetValue(key,out var finish)){finish=Finish(key);finishes.Add(key,finish);}
                    slots[i]=finish;
                }
                renderer.sharedMaterials=slots;renderer.receiveShadows=true;
            }
            wheel=Emitter(ride.transform,"Collar vibration",hub.position);
            rail=Emitter(ride.transform,"Guide bearing housing",ride.exterior.guideway.lanes[0]);
            foreach(string name in turns)Load(name);
            foreach(string name in impactNames.Values)Load(name);
            Load("GuideJoint");Load("SleeveContact");ReadPointer();
        }
        void Load(string name){clips[name]=Resources.Load<AudioClip>("Docking/"+name);}
        static Material Finish(string key){
            string color;float metal,rough;
            switch(key){
                case "ClampCasting":color="#536160";metal=.61f;rough=.43f;break;
                case "ClampSteel":color="#9ca6a2";metal=.83f;rough=.30f;break;
                case "ClampPacking":color="#242a29";metal=.04f;rough=.70f;break;
                case "ClampPointer":color="#303b39";metal=.28f;rough=.38f;break;
                case "ClampVermilion":color="#b74522";metal=.12f;rough=.37f;break;
                default:color="#ffffff";metal=.03f;rough=.53f;break;
            }
            var material=new Material(Shader.Find("Upwell/Carriage finish")){name=key};
            ColorUtility.TryParseHtmlString(color,out var tint);material.color=tint;
            material.SetFloat("_Metallic",metal);material.SetFloat("_Roughness",rough);material.SetFloat("_FinishEligible",0);
            if(key=="ClampEnamel")material.mainTexture=Resources.Load<Texture2D>("Docking/ClampEnamel");
            return material;
        }
        static AudioSource Emitter(Transform root,string label,Vector3 point){
            var node=new GameObject(label);node.transform.SetParent(root,false);node.transform.position=point;
            return Configure(node.AddComponent<AudioSource>());
        }
        static AudioSource Configure(AudioSource source){
            source.playOnAwake=false;source.spatialBlend=.74f;source.minDistance=1.4f;
            source.maxDistance=18;source.dopplerLevel=0;return source;
        }
        void Play(AudioSource source,string name,float gain){if(clips.TryGetValue(name,out var clip)&&clip)source.PlayOneShot(clip,gain);}
        public void Turn(int n){Play(wheel,turns[n-1],.86f);}
        public void Impact(LooseItemBody item,float gain){
            if(!impactNames.TryGetValue(item.item.id,out var name))return;
            if(!item.TryGetComponent<AudioSource>(out var sound))sound=Configure(item.gameObject.AddComponent<AudioSource>());
            Play(sound,name,Mathf.Min(1,gain+.12f));
        }
        void ReadPointer(){
            NeedleAngle=236*ride.exterior.arrivalBay.FollowerTravel;
            pointer.localRotation=Quaternion.AngleAxis(NeedleAngle-118,Vector3.forward)*pointerHome;
        }
        public void Update(double seconds,float dt){
            ReadPointer();
            var guide=ride.exterior.guideway;
            double travel=guide.DistanceTravelled;
            long joint=(long)Math.Floor(travel/guide.spliceEvery);
            bool contact=ride.exterior.arrivalBay.SleeveStroke>=1;
            bool continuous=seconds>=lastSeconds-.002&&seconds-lastSeconds<.6;
            if(continuous){
                if(contact&&!seated)Play(wheel,"SleeveContact",.76f);
                float speed=dt>0?(float)(Math.Abs(travel-lastTravel)/dt):0;
                if(joint==lastJoint+1&&speed>.12f&&speed<46)
                    Play(rail,"GuideJoint",.52f*Mathf.Clamp01(speed/4)*Mathf.Clamp01((46-speed)/16));
            }
            lastSeconds=seconds;lastTravel=travel;lastJoint=joint;seated=contact;
        }
        public void Dispose(){foreach(var material in finishes.Values)UnityEngine.Object.Destroy(material);}
    }
}
