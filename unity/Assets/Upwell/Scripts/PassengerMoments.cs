using System;
using UnityEngine;

namespace Upwell {
    public sealed partial class Passenger {
        [Serializable] public sealed class PassageMoment {
            public string id,name,view,detail;
            public float start, @event;
        }
        [Serializable] sealed class MomentList { public PassageMoment[] moments,observations; }
        PassageMoment[] moments,observations;
        string pendingBoardingMoment;
        Vector2 momentScroll;
        bool momentsOpen,followMomentView,autoMomentFixture;
        sealed class PassageOrigin {
            public int watch;
            public bool rest,berth,glazing,drift,rail;
            public float heading,elevation,walkPitch;
            public double time;
            public Vector3 foot,velocity,walk,seatExit;
            public Quaternion walkTurn,seatTurn;
            public bool InAisle=>watch==0&&!rest;
        }
        PassageOrigin momentOrigin;
        bool applyingMoment;
        public string LastMoment {get;private set;}
        public int MomentIndex {get;private set;}=-1;
        public int MomentCount=>moments?.Length??0;
        public bool MomentMenuVisible=>momentsOpen;
        public bool FollowsMomentView=>followMomentView;
        public int SelectedView=>watchView;
        public PassageMoment MomentAt(int index)=>moments[index];

