using System.Collections.Generic;
using UnityEngine;
namespace Upwell{
    public sealed class LooseItemBody:MonoBehaviour{
        public const int Layer=14;
        public TransitProp item;public Rigidbody Body{get;private set;}
        readonly List<Collider> physical=new List<Collider>();Collider[] surveyColliders;TransitRide ride;
        CharacterController releaseOwner;
        float nextImpact;
        public bool Free{get;private set;}public int Impacts{get;private set;}float area,cd;Vector3 safe;
        void ShapeBox(string n,Vector3 c,Vector3 size){
            var g=new GameObject(n);g.layer=Layer;g.transform.SetParent(transform,false);var b=g.AddComponent<BoxCollider>();b.center=c;b.size=Vector3.Max(size,new Vector3(.006f,.004f,.006f));b.enabled=false;physical.Add(b);
        }
        public void Initialize(){
            if(Body)return;if(!item)item=GetComponent<TransitProp>();ride=FindAnyObjectByType<TransitRide>();
            surveyColliders=GetComponentsInChildren<Collider>(true);
            var meshes=GetComponentsInChildren<MeshFilter>(true);var bounds=new Bounds();bool first=true;
            foreach(var m in meshes){if(m.GetComponentInParent<FlexibleTail>())continue;var b=m.sharedMesh.bounds;
                for(int j=0;j<8;j++){var pt=b.center+Vector3.Scale(b.extents,new Vector3((j&1)==0?-1:1,(j&2)==0?-1:1,(j&4)==0?-1:1));
                    pt=transform.InverseTransformPoint(m.transform.TransformPoint(pt));if(first){bounds=new Bounds(pt,Vector3.zero);first=false;}else bounds.Encapsulate(pt);}}
            var s=bounds.size;var c=bounds.center;
            if(item.id=="field_glasses"){foreach(float sign in new[]{-1f,1f})ShapeBox("Optical barrel collision",c+Vector3.right*sign*s.x*.26f,new Vector3(s.x*.43f,s.y*.78f,s.z*.89f));}
            else if(item.id=="mug"){ShapeBox("Vessel body collision",c-new Vector3(s.x*.05f,0,0),new Vector3(s.x*.77f,s.y,s.z*.84f));ShapeBox("Handle collision",c+Vector3.right*s.x*.39f,new Vector3(s.x*.20f,s.y*.66f,s.z*.32f));}
            else if(item.id=="tool_roll"){ShapeBox("Wallet spine collision",c-Vector3.up*s.y*.23f,new Vector3(s.x,s.y*.52f,s.z));ShapeBox("Retained drivers collision",c+Vector3.up*s.y*.20f,new Vector3(s.x*.76f,s.y*.53f,s.z*.81f));}
            else ShapeBox("Bonded case collision",c,s);
            foreach(var collider in surveyColliders)if(collider)collider.enabled=false;
            Body=gameObject.AddComponent<Rigidbody>();Body.isKinematic=true;Body.useGravity=false;Body.detectCollisions=false;Body.interpolation=RigidbodyInterpolation.Interpolate;
            Body.mass=item.id=="access_card"?.018f:item.id=="mug"?.32f:item.id=="field_glasses"?.79f:item.id=="logbook"?.42f:1.08f;
            Body.linearDamping=0;Body.angularDamping=.035f;Body.maxAngularVelocity=24;
            area=Mathf.Max(s.x*s.y,Mathf.Max(s.x*s.z,s.y*s.z));cd=item.id=="access_card"?1.18f:.76f;
        }
        public void LetGo(Vector3 p,Quaternion rot,Vector3 velocity,Vector3 spin){
            Initialize();transform.SetParent(null,true);foreach(var c in surveyColliders)if(c)c.enabled=false;
            foreach(var c in physical)c.enabled=true;Body.detectCollisions=true;Body.position=p;Body.rotation=rot;transform.SetPositionAndRotation(p,rot);
            Body.isKinematic=false;Body.collisionDetectionMode=CollisionDetectionMode.ContinuousDynamic;Physics.SyncTransforms();
            var passenger=FindFirstObjectByType<Passenger>();var owner=passenger?passenger.GetComponent<CharacterController>():null;
            if(owner){foreach(var c in physical)if(c.bounds.Intersects(owner.bounds)){releaseOwner=owner;break;}
                if(releaseOwner)foreach(var c in physical)Physics.IgnoreCollision(c,releaseOwner,true);}
            foreach(var c in physical){
                var b=c.bounds;foreach(var other in Physics.OverlapBox(b.center,b.extents+Vector3.one*.002f,Quaternion.identity,(1<<0)|(1<<Passenger.ShellRay)|(1<<Passenger.PropRay),QueryTriggerInteraction.Ignore)){
                    if(other.transform.IsChildOf(transform)||other.GetComponentInParent<Passenger>())continue;
                    if(Physics.ComputePenetration(c,c.transform.position,c.transform.rotation,other,other.transform.position,other.transform.rotation,out Vector3 axis,out float depth))Body.position+=axis*(depth+.0015f);
                }
            }
            Body.linearVelocity=Vector3.ClampMagnitude(velocity,3);Body.angularVelocity=Vector3.ClampMagnitude(spin,14);safe=Body.position;Free=true;Impacts=0;Body.WakeUp();
        }
        void RestorePassengerContact(){if(!releaseOwner)return;foreach(var c in physical)Physics.IgnoreCollision(c,releaseOwner,false);releaseOwner=null;}
        public void Recover(){
            RestorePassengerContact();
            if(!Body)return;if(!Body.isKinematic){Body.linearVelocity=Vector3.zero;Body.angularVelocity=Vector3.zero;}
            Body.collisionDetectionMode=CollisionDetectionMode.Discrete;Body.isKinematic=true;Body.detectCollisions=false;foreach(var c in physical)c.enabled=false;
            foreach(var c in surveyColliders)if(c)c.enabled=true;Free=false;
        }
        void FixedUpdate(){if(Free&&ride)ApplyField(ride.Forces.Apparent-ride.StructureImpulse);}
        internal bool SupportedByDeck(){
            if(Body.linearVelocity.sqrMagnitude>.0009f||Body.angularVelocity.sqrMagnitude>.09f)return false;
            foreach(var shape in physical){
                var bounds=shape.bounds;
                if(Physics.Raycast(bounds.center,Vector3.down,bounds.extents.y+.008f,1,QueryTriggerInteraction.Ignore))return true;
            }
            return false;
        }
        internal void ApplyField(Vector3 acceleration){
            if(releaseOwner){bool overlaps=false;foreach(var c in physical)overlaps|=c.bounds.Intersects(releaseOwner.bounds);if(!overlaps)RestorePassengerContact();}
            Vector3 velocity=Body.linearVelocity;Vector3 air=ride.CabinFanOn?new Vector3(.010f,0,.006f):Vector3.zero;var relative=velocity-air;
            Body.AddForce(acceleration,ForceMode.Acceleration);
            Body.AddForce(-.5f*1.18f*cd*area*relative.magnitude*relative,ForceMode.Force);
            Vector3 p=Body.position;
            if(Mathf.Abs(p.x)<2.18f&&Mathf.Abs(p.z)<5.69f&&p.y>-.05f&&p.y<2.67f)safe=p;
            else if(Mathf.Abs(p.x)>2.55f||Mathf.Abs(p.z)>6.05f||p.y<-.45f||p.y>3.05f){Body.position=safe;Body.linearVelocity=Vector3.zero;}
        }
        void OnCollisionEnter(Collision c){
            if(!Free)return;Impacts++;
            var fabric=c.collider.GetComponentInParent<FurnishingSurface>();
            if(fabric&&c.contactCount>0){var hit=c.GetContact(0);fabric.React(hit.point,-hit.normal*Mathf.Min(.74f,c.impulse.magnitude*(fabric.IsCable?3.5f:2.4f)));}
            if(c.relativeVelocity.sqrMagnitude>.084f&&ride&&!ride.ReplayingLoads&&Time.time>=nextImpact){
                nextImpact=Time.time+.16f;ride.Impact(this,Mathf.Min(.9f,c.relativeVelocity.magnitude*.58f));
            }
        }
    }
}
