using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using UnityEngine;

namespace Upwell {
    public sealed partial class RideVerification : MonoBehaviour {
        [Serializable] class Receipt {public int controls,rooms; public bool passed;public string[] checks;public string failure;}
        readonly List<string> checks=new List<string>();
        string output;Passenger person;TransitRide ride;Receipt receipt;
        IEnumerator Start(){
            var args=Environment.GetCommandLineArgs();int index=Array.IndexOf(args,"-verify-upwell");
            if(index<0||index+1>=args.Length){enabled=false;yield break;}
            output=Path.GetFullPath(args[index+1]);Directory.CreateDirectory(output);Application.runInBackground=true;
            person=GetComponent<Passenger>();ride=person.ride;receipt=new Receipt();yield return null;yield return null;
            if(Array.IndexOf(args,"-verify-photo-journal-input")>=0){
                // Leave the ordinary passenger in control on the private test desktop.
                while(!person.CabinEdges||person.CabinEdges.LastSceneFrame<0)yield return null;
                File.WriteAllText(Path.Combine(output,"photo-input-ready.txt"),person.CabinEdges.LastSceneFrame.ToString());
                yield break;
            }
            if(Array.IndexOf(args,"-capture-aster-relay")>=0){
                try{CaptureAsterRelay();Application.Quit(0);}catch(Exception e){Debug.LogException(e);Application.Quit(2);}yield break;
            }
            bool inputSurvey=Array.IndexOf(args,"-verify-native-input")>=0;
            bool reload=Array.IndexOf(args,"-verify-graphics-reload")>=0;
            bool software=Array.IndexOf(args,"-verify-software-graphics")>=0;
            if(!reload)PlayerGraphics.RestoreDefaults();
            bool fractureOnly=Array.IndexOf(args,"-verify-fracture-only")>=0;
            bool gravityOnly=Array.IndexOf(args,"-verify-gravity")>=0;
            var test=gravityOnly?GravityInputs():fractureOnly?FractureSurvey():software?SoftwareSurvey():reload?ReloadGraphics():inputSurvey?NativePassageInputs():Run();
            for(;;){object step=null;bool next=false;try{next=test.MoveNext();if(next)step=test.Current;}catch(Exception e){receipt.failure=e.ToString();Debug.LogError(e);break;}
                if(!next){receipt.passed=true;break;}yield return step;}
            receipt.checks=checks.ToArray();File.WriteAllText(Path.Combine(output,gravityOnly?"gravity-windows.json":fractureOnly?"fracture/native-fracture.json":software?"graphics/native-software.json":reload?"graphics/native-persistence.json":inputSurvey?"native-input-checks.json":"native-checks.json"),JsonUtility.ToJson(receipt,true));
            Application.Quit(receipt.passed?0:2);
        }
        void Check(bool ok,string text){if(!ok)throw new InvalidOperationException(text);checks.Add(text);}
        bool Reachable(TransitProp target,float centerZ){
            // Test the actual first-person aim resolver from points inside the central aisle.
            var bounds=new Bounds(target.Focus,Vector3.zero);
            foreach(var r in target.GetComponentsInChildren<MeshRenderer>())bounds.Encapsulate(r.bounds);
            Vector3[] aims={target.Focus,bounds.center,bounds.center+Vector3.up*bounds.extents.y*.72f,
                bounds.center+Vector3.right*bounds.extents.x*.64f,bounds.center-Vector3.right*bounds.extents.x*.64f};
            foreach(float z in new[]{-.98f,0,.98f,-1.36f,1.36f})
            foreach(float x in new[]{0f,-.83f,.83f}) {
                var foot=new Vector3(x,.037f,centerZ+z);
                foreach(var aim in aims){
                    var d=(aim-foot-person.eye.transform.localPosition).normalized;
                    person.Place(foot,Mathf.Atan2(d.x,d.z)*Mathf.Rad2Deg,-Mathf.Asin(d.y)*Mathf.Rad2Deg);
                    Physics.SyncTransforms();if(person.FindFocus()==target)return true;
                }
            }
            return false;
        }
        IEnumerator Photo(string name,Camera source=null){
            yield return new WaitForSecondsRealtime(.16f);yield return new WaitForEndOfFrame();
            // Hidden GPU verification has no swap-chain back buffer. Render the actual passenger camera instead.
            ride.exterior.RenderFeed();Camera camera=source?source:person.eye;
            int width=1440,height=900;var original=camera.targetTexture;var active=RenderTexture.active;
            var canvas=RenderTexture.GetTemporary(width,height,24,RenderTextureFormat.ARGB32,RenderTextureReadWrite.sRGB,1);
            camera.targetTexture=canvas;camera.Render();RenderTexture.active=canvas;
            var image=new Texture2D(width,height,TextureFormat.RGB24,false,false);image.ReadPixels(new Rect(0,0,width,height),0,0);image.Apply();
            File.WriteAllBytes(Path.Combine(output,name+".jpg"),image.EncodeToJPG(90));
            if(name=="16-earth-terminator"){
                var samples=image.GetPixels32();int lit=0,blue=0;
                for(int j=0;j<samples.Length;j+=8){var c=samples[j];if(c.r+c.g+c.b>94)lit++;if(c.b>c.r+9&&c.g>c.r+3)blue++;}
                Check(lit*8>samples.Length*.12f&&blue*8>samples.Length*.016f,"Earth optics frame contains a substantial lit disc, colored ocean and atmospheric limb");
            }
            camera.targetTexture=original;RenderTexture.active=active;RenderTexture.ReleaseTemporary(canvas);Destroy(image);
        }
        void ShadowChange(){
            var cam=person.eye;var old=cam.targetTexture;var active=RenderTexture.active;var frame=RenderTexture.GetTemporary(900,562,24,RenderTextureFormat.ARGB32,RenderTextureReadWrite.sRGB,1);
            cam.targetTexture=frame;var masks=new List<byte[]>();string folder=Path.Combine(output,"illumination");Directory.CreateDirectory(folder);
            try{
                foreach(double t in new[]{5.0,15.6,24.0,40.0,183.0}){
                    ride.Seek(t);var light=ride.exterior.sun;var before=light.shadows;light.shadows=LightShadows.Soft;
                    var actual=ReadFinishFrame(cam,frame,RegisteredFinish.FinishWeight);light.shadows=LightShadows.None;
                    var noCast=ReadFinishFrame(cam,frame,RegisteredFinish.FinishWeight);light.shadows=before;
                    var p=actual.GetPixels32();var q=noCast.GetPixels32();var mask=new byte[p.Length];
                    for(int i=0;i<p.Length;i++)mask[i]=(byte)Mathf.Clamp((q[i].r+q[i].g+q[i].b-p[i].r-p[i].g-p[i].b)/3,0,255);
                    masks.Add(mask);File.WriteAllBytes(Path.Combine(folder,"cabin-"+t.ToString("0.0",System.Globalization.CultureInfo.InvariantCulture)+"s.jpg"),actual.EncodeToJPG(92));
                    Destroy(actual);Destroy(noCast);
                }
                // Count only the deck, console and sitting surfaces below the lower window edge.
                int count=0,relevant=0;for(int y=8;y<213;y++)for(int x=25;x<875;x++){
                    int idx=y*900+x;byte a=255,b=0;foreach(var m in masks){a=Math.Min(a,m[idx]);b=Math.Max(b,m[idx]);}
                    if(b-a>=4)count++;relevant++;
                }
                Check(count>relevant*.010f,"Moving solar occluders change "+(100f*count/relevant).ToString("0.0")+"% of sampled deck and console shadow pixels");
            }finally{cam.targetTexture=old;RenderTexture.active=active;RenderTexture.ReleaseTemporary(frame);}
        }
        void WeatherEvolution(){
            var rig=ride.exterior;ride.Seek(69);rig.Select(0);var cam=rig.SensorCamera;var old=cam.targetTexture;var active=RenderTexture.active;
            var frame=RenderTexture.GetTemporary(768,432,16,RenderTextureFormat.ARGB32,RenderTextureReadWrite.sRGB);cam.targetTexture=frame;
            try{
                float t=69;double km=AscentRoute.Height(t);rig.SetProgress(t,km,AscentRoute.Command(km),0,t);
                var a=ReadFinishFrame(cam,frame,RegisteredFinish.FinishWeight);rig.SetProgress(t,km,AscentRoute.Command(km),0,t+112);
                var b=ReadFinishFrame(cam,frame,RegisteredFinish.FinishWeight);var x=a.GetPixels32();var y=b.GetPixels32();int varied=0;
                for(int i=0;i<x.Length;i++)if(Math.Abs(x[i].r-y[i].r)+Math.Abs(x[i].g-y[i].g)+Math.Abs(x[i].b-y[i].b)>14)varied++;
                string dir=Path.Combine(output,"illumination");File.WriteAllBytes(Path.Combine(dir,"fixed-cloud-a.jpg"),a.EncodeToJPG(92));File.WriteAllBytes(Path.Combine(dir,"fixed-cloud-b.jpg"),b.EncodeToJPG(92));Destroy(a);Destroy(b);
                Check(varied>x.Length*.015f,"Advected cloud density changes "+(100f*varied/x.Length).ToString("0.0")+"% of a fixed optical view at the same altitude and solar angle");
            }finally{cam.targetTexture=old;RenderTexture.active=active;RenderTexture.ReleaseTemporary(frame);}
        }
        void RegionalWeatherHandoff(){
            var rig=ride.exterior;var optical=rig.SensorCamera;var target=optical.targetTexture;var active=RenderTexture.active;
            var field=rig.RuntimeSky.GetTexture("_Atlantic");var rotation=optical.transform.rotation;float angle=optical.fieldOfView;int layers=optical.cullingMask;
            var frame=RenderTexture.GetTemporary(768,480,16,RenderTextureFormat.ARGB32,RenderTextureReadWrite.sRGB);
            try{
                foreach(double seconds in new[]{184.0,257.0,360.0}){
                    ride.Seek(seconds);optical.targetTexture=frame;optical.cullingMask=0;
                    optical.transform.rotation=Quaternion.LookRotation(Vector3.down,Vector3.forward);
                    float disk=2*Mathf.Asin(6371f/(6371f+ride.Altitude))*Mathf.Rad2Deg;
                    optical.fieldOfView=Mathf.Clamp(disk*1.20f,20,66);
                    rig.RuntimeSky.SetTexture("_Atlantic",field);var a=ReadFinishFrame(optical,frame,RegisteredFinish.FinishWeight);
                    // Force thick, high cloud everywhere in the regional survey and compare the actual GPU radiance.
                    rig.RuntimeSky.SetTexture("_Atlantic",Texture2D.whiteTexture);var b=ReadFinishFrame(optical,frame,RegisteredFinish.FinishWeight);
                    var original=a.GetPixels32();var changed=b.GetPixels32();int affected=0;
                    for(int i=0;i<original.Length;i++){
                        if(Math.Abs(original[i].r-changed[i].r)+Math.Abs(original[i].g-changed[i].g)+Math.Abs(original[i].b-changed[i].b)>3)affected++;
                    }
                    float fraction=(float)affected/original.Length;
                    if(seconds<200)Check(fraction>.008f,"Measured Atlantic optical depth/top affects "+(100*fraction).ToString("0.0")+"% of nadir radiance at 660 km");
                    else Check(affected==0,"Substituting the entire measured Atlantic survey changes zero globe pixels at "+Math.Round(ride.PreciseAltitude).ToString("N0")+" km");
                    Destroy(a);Destroy(b);rig.RuntimeSky.SetTexture("_Atlantic",field);
                }
            }finally{
                rig.RuntimeSky.SetTexture("_Atlantic",field);optical.transform.rotation=rotation;optical.fieldOfView=angle;optical.cullingMask=layers;
                optical.targetTexture=target;RenderTexture.active=active;RenderTexture.ReleaseTemporary(frame);
            }
        }
        IEnumerator ExteriorSurvey(){
            var ext=ride.exterior;ride.Seek(0);
            Check(ride.Altitude==0&&ride.Velocity==0&&ext.anchorBay.gameObject.activeInHierarchy,"Passenger boards at sea level with anchored guides and zero drive speed");
            Check(ext.anchorBay.actuators.Length>=7&&ext.arrivalBay.actuators.Length>=7,"Launch and receiving bays contain independently animated hardware");
            Check(ext.RuntimeSky.shader.name=="Upwell/Moving atmosphere and Earth"&&ext.RuntimeSky.GetTexture("_NoiseField") is Texture3D,"GPU sky uses geographic Earth data and a volumetric weather field");
            person.Place(new Vector3(1.22f,.036f,2.28f),-32,4);
            yield return Photo("10-anchor-checkout");
            ShadowChange();
            WeatherEvolution();
            ride.Seek(22);Check(Math.Abs(ext.anchorBay.DockDistance-40)<.01&&ext.anchorBay.Clearance>.99f,"Launch tower moves vertically by its surveyed 40 m clearance");
            person.SetWatch(1);yield return Photo("11-launch-clearance");person.SetWatch(0);
            person.SetWatch(6);yield return Photo("21-floor-window-launch");person.SetWatch(0);
            person.SetWatch(5);yield return Photo("19-guide-contact",ext.SensorCamera);person.SetWatch(0);
            Check(ext.guideway.ContactRollers==16,"Two adjacent physical load ribbons each have eight independent contact rollers");
            foreach(var pair in new[]{new[]{58f,12f},new[]{76f,13f},new[]{104f,14f},new[]{135f,15f}}){
                ride.Seek(pair[0]);person.Place(new Vector3(-.65f,.035f,4.25f),4,8);
                yield return Photo(((int)pair[1]).ToString()+"-weather-"+((int)pair[0]).ToString());
            }
            foreach(int second in new[]{93,102,108}){
                ride.Seek(second);person.SetWatch(4);yield return Photo("cloud-optics-"+second,ext.SensorCamera);
                person.SetWatch(0);
            }
            ride.Seek(224);person.SetWatch(3);yield return Photo("16-earth-terminator",ext.SensorCamera);person.SetWatch(0);
            RegionalWeatherHandoff();ride.Seek(257);person.SetWatch(6);yield return Photo("22-floor-window-orbit");
            ride.Seek(360);yield return Photo("23-floor-window-geostationary");
            Check(Mathf.Abs(person.eye.transform.position.y-1.38f)<.01f&&Vector3.Dot(person.eye.transform.forward,Vector3.down)>.99f,"Passenger looks down from inside the car through its deck pressure window");person.SetWatch(0);
            ride.Seek(323);Check(Math.Abs(ext.arrivalBay.DockDistance-180)<.01&&ext.arrivalBay.gameObject.activeInHierarchy,"Station distance resolves 180 m below the terminal");person.SetWatch(4);yield return Photo("17-capture-180m",ext.SensorCamera);
            ride.Seek(339);yield return Photo("20-receiving-46m",ext.SensorCamera);
            ride.Seek(351);Check(Math.Abs(ext.arrivalBay.DockDistance-6)<.01,"Station approach resolves six metres from docking");yield return Photo("18-capture-6m",ext.SensorCamera);
            ride.Seek(360);Check(ext.arrivalBay.DockDistance<.001&&ride.Velocity==0,"Receiving cradle and car meet without a scene cut");person.SetWatch(0);
            ride.Seek(76);
        }
        void FlexibleSurvey(){
            var flex=FindObjectsByType<FlexibleTail>(FindObjectsInactive.Exclude);Check(flex.Length==7,"Seven actual retention strips and lanyards are mechanically bound");
            var drift=new Dictionary<FlexibleTail,float>();ride.Seek(0);for(int n=0;n<95;n++)foreach(var f in flex)f.Simulate(1/60f);foreach(var f in flex)drift[f]=f.Displacement;
            Check(ride.Forces.GravityG>.98&&ride.Forces.GravityG<1.02,"Docked anchor gravity is terrestrial");
            var cruise=CarriageForces.At(16000);Check(Math.Abs(cruise.Velocity-170)<.001&&Math.Abs(cruise.West-.02479)<.0001,"Cruise speed and westward Coriolis term agree with the physical drive law");
            ride.Seek(350);Check(ride.Forces.Down<0,"Braking below geostationary altitude reverses effective vertical force");
            ride.Seek(360);Check(ride.Forces.GravityG<.002&&ride.Forces.Velocity==0,"Parked geostationary carriage approaches weightlessness");
            for(int n=0;n<120;n++)foreach(var f in flex)f.Simulate(1/60f);float shift=0,pin=0;
            foreach(var f in flex){shift=Mathf.Max(shift,Mathf.Abs(drift[f]-f.Displacement));pin=Mathf.Max(pin,f.PinError);}
            Check(shift>.0015f&&pin<.00001f,"Gravity changes soft-gear deflection by "+(shift*1000).ToString("0.0")+" mm while pinned vertices remain attached");
            ride.Seek(76);
        }
        IEnumerator SwitchSurvey(){
            var s=ride.systems;Check(s.LitScreens>=15,"Live normalized instrument faces and four station SCADA channels are bound");
            foreach(string key in new[]{"guide_flood","cabin_lights","solar_film","vent_fan","key_route","key_optics","key_seals","key_load","key_traffic","key_comms","key_lamp_test","panel_gain","camera_focus","diagnostic_screen","drive_screen"})
                Check(Reachable(ride.props[key],3.8f),"First-person aim isolates "+key);
            ride.Use(ride.props["guide_flood"],person);Check(s.GuideFlood,"Guide flood powers the external contact assembly");
            bool lamps=ride.practicals[0].enabled;ride.Use(ride.props["cabin_lights"],person);Check(ride.practicals[0].enabled!=lamps,"Console rocker controls saloon illumination");ride.Use(ride.props["cabin_lights"],person);
            ride.Use(ride.props["solar_film"],person);Check(s.Film,"Window film changes glazing transmission");ride.Use(ride.props["solar_film"],person);
            float rpm=s.FanRPM;ride.Use(ride.props["vent_fan"],person);yield return new WaitForSecondsRealtime(.5f);Check(!ride.CabinFanOn&&s.FanRPM<rpm,"Blower coasts down after ventilation switch opens");ride.Use(ride.props["vent_fan"],person);
            var keys=new[]{"key_route","key_optics","key_seals","key_load","key_traffic","key_comms"};
            for(int j=0;j<keys.Length;j++){ride.Use(ride.props[keys[j]],person);Check(ride.DisplayMode==j,"Dedicated "+keys[j]+" displays its own live page");}
            ride.Use(ride.props["key_lamp_test"],person);Check(s.LampTime>2,"Momentary lamp test addresses the physical annunciators");
            int gain=s.Gain,focal=s.Focal;ride.Use(ride.props["panel_gain"],person);ride.Use(ride.props["camera_focus"],person);
            Check(s.Gain!=gain&&s.Focal!=focal&&Mathf.Abs(ride.exterior.LensAngle-36)<.01f,"Panel luminance and optical focal length respond to separate detented encoders");
            ride.Use(ride.props["diagnostic_screen"],person);ride.Use(ride.props["drive_screen"],person);Check(s.Electrical&&s.Guides,"The two secondary glass displays switch independently");
            ride.Use(ride.props["key_route"],person);ride.Use(ride.props["guide_flood"],person);
        }
        IEnumerator FreeSurvey(){
            var item=ride.props["mug"];ride.Seek(0);person.Place(new Vector3(0,.035f,.40f),0,3);
            ride.Pickup(item);person.Inspect(item);person.LetGo();var loose=item.GetComponent<LooseItemBody>();float start=loose.Body.position.y;
            yield return new WaitForSecondsRealtime(.56f);
            Check(loose.Free&&!ride.Has("mug")&&start-loose.Body.position.y>.45f,"Opening the hand at the anchor releases a colliding body under terrestrial gravity");
            yield return new WaitForSecondsRealtime(1.25f);Check(loose.Impacts>0&&loose.Body.position.y<.36f,"Released vessel strikes and settles on a physical deck");
            var aim=item.Focus;Vector3 foot=new Vector3(aim.x,.033f,aim.z-.78f);var ray=(aim-foot-person.eye.transform.localPosition).normalized;person.Place(foot,Mathf.Atan2(ray.x,ray.z)*Mathf.Rad2Deg,-Mathf.Asin(ray.y)*Mathf.Rad2Deg);Physics.SyncTransforms();
            Check(person.FindFocus()==item,"A dropped vessel remains reachable through the normal aim-and-catch path");ride.Use(item,person);
            ride.Seek(360);person.Place(new Vector3(0,.035f,.45f),0,1);person.CloseInspect();person.Inspect(item);person.LetGo();var parked=loose.Body.position;
            yield return new WaitForSecondsRealtime(.90f);Check((loose.Body.position-parked).magnitude<.06f,"Stationary GEO release retains its place in the carriage");
            ride.Pickup(item);ride.Release(item,new Vector3(0,1.27f,.45f),Quaternion.identity,new Vector3(.58f,.08f,.22f),new Vector3(.45f,1.35f,.27f));
            var initial=loose.Body.position;for(int step=0;step<20;step++)yield return new WaitForFixedUpdate();
            Check(Vector3.Dot(loose.Body.position-initial,Vector3.right)>.10f&&loose.Body.angularVelocity.magnitude>.65f,"Released moving equipment retains measured translation and spin in near-zero g ("+(loose.Body.position.x-initial.x).ToString("F3")+" m, "+loose.Body.angularVelocity.magnitude.ToString("F2")+" rad/s)");
            ride.Pickup(item);Check(ride.Has("mug")&&!loose.Free,"Recapture stows one inventory item and deactivates its free body");
            person.Place(new Vector3(0,.035f,-3),0,0);person.Inspect(item);
            Check(!person.FitFlask()&&ride.Has("mug"),"A passenger across the carriage cannot reach the galley cradle");
            person.CloseInspect();person.Place(new Vector3(1.12f,.035f,.81f),75,34);person.Inspect(item);
            var valve=item.GetComponentInChildren<HandMechanism>(true);
            person.CloseInspect();valve.HoldValve(true);
            for(int n=0;n<32;n++){valve.Advance(.03f);yield return null;}
            Check(valve.Setting==1&&valve.Travel>.95f,"The flask valve remains open under continuous thumb pressure");
            valve.HoldValve(false);yield return new WaitForSeconds(.4f);
            for(int n=0;n<24;n++){valve.Advance(.03f);yield return null;}
            Check(valve.Setting==0&&valve.Travel<.015f,"Releasing the thumb reseats the drinking valve");
            person.Inspect(item);Check(person.FitFlask()&&!ride.Has("mug"),"A passenger can secure the recovered flask on its real keeper");
            yield return new WaitForSeconds(.85f);
            Check(!ride.Cradle.Moving&&!loose.Free&&item.gameObject.activeSelf&&Vector3.Distance(item.transform.localPosition,item.HomePosition)<.007f,"The latch seats at the original mount with the flask retained in microgravity");
            yield return Photo("galley-flask-secured");ride.Seek(76);
        }
        Texture2D ReadFinishFrame(Camera camera, RenderTexture frame,float weight){
            RegisteredFinish.Weight(weight);camera.Render();RenderTexture.active=frame;
            var image=new Texture2D(frame.width,frame.height,TextureFormat.RGB24,false,false);
            image.ReadPixels(new Rect(0,0,frame.width,frame.height),0,0);image.Apply();return image;
        }
        void CompareFinishes(){
            var layers=FindObjectsByType<RegisteredFinish>(FindObjectsInactive.Exclude);Check(layers.Length==3,"Registered finish maps bound for all three rooms");
            var camera=person.eye;var originalTarget=camera.targetTexture;var active=RenderTexture.active;float fov=camera.fieldOfView;
            var previousPosition=camera.transform.position;var previousRotation=camera.transform.rotation;
            string folder=Path.Combine(output,"finish");Directory.CreateDirectory(folder);
            var frame=RenderTexture.GetTemporary(1200,675,24,RenderTextureFormat.ARGB32,RenderTextureReadWrite.sRGB,1);
            camera.targetTexture=frame;
            try {
                foreach(var layer in layers){
                    camera.transform.SetPositionAndRotation(layer.ReferenceEye,Quaternion.LookRotation(layer.ReferenceDirection,layer.ReferenceUp));camera.fieldOfView=layer.ReferenceFov;
                    var without=ReadFinishFrame(camera,frame,0);var with=ReadFinishFrame(camera,frame,RegisteredFinish.FinishWeight);
                    var a=without.GetPixels32();var b=with.GetPixels32();long sum=0;int changed=0;
                    for(int i=0;i<a.Length;i++){int delta=Math.Abs(a[i].r-b[i].r)+Math.Abs(a[i].g-b[i].g)+Math.Abs(a[i].b-b[i].b);sum+=delta;if(delta>=4)changed++;}
                    File.WriteAllBytes(Path.Combine(folder,layer.room+"-base.jpg"),without.EncodeToJPG(93));
                    File.WriteAllBytes(Path.Combine(folder,layer.room+"-registered.jpg"),with.EncodeToJPG(93));Destroy(without);Destroy(with);
                    Check(changed>a.Length*.012f&&sum>a.Length*.08f,layer.room+" GPU material residual affects "+(100f*changed/a.Length).ToString("0.0")+"% of the reference frame");
                }
            } finally{
                RegisteredFinish.Weight(RegisteredFinish.FinishWeight);camera.transform.SetPositionAndRotation(previousPosition,previousRotation);camera.fieldOfView=fov;
                camera.targetTexture=originalTarget;RenderTexture.active=active;RenderTexture.ReleaseTemporary(frame);
            }
        }
        IEnumerator Run(){
            receipt.controls=ride.props.Count;var rooms=new HashSet<string>();foreach(var p in ride.props.Values)rooms.Add(p.room);receipt.rooms=rooms.Count;
            Check(receipt.controls==50&&receipt.rooms==3,"50 directly addressable props and controls across three imported rooms");
            var graphics=GraphicsSurvey();while(graphics.MoveNext())yield return graphics.Current;
            var instruments=InstrumentDisplaySurvey();while(instruments.MoveNext())yield return instruments.Current;
            var moments=PassageMoments();while(moments.MoveNext())yield return moments.Current;
            var survey=ExteriorSurvey();while(survey.MoveNext())yield return survey.Current;
            FlexibleSurvey();
            var fixtures=CabinPhysicsSurvey();while(fixtures.MoveNext())yield return fixtures.Current;
            CompareFinishes();
            var panels=SwitchSurvey();while(panels.MoveNext())yield return panels.Current;
            var loose=FreeSurvey();while(loose.MoveNext())yield return loose.Current;
            var card=ride.props["access_card"];var drawer=ride.props["locker_drawer"];var hatch=ride.props["pressure_hatch"];
            Check(!ride.Pickup(card),"Closed crew drawer holds the credential");ride.Use(hatch,person);Check(!ride.Unlocked&&!hatch.Open,"Service hatch rejects missing credential");
            float v0=ride.Velocity;ride.Use(ride.props["ascent_lever"],person);Check(ride.Feeds==1&&Mathf.Abs(ride.Velocity-v0)<.10f,"Selector changes the real exterior feed without changing car speed");
            ride.Use(ride.props["ascent_lever"],person);Check(ride.Feeds==2&&ride.exterior.Feed.IsCreated(),"Counterline render camera has a live target");ride.SetFeed(0);
            ride.Use(ride.props["nav_screen"],person);Check(ride.DisplayMode==1,"Bonded MFD cycles telemetry");ride.Use(ride.props["nav_screen"],person);ride.Use(ride.props["nav_screen"],person);
            ride.Seek(105);ride.Say("",0);person.Place(new Vector3(-.56f,.03f,2.27f),9,4);
            yield return Photo("01-observation");
            ride.Use(drawer,person);yield return new WaitForSecondsRealtime(.85f);
            Check(drawer.Position>.99f&&(drawer.transform.localPosition-drawer.HomePosition).magnitude>.35f,"Crew drawer runs to its open stop");
            foreach(string id in new[]{"ascent_lever","nav_screen","roller_shade","locker_drawer","access_card","card_reader","pressure_hatch","intercom","service_cabinet","docking_wheel"}){
                var prop=ride.props[id];float center=id=="card_reader"||id=="pressure_hatch"?0:prop.room=="observation"?3.8f:prop.room=="berth"?0:-3.8f;
                Check(Reachable(prop,center),"First-person aim reaches "+id+" from the walkable aisle");
            }
            Check(card.transform.parent==drawer.transform&&ride.Pickup(card)&&ride.Has("access_card"),"Moving drawer exposes a collectible service key");
            ride.Seek(104);person.Place(new Vector3(-.12f,.03f,3.32f),176,3);person.Inspect(card);yield return Photo("02-credential");Check(person.Examined==card&&person.CarriedModel.transform.parent==person.eye.transform,"Service credential is physically held at the passenger window");person.CloseInspect();
            ride.Seek(171);person.Place(new Vector3(.65f,.03f,3.03f),-76,5);
            foreach(string item in new[]{"field_glasses","mug","tool_roll","logbook"}){
                person.Inspect(ride.props[item]);var mechanism=ride.props[item].GetComponentInChildren<HandMechanism>(true);int old=mechanism.Setting;
                person.OperateHeld();
                for(int frame=0;frame<90&&(old==mechanism.Setting||mechanism.Travel<.1f);frame++)yield return null;
                Check(old!=mechanism.Setting&&mechanism.Travel>=.1f,mechanism.label+" physically moves the held hardware");
                yield return Photo("held-"+item);
                Check(person.CarriedModel&&person.CarriedModel.GetComponentInChildren<MeshRenderer>().receiveShadows,item+" is a lit two-sided inspection in the real cabin");person.CloseInspect();
            }
            ride.Use(ride.props["card_reader"],person);Check(ride.Equalizing&&!hatch.Open,"Door waits for its pressure-equalization cycle");yield return new WaitForSecondsRealtime(2.85f);
            Check(ride.Unlocked&&hatch.Position>.99f,"Credential and pressure match open the moving hatch");
            var body=person.GetComponent<CharacterController>();person.Place(new Vector3(0,.035f,-.9f),180,0);
            for(int i=0;i<45;i++)body.Move(Vector3.back*.05f);Check(person.transform.position.z< -2.55f,"Passenger controller traverses the open service hatch");
            ride.Clock(.40f);ride.Say("",0);person.Place(new Vector3(.55f,.035f,-3.03f),260,-1);
            yield return Photo("03-service-port");
            ride.Use(ride.props["service_cabinet"],person);yield return new WaitForSecondsRealtime(.8f);Check(ride.props["service_cabinet"].Position>.99f,"Maintenance cabinet swings fully open");
            foreach(string test in new[]{"power","fiber","seal","return"}){var key=ride.props["test_"+test];Check(Reachable(key,-3.8f),"Opened cabinet exposes "+key.id);ride.Use(key,person);Check(ride.systems.Test==test&&ride.systems.TestClock>2,"Cable witness pulse and "+test+" result start together");}
            person.Place(new Vector3(.80f,.032f,-3.45f),96,3);ride.Say("",0);yield return Photo("07-open-service-cabinet");
            bool lit=ride.practicals[2].enabled;ride.Use(ride.props["breaker"],person);Check(lit!=ride.practicals[2].enabled,"Physical breaker switches the service practical");ride.Use(ride.props["breaker"],person);
            var tender=System.Array.Find(AscentRoute.Services,s=>s.Kind=="tender");
            ride.Clock((float)tender.Progress);yield return null;Check(ride.exterior.lastPass.gameObject.activeInHierarchy,"Scheduled cable tender passes the windows");
            person.Place(new Vector3(1.04f,.03f,3.03f),340,0);ride.Say("",0);yield return Photo("04-counterline");
            person.Place(new Vector3(.74f,.03f,.88f),246,4);yield return Photo("05-berth");
            ride.SecureTurn();Check(ride.Turns==0,"Docking interlock refuses a moving carriage");
            ride.Clock(1);person.Place(new Vector3(-.79f,.03f,2.3f),9,0);ride.Say("",0);yield return Photo("06-terminal");
            Check(ride.exterior.arrivalBay.BridgeClearance>.97f,"Transfer sleeve remains withdrawn before hard capture");
            person.Place(new Vector3(.08f,.035f,-4.70f),187,25);yield return Photo("clamp-travel-open");
            ride.SecureTurn();yield return new WaitForSeconds(.43f);
            Check(Mathf.Abs(ride.exterior.arrivalBay.FollowerTravel*18-6)<.05f&&ride.ClampNeedleAngle>77&&ride.ClampNeedleAngle<80,"First detent centers the jaws and indicates 6 mm on the fixed dial");
            ride.SecureTurn();yield return new WaitForSeconds(.43f);
            Check(Mathf.Abs(ride.exterior.arrivalBay.FollowerTravel*18-13.5f)<.05f&&ride.exterior.arrivalBay.BridgeClearance>.99f,"Second detent draws the jaws in before the transfer sleeve can extend");
            yield return Photo("clamp-travel-drawn");
            ride.SecureTurn();Check(ride.Velocity==0&&ride.Docked,"Automatic terminal stop and three-tooth docking clamp");
            yield return new WaitForSeconds(2.3f);Check(ride.exterior.arrivalBay.SleeveStroke>=1&&ride.ClampNeedleAngle>235,"Hard capture seats the passenger transfer sleeve and the 18 mm follower");
            yield return Photo("clamp-travel-seated");
            var finishes=new HashSet<string>();
            foreach(var surface in ride.exterior.habitat.GetComponentsInChildren<MeshRenderer>(true))
                if(surface.enabled)foreach(var material in surface.sharedMaterials)if(material)finishes.Add(material.name);
            Check(finishes.Contains("Aster_Soil")&&finishes.Contains("Aster_Glass")&&finishes.Contains("Aster_Mirror")&&finishes.Contains("Aster_Radiator"),
                "Physical settlement separates glazed valleys, inhabited soil, collector mirrors and radiator finishes");
            person.Place(new Vector3(-.70f,.095f,4.32f),7.65f,-7.1f);person.Observe();person.eye.fieldOfView=40;ride.Say("",0);
            yield return Photo("09-aster-reach");person.Observe();
            person.Place(new Vector3(.64f,.032f,4.13f),1,14);ride.Say("",0);yield return Photo("08-terminal-instruments");
            var contacts=FurnishingContacts();while(contacts.MoveNext())yield return contacts.Current;
            var fracture=FractureSurvey();while(fracture.MoveNext())yield return fracture.Current;
        }
    }
}
