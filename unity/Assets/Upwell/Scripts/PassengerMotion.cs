using UnityEngine;

namespace Upwell {
    public sealed partial class Passenger {
        Vector3 cabinVelocity,lastDirection;
        bool drifting,hadMotionInput,queuedPush,queuedBrace,previouslyReduced,holdingRail;
        int touchAxes;
        public Vector3 CabinVelocity=>cabinVelocity;
        public bool Drifting=>drifting;
        public bool ReducedLoad=>ride&&ride.Forces.GravityG<.12;

        public void TouchMotion(string command){
            if(!int.TryParse(command,out var state))return;
            if((state&16)!=0&&(touchAxes&16)==0)queuedPush=true;
            if((state&64)!=0&&(touchAxes&64)==0)queuedBrace=true;
            touchAxes=state;
        }
        void ResetMotion(){
            cabinVelocity=lastDirection=Vector3.zero;drifting=holdingRail=hadMotionInput=false;
            previouslyReduced=ReducedLoad;
        }
        bool CloseToStructure(){
            var foot=transform.position;
            if(Physics.Raycast(foot+Vector3.up*.1f,Vector3.down,.32f,1,QueryTriggerInteraction.Ignore))return true;
            if(Physics.Raycast(foot+Vector3.up*(body.height-.10f),Vector3.up,.48f,1,QueryTriggerInteraction.Ignore))return true;
            return Physics.CheckCapsule(foot+Vector3.up*1.09f,foot+Vector3.up*1.45f,body.radius+.43f,1,QueryTriggerInteraction.Ignore);
        }
        Vector3 PushNormal(){
            float reach=.58f;
            bool floor=Physics.Raycast(transform.position+Vector3.up*.12f,Vector3.down,out var below,reach,1,QueryTriggerInteraction.Ignore);
            bool ceiling=Physics.Raycast(transform.position+Vector3.up*(body.height-.12f),Vector3.up,out var above,reach,1,QueryTriggerInteraction.Ignore);
            return ceiling&&(!floor||above.distance<below.distance)?Vector3.down:Vector3.up;
        }
        void LeaveObservationForPush(){
            if(Examined&&!exhibit)CloseInspect();
            if(Resting)Rise();
            if(watchView!=0)SetWatch(0);
        }
        internal bool CanReplayMotion=>!holdingRail&&!Resting&&watchView==0&&(!Examined||exhibit)&&body&&body.enabled;
        internal void AdvanceUnrestrained(Vector3 field,float dt){
            if(!drifting&&field.y<=.0008f)return;
            drifting=true;AdvanceDrift(field,dt);
        }
        internal void Brace(){
            if(!ReducedLoad||!CloseToStructure())return;
            ResetMotion();holdingRail=true;ride.Say("Handhold secured");
        }
        internal void FrameDockAisle(){
            if(!Physics.Raycast(eye.transform.position,eye.transform.forward,.85f,1|(1<<ShellRay)|(1<<PropRay),QueryTriggerInteraction.Ignore))return;
            Vector3 to=new Vector3(0,1.58f,Mathf.Min(5.23f,eye.transform.position.z+4.1f))-eye.transform.position;
            yaw=Mathf.Atan2(to.x,to.z)*Mathf.Rad2Deg;pitch=-Mathf.Asin(to.normalized.y)*Mathf.Rad2Deg;
            transform.rotation=Quaternion.Euler(0,yaw,0);eye.transform.localRotation=Quaternion.Euler(pitch,0,0);
        }
        void ReadWalkingAxes(out float h,out float v){
            h=((Input.GetKey(KeyCode.D)||Input.GetKey(KeyCode.RightArrow)||(touchAxes&2)!=0)?1:0)
               -((Input.GetKey(KeyCode.A)||Input.GetKey(KeyCode.LeftArrow)||(touchAxes&1)!=0)?1:0);
            v=((Input.GetKey(KeyCode.W)||Input.GetKey(KeyCode.UpArrow)||(touchAxes&4)!=0)?1:0)
               -((Input.GetKey(KeyCode.S)||Input.GetKey(KeyCode.DownArrow)||(touchAxes&8)!=0)?1:0);
        }
        void MovePassenger(float h,float v,bool holding){
            bool push=queuedPush||Input.GetKeyDown(KeyCode.Space);queuedPush=false;
            bool deckward=Input.GetKey(KeyCode.X)||Input.GetKey(KeyCode.LeftControl)||Input.GetKey(KeyCode.RightControl)||(touchAxes&32)!=0;
            float dt=Time.deltaTime;
            if(ReducedLoad){
                if(!previouslyReduced&&cabinVelocity.sqrMagnitude>.018f)drifting=true;
                Vector3 wanted=eye.transform.forward*v+transform.right*h;
                if(push)wanted+=PushNormal();
                else if(deckward)wanted+=Vector3.down;
                bool active=wanted.sqrMagnitude>.001f;
                bool canReach=active&&CloseToStructure();
                if(active&&(push||!hadMotionInput||Vector3.Dot(lastDirection,wanted.normalized)<.68f)&&canReach){
                    Vector3 direction=wanted.normalized;float speed=push||deckward?.64f:.89f;
                    cabinVelocity=Vector3.ClampMagnitude(cabinVelocity+direction*Mathf.Max(0,speed-Vector3.Dot(cabinVelocity,direction)),1.35f);
                    drifting=true;holdingRail=false;
                }
                if(queuedBrace||Input.GetKeyDown(KeyCode.H)){queuedBrace=false;Brace();}
                hadMotionInput=active;if(active)lastDirection=wanted.normalized;
                if(!holdingRail)AdvanceUnrestrained(ride.Forces.Apparent-ride.StructureImpulse,dt);
            }else{
                bool airborne=drifting;drifting=false;holdingRail=false;hadMotionInput=false;
                Vector3 walk=Vector3.ClampMagnitude(transform.right*h+transform.forward*v,1)*(holding?.90f:Input.GetKey(KeyCode.LeftShift)?2.4f:1.62f);
                if(!airborne&&body.isGrounded)cabinVelocity.y=Mathf.Min(0,cabinVelocity.y);
                Vector3 tangent=Vector3.MoveTowards(new Vector3(cabinVelocity.x,0,cabinVelocity.z),walk,dt*(body.isGrounded?16:5));
                cabinVelocity.x=tangent.x;cabinVelocity.z=tangent.z;
                cabinVelocity.y=Mathf.Max(-5,cabinVelocity.y+(float)-ride.Forces.Down*dt);
                MoveWithContacts(dt);
            }
            previouslyReduced=ReducedLoad;
            if(transform.position.y<-.5f)Place(new Vector3(.24f,.04f,2.28f),0,0);
        }
        internal void AdvanceDrift(Vector3 acceleration,float dt){
            int count=Mathf.Max(1,Mathf.CeilToInt(dt/.035f));float step=dt/count;
            for(int i=0;i<count;i++){
                cabinVelocity=Vector3.ClampMagnitude(cabinVelocity+acceleration*step,3.7f);
                MoveWithContacts(step);
            }
        }
        void MoveWithContacts(float dt){
            body.Move(cabinVelocity*dt);
        }
        void OnControllerColliderHit(ControllerColliderHit hit){
            float into=Vector3.Dot(cabinVelocity,hit.normal);
            if(into>=0)return;
            var other=hit.collider.attachedRigidbody;
            if(other&&!other.isKinematic&&other.TryGetComponent<LooseItemBody>(out var item)&&item.Free){
                float closing=Vector3.Dot(other.GetPointVelocity(hit.point)-cabinVelocity,hit.normal);
                float impulse=Mathf.Clamp(closing,0,2.4f)/(1/other.mass+1/76f);
                other.AddForceAtPosition(-hit.normal*impulse,hit.point,ForceMode.Impulse);
                cabinVelocity+=hit.normal*(impulse/76f);return;
            }
            cabinVelocity-=hit.normal*into;
        }
    }
}
