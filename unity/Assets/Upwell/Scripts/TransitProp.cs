using UnityEngine;

namespace Upwell {
    public sealed class TransitProp : MonoBehaviour {
        public string id, room, title, action, motion;
        public Vector3 motionAxis, localFocus;
        public float amount;
        public bool portable;
        public bool panelControl;public float neutral;float release;
        public Vector3 HomePosition { get; private set; }
        Quaternion homeRotation;
        Vector3 homeScale;
        Rigidbody mechanism;
        public float Target { get; private set; }
        public float Position { get; private set; }
        public Vector3 Focus => transform.TransformPoint(localFocus);
        public bool Open => Target > .5f;

        void Awake() {
            HomePosition=transform.localPosition;
            homeRotation=transform.localRotation;
            homeScale=transform.localScale;
            mechanism=GetComponent<Rigidbody>();
            Target=Position=neutral;
        }
        public void SetOpen(bool open) => SetTarget(open ? 1 : 0);
        public void SetTarget(float value) => Target=Mathf.Clamp01(value);
        public void Pulse(){SetTarget(1);release=.14f;}
        public void Step(float dt) {
            if (Mathf.Approximately(Position,Target)) return;
            float rate=motion=="press"?18f:panelControl?6.4f:id=="ascent_lever"?6f:id=="pressure_hatch"?.90f:id=="roller_shade"?.83f:id=="docking_wheel"?2.2f:1.55f;
            Position=Mathf.MoveTowards(Position,Target,dt*rate);
            Pose(Mathf.SmoothStep(0,1,Position)-Mathf.SmoothStep(0,1,neutral));
        }
        public void Drive(float fraction) {
            Position=Target=Mathf.Clamp01(fraction);Pose(Position-neutral);
        }
        void Pose(float t) {
            switch(motion) {
                case "translate": case "slide":case "press":
                    var p=HomePosition+motionAxis*amount*t;
                    if(mechanism)mechanism.MovePosition(transform.parent?transform.parent.TransformPoint(p):p);else transform.localPosition=p;break;
                case "rotate": case "hinge":
                    var q=homeRotation*Quaternion.AngleAxis(amount*t,motionAxis);
                    if(mechanism)mechanism.MoveRotation(transform.parent?transform.parent.rotation*q:q);else transform.localRotation=q;break;
                case "scale":
                    transform.localScale=Vector3.Scale(homeScale,Vector3.one+motionAxis*(amount-1)*t);break;
            }
        }
        void Update(){if(release>0){release-=Time.deltaTime;if(release<=0)SetTarget(neutral);}if(!mechanism)Step(Time.deltaTime);}
        void FixedUpdate(){if(mechanism&&mechanism.isKinematic)Step(Time.fixedDeltaTime);}
        public void Emission(float output) {
            foreach(var r in GetComponentsInChildren<MeshRenderer>()) {
                var mats=r.sharedMaterials;
                for(int k=0;k<mats.Length;k++) if(mats[k]!=null&&mats[k].HasProperty("_Emission")&&mats[k].GetFloat("_Emission")>0) {
                    var block=new MaterialPropertyBlock(); r.GetPropertyBlock(block,k);
                    block.SetFloat("_Emission",output*mats[k].GetFloat("_Emission"));r.SetPropertyBlock(block,k);
                }
            }
        }
        public void Screen(int mode) {
            Color[] phosphors={new Color(.73f,1,1),new Color(.55f,.9f,1),new Color(1,.80f,.5f)};
            foreach(var r in GetComponentsInChildren<MeshRenderer>()) {
                var mats=r.sharedMaterials;
                for(int k=0;k<mats.Length;k++) if(mats[k]!=null&&mats[k].HasProperty("_Instrument")&&mats[k].GetFloat("_Instrument")>.5f) {
                    var block=new MaterialPropertyBlock();r.GetPropertyBlock(block,k);
                    block.SetColor("_DisplayTint",phosphors[mode]);r.SetPropertyBlock(block,k);
                }
            }
        }
    }
}
