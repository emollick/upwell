using System;
using UnityEngine;
namespace Upwell {
    public sealed class StationRig : MonoBehaviour {
        [Serializable] public class Mechanism {
            public Transform part;public string kind,id;public Vector3 axis,home;public Quaternion rest;public float amount,delay;
        }
        public bool receiving;
        public Mechanism[] actuators;
        public Light[] lights;
        public double DockDistance {get;private set;}
        public float Clearance {get;private set;}
        public float BridgeClearance {get;private set;}=1;
        public float FollowerTravel {get;private set;}
        public float SleeveStroke {get;private set;}
        public string CaptureStatus => SleeveStroke>=1 ? "TRANSFER READY" : FollowerTravel>=1 ? "SLEEVE EXTENDING" :
            FollowerTravel>=.73f ? "COLLAR DRAWN IN" : FollowerTravel>=.32f ? "JAWS CENTERED" : "SOFT CAPTURE";
        static readonly float[] followerStops={0,6f/18f,13.5f/18f,1};
        double lastSeconds=double.NaN;
        static float Smooth(float a,float b,float x)=>Mathf.SmoothStep(0,1,Mathf.InverseLerp(a,b,x));
        void WindCollar(double sec,int turns,float dt){
            float target=sec>=AscentRoute.Duration?followerStops[Mathf.Clamp(turns,0,3)]:0;
            bool jumped=double.IsNaN(lastSeconds)||sec<lastSeconds-.01||Math.Abs(sec-lastSeconds)>1.5;
            if(sec<AscentRoute.Duration||jumped){
                FollowerTravel=target;SleeveStroke=target>=1?1:0;
            }else{
                float timeToSeat=(1-FollowerTravel)/1.55f;
                FollowerTravel=Mathf.MoveTowards(FollowerTravel,target,dt*1.55f);
                if(FollowerTravel>=1)SleeveStroke=Mathf.Min(1,SleeveStroke+Mathf.Max(0,dt-timeToSeat)/1.68f);
            }
            BridgeClearance=1-Mathf.SmoothStep(0,1,SleeveStroke);lastSeconds=sec;
        }
        public void SetState(double sec,double altitude,int turns=0,float dt=0){
            double metres=receiving?(AscentRoute.Terminal-altitude)*1000:altitude*1000;DockDistance=Math.Max(0,metres);
            if(receiving)WindCollar(sec,turns,dt);
            bool visible=DockDistance<2200;gameObject.SetActive(visible);if(!visible)return;
            transform.position=Vector3.up*(float)(receiving?DockDistance:-DockDistance);
            float time=(float)sec;float arrival=(float)DockDistance;
            Clearance=receiving?Smooth(.08f,2.9f,arrival):Smooth(.8f,7.8f,time);
            foreach(var a in actuators){
                float x=Clearance;
                if(a.id.Contains("shutter"))x=receiving?(1-Smooth(38,115,arrival))*Smooth(.1f,3.5f,arrival):Smooth(.45f,6.4f,time);
                else if(a.id.Contains("bridge")){
                    if(receiving)x=BridgeClearance;
                    else{x=Smooth(.5f,5.2f,time);BridgeClearance=x;}
                }
                else if(a.id.Contains("arm"))x=receiving?Mathf.Lerp(.18f*(1-FollowerTravel),1,Smooth(.16f,3.2f,arrival)):Smooth(3.1f,8.35f,time);
                else if(receiving&&a.id.Contains("drum"))x=Mathf.Min(1,arrival*.08f)+FollowerTravel*.72f;
                if(a.kind=="spin"){a.part.localRotation=a.rest*Quaternion.AngleAxis(Mathf.Repeat(Time.time*38,360),a.axis);continue;}
                x=Mathf.Clamp01((x-a.delay)/(1-a.delay));
                if(a.kind=="rotate")a.part.localRotation=a.rest*Quaternion.AngleAxis(a.amount*x,a.axis);
                else if(a.kind=="translate")a.part.localPosition=a.home+a.axis*(a.amount*x);
            }
            if(lights!=null)foreach(var l in lights)if(l)l.enabled=DockDistance<580;
        }
    }
}
