using System;
using System.Collections.Generic;
using UnityEngine;

namespace Upwell {
    [DefaultExecutionOrder(20)]
    public sealed partial class TransitRide : MonoBehaviour {
        public ExteriorRig exterior;
        public CabinSystems systems;
        public CabinExperiments experiments;
        public FractureCartridge fracture;
        public Light[] practicals;
        public AudioClip motor,relay,runner,latch,keyscan,passengerPass,freightPass;
        public AudioClip[] dispatch;
        public readonly Dictionary<string,TransitProp> props=new Dictionary<string,TransitProp>();
        public readonly List<TransitProp> inventory=new List<TransitProp>();
        public float Progress {get;private set;}
        public float Altitude {get;private set;}
        public double PreciseAltitude {get;private set;}
        public double Seconds {get;private set;}
        public bool RealShipTime {get;private set;}
        double realShipClock;
        float stargazingSeconds;
        public double ShipRate=>Seconds>=AscentRoute.Duration?0:RealShipTime||stargazingSeconds>0?1:AscentRoute.ShipRateAt(Seconds);
        public void BeginStargazing(){
            clockWarmupFrames=2;
            if(!RealShipTime){stargazingSeconds=20;realShipClock=AboardSeconds;}
        }
        int clockWarmupFrames=2;
        void OnApplicationPause(bool paused){clockWarmupFrames=2;}
        public double AboardSeconds=>Seconds<=9?Seconds:9+Forces.ShipSeconds;
        public string PaceText {
            get {
                if(Seconds>=AscentRoute.Duration)return "Docked";
                if(RealShipTime)return "Real 1×";
                if(stargazingSeconds>0)return "Stargazing 1×";
                double rate=ShipRate;
                return "Guided "+rate.ToString(rate<2?"0.##":rate<10?"0.#":"#,0",System.Globalization.CultureInfo.InvariantCulture)+"×";
            }
        }
        public string AboardClock {
            get {int t=(int)Math.Floor(AboardSeconds+.000001);return (t/3600).ToString("00")+":"+(t/60%60).ToString("00")+":"+(t%60).ToString("00");}
        }
        public void SetRealTime(bool real){stargazingSeconds=0;RealShipTime=real;realShipClock=AboardSeconds;}
        public CarriageForces Forces{get;private set;}
        public Vector3 StructureImpulse{get;private set;}
        public float Velocity {get;private set;}
        public int Stage {get;private set;}
        public int Feeds {get;private set;}
        public int DisplayMode {get;private set;}
        public bool CabinFanOn{get;set;}=true;
        public bool RadioPlaying=>speaker&&speaker.isPlaying;
        public int Turns {get;private set;}
        public bool Unlocked {get;private set;}
        public bool Docked=>Turns>=3;
        public float Pressure {get;private set;}
        public bool Equalizing=>equalization>0;
        public string Notice {get;private set;}="";
        public float NoticeUntil {get;private set;}
        public static readonly string[] Stages=AscentRoute.Stages;
        public static readonly string[] Channels={"Horizon","Tether guide","Counterline"};
        public static readonly string[] Announcements={
            "Anchor control to Car Seven. Boarding bridge locked. Stand by while we release the guide arms.",
            "Car Seven has cleared the tower. All six guide drives are engaged.",
            "We are entering marine cloud. The exterior optical feed may briefly lose sight of the sea.",
            "Cloud tops below. The guide rollers are holding their nominal temperature.",
            "Stratosphere. The cabin is holding one atmosphere.",
            "Passing one hundred kilometres. The blue rim below the window is the atmosphere.",
            "Earth limb sector. The observation optics are following the horizon.",
            "High orbit. Anchor control is handing us over to Aster Reach.",
            "Aster control has acquired the carriage. Automatic terminal braking is active.",
            "Inside the receiving cradle. Keep the hatch shut until pressure matching completes.",
            "Carriage at rest. Set the docking handwheel to seat the terminal clamp."
        };
        FlightDisplay pixels;
        CollarFeedback collarFeedback;
        public VesselCradle Cradle {get;private set;}
        public float ClampNeedleAngle=>collarFeedback?.NeedleAngle??0;
        public void Impact(LooseItemBody item,float force){collarFeedback?.Impact(item,force);}
        AudioSource drive,speaker,mechanism;
        float equalization,displayClock;
        readonly bool[] warned=new bool[AscentRoute.PassSeconds.Length],passed=new bool[AscentRoute.PassSeconds.Length];
        public int SelectedItem {get;private set;}
        bool queuedOpen,webBoarded;
        public void Board(){webBoarded=true;clockWarmupFrames=2;if(drive&&!drive.isPlaying)drive.Play();}

