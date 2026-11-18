using UnityEngine;

namespace Upwell {
    public sealed class HandMechanism : MonoBehaviour {
        public string partId,label;
        public Vector3 axis;
        public float angle;
        public int detents=2;
        public int Setting {get;private set;}
        public float Travel => Mathf.Clamp01(spring.value);
        SpringReading spring;
        Quaternion rest;
        float valveDwell,lastAdvance=-1;
        bool held;
        int lastFrame=-1;
        bool IsValve => partId=="mech_mug_valve";

        void Awake(){rest=transform.localRotation;}
        public void Click(){
            if(IsValve){Setting=1;valveDwell=.64f;}
            else Setting=(Setting+1)%Mathf.Max(2,detents);
        }
        public void HoldValve(bool value){
            if(!IsValve||held==value)return;
            held=value;
            if(value){Setting=1;valveDwell=.34f;}
            else if(valveDwell<=0)Setting=0;
        }
        public void Advance(float dt){
            // A held replica and an active mount may both request this pose in one frame.
            if(lastFrame==Time.frameCount)return;
            lastFrame=Time.frameCount;
            float now=Time.unscaledTime;
            float step=Mathf.Clamp(dt,0,.2f);
            // A click must produce travel even if a frame stalls between the
            // input event and the first update of the held joint.
            if(IsValve&&!held&&valveDwell<=0)Setting=0;
            float target=Setting/(float)Mathf.Max(1,detents-1);
            if(lastAdvance>=0&&now-lastAdvance>.75f&&Setting==0)spring=new SpringReading();
            lastAdvance=now;
            float rate=IsValve?(Setting==0?31:19):partId=="mech_log_leaf"?13:26;
            spring.Follow(target,rate,IsValve ? .86f : .82f,step);
            if(IsValve&&valveDwell>0)valveDwell=Mathf.Max(0,valveDwell-step);
            if(spring.value<0||spring.value>1){spring.value=Travel;spring.velocity=0;}
            transform.localRotation=rest*Quaternion.AngleAxis(angle*Travel,axis);
        }
        void Update(){Advance(Time.deltaTime);}
    }
}
