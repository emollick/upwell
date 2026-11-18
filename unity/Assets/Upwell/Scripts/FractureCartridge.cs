using System;
using UnityEngine;

namespace Upwell {
    // The force dial measures the live cam stroke. Its drag pointer remains at the highest load.
    [DefaultExecutionOrder(36)]
    public sealed partial class FractureCartridge : MonoBehaviour {
        public TransitRide ride;
        public float LoadNewton {get;private set;}
        public float PeakNewton {get;private set;}
        public float Stroke {get;private set;}
        public bool Broken {get;private set;}
        public int BreakCount {get;private set;}
        public int ExchangeCount {get;private set;}
        public int Impacts {get;private set;}
        public float ShutterCoverage {get;private set;}
        public float EnclosureError {get;private set;}
        public float LargestContactCorrection {get;private set;}
        public bool Reloading => reloadTime>=0;
        public bool Pressed => pressing;
        public Rigidbody[] Fragments {get;private set;}
        public Vector3 InspectionEye => transform.TransformPoint(new Vector3(.014f,.041f,.78f));
        public Vector3 ViewCenter => transform.TransformPoint(new Vector3(-.014f,0,.079f));
        public TransitProp Cell {get;private set;}
        public TransitProp Lever {get;private set;}
        public TransitProp Magazine {get;private set;}
        Cartridge recipe;
        Actuator lever,punch,needle,peakPointer,magazine;
        Actuator[] shutters;
        Transform coupon;
        SkinnedMeshRenderer couponSkin;int flexIndex=-1;
        bool pressing,exchanged;
        float reloadTime=-1,snapTime=10;
        SpringReading liveNeedle;
        AudioSource sound;
        AudioClip snap,tick,strokeSound;
        public static bool IsInstrument(string id)=>id=="fracture_cell"||id=="fracture_press"||id=="fracture_reload";
        public string Status => Reloading?"Exchanging sealed insert":Broken?"Coupon fractured · retained peak "+Mathf.RoundToInt(PeakNewton)+" N":
            "Load "+Mathf.RoundToInt(LoadNewton)+" N   ·   "+(Stroke>.12f?"Ceramic under load":"Scored ceramic seated");
        public bool BeginPress(){
            if(reloadTime>=0||pressing)return false;
            if(Broken){ride.Say("Spent coupon · cycle the magazine");return false;}
            pressing=true;sound.PlayOneShot(strokeSound,.40f);return true;
        }
        public void ReleasePress(){pressing=false;}
        public bool Reload(){
            if(Reloading)return false;
            if(!Broken){ride.Say("An intact coupon is seated");return false;}
            if(pressing||Stroke>.10f){ride.Say("Release the proof lever before exchanging the insert");return false;}
            reloadTime=0;exchanged=false;sound.PlayOneShot(strokeSound,.58f);
            return true;
        }
        void Fracture(){
            Broken=true;BreakCount++;snapTime=0;PeakNewton=recipe.breakLoadN;coupon.gameObject.SetActive(false);
            LaunchFragments();sound.PlayOneShot(snap,.91f);ride.Say("Coupon fractured · "+Mathf.RoundToInt(PeakNewton)+" N peak",2.2f);
        }
        public void Advance(float dt){
            if(recipe==null||dt<=0)return;
            float remaining=Mathf.Min(dt,1.5f);
            while(remaining>.000001f){
                float step=Mathf.Min(remaining,1f/120);remaining-=step;snapTime+=step;
                Stroke=Mathf.MoveTowards(Stroke,pressing?1:0,step/(pressing?recipe.holdSeconds:.31f));
                float progress=Mathf.Clamp01((Stroke-.12f)/(recipe.snapFraction-.12f));
                if(!Broken&&Stroke>=recipe.snapFraction)Fracture();
                LoadNewton=Broken?0:recipe.breakLoadN*Mathf.Pow(progress,1.42f);
                PeakNewton=Mathf.Max(PeakNewton,LoadNewton);
                liveNeedle.Follow(LoadNewton/recipe.dialMaxN,42,.72f,step);
                if(Reloading){
                    reloadTime+=step;float t=reloadTime/recipe.reloadSeconds;
                    ShutterCoverage=Mathf.SmoothStep(0,1,t<.62f?Mathf.Clamp01(t/.36f):Mathf.Clamp01((1-t)/.38f));
                    if(!exchanged&&t>=recipe.exchangeAt){
                        StowFragments();coupon.gameObject.SetActive(true);PeakNewton=0;Broken=false;exchanged=true;ExchangeCount++;
                        sound.PlayOneShot(tick,.55f);
                    }
                    if(t>=1){reloadTime=-1;ShutterCoverage=0;}
                }
            }
            float kick=Broken?Mathf.Sin(snapTime*56)*Mathf.Exp(-snapTime*20)*.055f:0;
            float loaded=LoadNewton/recipe.breakLoadN;
            float ram=Broken?Mathf.Min(1,Stroke/recipe.snapFraction):(2.9f*Mathf.Clamp01(Stroke/.12f)+.7f*loaded)/3.6f;
            lever.Pose(Mathf.Clamp01(Stroke+kick));punch.Pose(ram);needle.Pose(Mathf.Clamp01(liveNeedle.value));
            if(couponSkin&&flexIndex>=0)couponSkin.SetBlendShapeWeight(flexIndex,100*loaded);
            peakPointer.Pose(Mathf.Clamp01(PeakNewton/recipe.dialMaxN));magazine.Pose(ShutterCoverage);
            foreach(var blade in shutters)blade.Pose(ShutterCoverage);
        }
        void Awake(){BuildFromBlender();}
        void Update(){Advance(Time.deltaTime);}
        double impactTime;
        internal void DisturbPile(){pileSince=-1;}
        internal void Impact(float speed){
            if(!Broken||speed<.035f)return;Impacts++;
            if(ride.ReplayingLoads)return;
            if(Time.unscaledTimeAsDouble-impactTime<.052)return;
            impactTime=Time.unscaledTimeAsDouble;sound.PlayOneShot(tick,Mathf.Clamp(speed*.23f,.035f,.27f));
        }
        static void ResolveTip(Rigidbody body,Vector3 normal,Vector3 contact,float restitution,float threshold){
            float inward=Vector3.Dot(body.GetPointVelocity(contact),normal);if(inward>=-.003f)return;
            Vector3 arm=contact-body.worldCenterOfMass;Quaternion inertia=body.rotation*body.inertiaTensorRotation;
            Vector3 v=Quaternion.Inverse(inertia)*Vector3.Cross(arm,normal),I=body.inertiaTensor;
            var inverseV=new Vector3(v.x/Mathf.Max(1e-12f,I.x),v.y/Mathf.Max(1e-12f,I.y),v.z/Mathf.Max(1e-12f,I.z));
            float impulse=-inward*(inward < -threshold?1+restitution:1)/(1/body.mass+Vector3.Dot(v,inverseV));
            body.linearVelocity+=normal*(impulse/body.mass);body.angularVelocity+=inertia*inverseV*impulse;
        }
        float skippedTime;
        internal float ContactTime=>Time.fixedTime+skippedTime;
        internal bool AllPiecesSupported=>Array.TrueForAll(Fragments,body=>body.isKinematic||body.IsSleeping());
        internal void SkipSupportedTime(float step){skippedTime+=step;snapTime+=step;}
        internal void AdvanceSkippedField(Vector3 acceleration,float step){SkipSupportedTime(step);StepField(acceleration);}
        void FixedUpdate(){if(Broken)StepField(ride.Forces.Apparent-ride.StructureImpulse);}
        void StepField(Vector3 acceleration){
            if(!Broken)return;
            var local=transform.worldToLocalMatrix;
            for(int i=0;i<Fragments.Length;i++){var body=Fragments[i];
                if(contacts[i].SupportedRest(body,acceleration))continue;
                bool weighted=acceleration.sqrMagnitude>=1;
                if(weighted)body.linearVelocity+=acceleration*Time.fixedDeltaTime;else body.AddForce(acceleration,ForceMode.Acceleration);
                var pose=local*Matrix4x4.TRS(body.position,body.rotation,Vector3.one);
                // Thin, spinning plates can enter a static plane during PhysX's angular CCD interval.
                // Resolve the real tip/plane constraint with the body's effective mass and inertia.
                // PhysX still supplies shard–shard, anvil and normal enclosure contacts.
                Vector3 correction=Vector3.zero;
                for(int axis=0;axis<3;axis++){
                    float low=0,high=0;Vector3 lowPoint=default,highPoint=default;
                    foreach(var corner in shardCorners[i]){
                        Vector3 p=pose.MultiplyPoint3x4(corner);
                        float a=chamber.min[axis]-p[axis],b=p[axis]-chamber.max[axis];
                        if(axis==1&&((acceleration.y< -1&&a>-.0011f)||(acceleration.y>1&&b>-.0011f)))contacts[i].GuardContact();
                        if(a>low){low=a;lowPoint=p;}if(b>high){high=b;highPoint=p;}
                    }
                    float penetration=Mathf.Max(low,high);
                    if(weighted&&axis==1){
                        float gravitySign=acceleration.y<0?1:-1;Vector3 normalWorld=transform.TransformDirection(Vector3.up*gravitySign);
                        float limit=gravitySign>0?chamber.min.y:chamber.max.y;Vector3 patch=Vector3.zero;int contactCount=0;
                        foreach(var vertex in shardCorners[i]){var q=pose.MultiplyPoint3x4(vertex);if((q.y-limit)*gravitySign<.0008f){patch+=q;contactCount++;}}
                        if(contactCount>0){
                            contacts[i].GuardContact();Vector3 at=transform.TransformPoint(patch/contactCount);
                            float incoming=-Vector3.Dot(body.GetPointVelocity(at),normalWorld),threshold=Mathf.Max(.12f,2.8f*acceleration.magnitude*Time.fixedDeltaTime);
                            ResolveTip(body,normalWorld,at,.20f,threshold);
                            for(int iter=0;iter<3;iter++)foreach(var vertex in shardCorners[i]){
                                var q=pose.MultiplyPoint3x4(vertex);if((q.y-limit)*gravitySign<.0008f)ResolveTip(body,normalWorld,transform.TransformPoint(q),0,threshold);
                            }
                            if(incoming>threshold)Impact(incoming);
                        }
                    }
                    if(penetration<=.00010f)continue;
                    float sign=low>high?1:-1;Vector3 n=Vector3.zero;n[axis]=sign;correction[axis]=sign*penetration;
                    Vector3 normal=transform.TransformDirection(n);Vector3 contact=transform.TransformPoint(low>high?lowPoint:highPoint);
                    float inward=Vector3.Dot(body.GetPointVelocity(contact),normal);
                    if(inward<-.006f){
                        float threshold=weighted?Mathf.Max(.12f,2.8f*acceleration.magnitude*Time.fixedDeltaTime):.12f;
                        ResolveTip(body,normal,contact,.20f,threshold);if(-inward>threshold||!weighted)Impact(-inward);
                    }
                }
                if(correction!=Vector3.zero){body.position+=transform.TransformVector(correction);LargestContactCorrection=Mathf.Max(LargestContactCorrection,correction.magnitude);}
                foreach(var corner in shardCorners[i]){Vector3 point=pose.MultiplyPoint3x4(corner)+correction;
                    EnclosureError=Mathf.Max(EnclosureError,Vector3.Distance(point,chamber.ClosestPoint(point)));}
            }
            if(acceleration.sqrMagnitude>=1&&snapTime>.64f)SettleContactPile(acceleration);else pileSince=-1;
        }
        void SettleContactPile(Vector3 load){
            if(Vector3.Dot(load.normalized,pileDirection)<.96f){pileSince=-1;pileDirection=load.normalized;}
            Vector3 center=Vector3.zero;float totalMass=0;bool supported=true,newPatch=pileSince<0;
            for(int i=0;i<Fragments.Length;i++){
                var b=Fragments[i];center+=b.worldCenterOfMass*b.mass;totalMass+=b.mass;
                float supportLimit=load.y<0?chamber.min.y+.004f:chamber.max.y-.004f;
                var pose=transform.worldToLocalMatrix*Matrix4x4.TRS(b.position,b.rotation,Vector3.one);
                bool close=false;foreach(var corner in shardCorners[i]){
                    float y=pose.MultiplyPoint3x4(corner).y;
                    if(load.y<0?y<supportLimit:y>supportLimit){close=true;break;}
                }
                supported&=close||contacts[i].Touching;
                newPatch|=(b.position-pileReference[i]).sqrMagnitude>.0004f;
            }
            center/=totalMass;
            if(!supported){pileSince=-1;return;}
            pileFilteredCenter=pileSince<0?center:Vector3.Lerp(pileFilteredCenter,center,1-Mathf.Exp(-8*Time.fixedDeltaTime));
            if(newPatch||(pileFilteredCenter-pileCenter).sqrMagnitude>.00001764f){
                pileSince=ContactTime;pileCenter=pileFilteredCenter;for(int i=0;i<Fragments.Length;i++)pileReference[i]=Fragments[i].position;return;
            }
            // Static friction is a collective constraint in a wedged five-piece pile.
            // Require persistent physical contacts, a stationary mass centre, and a bounded footprint.
            if(ContactTime-pileSince>.48f)for(int i=0;i<Fragments.Length;i++)contacts[i].Park(Fragments[i]);
        }
        void BuildAudio(){
            sound=gameObject.AddComponent<AudioSource>();sound.playOnAwake=false;sound.spatialBlend=.62f;sound.minDistance=.9f;sound.maxDistance=7;
            snap=ImpactSound("Scored alumina • release and guard ring",.26f,1,.35f);
            tick=ImpactSound("Ceramic contact",.13f,.63f,.58f);
            strokeSound=ImpactSound("Cam follower and spring",.15f,.29f,.16f);
        }
        static AudioClip ImpactSound(string name,float duration,float pitch,float ring){
            const int rate=24000;var data=new float[(int)(rate*duration)];uint noise=771983u;
            for(int i=0;i<data.Length;i++){
                double t=i/(double)rate;noise=1664525u*noise+1013904223u;
                double crack=((noise>>8)/8388608.0-1)*Math.Exp(-t*470);
                double first=(Math.Sin(t*2*Math.PI*2130*pitch)+.55*Math.Sin(t*2*Math.PI*3521*pitch))*Math.Exp(-t*48);
                double shell=Math.Sin(t*2*Math.PI*736*pitch)*Math.Exp(-t*28);
                data[i]=(float)((1-Math.Exp(-t*3600))*(crack*.46+first*.28+shell*ring));
            }
            var clip=AudioClip.Create(name,data.Length,1,rate,false);clip.SetData(data,0);return clip;
        }
    }
}