        void LoadMoments(){
            var data=Resources.Load<TextAsset>("PassageMoments");
            var catalogue=data?JsonUtility.FromJson<MomentList>(data.text):null;
            moments=catalogue?.moments??Array.Empty<PassageMoment>();observations=catalogue?.observations??Array.Empty<PassageMoment>();
            followMomentView=PlayerPrefs.GetInt("Upwell.FollowMomentView",1)!=0;
        }
        int AdjacentMoment(int direction){
            if(moments==null||moments.Length==0)return -1;
            if(direction>0&&momentOrigin!=null&&MomentIndex<moments.Length-1&&ride.Seconds>=AscentRoute.Duration-.08)return moments.Length-1;
            if(direction>0&&autoMomentFixture&&MomentIndex==moments.Length-2)return moments.Length-1;
            int i=0;while(i<moments.Length&&moments[i].start<=ride.Seconds+.08)i++;
            if(direction>0)return i<moments.Length?i:-1;
            i--;if(i<0)return -1;
            return ride.Seconds<=moments[i].@event+1.25f?i-1:i;
        }
        public void StepMoment(int direction){GoToMoment(AdjacentMoment(direction));}
        public void ContinueFromGalley(){if(autoMomentFixture&&MomentIndex==MomentCount-2)StepMoment(1);}
        public void ToggleMoments(){SetMomentsOpen(!momentsOpen);}
        public void SetBoardingPace(string value){ride.SetRealTime(value=="real");}
        public void SetFollowMomentView(bool follow){
            if(followMomentView==follow)return;
            if(!follow)momentOrigin=null;
            followMomentView=follow;PlayerPrefs.SetInt("Upwell.FollowMomentView",follow?1:0);PlayerPrefs.Save();
        }
        PassageOrigin RememberPassenger()=>new PassageOrigin{
            watch=watchView,rest=Resting,berth=InBerth,glazing=observing,foot=transform.position,heading=yaw,elevation=pitch,
            drift=drifting,rail=holdingRail,velocity=cabinVelocity,time=ride.Seconds,walk=walkOrigin,walkTurn=walkRotation,
            walkPitch=savedPitch,seatExit=savedPosition,seatTurn=savedHeading
        };
        void RestorePassenger(PassageOrigin origin){
            if(Examined)CloseInspect();
            Resting=origin.rest;InBerth=origin.berth;watchView=origin.watch;observing=origin.glazing;
            walkOrigin=origin.walk;walkRotation=origin.walkTurn;savedPitch=origin.walkPitch;
            savedPosition=origin.seatExit;savedHeading=origin.seatTurn;
            ride.exterior.WatchSensor(UsingSensor?(watchView>=8?watchView-4:watchView-2):0);
            eye.enabled=!UsingSensor;eye.fieldOfView=watchView==11?52:watchView==6?59:observing?38:viewFov;Focus=null;
            Place(origin.foot,origin.heading,origin.elevation);
            drifting=origin.drift;holdingRail=origin.rail;cabinVelocity=origin.velocity;
            // Gear has continued to simulate while the passenger was using the suggested
            // camera. Advance only their remembered body through those unattended seconds.
            if(!origin.InAisle||holdingRail||ride.Seconds<=origin.time)return;
            for(double t=origin.time;t<ride.Seconds-.00001;){
                double interval=Math.Min(1,ride.Seconds-t);
                if(!drifting&&CarriageForces.At(AscentRoute.Height(t)).Apparent.y<=0&&CarriageForces.At(AscentRoute.Height(t+interval)).Apparent.y<=0){t+=interval;continue;}
                float step=(float)Math.Min(Time.fixedDeltaTime,interval);
                AdvanceUnrestrained(CarriageForces.At(AscentRoute.Height(t+step*.5)).Apparent,step);t+=step;
            }
        }
        void LeaveSuggestedTour(){
            if(applyingMoment||momentOrigin==null)return;
            var origin=momentOrigin;momentOrigin=null;applyingMoment=true;
            try{RestorePassenger(origin);}finally{applyingMoment=false;}
        }
        void FinishPassageGesture(){
            if(ride&&ride.fracture)ride.fracture.ReleasePress();
            if(gripped)gripped.Release();
            if(pressedInstrument&&ride.experiments)ride.experiments.ReleaseControl(pressedInstrument);
            if(activeRail)ReleaseRail(false);
            pressedInstrument=null;gripped=null;dragging=null;softCandidate=null;handDown=handMoved=false;dragOffset=Vector3.zero;
        }
        void SetMomentsOpen(bool open){
            momentsOpen=open;Help=false;
            if(open){
                FinishPassageGesture();int near=0;
                while(near+1<MomentCount&&moments[near+1].start<=ride.Seconds+.08)near++;
                momentScroll.y=Mathf.Max(0,near-2)*55;
            }
            SetPassengerPointer(open);
        }
        public void BoardAtMoment(string id){
            // The browser can deliver the boarding click before the scene has run Start.
            pendingBoardingMoment=id;
        }
        void ApplyBoardingMoment(){
            var id=pendingBoardingMoment;
            pendingBoardingMoment=null;
            BoardWeb();
            var observation=observations==null?null:Array.Find(observations,m=>m.id==id);
            if(observation!=null){VisitObservation(observation);return;}
            if(moments!=null)GoToMoment(Array.FindIndex(moments,m=>m.id==id));
        }
        void VisitObservation(PassageMoment observation){
            if(observation==null)return;
            FinishPassageGesture();SetMomentsOpen(false);if(Examined)CloseInspect();if(Resting)Rise();
            momentOrigin=null;autoMomentFixture=false;MomentIndex=-1;LastMoment=observation.id;
            if(observation.id=="stargazing"){
                ride.Seek(observation.start);ride.BeginStargazing();ride.systems.PrepareForStargazing();SetWatch(1);ride.Say(observation.detail);return;
            }
            ride.Seek(observation.start);SetWatch(observation.view=="valley"?12:observation.view=="counter"?8:observation.view=="earth"?3:11);ride.Say(observation.detail);
        }
        public void GoToMoment(int index){
            if(moments==null||index<0||index>=moments.Length)return;
            var m=moments[index];
            FinishPassageGesture();
            bool keepItem=Examined&&(!autoMomentFixture||!followMomentView);
            if(momentsOpen||Help)SetMomentsOpen(false);
            bool follow=followMomentView&&!keepItem,dock=m.start>=AscentRoute.Duration;
            applyingMoment=true;
            try{
                if(!keepItem&&Examined)CloseInspect();
                if(follow&&momentOrigin!=null&&(momentOrigin.InAisle||dock))RestorePassenger(momentOrigin);
                ride.Seek(m.start);LastMoment=m.id;MomentIndex=index;
                if(follow){
                    if(dock){
                        momentOrigin=null;
                        if(watchView==0&&!Resting)FrameDockAisle();
                    }else{
                        // The free-body checkpoint is now at this route time. Deliberate
                        // seats and optical stations keep their original restraint and pose.
                        if(momentOrigin==null||momentOrigin.InAisle)momentOrigin=RememberPassenger();
                        if(Resting)Rise();
                        if(m.view=="cell"){VisitFixture("capillary_cell");autoMomentFixture=true;}
                        else {
                            int watch=m.view=="floor"?6:m.view=="earth"?3:m.view=="forward"?4:m.view=="counter"?8:m.view=="stars"?9:m.view=="colony"?10:1;
                            SetWatch(watch);
                        }
                    }
                }
            }finally{applyingMoment=false;}
            ride.Say(m.name,2.5f);
        }
        void DrawMomentMenu(float w,float h){
            float width=Mathf.Min(500,w-24),height=Mathf.Min(650,h-26),x=(w-width)*.5f,y=(h-height)*.5f;
            Plate(new Rect(x,y,width,height));GUI.Label(new Rect(x+17,y+11,width-100,34),"Passage moments",heading);
            if(GUI.Button(new Rect(x+width-70,y+11,54,29),"Close")){SetMomentsOpen(false);return;}
            bool compact=width<372;
            bool follow=GUI.Toggle(new Rect(x+18,y+50,compact?width-36:width-191,30),followMomentView," Use suggested view");
            SetFollowMomentView(follow);
            if(GUI.Button(new Rect(compact?x+18:x+width-171,y+(compact?80:49),154,28),"Shaded side window")){
                SetMomentsOpen(false);SetWatch(11);return;
            }
            float inner=width-50,contentHeight=0;
            foreach(var moment in moments)contentHeight+=Mathf.Max(53,32+small.CalcHeight(new GUIContent(moment.detail),inner-20));
            float settingsY=compact?114:84;
            bool real=GUI.Toggle(new Rect(x+18,y+settingsY,width-36,26),ride.RealShipTime," Real ship time (1×)");
            if(real!=ride.RealShipTime)ride.SetRealTime(real);
            string timing=real?"One second aboard per second. You can still skip to any moment.":"Guided time fits 58 h 43 m into six minutes. Close passes slow down. Your hands and loose objects move in real time.";
            float timingHeight=small.CalcHeight(new GUIContent(timing),width-42)+4;
            GUI.Label(new Rect(x+20,y+settingsY+28,width-42,timingHeight),timing,small);
            float shortcutsY=settingsY+32+timingHeight,buttonWidth=(width-43)/2;
            if(GUI.Button(new Rect(x+18,y+shortcutsY,buttonWidth,27),"Harbor optics")){VisitObservation(Array.Find(observations,m=>m.id=="harbor"));return;}
            if(GUI.Button(new Rect(x+25+buttonWidth,y+shortcutsY,buttonWidth,27),"Cable tender T03")){VisitObservation(Array.Find(observations,m=>m.id=="tender"));return;}
            shortcutsY+=30;
            if(GUI.Button(new Rect(x+18,y+shortcutsY,buttonWidth,27),"Valley gallery")){VisitObservation(Array.Find(observations,m=>m.id=="valley"));return;}
            if(GUI.Button(new Rect(x+25+buttonWidth,y+shortcutsY,buttonWidth,27),"Stargazing window")){VisitObservation(Array.Find(observations,m=>m.id=="stargazing"));return;}
            string service="Downbound about every 4 ship hours · 5 passenger, 9 freight, 2 tenders.";
            float serviceHeight=small.CalcHeight(new GUIContent(service),width-42)+4;
            GUI.Label(new Rect(x+20,y+shortcutsY+31,width-42,serviceHeight),service,small);
            float listTop=shortcutsY+33+serviceHeight;
            momentScroll=GUI.BeginScrollView(new Rect(x+12,y+listTop,width-24,height-listTop-12),momentScroll,new Rect(0,0,inner,contentHeight));
            int selected=-1;float top=0;
            for(int i=0;i<moments.Length;i++){
                var m=moments[i];float caption=small.CalcHeight(new GUIContent(m.detail),inner-20),row=Mathf.Max(53,32+caption);
                var rect=new Rect(0,top,inner,row-2);top+=row;
                if(GUI.Button(rect,GUIContent.none))selected=i;
                if(MomentIndex==i){var tint=GUI.color;GUI.color=new Color(.46f,.79f,.76f);GUI.DrawTexture(new Rect(2,rect.y+4,3,row-10),Texture2D.whiteTexture);GUI.color=tint;}
                GUI.Label(new Rect(10,rect.y+3,inner-82,23),m.name,normal);
                GUI.Label(new Rect(10,rect.y+26,inner-20,caption+2),m.detail,small);
                int sec=(int)m.start;
                GUI.Label(new Rect(inner-51,rect.y+5,46,22),(sec/60)+":"+(sec%60).ToString("00"),small);
            }
            GUI.EndScrollView();if(selected>=0)GoToMoment(selected);
        }
    }
}