        void Start() {
            foreach(var p in FindObjectsByType<TransitProp>(FindObjectsInactive.Include))props[p.id]=p;
            props["access_card"].transform.SetParent(props["locker_drawer"].transform,true);
            drive=gameObject.AddComponent<AudioSource>();drive.clip=motor;drive.loop=true;drive.volume=.38f;drive.Play();
            speaker=gameObject.AddComponent<AudioSource>();speaker.volume=.72f;
            mechanism=gameObject.AddComponent<AudioSource>();mechanism.volume=.65f;
            pixels=new FlightDisplay(props["nav_screen"],exterior.Feed);
            Clock(0);systems.Initialize();collarFeedback=new CollarFeedback(this);Cradle=new VesselCradle(this);
        }
        void OnDestroy(){collarFeedback?.Dispose();}
        public void Say(string text,float duration=3.5f){Notice=text;NoticeUntil=Time.unscaledTime+duration;}
        public void Click(AudioClip clip,float volume=1){if(clip&&mechanism)mechanism.PlayOneShot(clip,volume);}
        public void Announce(){speaker.Stop();if(dispatch.Length>Stage&&dispatch[Stage])speaker.PlayOneShot(dispatch[Stage]);Say(Announcements[Stage],7);}
        public void ApplyPanelGain(float gain){pixels?.Settings(DisplayMode,gain);}
        public void SelectPage(int page){DisplayMode=(page+6)%6;pixels?.Settings(DisplayMode,systems.GainValue);Say(new[]{"Route and altitude","External optical feed","Pressure and seals","Drive and cabin load","Counterline traffic","Dispatch channel"}[DisplayMode]);}
        public void Clock(float p) {
            SetClock(Math.Max(0,Math.Min(360,p*360.0)));
            realShipClock=AboardSeconds;
        }
        void SetClock(double sec){
            Seconds=Math.Min(AscentRoute.Duration,sec);Progress=(float)(Seconds/AscentRoute.Duration);
            PreciseAltitude=AscentRoute.Height(Seconds);Altitude=(float)PreciseAltitude;
            Stage=AscentRoute.Stage(Seconds);Forces=CarriageForces.At(PreciseAltitude);Velocity=(float)(Forces.Velocity*3.6);
        }
        void Update() {
            float previous=Progress;
            if((Application.platform!=RuntimePlatform.WebGLPlayer||webBoarded)&&Seconds<AscentRoute.Duration){
                float visibleDelta=clockWarmupFrames>0?0:Time.unscaledDeltaTime;
                if(clockWarmupFrames>0)clockWarmupFrames--;
                if(RealShipTime||stargazingSeconds>0){
                    float step=RealShipTime?visibleDelta:Mathf.Min(stargazingSeconds,visibleDelta);
                    realShipClock+=step;stargazingSeconds=Mathf.Max(0,stargazingSeconds-step);
                    SetClock(AscentRoute.SecondsAtShipTime(realShipClock));
                }
                else SetClock(Seconds+Math.Min(visibleDelta,Time.deltaTime));
            }
            float dt=Time.deltaTime;exterior.ClampTurns=Turns;exterior.SetProgress(Seconds,PreciseAltitude,Velocity,dt);
            exterior.AdaptPassengerEye(practicals[0].enabled,systems.Gain,clockWarmupFrames>0?0:Time.unscaledDeltaTime);
            collarFeedback?.Update(Seconds,dt);
            Cradle?.Step(dt);
            float t=(float)Seconds,gate=Velocity/612f;
            float splice=Mathf.Repeat(t,11.7f),ring=splice<1?Mathf.Sin(splice*38)*Mathf.Exp(-splice*7.6f)*gate:0;
            foreach(float p in ExteriorRig.Passes){float elapsed=t-p*360;if(elapsed>=0&&elapsed<1.5f)ring+=.76f*Mathf.Sin(elapsed*26)*Mathf.Exp(-elapsed*4.3f);}
            StructureImpulse=new Vector3(.16f*ring,.8f*ring+.021f*gate*Mathf.Sin(t*23),.27f*ring);
            if(drive){drive.pitch=Mathf.Lerp(.55f,1.02f,Velocity/612);drive.volume=Mathf.Lerp(.10f,.34f,Velocity/612);}
            for(int j=0;j<ExteriorRig.Passes.Length;j++) {
                float at=ExteriorRig.Passes[j];
                float approach=(float)(AscentRoute.ApproachSeconds[j]/AscentRoute.Duration);
                var service=AscentRoute.Services[j];
                if(!warned[j]&&previous<approach&&Progress>=approach){warned[j]=true;Click(keyscan,.44f);Say(service.Car+" · descending "+service.Type.ToLowerInvariant(),3.3f);}
                if(!passed[j]&&previous<at&&Progress>=at){passed[j]=true;Click(service.Kind=="passenger"?passengerPass:freightPass,.82f);}
            }
            if(previous<1&&Progress>=1){Click(keyscan);Say("Aster Reach · terminal collar aligned",5);}
            if(equalization>0) {
                equalization=Mathf.Max(0,equalization-dt);Pressure=Mathf.Lerp(0,.36f,equalization/1.45f);
                if(equalization==0){Unlocked=true;if(queuedOpen)props["pressure_hatch"].SetOpen(true);Click(latch);Say("Pressure matched · service hatch released");}
            }
            if((displayClock-=dt)<=0){displayClock=.18f;pixels.Draw(this);}
        }
        public void NextWaypoint(){
            foreach(float t in AscentRoute.StageSeconds)if(t>Seconds+.6f){Seek(t);return;}Seek(AscentRoute.Duration);
        }
        public void PreviousWaypoint(){
            for(int i=AscentRoute.StageSeconds.Length-1;i>=0;i--)if(AscentRoute.StageSeconds[i]<Seconds-.9f){Seek(AscentRoute.StageSeconds[i]);return;}Seek(0);
        }
        public void Seek(double t){
            stargazingSeconds=0;
            t=Math.Max(0,Math.Min(AscentRoute.Duration,t));
            pixels?.ResetHistory();displayClock=0;
            if(t<Seconds){Turns=0;props["docking_wheel"].SetTarget(0);}
            StructureImpulse=Vector3.zero;
            AdvanceLoosePassage(Seconds,t);
            SetClock(t);realShipClock=AboardSeconds;for(int j=0;j<ExteriorRig.Passes.Length;j++){warned[j]=t>=AscentRoute.ApproachSeconds[j];passed[j]=t>=AscentRoute.PassSeconds[j];}
            Say(Stages[Stage]);exterior.ClampTurns=Turns;exterior.SetProgress(Seconds,PreciseAltitude,Velocity,0);
        }
        public bool Has(string id)=>inventory.Exists(p=>p.id==id);
        public TransitProp Held=>inventory.Count>0?inventory[SelectedItem]:null;
        public void CycleItem(){
            if(inventory.Count==0){Say("Your pockets are empty");return;}
            SelectedItem=(SelectedItem+1)%inventory.Count;Say("In hand · "+Held.title);
        }
        public bool Pickup(TransitProp p) {
            if(p.id=="mug"&&Cradle!=null&&Cradle.Moving)return false;
            if(p.id=="access_card"&&p.transform.parent==props["locker_drawer"].transform&&props["locker_drawer"].Position<.48f){Say("The card is inside the closed drawer");return false;}
            var loose=p.GetComponent<LooseItemBody>();if(loose)loose.Recover();
            if(!inventory.Contains(p))inventory.Add(p);
            SelectedItem=inventory.IndexOf(p);p.transform.SetParent(null,true);p.gameObject.SetActive(false);Click(relay,.50f);
            Say("Stowed · "+p.title+"     [I] Inspect");return true;
        }
        public void Release(TransitProp p,Vector3 pos,Quaternion rotation,Vector3 velocity,Vector3 spin){
            if(!p||!p.portable)return;inventory.Remove(p);SelectedItem=Mathf.Clamp(SelectedItem,0,Mathf.Max(0,inventory.Count-1));
            p.transform.SetParent(null,true);p.gameObject.SetActive(true);var mount=p.GetComponentInChildren<EquipmentMount>();if(mount)mount.enabled=false;
            var loose=p.GetComponent<LooseItemBody>();if(!loose)loose=p.gameObject.AddComponent<LooseItemBody>();loose.item=p;loose.LetGo(pos,rotation,velocity,spin);
            Say("Released · "+p.title+"     E to catch");
        }
        public bool ParkVessel(Vector3 eye,Vector3 from,Quaternion angle){
            var vessel=props["mug"];
            if(!inventory.Contains(vessel)||Cradle.Moving)return false;
            if(!Cradle.InReach(eye)){Say("Carry the flask to the counter in the crew sleeper.");return false;}
            inventory.Remove(vessel);SelectedItem=Mathf.Clamp(SelectedItem,0,Mathf.Max(0,inventory.Count-1));
            Cradle.Park(from,angle);return true;
        }
        public void SetFeed(int channel) {
            Feeds=(channel+3)%3;props["ascent_lever"].SetTarget(Feeds/2f);exterior.Select(Feeds);Click(relay);Say("Exterior camera · "+Channels[Feeds]);
        }
        public void SecureTurn() {
            var wheel=props["docking_wheel"];
            if(Progress<1){wheel.SetTarget(wheel.Target>.06f?0:.13f);Click(relay,.72f);Say("Clamp interlock · terminal collar out of range");return;}
            if(Docked){Say(exterior.arrivalBay.CaptureStatus);return;}
            Turns++;wheel.SetTarget(Turns/3f);collarFeedback.Turn(Turns);
            Say(Turns==1?"Centering the capture jaws":Turns==2?"Drawing the collar against its stops":"Locking the collar · transfer sleeve standing by");
        }
        public void Use(TransitProp p,Passenger passenger) {
            if(!p)return;
            if(p.portable){if(Pickup(p))passenger.Inspect(p);return;}
            if(p.id=="grab_handle"&&passenger.ReducedLoad){
                if(Vector3.Distance(passenger.eye.transform.position,p.Focus)<.96f)passenger.Brace();else Say("Move within arm's reach of the handhold");
                return;
            }
            if(systems.Use(p))return;
            switch(p.id){
                case "fracture_cell":passenger.Inspect(p);break;
                case "fracture_press":fracture.BeginPress();break;
                case "fracture_reload":fracture.Reload();break;
                case "accelerometer":case "capillary_cell":passenger.Inspect(p);break;
                case "accel_test":case "capillary_primer":experiments.Operate(p.id);break;
                case "ascent_lever":SetFeed(Feeds+1);break;
                case "nav_screen":SelectPage(DisplayMode+1);Click(relay,.5f);break;
                case "pilot_console":Click(relay);Say("Automatic drive  /  "+Mathf.RoundToInt(Velocity)+" km/h  /  "+Forces.GravityG.ToString("0.000")+" g  /  "+Forces.Drive.ToString("0.00")+" m/s² thrust");break;
                case "roller_shade":case "privacy_curtain":case "locker_drawer":case "service_cabinet":
                    p.SetOpen(!p.Open);Click(runner);Say(p.title+" · "+(p.Open?"extended":"stowed"));break;
                case "lamp":case "reading_lamp":case "breaker":{
                    int i=p.id=="lamp"?0:p.id=="reading_lamp"?1:2;practicals[i].enabled=!practicals[i].enabled;
                    p.SetOpen(!practicals[i].enabled);p.Emission(practicals[i].enabled?1:.08f);
                    Click(relay);Say(p.title+" · "+(practicals[i].enabled?"on":"off"));break;}
                case "card_reader":case "pressure_hatch":{
                    var hatch=props["pressure_hatch"];
                    if(Equalizing){Say("Matching pressure · "+Pressure.ToString("0.00")+" kPa");break;}
                    if(!Unlocked){
                        if(!Has("access_card")){Click(relay,.38f);Say("Service credential required");break;}
                        queuedOpen=true;equalization=1.45f;Pressure=.36f;Click(keyscan);Say("Credential accepted · equalizing pressure");break;
                    }
                    if(hatch.Open&&Mathf.Abs(passenger.transform.position.z+1.9f)<.42f&&Mathf.Abs(passenger.transform.position.x)<.92f){Say("Hatchway occupied");break;}
                    hatch.SetOpen(!hatch.Open);Click(latch);Say(hatch.Open?"Service hatch opening":"Service hatch closing");break;}
                case "pressure_gauge":systems.TogglePressureUnits();Say("Cabin 101.3 kPa  /  Δ "+systems.IndicatedPressure.ToString("0.00")+" kPa");Click(relay,.4f);break;
                case "intercom":p.Pulse();Announce();break;
                case "docking_wheel":SecureTurn();break;
                case "lounge_seat":case "bunk":passenger.Rest(p);break;
                case "window":passenger.Observe();break;
                default:passenger.Inspect(p);break;
            }
        }
    }
}
