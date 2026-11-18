using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using UnityEngine;

namespace Upwell {
    [RequireComponent(typeof(CharacterController))]
    public sealed partial class Passenger : MonoBehaviour {
        public TransitRide ride;
        public Camera eye;
        public TransitProp Focus {get;private set;}
        public TransitProp Examined {get;private set;}
        public bool Resting {get;private set;}
        public bool InBerth {get;private set;}
        public bool Help {get;private set;}
        CharacterController body;
        float yaw,pitch,viewFov=66,inspectYaw,inspectPitch;
        bool observing;
        Vector3 savedPosition;
        Quaternion savedHeading;
        GameObject exhibit;float holdingDistance,holdingZoom=1,flip;PassengerOptics optics;
        HandMechanism heldControl;Transform heldJoint,heldOrigin;Vector3 handVelocity,dragOffset,releaseVelocity,releaseSpin,lastHand;Quaternion lastAttitude;
        bool handDown,handMoved,valveFinger,valvePad,valveGui;
        readonly List<MeshRenderer> liftedRenderers=new List<MeshRenderer>();
        int watchView;Vector3 walkOrigin;Quaternion walkRotation;float savedPitch,harborRailWeight;
        public GameObject CarriedModel=>exhibit;
        float dragTime,dragSum,dragOrigin;bool workingHandle;TransitProp dragging;
        TransitProp pressedInstrument;
        FurnishingSurface softFocus,softCandidate,gripped,examinedFabric;
        public CurtainHandle RailFocus{get;private set;}
        CurtainHandle activeRail,examinedRail;
        CurtainHandle berthGrip;
        float screenStroke,pendingPixels,verticalPixels;
        bool railMoved;
        Vector3 softHit,gripPoint,gripDelta;
        bool fixedInspection;Vector3 beforeFixture;float beforeYaw,beforePitch;
        GUIStyle normal,small,heading,center;
        static readonly Dictionary<string,string> descriptions=new Dictionary<string,string>{
            {"field_glasses","Ceramic-coated objectives, a bonded rangefinder, and two thumbwheels for fine focus. Serial 07-318."},
            {"access_card","ASTER REACH / SERVICE. The orange contact stripe matches the reader beside the pressure hatch."},
            {"logbook","02:14 anchor time. The port guide ran warm over splice 21. Replaced the upper bearing and watched it for three cycles. — A. Imani"},
            {"mug","A magnetic foot keeps the cup on the galley strip when the carriage crosses a ribbon splice."},
            {"tool_roll","A sealed kit of torque keys and insulated drivers. The 6 mm key has a fresh witness mark."},
            {"grab_handle","Forged titanium anchor. The exposed contact face has been polished by thousands of hands."},
            {"window","Optically bonded pressure laminates. The black edge band protects the seal from ultraviolet light."},
            {"ascent_lever","Three positive detents switch the exterior cameras. The carriage drive follows anchor control."},
            {"roller_shade","A low-glare sunshade traverses the front glazing on a pair of tensioned runners."},
            {"service_cabinet","The power trunk and the isolated data harness run on separate retainers."},
            {"pressure_hatch","A pressure interlock holds the door until the two compartments equalize."},
            {"docking_wheel","Three ratchet teeth seat the terminal clamp after the autonomous drive reaches a full stop."}
        };
        public const int ShellRay=10,PropRay=11,InspectionLayer=30,PassengerLayer=12;
        public static bool SoftwareGraphics{get;private set;}
        bool boarded;
        public void BoardWeb(){boarded=true;SetPassengerPointer(false);if(ride)ride.Board();}
        int lookAfterFrame,closingPressFrame;float lookAfterTime,closingPressTime;bool consumeClosingPress;
        public bool GlazingMagnified=>observing;
        public void RecapturePointer(){lookAfterFrame=Time.frameCount+3;lookAfterTime=Time.unscaledTime+.14f;}
        void SetPassengerPointer(bool free,bool closedByMouse=false){
            Cursor.lockState=free?CursorLockMode.None:CursorLockMode.Locked;Cursor.visible=free;
            if(!free)RecapturePointer();
            consumeClosingPress=!free&&closedByMouse;
            if(consumeClosingPress){closingPressFrame=Time.frameCount+3;closingPressTime=Time.unscaledTime+.14f;}
        }
        #if UNITY_WEBGL && !UNITY_EDITOR
        [DllImport("__Internal")] static extern void UpwellReturnToSeat();
        [DllImport("__Internal")] static extern void UpwellFrameSample(int frame,double seconds,float signedLoad,float gasFraction,int tests,int strokes,float curtain,int contact,int holds,int fabricTugs);
        [DllImport("__Internal")] static extern void UpwellMomentSample(double clock,int count,int selected,int menu,int follows,int watch,int cell,int direct,int w,int h,int sky,float lens,float km,double aboard,double rate,int realTime);
        [DllImport("__Internal")] static extern int UpwellSoftwareGraphics();
        double nextFrameSample;
        #endif
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.BeforeSceneLoad)]
        static void ReadBrowserBudget(){
            #if UNITY_WEBGL && !UNITY_EDITOR
            SoftwareGraphics=UpwellSoftwareGraphics()!=0;
            #else
            string renderer=(SystemInfo.graphicsDeviceName??"").ToLowerInvariant();
            SoftwareGraphics=renderer.Contains("basic render")||renderer.Contains("swiftshader")||renderer.Contains("llvmpipe")||renderer.Contains("warp");
            #endif
            Shader.SetGlobalFloat("_UpwellSimplifiedOptics",SoftwareGraphics?1:0);
            if(!SoftwareGraphics)return;
            QualitySettings.antiAliasing=0;QualitySettings.pixelLightCount=2;
            QualitySettings.shadowCascades=0;QualitySettings.shadowDistance=24;QualitySettings.shadowResolution=ShadowResolution.Low;
            QualitySettings.shadows=ShadowQuality.HardOnly;
        }
        static void Leave(){
            #if UNITY_WEBGL && !UNITY_EDITOR
            UpwellReturnToSeat();
            #else
            Application.Quit();
            #endif
        }
        void Start(){
            LoadMoments();
            InstallGraphics();
            body=GetComponent<CharacterController>();body.minMoveDistance=0;yaw=transform.eulerAngles.y;eye.fieldOfView=viewFov;
            berthGrip=FindFirstObjectByType<CurtainHandle>();
            optics=eye.GetComponent<PassengerOptics>();
            Physics.IgnoreLayerCollision(PassengerLayer,ShellRay);Physics.IgnoreLayerCollision(PassengerLayer,PropRay);
            Physics.IgnoreLayerCollision(LooseItemBody.Layer,15);
            #if UNITY_WEBGL && !UNITY_EDITOR
            if(!boarded){Cursor.lockState=CursorLockMode.None;Cursor.visible=true;}
            #else
            boarded=true;Cursor.lockState=CursorLockMode.Locked;Cursor.visible=false;
            #endif
        }
        void Update(){
            if(pendingBoardingMoment!=null)ApplyBoardingMoment();
            if(watchView==12&&ride.Seconds<AscentRoute.Duration)SetWatch(10);
            #if UNITY_WEBGL && !UNITY_EDITOR
            double sampleTime=Time.realtimeSinceStartupAsDouble;
            if(sampleTime>=nextFrameSample){
                nextFrameSample=sampleTime+.40;var bench=ride?ride.experiments:null;
                UpwellFrameSample(Time.frameCount,sampleTime,bench?bench.IndicatedG:0,bench&&bench.fluid?bench.fluid.MeasuredGasFraction:0,bench?bench.TestCount:0,bench?bench.PrimeCount:0,berthGrip?berthGrip.control.Position:0,activeRail||RailFocus?1:softFocus&&softFocus.IsCurtain?2:0,railGestures,hemGestures);
                if(ride&&ride.exterior&&ride.exterior.SensorCamera){
                    var sensor=ride.exterior.SensorCamera;
                    UpwellMomentSample(ride.Seconds,MomentCount,MomentIndex,momentsOpen?1:0,followMomentView?1:0,watchView,
                        Examined&&Examined.id=="capillary_cell"?(autoMomentFixture?2:1):0,sensor.enabled&&sensor.targetTexture==null?1:0,sensor.pixelWidth,sensor.pixelHeight,ride.exterior.SensorRadianceWidth,sensor.fieldOfView,ride.Altitude,ride.AboardSeconds,ride.ShipRate,ride.RealShipTime?1:0);
                    ReportGraphics();
                }
            }
            #endif
            if(!boarded)return;
            if(watchView==1)FollowHarborRail();
            if(JournalInput())return;
            if(Input.GetKeyDown(KeyCode.F2)){SetGraphicsMenu(!GraphicsMenuVisible);return;}
            if(GraphicsMenuVisible){GraphicsKeys();return;}
            if(Input.GetKeyDown(KeyCode.M)){ToggleMoments();return;}
            if(momentsOpen&&Input.GetKeyDown(KeyCode.Escape)){SetMomentsOpen(false);return;}
            if(momentsOpen&&Input.GetKeyDown(KeyCode.Home)){momentScroll.y=0;return;}
            if(momentsOpen&&Input.GetKeyDown(KeyCode.End)){momentScroll.y=100000;return;}
            bool nextStage=Input.GetKeyDown(KeyCode.N),previousStage=Input.GetKeyDown(KeyCode.P);
            if(nextStage||previousStage||Input.GetKeyDown(KeyCode.RightBracket)||Input.GetKeyDown(KeyCode.LeftBracket)){
                int direction=nextStage||Input.GetKeyDown(KeyCode.RightBracket)?1:-1;
                if(nextStage||previousStage||Input.GetKey(KeyCode.LeftShift)||Input.GetKey(KeyCode.RightShift)){
                    FinishPassageGesture();if(momentsOpen)SetMomentsOpen(false);MomentIndex=-1;LastMoment=null;
                    if(direction>0)ride.NextWaypoint();else ride.PreviousWaypoint();
                }
                else StepMoment(direction);
                return;
            }
            if(momentsOpen)return;
            if(Input.GetKeyDown(KeyCode.F1)||Input.GetKeyDown(KeyCode.Escape)){
                if(Examined)CloseInspect();else {Help=!Help;SetPassengerPointer(Help);}
            }
            // Only the mouse click that closed a panel is consumed. A later pointer lock event
            // can correct look deltas, but it must never discard a fresh world interaction.
            if(consumeClosingPress){
                if(Time.frameCount<=closingPressFrame||Time.unscaledTime<closingPressTime)return;
                consumeClosingPress=false;
            }
            if(pressedInstrument){
                if(Help||!Input.GetKey(KeyCode.E)&&!Input.GetMouseButton(0)){
                    ride.experiments.ReleaseControl(pressedInstrument);pressedInstrument=null;
                }else return;
            }
            if(Help){if(gripped)gripped.Release();gripped=null;softCandidate=null;dragging=null;if(activeRail)ReleaseRail(false);return;}
            if(ReducedLoad&&(queuedPush||Input.GetKeyDown(KeyCode.Space))&&(Resting||watchView!=0||Examined&&!exhibit))LeaveObservationForPush();
            float mx=Input.GetAxisRaw("Mouse X"),my=Input.GetAxisRaw("Mouse Y");
            if(Time.frameCount<=lookAfterFrame||Time.unscaledTime<lookAfterTime){mx=0;my=0;}
            if(activeRail) {
                if(Input.GetMouseButton(0))DragRail(mx*10,my*10);
                if(Input.GetMouseButtonUp(0)||!Input.GetMouseButton(0))ReleaseRail(true);return;
            }
            if(Examined){
                if(FractureCartridge.IsInstrument(Examined.id)){
                    if(Input.GetKeyDown(KeyCode.Q)||Input.GetMouseButtonDown(0))ride.fracture.BeginPress();
                    if(Input.GetKeyUp(KeyCode.Q)||Input.GetMouseButtonUp(0))ride.fracture.ReleasePress();
                    if(Input.GetKeyDown(KeyCode.R))ride.fracture.Reload();
                    if(Input.GetKeyDown(KeyCode.F)||Input.GetKeyDown(KeyCode.E)||Input.GetKeyDown(KeyCode.I))CloseInspect();
                    return;
                }
                if(examinedRail&&Input.GetMouseButtonDown(0)){BeginRail(examinedRail);return;}
                if(exhibit&&Examined.id=="mug"&&Input.GetKeyDown(KeyCode.T)){FitFlask();return;}
                if(exhibit&&Input.GetKeyDown(KeyCode.G)){LetGo();return;}
                bool flask=exhibit&&Examined.id=="mug"&&heldControl;
                if(flask&&Input.GetMouseButtonDown(0)&&ValveUnderPointer())valveFinger=true;
                if(!Input.GetMouseButton(0))valveFinger=false;
                if(flask){
                    bool pressing=valveFinger||valveGui||Input.GetKey(KeyCode.Q);
                    if(pressing&&!valvePad)ride.Click(ride.relay,.20f);
                    heldControl.HoldValve(pressing);valvePad=pressing;
                }
                if(exhibit&&!valveFinger&&Input.GetMouseButtonDown(0)){handDown=true;handMoved=false;dragOffset=Vector3.zero;}
                if(handDown&&Input.GetMouseButton(0)){dragOffset=Vector3.ClampMagnitude(dragOffset+new Vector3(mx,my,0)*.014f,.24f);if(dragOffset.magnitude>.027f)handMoved=true;}
                if(handDown&&Input.GetMouseButtonUp(0)){handDown=false;if(handMoved){LetGo();return;}if(!flask)OperateHeld();}
                if(exhibit&&Input.GetMouseButton(1)){yaw+=mx*1.7f;pitch=Mathf.Clamp(pitch-my*1.4f,-83,83);transform.rotation=Quaternion.Euler(0,yaw,0);eye.transform.localRotation=Quaternion.Euler(pitch,0,0);}
                else if(!handDown&&!valvePad)RotateItem(mx*4,-my*3);
                holdingZoom=Mathf.Clamp(holdingZoom-Input.mouseScrollDelta.y*.09f,.68f,1.45f);
                if(Input.GetKeyDown(KeyCode.Q)&&!flask){
                    if(examinedRail)ride.Use(examinedRail.control,this);
                    else if(examinedFabric)examinedFabric.Brush(examinedFabric.TouchPoint);
                    else if(!exhibit&&ride.experiments&&ride.experiments.IsInstrument(Examined.id))ride.experiments.Operate(Examined.id);else OperateHeld();
                }
                if(Input.GetKeyDown(KeyCode.R))flip=flip==0?180:0;
                if(exhibit&&body.enabled){ReadWalkingAxes(out float side,out float walk);MovePassenger(side,walk,true);}
                if(exhibit)PoseInHand();
                if(Input.GetKeyDown(KeyCode.I)||Input.GetKeyDown(KeyCode.F)||Input.GetKeyDown(KeyCode.E)){
                    if(Input.GetKeyDown(KeyCode.E)&&Examined.portable&&!ride.Has(Examined.id))ride.Pickup(Examined);CloseInspect();}
                return;
            }
            if(Input.GetKeyDown(KeyCode.B)){VisitFixture("fracture_cell");return;}
            if(Input.GetKeyDown(KeyCode.Alpha7)||Input.GetKeyDown(KeyCode.Alpha8)){
                VisitFixture(Input.GetKeyDown(KeyCode.Alpha7)?"accelerometer":"capillary_cell");return;
            }
            if(Input.GetKeyDown(KeyCode.Alpha9)){SetWatch(7);return;}
            if(Input.GetKeyDown(KeyCode.C)){SetWatch(10);return;}
            if(Input.GetKeyDown(KeyCode.L)&&ride.Progress>=1){SetWatch(12);return;}
            if(Input.GetKeyDown(KeyCode.O)){SetWatch(11);return;}
            if(Input.GetKeyDown(KeyCode.V)){SetWatch((watchView+1)%7);return;}
            for(int view=0;view<=6;view++)if(Input.GetKeyDown((KeyCode)((int)KeyCode.Alpha0+view))){SetWatch(view);return;}
            if(watchView>0&&((watchView!=7&&Input.GetKeyDown(KeyCode.E))||Input.GetKeyDown(KeyCode.W)||Input.GetKeyDown(KeyCode.S))){SetWatch(0);return;}
            if(UsingSensor)return;
            if(Input.GetKeyDown(KeyCode.Tab))ride.CycleItem();
            if(Input.GetKeyDown(KeyCode.I)){if(ride.Held)Inspect(ride.Held);else ride.Say("Your pockets are empty");return;}
            ReadWalkingAxes(out float h,out float v);
            if(Resting&&(Input.GetKeyDown(KeyCode.E)||Input.GetMouseButtonDown(0)||Mathf.Abs(h)+Mathf.Abs(v)>.5f)){Rise();return;}
            if(watchView==11)AimShadedWindow(mx,my,false);
            else if(!dragging) {
                yaw+=mx*1.75f;pitch=Mathf.Clamp(pitch-my*1.5f,-88,watchView==6?89.8f:83);
                transform.rotation=Quaternion.Euler(0,yaw,0);eye.transform.localRotation=Quaternion.Euler(pitch,0,0);
            }
            if(!Resting&&watchView==0)MovePassenger(h,v,false);
            if(!dragging)Focus=FindFocus();
            if(!Resting&&RailFocus&&Input.GetMouseButtonDown(0)){BeginRail(RailFocus);return;}
            if(softFocus&&Input.GetKeyDown(KeyCode.Q))softFocus.Brush(softHit);
            if(!Resting&&Focus&&ride.experiments&&(Input.GetKeyDown(KeyCode.E)||Input.GetMouseButtonDown(0))&&ride.experiments.HoldControl(Focus)){
                pressedInstrument=Focus;return;
            }
            if(Input.GetKeyDown(KeyCode.E)&&!Resting){
                if(softFocus&&softFocus.IsCable)softFocus.Brush(softHit);else ride.Use(Focus,this);
            }
            if(Input.GetKeyDown(KeyCode.F)&&Focus)Inspect(Focus);
            if(Input.GetMouseButtonDown(0)&&!Resting&&Focus){dragging=Focus;dragSum=0;workingHandle=false;dragOrigin=Focus.Target;dragTime=Time.unscaledTime;softCandidate=softFocus;gripPoint=softHit;gripDelta=Vector3.zero;}
            if(dragging&&Input.GetMouseButton(0)){
                dragSum+=mx-my;
                if(softCandidate&&Time.unscaledTime-dragTime>=.16f&&(gripped||Mathf.Abs(dragSum)>.25f||Time.unscaledTime-dragTime>.38f)){
                    if(!gripped&&softCandidate.Grip(gripPoint)){gripped=softCandidate;if(gripped.IsCurtain)hemGestures++;}
                    if(gripped){
                        gripDelta+=(eye.transform.right*mx+eye.transform.up*my)*.022f;
                        gripped.Pull(gripDelta-eye.transform.forward*Mathf.Min(.045f,gripDelta.magnitude*.21f));return;
                    }
                }
                bool variable=dragging.id=="locker_drawer"||dragging.id=="service_cabinet"||dragging.id=="roller_shade"||dragging.id=="privacy_curtain";
                if(variable&&!softCandidate&&Mathf.Abs(dragSum)>.75f){
                    if(!workingHandle)ride.Click(ride.runner,.5f);workingHandle=true;
                    float sign=dragOrigin>.5f?-1:1;dragging.SetTarget(dragOrigin+sign*Mathf.Abs(dragSum)*.14f);
                }
            }
            if(dragging&&Input.GetMouseButtonUp(0)){
                if(gripped){gripped.Release();gripped=null;}
                else if(softCandidate&&softCandidate.IsCable){softCandidate.Brush(gripPoint);}
                else if(workingHandle){dragging.SetOpen(dragging.Target>.48f);ride.Click(ride.relay,.62f);}
                else if(dragging.id=="ascent_lever"&&Mathf.Abs(dragSum)>.7f)ride.SetFeed(ride.Feeds+(dragSum>0?1:-1));
                else if(Time.unscaledTime-dragTime<.6f||Mathf.Abs(dragSum)>.65f)ride.Use(dragging,this);
                dragging=null;softCandidate=null;
            }
            eye.fieldOfView=Mathf.Lerp(eye.fieldOfView,watchView==11?52:watchView==6?59:observing?38:viewFov,Time.deltaTime*7);
        }
        public TransitProp FindFocus() {
            softFocus=null;RailFocus=null;
            var ray=new Ray(eye.transform.position,eye.transform.forward);int layers=(1<<PropRay)|(1<<ShellRay)|(1<<LooseItemBody.Layer);
            if(Physics.Raycast(ray,out RaycastHit direct,3.05f,layers,QueryTriggerInteraction.Collide)){
                RailFocus=direct.collider.GetComponentInParent<CurtainHandle>();
                if(RailFocus)return RailFocus.control;
                var textile=direct.collider.GetComponentInParent<FurnishingSurface>();
                if(textile&&textile.Accessible){softFocus=textile;softHit=direct.point;return textile.control;}
                var prop=direct.collider.GetComponentInParent<TransitProp>();
                if(prop&&VisibleProp(prop))return prop;
            }
            // Tiny latches and cards have forgiving targets, while shell geometry still occludes them.
            TransitProp best=null;float score=.982f;
            foreach(var p in ride.props.Values){
                if(!p.gameObject.activeInHierarchy||!VisibleProp(p))continue;
                if(!p.portable&&!p.panelControl&&p.id!="ascent_lever"&&p.id!="roller_shade"&&p.id!="card_reader"&&p.id!="breaker")continue;
                Vector3 d=p.Focus-ray.origin;float length=d.magnitude;if(length>2.5f||length<.001f)continue;
                float dot=Vector3.Dot(ray.direction,d/length);if(dot<=score)continue;
                if(Physics.Raycast(ray.origin,d/length,out var wall,length-.045f,layers,QueryTriggerInteraction.Collide)){
                    var ahead=wall.collider.GetComponentInParent<TransitProp>();
                    if(ahead!=p)continue;
                }
                best=p;score=dot;
            }return best;
        }
        public void BeginRail(CurtainHandle handle) {
            activeRail=handle;screenStroke=handle.ScreenTravel(eye);pendingPixels=verticalPixels=0;railMoved=false;
            handle.control.Drive(handle.control.Position);
        }
        int railGestures,hemGestures;
        public void DragRail(float horizontal,float vertical) {
            if(!activeRail)return;verticalPixels+=Mathf.Abs(vertical);
            if(!railMoved){
                pendingPixels+=horizontal;if(Mathf.Abs(pendingPixels)<3)return;
                horizontal=pendingPixels;railMoved=true;railGestures++;ride.Click(ride.runner,.46f);
            }
            activeRail.control.Drive(Mathf.Clamp01(activeRail.control.Position+horizontal/screenStroke));
        }
        public void ReleaseRail(bool allowClick) {
            if(!activeRail)return;var handle=activeRail;activeRail=null;
            if(railMoved){
                float t=handle.control.Position;
                handle.control.Drive(t<.015f?0:t>.985f?1:t);
                if(t<.015f||t>.985f)ride.Click(ride.relay,.50f);
            }else if(allowClick&&verticalPixels<5)ride.Use(handle.control,this);
        }
        bool VisibleProp(TransitProp p)=>p.id!="access_card"||p.transform.parent!=ride.props["locker_drawer"].transform||ride.props["locker_drawer"].Position>.48f;
        public void Place(Vector3 pos,float heading,float elevation){
            ResetMotion();
            if(body)body.enabled=false;transform.position=pos;yaw=heading;pitch=elevation;
            transform.rotation=Quaternion.Euler(0,yaw,0);eye.transform.localRotation=Quaternion.Euler(pitch,0,0);
            if(body)body.enabled=!Resting;
        }
        public void Rest(TransitProp p){
            if(!applyingMoment)momentOrigin=null;
            savedPosition=transform.position;savedHeading=Quaternion.Euler(pitch,yaw,0);Resting=true;InBerth=p.id=="bunk";observing=false;
            var f=p.Focus;
            if(p.id=="bunk")Place(new Vector3(f.x+.18f,f.y+.18f-1.58f,f.z),82,-7);
            else Place(new Vector3(f.x+.08f,1.19f-1.58f,f.z),18,-2);
            Focus=null;ride.Say(p.id=="bunk"?"Sleeper berth · E to get up":"Window seat · E to stand");
        }
        public void Rise(){Resting=false;InBerth=false;float s=savedHeading.eulerAngles.x;Place(savedPosition,savedHeading.eulerAngles.y,s>180?s-360:s);ride.Say("Standing");}
        public void Observe(){observing=!observing;ride.Say(observing?"Observation glazing · E to widen view":"Cabin view");}
        float HarborRailWeight()=>1-Mathf.SmoothStep(0,1,Mathf.InverseLerp(23,36,(float)ride.Seconds));
        void FollowHarborRail(){
            float next=HarborRailWeight(),d=next-harborRailWeight;
            if(Mathf.Abs(d)<.000001f)return;
            // Shift along the existing rail without taking the passenger's mouse-look away.
            transform.position+=new Vector3(-.51f,-.075f,.49f)*d;
            yaw-=8.36f*d;pitch+=5.5f*d;harborRailWeight=next;
            transform.rotation=Quaternion.Euler(0,yaw,0);eye.transform.localRotation=Quaternion.Euler(pitch,0,0);
        }
        bool UsingSensor=>(watchView>=3&&watchView<=5)||(watchView>=8&&watchView<=10)||watchView==12;
        Vector2 shadedLook;
        void AimShadedWindow(float mouseX,float mouseY,bool entering){
            var ray=-AscentRoute.Sun(ride.PreciseAltitude);
            if(entering)shadedLook=Vector2.zero;
            else shadedLook=new Vector2(Mathf.Clamp(shadedLook.x+mouseX*1.75f,-56,56),Mathf.Clamp(shadedLook.y-mouseY*1.5f,-41,41));
            float halfWidth=Mathf.Atan(Mathf.Tan(26*Mathf.Deg2Rad)*eye.aspect)*Mathf.Rad2Deg;
            var aim=Quaternion.LookRotation(ray,Vector3.up)*Quaternion.Euler(-2.5f,Mathf.Min(5,.35f*halfWidth),0)*Vector3.forward;
            yaw=Mathf.Atan2(aim.x,aim.z)*Mathf.Rad2Deg+shadedLook.x;
            pitch=Mathf.Clamp(-Mathf.Asin(Mathf.Clamp(aim.y,-1,1))*Mathf.Rad2Deg+shadedLook.y,-89,89);
            float side=ray.x<0?-1.28f:1.28f;
            if(entering||side*transform.position.x<0)Place(new Vector3(side,1.82f,4.03f)-eye.transform.localPosition,yaw,pitch);
            else {transform.rotation=Quaternion.Euler(0,yaw,0);eye.transform.localRotation=Quaternion.Euler(pitch,0,0);}
        }
        public void SetWatch(int mode){
            if(mode==12&&ride.Seconds<AscentRoute.Duration)return;
            if(!applyingMoment&&momentOrigin!=null){LeaveSuggestedTour();if(Resting)Rise();}
            if(mode==0&&watchView==0)return;
            if(watchView==0){walkOrigin=transform.position;walkRotation=transform.rotation;savedPitch=pitch;}
            watchView=mode;ride.exterior.WatchSensor(UsingSensor?(mode>=8?mode-4:mode-2):0);eye.enabled=!UsingSensor;Focus=null;
            if(mode==0){Place(walkOrigin,walkRotation.eulerAngles.y,savedPitch);ride.Say("Aisle");}
            else if(mode==1){
                harborRailWeight=HarborRailWeight();
                Place(new Vector3(-.70f,.095f,4.32f)+new Vector3(-.51f,-.075f,.49f)*harborRailWeight,
                    ride.Seconds>322?7.65f:-8.36f*harborRailWeight,ride.Seconds>322?-7.1f:2+5.5f*harborRailWeight);
                ride.Say("Forward observation · V changes view");
            }
            else if(mode==2){float s=AscentRoute.Sun(ride.PreciseAltitude).x>=0?1:-1;Place(new Vector3(s*.40f,.035f,3.64f),s*86,-1);ride.Say("Sunward window · V changes view");}
            else if(mode==3)ride.Say("Earth observation optics");
            else if(mode==4){ride.Say("Stabilized berthing optics");}
            else if(mode==5)ride.Say("Along the guide rail");
            else if(mode==6){Place(new Vector3(0,-.17f,3.80f),0,88);eye.fieldOfView=59;ride.Say("Earthward floor window");}
            else if(mode==11){AimShadedWindow(0,0,true);eye.fieldOfView=52;ride.Say("Shaded side window · facing away from the Sun");}
            else if(mode==12)ride.Say("Valley gallery · live from the transfer spindle");
            else if(mode>=8)ride.Say(mode==8?"Counterline optics":mode==9?"Star field":ride.exterior.OnHabitatRelay?"Aster hub relay":"Colony optics");
            else if(berthGrip){
                var grip=berthGrip.Grip;var foot=new Vector3(.22f,.03f,grip.z);
                var ray=(grip-foot-eye.transform.localPosition).normalized;
                Place(foot,Mathf.Atan2(ray.x,ray.z)*Mathf.Rad2Deg,-Mathf.Asin(ray.y)*Mathf.Rad2Deg);
                Physics.SyncTransforms();Focus=FindFocus();ride.Say("Berth screen handle · drag horizontally");
            }
        }
        public void OperateHeld(){
            if(!exhibit)return;
            if(heldControl){heldControl.Click();ride.Click(heldControl.detents>2?ride.relay:ride.latch,.6f);}
            else{flip=flip==0?180:0;ride.Click(ride.relay,.24f);}
        }
        public void RotateItem(float horizontal,float vertical){inspectYaw+=horizontal;inspectPitch=Mathf.Clamp(inspectPitch+vertical,-88,88);}
        public void VisitFixture(string id){
            if(!ride.experiments||!ride.props.ContainsKey(id))return;
            if(id=="fracture_cell"&&!ride.Unlocked&&transform.position.z> -2.05f){
                ride.Say("Service hatch locked · the crew key is in the berth drawer",3.4f);return;
            }
            LeaveSuggestedTour();
            if(watchView>0)SetWatch(0);
            if(Resting)Rise();
            beforeFixture=transform.position;beforeYaw=yaw;beforePitch=pitch;
            if(id=="fracture_cell")Place(ride.fracture.InspectionEye-eye.transform.localPosition,180,3);
            else if(id=="accelerometer")Place(new Vector3(-.70f,.04f,3.86f),0,10);
            else Place(new Vector3(.55f,.04f,.55f),89,8);
            fixedInspection=true;Inspect(ride.props[id]);
        }
        public void LetGo(){
            if(!exhibit||!heldOrigin||!Examined)return;
            var p=Examined;Vector3 pos=heldOrigin.position;Quaternion attitude=heldOrigin.rotation;Vector3 v=releaseVelocity,w=releaseSpin;
            CloseInspect();ride.Release(p,pos,attitude,v,w);
        }
        public bool FitFlask(){
            if(!exhibit||!heldOrigin||!Examined||Examined.id!="mug")return false;
            if(!ride.ParkVessel(eye.transform.position,heldOrigin.position,heldOrigin.rotation))return false;
            CloseInspect();return true;
        }
        bool ValveUnderPointer(){
            if(!heldJoint)return false;
            var ray=Cursor.lockState==CursorLockMode.Locked?eye.ViewportPointToRay(new Vector3(.5f,.5f,0)):eye.ScreenPointToRay(Input.mousePosition);
            foreach(var mesh in heldJoint.GetComponentsInChildren<MeshRenderer>())if(mesh.bounds.IntersectRay(ray))return true;
            return false;
        }
        void PoseInHand(bool snap=false){
            float dist=holdingDistance*holdingZoom;
            float g=(float)ride.Forces.GravityG;
            var target=new Vector3(.018f,-.016f+.005f*(1-Mathf.Clamp01(g)),dist)+ride.StructureImpulse*.0028f+dragOffset;
            exhibit.transform.localPosition=snap?target:Vector3.SmoothDamp(exhibit.transform.localPosition,target,ref handVelocity,.08f);
            var rotation=Quaternion.Euler(inspectPitch,inspectYaw,0)*Quaternion.AngleAxis(flip,Vector3.right);
            exhibit.transform.localRotation=snap?rotation:Quaternion.Slerp(exhibit.transform.localRotation,rotation,1-Mathf.Exp(-15*Time.deltaTime));
            if(heldControl&&heldJoint){heldControl.Advance(Time.deltaTime);heldJoint.localRotation=heldControl.transform.localRotation;}
            Vector3 position=exhibit.transform.position;var attitude=exhibit.transform.rotation;
            if(snap){releaseVelocity=releaseSpin=Vector3.zero;}else{
                float dt=Mathf.Max(.001f,Time.deltaTime),blend=1-Mathf.Exp(-22*dt);
                releaseVelocity=Vector3.Lerp(releaseVelocity,(position-lastHand)/dt,blend);
                Quaternion delta=attitude*Quaternion.Inverse(lastAttitude);delta.ToAngleAxis(out float degrees,out var axis);if(degrees>180)degrees-=360;
                if(axis.sqrMagnitude>.01f&&!float.IsNaN(axis.x))releaseSpin=Vector3.Lerp(releaseSpin,axis*(degrees*Mathf.Deg2Rad/dt),blend);
            }
            lastHand=position;lastAttitude=attitude;
            if(optics)optics.FocusDistance=dist;
        }
        public void Inspect(TransitProp p){
            if(!applyingMoment)momentOrigin=null;
            if(!p)return;if(Examined)CloseInspect();Examined=p;examinedRail=RailFocus&&RailFocus.control==p?RailFocus:null;examinedFabric=softFocus&&softFocus.control==p?softFocus:null;
            if(!examinedRail&&!examinedFabric&&(p.id=="bunk"||p.id=="privacy_curtain"||p.id=="service_cabinet"))
                foreach(var f in FindObjectsByType<FurnishingSurface>(FindObjectsInactive.Exclude))if(f.control==p&&f.Accessible){examinedFabric=f;break;}
            dragging=null;inspectYaw=p.id=="mug"?-62:-16;holdingZoom=1;flip=0;handVelocity=Vector3.zero;
            handDown=handMoved=false;dragOffset=Vector3.zero;
            var loose=p.GetComponent<LooseItemBody>();if(loose&&loose.Free)ride.Pickup(p);
            if(!optics)optics=eye.GetComponent<PassengerOptics>();
            if(!p.portable){
                var lookAt=examinedRail?examinedRail.Grip:examinedFabric?examinedFabric.TouchPoint:p.Focus;bool bench=ride.experiments&&ride.experiments.IsInstrument(p.id);
                if(FractureCartridge.IsInstrument(p.id))lookAt=ride.fracture.ViewCenter;
                if(bench&&(p.id=="accel_test"||p.id=="capillary_primer"))
                    lookAt=ride.props[p.id=="accel_test"?"accelerometer":"capillary_cell"].Focus;
                Vector3 look=(lookAt-eye.transform.position).normalized;
                eye.transform.rotation=Quaternion.LookRotation(look,Vector3.up);
                float halfFrame=FractureCartridge.IsInstrument(p.id)?.221f:p.id=="capillary_cell"||p.id=="capillary_primer"?.182f:.28f;
                eye.fieldOfView=bench?Mathf.Clamp(2*Mathf.Atan(halfFrame/Mathf.Max(.1f,Vector3.Distance(eye.transform.position,lookAt)))*Mathf.Rad2Deg,10,50):47;
                if(optics)optics.FocusDistance=Vector3.Distance(eye.transform.position,lookAt);return;
            }
            inspectPitch=p.id=="access_card"||p.id=="logbook"||p.id=="tool_roll"?-66:p.id=="field_glasses"?-38:p.id=="mug"?-36:-18;
            exhibit=new GameObject("Held "+p.title);exhibit.transform.SetParent(eye.transform,false);
            var holder=new GameObject("Centered object").transform;holder.SetParent(exhibit.transform,false);heldOrigin=holder;
            heldControl=p.GetComponentInChildren<HandMechanism>(true);if(heldControl){heldJoint=new GameObject(heldControl.partId).transform;heldJoint.SetParent(holder,false);heldJoint.localPosition=p.transform.InverseTransformPoint(heldControl.transform.position);heldJoint.localRotation=heldControl.transform.localRotation;}
            Bounds bound=new Bounds();bool first=true;
            foreach(var source in p.GetComponentsInChildren<MeshFilter>(true)){
                if(source.sharedMesh==null)continue;
                bool articulated=heldControl&&source.transform.IsChildOf(heldControl.transform);var g=new GameObject(source.name);g.transform.SetParent(articulated?heldJoint:holder,false);
                Matrix4x4 relative=p.transform.worldToLocalMatrix*source.transform.localToWorldMatrix;
                var pose=articulated?heldControl.transform.worldToLocalMatrix*source.transform.localToWorldMatrix:relative;
                g.transform.localPosition=pose.GetColumn(3);g.transform.localRotation=pose.rotation;g.transform.localScale=pose.lossyScale;
                g.AddComponent<MeshFilter>().sharedMesh=source.sharedMesh;var r=g.AddComponent<MeshRenderer>();var srcRenderer=source.GetComponent<MeshRenderer>();r.sharedMaterials=srcRenderer.sharedMaterials;
                var flexible=source.GetComponent<FlexibleTail>();if(flexible)flexible.CopyTo(g);
                for(int slot=0;slot<r.sharedMaterials.Length;slot++){var block=new MaterialPropertyBlock();srcRenderer.GetPropertyBlock(block,slot);if(!block.isEmpty)r.SetPropertyBlock(block,slot);}
                r.shadowCastingMode=UnityEngine.Rendering.ShadowCastingMode.On;r.receiveShadows=true;
                if(p.gameObject.activeInHierarchy&&srcRenderer.enabled){liftedRenderers.Add(srcRenderer);srcRenderer.enabled=false;}
                var local=source.sharedMesh.bounds;for(int j=0;j<8;j++){
                    Vector3 corner=local.center+Vector3.Scale(local.extents,new Vector3((j&1)==0?-1:1,(j&2)==0?-1:1,(j&4)==0?-1:1));
                    var v=relative.MultiplyPoint3x4(corner);if(first){bound=new Bounds(v,Vector3.zero);first=false;}else bound.Encapsulate(v);
                }
            }
            holder.localPosition=-bound.center;eye.fieldOfView=44;
            // Fit a conservative bounding sphere even after a hinge opens or the passenger turns the assembly end-on.
            float radius=bound.size.magnitude*.5f;
            float comfortable=radius/(Mathf.Sin(22*Mathf.Deg2Rad)*.73f)+.035f;
            holdingDistance=Mathf.Max(.205f,comfortable);PoseInHand(true);
        }
        public void CloseInspect(){if(!applyingMoment&&autoMomentFixture&&momentOrigin!=null){LeaveSuggestedTour();return;}if(Examined&&FractureCartridge.IsInstrument(Examined.id))ride.fracture.ReleasePress();if(exhibit){exhibit.SetActive(false);Destroy(exhibit);}exhibit=null;heldControl=null;heldJoint=null;heldOrigin=null;handDown=handMoved=false;dragOffset=Vector3.zero;foreach(var r in liftedRenderers)if(r)r.enabled=true;liftedRenderers.Clear();
            if(Examined&&Examined.id=="mug")Examined.GetComponentInChildren<HandMechanism>(true)?.HoldValve(false);
            valveFinger=valveGui=valvePad=false;
            Examined=null;autoMomentFixture=false;examinedFabric=null;examinedRail=null;if(optics)optics.FocusDistance=0;eye.fieldOfView=viewFov;eye.transform.localRotation=Quaternion.Euler(pitch,0,0);
            if(fixedInspection){fixedInspection=false;Place(beforeFixture,beforeYaw,beforePitch);}}
        void Styles(){
            if(normal!=null)return;
            normal=new GUIStyle(GUI.skin.label){fontSize=16,wordWrap=true};normal.normal.textColor=new Color(.90f,.93f,.94f);
            small=new GUIStyle(normal){fontSize=12};small.normal.textColor=new Color(.70f,.77f,.79f);
            heading=new GUIStyle(normal){fontSize=22,fontStyle=FontStyle.Bold};
            center=new GUIStyle(normal){alignment=TextAnchor.MiddleCenter,fontSize=15};
        }
        static void Plate(Rect r){var previous=GUI.color;GUI.color=new Color(.025f,.043f,.050f,.87f);GUI.DrawTexture(r,Texture2D.whiteTexture);GUI.color=previous;}
        void OnGUI(){
            if(!ride||!eye)return;Styles();float u=Mathf.Clamp(Screen.height/850f,.74f,1.6f);
            GUI.matrix=Matrix4x4.Scale(new Vector3(u,u,1));float w=Screen.width/u,h=Screen.height/u;
            if(journalOpen){DrawPhotoJournal(w,h);return;}
            if(boarded&&!GraphicsMenuVisible&&!momentsOpen)DrawShutter(w,h);
            if(GraphicsMenuVisible){DrawGraphicsMenu(w,h);return;}
            if(GUI.Button(new Rect(w-122,17,104,29),"F2   Graphics")){SetGraphicsMenu(true);return;}
            if(momentsOpen){DrawMomentMenu(w,h);return;}
            if(!Help&&ReducedLoad){
                Plate(new Rect(w-224,54,206,62));
                var load=ride.Forces.GravityG<.0005?"Microgravity":ride.Forces.Down<0?"Braking":"Reduced gravity";
                GUI.Label(new Rect(w-216,57,196,20),load+"   ·   "+ride.Forces.GravityG.ToString("0.000")+" g",small);
                if(GUI.Button(new Rect(w-215,80,188,28),"Push off"))queuedPush=true;
            }
            if(Examined){
                float tw=Mathf.Min(530,w-50);float x=28;float top=h-132;
                if(autoMomentFixture&&MomentIndex+1<MomentCount&&GUI.Button(new Rect(18,17,244,35),"Next · "+MomentAt(MomentIndex+1).name)){StepMoment(1);return;}
                Plate(new Rect(x-12,top-4,tw+24,118));
                GUI.Label(new Rect(x,top,tw,32),examinedRail?"Privacy screen handle":examinedFabric?examinedFabric.DisplayName:Examined.title,heading);
                if(exhibit&&GUI.Button(new Rect(x+tw-105,top+2,105,28),"G   Release")){LetGo();return;}
                if(exhibit&&Examined.id=="mug"&&GUI.Button(new Rect(x+tw-154,top-37,154,31),"T   Fit in galley cradle")){FitFlask();return;}
                if(exhibit&&Examined.id=="mug"){
                    bool down=GUI.RepeatButton(new Rect(x,top-37,137,31),"Q   Hold drink valve");
                    if(Event.current.type==EventType.Repaint)valveGui=down;
                }
                string measured=ride.experiments?ride.experiments.Status(Examined.id):null;
                GUI.Label(new Rect(x,top+34,tw,56),measured??(descriptions.TryGetValue(Examined.id,out string text)?text:Examined.action),normal);
                string command=examinedRail?"Drag horizontally · Q  Draw / stow · E  Return":examinedFabric?"Q  "+examinedFabric.Gesture+"    E  Return":measured!=null?(Examined.id=="accelerometer"||Examined.id=="accel_test"?"Q  Check proof mass":"Q  Press primer")+"    E  Return":"E to return";
                if(FractureCartridge.IsInstrument(Examined.id))command="Hold Q or left mouse to press   ·   R  Reload   ·   E  Return";
                GUI.Label(new Rect(x,top+85,tw,30),Examined.portable?"Q "+(heldControl?heldControl.label:"Turn over")+" · R Flip · G Release · Drag to toss · E Stow":command,small);return;
            }
            if(Help){
                float x=(w-460)/2,y=(h-405)/2;Plate(new Rect(x,y,460,405));
                GUI.Label(new Rect(x+25,y+20,380,35),"Passenger controls",heading);
                GUI.Label(new Rect(x+25,y+57,418,280),"WASD / arrows   Walk or push along your sightline\nSpace   Push off     X / Ctrl   Deckward     H   Brace\nG   Release held gear     Mouse   Look\nE / click   Use / pick up    F / I   Inspect\nV   Cycle views     0   Return to aisle\n1 Forward    2 Sunward    3 Earth optics\n4 Berthing optics    5 Guide camera\n6 Floor window    9 Berth screen handle\n7 Accelerometer    8 Capillary cell    B Proof bench\nC   Colony optics / Aster hub relay\nM   Passage moments    [ / ]   Back / next\nN / P   Next / previous stage    ·    Shift + ] / [\nO   Shaded side window    F2   Graphics",normal);
                if(GUI.Button(new Rect(x+25,y+350,185,35),"Return to carriage")){Help=false;SetPassengerPointer(false,true);}
                if(GUI.Button(new Rect(x+245,y+350,185,35),"Leave carriage"))Leave();return;
            }
            Plate(new Rect(18,17,246,75));GUI.Label(new Rect(30,22,220,19),"CAR 07   /   ASTER REACH",small);
            GUI.Label(new Rect(30,40,226,27),TransitRide.Stages[ride.Stage]+"  ·  "+AscentRoute.AltitudeText(ride.PreciseAltitude),normal);
            GUI.Label(new Rect(30,65,227,21),ride.AboardClock+" aboard  ·  "+ride.PaceText,small);
            if(GUI.Button(new Rect(18,93,147,29),"M   Passage moments"))ToggleMoments();
            GUI.enabled=AdjacentMoment(-1)>=0;if(GUI.Button(new Rect(168,93,46,29),"[ ‹"))StepMoment(-1);
            GUI.enabled=AdjacentMoment(1)>=0;if(GUI.Button(new Rect(217,93,47,29),"› ]"))StepMoment(1);GUI.enabled=true;
            if(ride.Progress>=1&&watchView!=12&&GUI.Button(new Rect(18,126,147,28),"L   Valley gallery")){SetWatch(12);return;}
            if(watchView>=8){Plate(new Rect(18,h-45,340,29));GUI.Label(new Rect(30,h-42,332,24),(watchView==12?"Aster valley gallery":watchView==11?"Shaded side window":watchView==8?"Counterline":watchView==9?"Star field":ride.exterior.OnHabitatRelay?"Aster hub relay":"Colony optics")+"    ·   E  Return",small);return;}
            if(watchView>0&&watchView<7){bool landed=ride.Progress>=1;Plate(new Rect(18,h-45,landed?445:340,29));GUI.Label(new Rect(30,h-42,landed?430:332,24),new[]{"","Forward window","Sunward window","Earth observation optics","Stabilized berthing optics","Along the guide rail","Earthward floor window"}[watchView]+(landed?"   ·   C  Aster hub relay":"")+"   ·   V  Change   E  Return",small);return;}
            GUI.color=Focus?new Color(.97f,.77f,.40f):new Color(.85f,.9f,.89f,.82f);GUI.DrawTexture(new Rect(w/2-1.6f,h/2-1.6f,3.2f,3.2f),Texture2D.whiteTexture);GUI.color=Color.white;
            if(Focus&&!Resting){
                string action=softFocus&&softFocus.IsCable?"Pluck loop":Focus.portable?"Pick up":Focus.action;
                string reading=ride.experiments?ride.experiments.Status(Focus.id):null;
                if(softFocus)reading="Q  "+softFocus.Gesture+"   ·   Hold and drag to pull";
                if(RailFocus)reading="Drag horizontally   ·   "+Mathf.RoundToInt(Focus.Position*100)+"% drawn";
                float bw=Mathf.Min(w-45,Mathf.Max(reading==null?220:385,normal.CalcSize(new GUIContent(action)).x+55));
                float yy=h-(reading==null?103:124);Plate(new Rect((w-bw)/2,yy,bw,reading==null?55:75));
                GUI.Label(new Rect((w-bw)/2,yy+3,bw,22),RailFocus?"Privacy screen handle":softFocus?softFocus.DisplayName:Focus.title,center);
                if(reading!=null)GUI.Label(new Rect((w-bw)/2,yy+24,bw,20),reading,center);
                GUI.Label(new Rect((w-bw)/2,yy+(reading==null?26:46),bw,21),"E  "+action,center);
            }
            if(ride.NoticeUntil>Time.unscaledTime){float bw=Mathf.Min(w-50,680);Plate(new Rect((w-bw)/2,22,bw,34));GUI.Label(new Rect((w-bw)/2+6,23,bw-12,30),ride.Notice,center);}
            GUI.Label(new Rect(22,h-30,610,24),ReducedLoad?"WASD  Along sightline    Space  Push off    X  Deckward    H  Brace    E  Catch    F1  Controls":"WASD  Walk      E  Use      F  Inspect      V  Views      F1  Controls",small);
        }
    }
}
