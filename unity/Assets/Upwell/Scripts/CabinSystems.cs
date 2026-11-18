using System;
using System.Collections.Generic;
using UnityEngine;

namespace Upwell{
    public sealed class CabinSystems:MonoBehaviour{
        public TransitRide ride;public Transform fanRotor;public AudioClip fanSound;public Light portFixture;
        public bool GuideFlood{get;private set;}public bool Film{get;private set;}
        public int Gain{get;private set;}=2;public int Focal{get;private set;}=1;
        public bool Electrical{get;private set;}public bool Guides{get;private set;}
        public bool UnitsPsi{get;private set;}public string Test{get;private set;}="";public float TestClock{get;private set;}
        public float LampTime{get;private set;}public float FanRPM{get;private set;}
        public float GainValue=>gains[Gain];public int LitScreens=>screens.Count;
        public double? LoadReference{get;private set;}
        readonly Dictionary<string,InstrumentPixels> screens=new Dictionary<string,InstrumentPixels>();
        readonly Dictionary<string,Material> panels=new Dictionary<string,Material>(),annunciators=new Dictionary<string,Material>(),traces=new Dictionary<string,Material>();
        readonly Dictionary<Material,Material> runtime=new Dictionary<Material,Material>();
        readonly float[] gains={.32f,.55f,.80f,1,1.25f};readonly int[] focal={72,52,36,23,14};
        readonly string[] pages={"key_route","key_optics","key_seals","key_load","key_traffic","key_comms"};
        AudioSource ventilation;float refresh;bool ready;
        HandMechanism drinkValve;
        CabinHardware hardware;
        public void Initialize(){
            if(ready)return;ready=true;
            foreach(var r in FindObjectsByType<MeshRenderer>(FindObjectsInactive.Include)){
                var mats=r.sharedMaterials;bool replace=false;
                for(int i=0;i<mats.Length;i++){var m=mats[i];if(!m)continue;string name=m.name;
                    if(!name.StartsWith("Pixels_")&&!name.StartsWith("Ann_")&&!name.StartsWith("Trace_")&&name!="Berth_Diffuser")continue;
                    if(!runtime.TryGetValue(m,out var instance)){
                        instance=new Material(m){name=name};runtime[m]=instance;
                        if(name.StartsWith("Pixels_")){string key=name.Substring(7);var pixel=new InstrumentPixels(key);screens[key]=pixel;instance.mainTexture=pixel.texture;panels[key]=instance;}
                        else if(name.StartsWith("Trace_")){traces[name.Substring(6).ToLowerInvariant()]=instance;instance.SetFloat("_Pulse",-2);}
                        else annunciators[name.StartsWith("Ann_")?name.Substring(4):name]=instance;
                    }
                    mats[i]=instance;replace=true;
                }if(replace)r.sharedMaterials=mats;
            }
            foreach(var name in new[]{"Anchor","Aster","Scada","Scope"}){var s=new InstrumentPixels(name);screens[name]=s;Shader.SetGlobalTexture("_Upwell"+name,s.texture);}
            Shader.SetGlobalFloat("_UpwellTerminalLive",1);ventilation=gameObject.AddComponent<AudioSource>();ventilation.clip=fanSound;ventilation.loop=true;ventilation.volume=.24f;if(fanSound)ventilation.Play();
            hardware=gameObject.AddComponent<CabinHardware>();hardware.Install(ride);
            drinkValve=ride.props["mug"].GetComponentInChildren<HandMechanism>(true);
            Refresh();
        }
        string FanStatus=>ride.CabinFanOn?"FAN ONLINE":"FAN COAST";
        string HatchStatus=>ride.Equalizing?"EQUALIZING":ride.props["pressure_hatch"].Open?"HATCH OPEN":ride.Unlocked?"RELEASED":"SEALED";
        float BusCurrent=>1.32f+(ride.practicals[0].enabled?2.46f:0)+(ride.practicals[1].enabled?.57f:0)
            +(ride.CabinFanOn?.91f:0)+(ride.practicals[2].enabled?1.24f:0)+(GuideFlood?3.85f:0)+Gain*.19f;
        public float BusVoltage=>28.43f-BusCurrent*.043f-(Test=="power"&&TestClock>0?.26f:0);
        public float IndicatedPressure=>ride.Pressure+(Test=="seal"&&TestClock>0?.14f*Mathf.Sin(Mathf.PI*Mathf.Clamp01(TestClock/2.6f)):0);
        public string NextTraffic{
            get{
                var contact=AscentRoute.Counterline(ride.PreciseAltitude,ride.Forces);
                if(contact.InRange)return OrbitalHardware.CarIds[contact.Index]+" / "+(contact.Eta>=0?"INBOUND":"PASSING");
                for(int i=0;i<ExteriorRig.Passes.Length;i++){
                    float pass=ExteriorRig.Passes[i];if(pass<ride.Progress)continue;
                    double height=AscentRoute.Height(pass*AscentRoute.Duration);
                    double remaining=Math.Max(0,CarriageForces.At(height).ShipSeconds-ride.Forces.ShipSeconds);
                    string eta=remaining<60?Math.Ceiling(remaining)+" S":remaining<3600?(int)(remaining/60)+" MIN":(remaining/3600).ToString("0.0")+" H";
                    return OrbitalHardware.CarIds[i]+" / "+eta;
                }
                return "LINE CLEAR";
            }
        }
        public bool Use(TransitProp p){
            string key=p.id;
            int page=Array.IndexOf(pages,key);
            if(page>=0){
                p.Pulse();
                if(page==3&&ride.DisplayMode==3){
                    LoadReference=LoadReference.HasValue?(double?)null:ride.Forces.Down/9.80665;
                    ride.Say(LoadReference.HasValue?"Vertical load reference marked":"Load reference cleared");
                }else ride.SelectPage(page);
                if(page==5)ride.Announce();ride.Click(ride.relay,.72f);Refresh();return true;
            }
            switch(key){
                case "guide_flood":GuideFlood=!GuideFlood;p.SetOpen(GuideFlood);ride.exterior.guideway.Flood(GuideFlood);break;
                case "cabin_lights":ride.practicals[0].enabled=!ride.practicals[0].enabled;p.SetOpen(ride.practicals[0].enabled);ride.props["lamp"].Emission(ride.practicals[0].enabled?1:.06f);break;
                case "solar_film":Film=!Film;p.SetOpen(Film);Shader.SetGlobalFloat("_UpwellSolarFilm",Film?1:0);break;
                case "vent_fan":ride.CabinFanOn=!ride.CabinFanOn;p.SetOpen(ride.CabinFanOn);break;
                case "panel_gain":Gain=(Gain+1)%5;p.SetTarget(Gain/4f);break;
                case "camera_focus":Focal=(Focal+1)%5;p.SetTarget(Focal/4f);ride.exterior.LensAngle=focal[Focal];break;
                case "key_lamp_test":LampTime=2.4f;p.Pulse();break;
                case "diagnostic_screen":Electrical=!Electrical;break;case "drive_screen":Guides=!Guides;break;
                case "test_power":case "test_fiber":case "test_seal":case "test_return":
                    if(ride.props["service_cabinet"].Position<.65f){ride.Say("Open the maintenance cabinet to reach the test bank");return true;}
                    p.Pulse();Test=key.Substring(5);TestClock=2.6f;ride.Click(ride.keyscan,.65f);ride.Say(Test+" diagnostic running");break;
                default:return false;
            }
            ride.Click(ride.relay,.72f);Refresh();return true;
        }
        public void PrepareForStargazing(){
            if(ride.practicals[0].enabled)Use(ride.props["cabin_lights"]);
            if(Film)Use(ride.props["solar_film"]);
            if(Gain!=0){Gain=0;ride.props["panel_gain"].SetTarget(0);ride.Click(ride.relay,.5f);Refresh();}
        }
        public void TogglePressureUnits(){UnitsPsi=!UnitsPsi;}
        bool Lamp(string key){
            if(LampTime>0)return true;int page=Array.IndexOf(pages,key);if(page>=0)return ride.DisplayMode==page;
            switch(key){case "guide_flood":return GuideFlood;case "cabin_lights":return ride.practicals[0].enabled;case "solar_film":return Film;case "vent_fan":return ride.CabinFanOn;
                case "reading_lamp":case "Berth_Diffuser":return ride.practicals[1].enabled;case "breaker":return ride.practicals[2].enabled;case "intercom":return ride.RadioPlaying;}
            return key=="test_"+Test&&TestClock>0;
        }
        void Refresh(){
            if(!ride||ride.props.Count==0)return;
            if(portFixture)portFixture.enabled=ride.practicals[0].enabled;
            float g=(float)ride.Forces.GravityG;long minutes=(long)(ride.Forces.ShipSeconds/60);string clock=(minutes/60).ToString("00")+":"+(minutes%60).ToString("00");
            Shader.SetGlobalVector("_UpwellPracticalState",new Vector4(ride.practicals[0].enabled?1:.01f,ride.practicals[1].enabled?1:.01f,ride.practicals[2].enabled?1:.01f,0));
            Shader.SetGlobalVector("_UpwellRepeater",LampTime>0?Vector4.one:new Vector4(GuideFlood?1:.02f,ride.practicals[0].enabled?1:.02f,Film?1:.02f,ride.CabinFanOn?1:.02f));
            string alt=AscentRoute.AltitudeText(ride.PreciseAltitude).Replace(",","");
            string bus=BusVoltage.ToString("0.0")+" V";string seal=IndicatedPressure.ToString("0.00")+" KPA";
            foreach(var entry in screens){
                string upper=entry.Key,value="",lower="";float level=ride.Progress;
                switch(upper.ToLowerInvariant()){
                    case "diagnostic":value=Electrical?bus:"101.3 KPA";lower=Electrical?"28 V BUS  /  "+BusCurrent.ToString("0.00")+" A":FanStatus;level=Electrical?BusVoltage/32:FanRPM/840;break;
                    case "drive":value=Guides?"16 ROLLERS":Mathf.RoundToInt(ride.Velocity)+" KM/H";lower=Guides?"RETURN "+(ride.Forces.West*1000).ToString("0")+" MM/S2":"DRIVE "+ride.Forces.Drive.ToString("0.00")+" M/S2";level=ride.Velocity/612;break;
                    case "pressure":value=UnitsPsi?(IndicatedPressure*.1450377f).ToString("0.000")+" PSI":seal;lower=HatchStatus;level=IndicatedPressure/.36f;break;
                    case "access":value=ride.Unlocked?"AUTHORIZED":"PRESENT KEY";lower=ride.Equalizing?"MATCHING PRESSURE":ride.Has("access_card")?"CREW KEY NEARBY":"RESTRICTED";level=ride.Unlocked?1:0;break;
                    case "seal":value=HatchStatus;lower=seal+"  /  CAR 07";level=ride.props["pressure_hatch"].Position;break;
                    case "berth":value=g.ToString("0.000")+" G";lower=ride.practicals[1].enabled?"READ LAMP ON":"READ LAMP OFF";level=g;break;
                    case "intercom":value=ride.RadioPlaying?"RECEIVING":"STANDBY";lower=TransitRide.Stages[ride.Stage].ToUpperInvariant();level=ride.RadioPlaying?1:0;break;
                    case "service":value=TestClock>0?"TEST "+Test.ToUpperInvariant():string.IsNullOrEmpty(Test)?"TEST BANK":"PASS / "+Test.ToUpperInvariant();lower=Test=="power"?bus:Test=="fiber"?"MIN BEND "+hardware.FiberBendMM().ToString("0")+" MM":Test=="seal"?seal:Test=="return"?"RETURN 0.04 OHM":"PWR  FIB  SEAL  RTN";level=TestClock>0?1-TestClock/2.6f:1;break;
                    case "folio":value=TransitRide.Stages[ride.Stage].ToUpperInvariant();lower="SHIP "+clock+" / "+alt;break;
                    case "optic":value="STABILIZED";lower="FOCUS "+(1+(ride.props["field_glasses"].GetComponentInChildren<HandMechanism>(true)?.Setting??0));level=Focal/4f;break;
                    case "vessel":entry.Value.Vessel(drinkValve?drinkValve.Travel:0,g);continue;
                    case "anchor":value=ride.Seconds<9?"RELEASING":ride.Altitude<.15?"CLEAR TOWER":"UPBOUND";lower="CAR 07 / "+alt;break;
                    case "aster":
                        var collar=ride.exterior.arrivalBay;
                        value=ride.Progress>=1?collar.CaptureStatus:ride.Seconds>339?"RECEIVING":ride.Seconds>305?"TELEMETRY LOCK":"AWAIT CAR 07";
                        lower=ride.Progress>=1?"FOLLOWER "+(18*collar.FollowerTravel).ToString("0.0")+" MM":"RANGE "+Mathf.Min(99999,(float)collar.DockDistance).ToString("0")+" M";
                        break;
                    case "scada":value=bus;lower=HatchStatus+" / "+FanStatus;level=BusVoltage/32;break;
                    case "scope":value=ride.Velocity.ToString("0")+" KM/H";lower="GUIDE CONTACT / 16";level=ride.Velocity/612;break;
                    default:value=alt;lower=TransitRide.Stages[ride.Stage];break;
                }entry.Value.Panel(upper.ToUpperInvariant(),value,lower,level);
            }
            foreach(var x in panels.Values)x.SetFloat("_PanelGain",GainValue);
            foreach(var a in annunciators)a.Value.SetFloat("_Emission",Lamp(a.Key)?1.95f:.045f);
            if(ride.props.TryGetValue("cabin_lights",out var lightSwitch))lightSwitch.SetOpen(ride.practicals[0].enabled);
            ride.ApplyPanelGain(GainValue);
        }
        void Update(){
            if(!ready)return;float dt=Time.deltaTime;LampTime=Mathf.Max(0,LampTime-dt);TestClock=Mathf.Max(0,TestClock-dt);
            FanRPM=Mathf.MoveTowards(FanRPM,ride.CabinFanOn?840:0,dt*(ride.CabinFanOn?390:205));
            if(fanRotor)fanRotor.Rotate(Vector3.down,FanRPM*6*dt,Space.Self);
            if(ventilation){ventilation.pitch=Mathf.Lerp(.52f,1.08f,FanRPM/840);ventilation.volume=FanRPM/840*.32f;}
            foreach(var t in traces){float u=Test==t.Key&&TestClock>0?Mathf.Repeat((2.6f-TestClock)*1.1f,1.20f): -3;t.Value.SetFloat("_Pulse",u);}
            if((refresh-=dt)<=0){refresh=.36f;Refresh();}
        }
        void LateUpdate(){
            // The replica, lever and transducer all describe this rendered pose.
            if(drinkValve&&screens.TryGetValue("Vessel",out var readout))
                readout.Vessel(drinkValve.Travel,(float)ride.Forces.GravityG);
        }
        void OnDestroy(){foreach(var m in runtime.Values)if(m)Destroy(m);foreach(var p in screens.Values)if(p.texture)Destroy(p.texture);}
    }
}
