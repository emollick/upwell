using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;

namespace Upwell {
    public sealed partial class FractureCartridge {
        const string Folder="Fracture/";
        const int ShardLayer=19;
        [Serializable] sealed class Cartridge {
            public float[] origin,chamberMin,chamberMax,couponCenter;
            public float breakLoadN,dialMaxN,holdSeconds,snapFraction,reloadSeconds,exchangeAt;
            public Motion press,punch,needle,peakNeedle,reload;
            public Motion[] shutters;public Shard[] shards;public Support[] supports;public Finish[] finishes;
        }
        [Serializable] sealed class Motion {public string name;public float[] pivot,axis,travel;public float degrees;}
        [Serializable] sealed class Shard {public string name;public float[] pivot,velocity,spin;public float massKg;}
        [Serializable] sealed class Support {public float[] center;public float radius,halfHeight;}
        [Serializable] sealed class Finish {public string name,color,map;public float metal,rough,alpha,emission;}
        [Serializable] sealed class Shapes {public Shape[] shapes;}
        [Serializable] sealed class Shape {public string name;public float[] xyz;public int[] triangles;}
        struct Actuator {
            public Transform part;public Vector3 home,axis,travel;public Quaternion rotation;public float span;
            public void Pose(float amount){
                part.localPosition=home+travel*amount;
                if(span!=0)part.localRotation=Quaternion.AngleAxis(span*amount,axis)*rotation;
            }
        }
        Bounds chamber;
        PhysicsMaterial shellContact,ceramicContact;
        readonly Dictionary<string,Transform> nodes=new Dictionary<string,Transform>();
        readonly List<Material> finishes=new List<Material>();
        readonly List<Mesh> collisionMeshes=new List<Mesh>();
        Vector3[] stowPoints;
        Vector3[][] shardCorners;
        FractureContact[] contacts;
        Vector3[] pileReference;float pileSince=-1;Vector3 pileCenter,pileFilteredCenter,pileDirection;
        public Bounds ChamberBounds=>chamber;
        static Vector3 Web(float[] a)=>new Vector3(a[0],a[1],-a[2]);
        static T Read<T>(string path){var source=Resources.Load<TextAsset>(Folder+path);if(!source)throw new InvalidOperationException("Missing fracture recipe "+path);return JsonUtility.FromJson<T>(source.text);}
        void BuildFromBlender(){
            recipe=Read<Cartridge>("cartridge");transform.localPosition=Web(recipe.origin);
            var source=Resources.Load<GameObject>(Folder+"FractureCartridge");
            if(!source)throw new InvalidOperationException("Missing shared Blender fracture cartridge");
            var model=Instantiate(source,transform,false);model.name="Blender fracture bench";
            model.transform.localPosition=Vector3.zero;model.transform.localRotation=Quaternion.Euler(0,180,0);
            foreach(var node in model.GetComponentsInChildren<Transform>(true))if(node.name.StartsWith("fracture_",StringComparison.Ordinal))nodes[node.name]=node;
            var slots=new Dictionary<string,Material>();foreach(var f in recipe.finishes)slots.Add(f.name,MakeFinish(f));
            foreach(var renderer in model.GetComponentsInChildren<Renderer>(true)){
                var mats=renderer.sharedMaterials;
                for(int i=0;i<mats.Length;i++){string key=mats[i].name.Replace(" (Instance)","");mats[i]=slots[key];}
                renderer.sharedMaterials=mats;renderer.receiveShadows=true;
            }
            lever=Fit(recipe.press);punch=Fit(recipe.punch);needle=Fit(recipe.needle);peakPointer=Fit(recipe.peakNeedle);magazine=Fit(recipe.reload);
            shutters=new Actuator[recipe.shutters.Length];for(int i=0;i<shutters.Length;i++)shutters[i]=Fit(recipe.shutters[i]);
            coupon=nodes["fracture_coupon"];
            couponSkin=coupon.GetComponentInChildren<SkinnedMeshRenderer>(true);
            if(couponSkin)for(int i=0;i<couponSkin.sharedMesh.blendShapeCount;i++)
                if(couponSkin.sharedMesh.GetBlendShapeName(i).EndsWith("BeamFlex",StringComparison.Ordinal)){flexIndex=i;break;}
            Vector3 a=Web(recipe.chamberMin),b=Web(recipe.chamberMax);
            chamber=new Bounds((a+b)*.5f,new Vector3(Mathf.Abs(a.x-b.x),Mathf.Abs(a.y-b.y),Mathf.Abs(a.z-b.z)));
            Cell=Control(transform,"fracture_cell","Ceramic proof cell","Inspect the fracture bench",ViewCenter);
            RayMesh(nodes["fracture_frame"]);RayMesh(nodes["fracture_guard"]);
            Lever=Control(lever.part,"fracture_press","Proof lever","Hold to load the ceramic",RenderCenter(lever.part));RayMesh(lever.part);
            Magazine=Control(magazine.part,"fracture_reload","Specimen magazine","Exchange the sealed coupon",RenderCenter(magazine.part));RayMesh(magazine.part);
            BuildCollisions();
            var lightNode=new GameObject("Proof cell recessed work light");lightNode.transform.SetParent(transform,false);
            lightNode.transform.localPosition=new Vector3(-.029f,.077f,.071f);
            lightNode.transform.localRotation=Quaternion.LookRotation(Web(recipe.couponCenter)-lightNode.transform.localPosition,Vector3.up);
            var workLight=lightNode.AddComponent<Light>();workLight.type=LightType.Spot;workLight.spotAngle=111;workLight.innerSpotAngle=80;
            workLight.color=new Color(1f,.916f,.79f);workLight.intensity=.35f;workLight.range=.32f;workLight.shadows=LightShadows.None;
            workLight.renderMode=LightRenderMode.ForcePixel;
            // The strip throws light across the cell; its polished upper reveal also
            // returns light down the front of the specimen when the service bay is in shadow.
            var fillNode=new GameObject("Proof lamp • upper reveal return");fillNode.transform.SetParent(transform,false);
            fillNode.transform.localPosition=new Vector3(.034f,.073f,.109f);
            fillNode.transform.localRotation=Quaternion.LookRotation(chamber.center+Vector3.down*.016f-fillNode.transform.localPosition,Vector3.forward);
            var returned=fillNode.AddComponent<Light>();returned.type=LightType.Spot;returned.spotAngle=118;returned.innerSpotAngle=84;
            returned.color=new Color(1,.942f,.85f);returned.intensity=.62f;returned.range=.31f;returned.shadows=LightShadows.None;returned.renderMode=LightRenderMode.ForcePixel;
            BuildAudio();
        }
        Actuator Fit(Motion motion){
            var node=nodes[motion.name];node.SetParent(transform,true);
            return new Actuator{part=node,home=node.localPosition,rotation=node.localRotation,span=motion.degrees,
                axis=motion.axis==null?Vector3.forward:-Web(motion.axis),travel=motion.travel==null?Vector3.zero:Web(motion.travel)};
        }
        static Vector3 RenderCenter(Transform p){
            var renderers=p.GetComponentsInChildren<Renderer>(true);var box=renderers[0].bounds;
            for(int i=1;i<renderers.Length;i++)box.Encapsulate(renderers[i].bounds);return box.center;
        }
        static TransitProp Control(Transform node,string id,string name,string action,Vector3 focus){
            var control=node.gameObject.AddComponent<TransitProp>();control.id=id;control.room="service";control.title=name;control.action=action;
            control.localFocus=node.InverseTransformPoint(focus);control.panelControl=id!="fracture_cell";return control;
        }
        static void RayMesh(Transform node){
            foreach(var mesh in node.GetComponentsInChildren<MeshFilter>(true)){
                mesh.gameObject.layer=Passenger.PropRay;var hit=mesh.gameObject.AddComponent<MeshCollider>();hit.sharedMesh=mesh.sharedMesh;
            }
        }
        Material MakeFinish(Finish spec){
            // These are the same measured base colors, guard transmission and maps as the Blender/GLB assembly.
            bool printed=spec.name=="FC_Markings";
            var shader=spec.alpha<1?Resources.Load<Shader>(Folder+"GuardOptics"):printed?Resources.Load<Shader>(Folder+"ScalePrint"):Shader.Find("Upwell/Carriage finish");
            var mat=new Material(shader){name=spec.name};
            ColorUtility.TryParseHtmlString(spec.color,out var tint);tint.a=spec.alpha;
            mat.color=tint;
            if(!string.IsNullOrEmpty(spec.map))mat.mainTexture=Resources.Load<Texture2D>(Folder+spec.map);
            if(spec.alpha<1){
                mat.renderQueue=(int)RenderQueue.Transparent;
            }else{
                mat.SetFloat("_Metallic",spec.metal);
                mat.SetFloat("_Roughness",spec.rough);
                if(printed)mat.SetTexture("_DialLume",Resources.Load<Texture2D>(Folder+"dial_lume"));
                else{mat.SetFloat("_Emission",spec.emission);mat.SetFloat("_FinishEligible",0);}
                if(spec.map=="casting"){mat.SetTexture("_RoughMap",Resources.Load<Texture2D>(Folder+"casting_roughness"));mat.SetFloat("_MappedRoughness",1);
                    mat.SetTexture("_BumpMap",Resources.Load<Texture2D>(Folder+"casting_normal"));mat.SetFloat("_NormalStrength",.36f);}
            }
            finishes.Add(mat);return mat;
        }
        GameObject Physical(string name,Vector3 position){
            var obj=new GameObject(name);obj.layer=ShardLayer;obj.transform.SetParent(transform,false);obj.transform.localPosition=position;return obj;
        }
        void Wall(int axis,int sign){
            Vector3 center=chamber.center,size=chamber.size+Vector3.one*.018f;
            center[axis]+=sign*(chamber.extents[axis]+.006f);size[axis]=.012f;
            var wall=Physical("Sealed cell wall "+axis+" "+sign,center).AddComponent<BoxCollider>();
            wall.size=size;wall.contactOffset=.00025f;wall.sharedMaterial=shellContact;
        }
        void BuildCollisions(){
            for(int i=0;i<32;i++)if(i!=ShardLayer)Physics.IgnoreLayerCollision(ShardLayer,i);
            shellContact=new PhysicsMaterial("Shatter-cell retention"){bounciness=.28f,staticFriction=.57f,dynamicFriction=.38f};
            ceramicContact=new PhysicsMaterial("Fracture surface"){bounciness=.19f,staticFriction=.65f,dynamicFriction=.47f};
            for(int a=0;a<3;a++){Wall(a,-1);Wall(a,1);}
            foreach(var support in recipe.supports){
                var bearing=Physical("Specimen roller anvil",Web(support.center)).AddComponent<CapsuleCollider>();
                bearing.direction=1;bearing.radius=support.radius;bearing.height=support.halfHeight*2;bearing.contactOffset=.00022f;bearing.sharedMaterial=shellContact;
            }
            var shapes=Read<Shapes>("collision-hulls").shapes;
            Fragments=new Rigidbody[recipe.shards.Length];stowPoints=new Vector3[Fragments.Length];shardCorners=new Vector3[Fragments.Length][];contacts=new FractureContact[Fragments.Length];pileReference=new Vector3[Fragments.Length];
            for(int i=0;i<Fragments.Length;i++){
                Shard spec=recipe.shards[i];var mesh=nodes[spec.name];var center=Web(spec.pivot);stowPoints[i]=center;
                var part=Physical(spec.name+" • collision body",center);mesh.SetParent(part.transform,true);
                var body=part.AddComponent<Rigidbody>();Fragments[i]=body;body.isKinematic=true;body.useGravity=false;body.mass=spec.massKg;
                body.linearDamping=.035f;body.angularDamping=.14f;body.sleepThreshold=0;body.solverIterations=12;body.solverVelocityIterations=5;
                body.maxDepenetrationVelocity=2.5f;body.interpolation=RigidbodyInterpolation.Interpolate;
                Shape shape=Array.Find(shapes,s=>s.name==spec.name);if(shape==null)throw new InvalidOperationException("Missing shard collision outline "+spec.name);
                shardCorners[i]=new Vector3[shape.xyz.Length/3];
                for(int v=0;v<shardCorners[i].Length;v++)shardCorners[i][v]=new Vector3(shape.xyz[3*v],shape.xyz[3*v+1],-shape.xyz[3*v+2]);
                for(int n=0;n<shape.triangles.Length;n+=3)AddPrism(part,shape,n);
                contacts[i]=part.AddComponent<FractureContact>();contacts[i].instrument=this;
                foreach(var vertex in shardCorners[i])contacts[i].radius=Mathf.Max(contacts[i].radius,vertex.magnitude);
                part.SetActive(false);
            }
        }
        void AddPrism(GameObject body,Shape shape,int n){
            int ring=shape.xyz.Length/6;
            var positions=new Vector3[6];for(int i=0;i<6;i++){
                int index=(shape.triangles[n+i%3]+(i>=3?ring:0))*3;
                positions[i]=new Vector3(shape.xyz[index],shape.xyz[index+1],-shape.xyz[index+2]);
            }
            var mesh=new Mesh{name="Convex section of surveyed ceramic break"};
            mesh.vertices=positions;mesh.triangles=new[]{0,2,1,3,4,5,0,1,4,0,4,3,1,2,5,1,5,4,2,0,3,2,3,5};mesh.RecalculateBounds();
            var collider=body.AddComponent<MeshCollider>();collider.convex=true;collider.sharedMesh=mesh;collider.contactOffset=.00014f;collider.sharedMaterial=ceramicContact;
            collisionMeshes.Add(mesh);
        }
        void LaunchFragments(){
            EnclosureError=0;LargestContactCorrection=0;Impacts=0;pileSince=-1;
            for(int i=0;i<Fragments.Length;i++){
                var body=Fragments[i];body.gameObject.SetActive(true);body.position=transform.TransformPoint(stowPoints[i]);body.rotation=transform.rotation;
                contacts[i].ClearSupport();body.isKinematic=false;body.collisionDetectionMode=CollisionDetectionMode.ContinuousDynamic;body.WakeUp();
                body.linearVelocity=transform.TransformDirection(Web(recipe.shards[i].velocity));body.angularVelocity=transform.TransformDirection(-Web(recipe.shards[i].spin));
            }
        }
        void StowFragments(){
            foreach(var body in Fragments){
                if(!body.isKinematic){body.linearVelocity=Vector3.zero;body.angularVelocity=Vector3.zero;}body.collisionDetectionMode=CollisionDetectionMode.Discrete;
                body.isKinematic=true;body.gameObject.SetActive(false);
            }
        }
        void OnDestroy(){foreach(var m in finishes)if(m)Destroy(m);foreach(var mesh in collisionMeshes)if(mesh)Destroy(mesh);
            if(ceramicContact)Destroy(ceramicContact);if(shellContact)Destroy(shellContact);if(snap)Destroy(snap);if(tick)Destroy(tick);if(strokeSound)Destroy(strokeSound);}
    }
    public sealed class FractureContact:MonoBehaviour{
        public FractureCartridge instrument;
        public float radius;
        float lastSupport=-100,lastContact=-100,stableSince=-100,patchSince=-100,energyHeight;Vector3 referencePosition,patchPosition,supportDirection;bool parked;
        public bool Touching=>parked||instrument.ContactTime-Mathf.Max(lastContact,lastSupport)<.18f;
        public void ClearSupport(){lastSupport=lastContact=stableSince=patchSince=-100;supportDirection=Vector3.zero;parked=false;energyHeight=0;}
        public void Park(Rigidbody body){
            if(parked)return;
            body.linearVelocity=Vector3.zero;body.angularVelocity=Vector3.zero;
            body.collisionDetectionMode=CollisionDetectionMode.Discrete;body.isKinematic=true;parked=true;
        }
        void Unseat(Rigidbody body){parked=false;stableSince=patchSince=-100;body.isKinematic=false;body.collisionDetectionMode=CollisionDetectionMode.ContinuousDynamic;body.WakeUp();}
        void OnCollisionEnter(Collision contact){
            float speed=contact.relativeVelocity.magnitude;lastContact=instrument.ContactTime;instrument.Impact(speed);
            if(parked&&contact.rigidbody&&!contact.rigidbody.isKinematic&&!contact.rigidbody.IsSleeping()&&
                Mathf.Abs(Vector3.Dot(contact.relativeVelocity,contact.GetContact(0).normal))>.11f){
                var body=GetComponent<Rigidbody>();Unseat(body);
                if(!contact.rigidbody.GetComponent<FractureContact>())instrument.DisturbPile();
                // Restore the finite-mass share of the collision that woke this previously seated chip.
                var point=contact.GetContact(0);Vector3 n=point.normal;
                if(Vector3.Dot(n,body.worldCenterOfMass-contact.rigidbody.worldCenterOfMass)<0)n=-n;
                Vector3 j=n*Mathf.Min(contact.impulse.magnitude,2*contact.rigidbody.mass*speed);
                float share=body.mass/(body.mass+contact.rigidbody.mass);
                body.AddForceAtPosition(j*share,point.point,ForceMode.Impulse);
                contact.rigidbody.AddForceAtPosition(j*(1-share),point.point,ForceMode.Impulse);
            }
            OnCollisionStay(contact);
        }
        public void GuardContact(){lastSupport=instrument.ContactTime;}
        void OnCollisionStay(Collision contact){
            lastContact=instrument.ContactTime;
            var acceleration=instrument.ride.Forces.Apparent-instrument.ride.StructureImpulse;
            if(acceleration.sqrMagnitude<1)return;
            Vector3 up=-acceleration.normalized;
            for(int i=0;i<contact.contactCount;i++)if(Vector3.Dot(contact.GetContact(i).normal,up)>.23f){GuardContact();break;}
        }
        public bool SupportedRest(Rigidbody body,Vector3 acceleration){
            if(acceleration.sqrMagnitude<1||Vector3.Dot(acceleration.normalized,supportDirection)<.96f){
                if(parked)Unseat(body);else if(body.IsSleeping())body.WakeUp();
                stableSince=patchSince=-100;supportDirection=acceleration.normalized;
            }
            if(parked||body.IsSleeping())return true;
            float now=instrument.ContactTime;
            if(acceleration.sqrMagnitude<1||now-lastSupport>.12f){stableSince=patchSince=-100;return false;}
            float patchRadius=Mathf.Clamp(radius*.46f,.0055f,.011f);
            if(patchSince<0||(body.position-patchPosition).sqrMagnitude>patchRadius*patchRadius){patchSince=now;patchPosition=body.position;}
            // Dry rolling/sliding friction is bounded by the supported load. For particles
            // of a few millimetres the finite contact arm matters far more than their air drag.
            float impulse=acceleration.magnitude*Time.fixedDeltaTime;
            var tangent=Vector3.ProjectOnPlane(body.linearVelocity,acceleration);
            body.linearVelocity-=Vector3.ClampMagnitude(tangent,.29f*impulse);
            body.angularVelocity=Vector3.MoveTowards(body.angularVelocity,Vector3.zero,.26f*impulse/Mathf.Max(.004f,radius));
            // PhysX's general sleep test is too coarse for a 3 g plate. Compare the
            // real translational + rotational energy with that needed to climb its broken edge.
            Vector3 w=Quaternion.Inverse(body.rotation*body.inertiaTensorRotation)*body.angularVelocity,I=body.inertiaTensor;
            float specific=.5f*(body.linearVelocity.sqrMagnitude+(I.x*w.x*w.x+I.y*w.y*w.y+I.z*w.z*w.z)/body.mass);
            energyHeight=Mathf.Lerp(energyHeight,specific/acceleration.magnitude,1-Mathf.Exp(-10*Time.fixedDeltaTime));
            if(energyHeight<.0042f){
                float seated=Mathf.Exp(-13*Time.fixedDeltaTime);body.linearVelocity*=seated;body.angularVelocity*=seated;
            }
            bool lodged=now-patchSince>1.25f;
            if(!lodged&&(stableSince<0||(body.position-referencePosition).sqrMagnitude>.000081f||energyHeight>.0042f)){
                stableSince=now;referencePosition=body.position;return false;
            }
            if(!lodged&&now-stableSince<.48f)return false;
            // Supported grit can rest without keeping submillimetre contact chatter alive.
            // A colliding piece wakes it through PhysX; changing apparent weight also wakes it here.
            Park(body);return true;
        }
        public string RestReading(Rigidbody body)=>parked?"seated":body.IsSleeping()?"asleep":"v "+body.linearVelocity.magnitude.ToString("F3")+", w "+body.angularVelocity.magnitude.ToString("F2")+", energy mm "+(energyHeight*1000).ToString("F2")+", support age "+(instrument.ContactTime-lastSupport).ToString("F2");
    }
}
