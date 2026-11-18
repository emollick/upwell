using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;

namespace Upwell {
    public sealed class ExteriorRig : MonoBehaviour {
        public Material graphite,titanium,pearl,glass,amber,beacon;
        public Transform habitat;
        public RenderTexture Feed {get; private set;}
        public Camera SensorCamera=>view;
        public int SensorRadianceWidth {get;private set;}
        public int PassengerRadianceWidth {get;private set;}
        public int PassengerAtmosphereSteps {get;private set;}
        public bool OnHabitatRelay=>sensorView==6&&arrivalBay&&arrivalBay.DockDistance<=.101&&orbital?.HabitatRelay;
        public Bounds CounterEnvelope {get;private set;}
        Renderer[] counterSurfaces;
        public Material RuntimeSky {get; private set;}
        public Light sun;
        public Material rangePaint,rangeLamp;
        public Light[] windowBounce;
        public StationRig anchorBay,arrivalBay;
        public GuidewayRig guideway;
        public Shader[] reflectionKernels;
        public Shader liveRadiance;
        Material skyPresentation;bool tracing;readonly Dictionary<int,RenderTexture> skyBuffers=new Dictionary<int,RenderTexture>();
        Texture2D starCatalogue,galaxy;float stellarEye=.15f;
        public void AdaptPassengerEye(bool saloonOn,int gain,float dt) {
            stellarEye=StellarCatalog.Adapt(stellarEye,saloonOn,gain,-sun.transform.forward.y,SolarVisibility,dt);
        }
        public int ClampTurns;
        public float LensAngle=52;
        public ReflectionProbe[] roomReflections;
        public Transform lastPass {get;private set;}
        Transform vehicle,freightPallet;Camera view;int detent,sensorView;
        OrbitalHardware orbital;
        HarborFleet harbor;
        public OrbitalHardware Orbital {get{return orbital;}}
        WeatherOptics medium;float weatherTime,lightClock,feedClock,smoothedFrame,reflectionClock;
        int previousProbe=-1,probeJob=-1;Vector3 probeSun;
        Vector4 probeCircuits;float probeGain=-1,probeFilm=-1;
        double lastRoute=-100;public float CloudTransmission{get;private set;}=1;
        public float SolarVisibility{get;private set;}=1;
        public float LocalDensity{get;private set;}
        public static readonly float[] Passes=Array.ConvertAll(AscentRoute.PassSeconds,s=>(float)(s/AscentRoute.Duration));
        static readonly Vector3 Counter=new Vector3(-7.89f,0,24.8f);
        public const int ExteriorLayer=8;
        void OnEnable(){Camera.onPreRender+=PublishView;}
        void OnDisable(){Camera.onPreRender-=PublishView;}
        void PublishView(Camera camera){
            float half=Mathf.Tan(camera.fieldOfView*.5f*Mathf.Deg2Rad);var tr=camera.transform;
            Shader.SetGlobalVector("_SkyForward",tr.forward);Shader.SetGlobalVector("_SkyUp",tr.up*half);
            Shader.SetGlobalVector("_SkyRight",tr.right*half*camera.aspect);Shader.SetGlobalVector("_SkyEye",tr.position);
            if(!RuntimeSky||!skyPresentation||tracing)return;
            skyPresentation.SetFloat("_StellarEye",camera!=view&&camera.cameraType==CameraType.Game?stellarEye:.86f);
            bool web=Application.platform==RuntimePlatform.WebGLPlayer,slow=smoothedFrame>.08f;
            float scale=camera.cameraType==CameraType.Reflection?.64f:web?(slow?.30f:.46f):.58f;
            if(Passenger.SoftwareGraphics)scale=camera.cameraType==CameraType.Reflection?.6f:.29f;
            bool direct=camera==view&&sensorView>0;
            int widthLimit=web?760:1080;
            if(direct&&!Passenger.SoftwareGraphics){
                bool inSpace=RuntimeSky.GetFloat("_HeightKm")>95;
                scale=inSpace?(web?.86f:1f):web?(slow?.48f:.62f):.72f;
                widthLimit=web?1440:1920;
            }
            int detail=PlayerGraphics.Atmosphere;
            if(!Passenger.SoftwareGraphics && camera.cameraType!=CameraType.Reflection){
                float quality=detail==0?.70f:detail==2?1.25f:1;
                scale=Mathf.Min(1,scale*quality);
                widthLimit=Mathf.RoundToInt(widthLimit*quality);
            }
            int width=Mathf.Clamp(Mathf.CeilToInt(camera.pixelWidth*scale/8)*8,72,widthLimit),height=Mathf.Max(48,Mathf.RoundToInt(width/Mathf.Max(.15f,camera.aspect)));
            if(camera==view)SensorRadianceWidth=width;
            int key=camera==view?1:camera.cameraType==CameraType.Reflection?2:0;
            if(!skyBuffers.TryGetValue(key,out var buffer)||buffer.width!=width||buffer.height!=height){
                if(buffer){buffer.Release();Destroy(buffer);}var fmt=SystemInfo.SupportsRenderTextureFormat(RenderTextureFormat.ARGBHalf)?RenderTextureFormat.ARGBHalf:RenderTextureFormat.ARGB32;
                buffer=new RenderTexture(width,height,0,fmt,RenderTextureReadWrite.Linear){name="Current sky radiance",filterMode=FilterMode.Bilinear,wrapMode=TextureWrapMode.Clamp};buffer.Create();skyBuffers[key]=buffer;
            }
            int steps=Passenger.SoftwareGraphics?24:key==2?32:web?(slow?48:80):(slow?72:128);
            if(!Passenger.SoftwareGraphics&&key!=2)steps=detail==0?Mathf.RoundToInt(steps*.65f):detail==2?Mathf.Min(144,Mathf.RoundToInt(steps*1.23f)):steps;
            RuntimeSky.SetFloat("_Samples",steps);
            if(direct||key==0){PassengerRadianceWidth=width;PassengerAtmosphereSteps=steps;}
            var previous=RenderTexture.active;tracing=true;
            try{Graphics.Blit(null,buffer,RuntimeSky,0);skyPresentation.SetTexture("_Radiance",buffer);Shader.SetGlobalTexture("_UpwellCurrentSky",buffer);}
            finally{RenderTexture.active=previous;tracing=false;}
        }
        public void RenderFeed(){if(view&&view.targetTexture==Feed)view.Render();}
        GameObject Part(string name,PrimitiveType shape,Transform parent,Vector3 pos,Vector3 scale,Material mat,Quaternion rot) {
            var g=GameObject.CreatePrimitive(shape);g.name=name;g.layer=ExteriorLayer;g.transform.SetParent(parent,false);g.transform.localPosition=pos;g.transform.localScale=scale;g.transform.localRotation=rot;
            var c=g.GetComponent<Collider>();if(c){c.enabled=false;Destroy(c);}var r=g.GetComponent<MeshRenderer>();r.sharedMaterial=mat;r.shadowCastingMode=ShadowCastingMode.On;r.receiveShadows=true;return g;
        }
        GameObject Box(string name,Transform p,Vector3 c,Vector3 size,Material m)=>Part(name,PrimitiveType.Cube,p,c,size,m,Quaternion.identity);
        GameObject Beam(Transform root,Vector3 a,Vector3 b,float width,Material m){
            return Part("Brace",PrimitiveType.Cylinder,root,(a+b)*.5f,new Vector3(width,(b-a).magnitude*.5f,width),m,Quaternion.FromToRotation(Vector3.up,b-a));
        }
        void Awake(){
            RuntimeSky=new Material(RenderSettings.skybox);skyPresentation=new Material(liveRadiance);RenderSettings.skybox=skyPresentation;
            starCatalogue=StellarCatalog.Load();skyPresentation.SetTexture("_StarCatalogue",starCatalogue);
            galaxy=StellarCatalog.LoadGalacticLight();skyPresentation.SetTexture("_GalacticLight",galaxy);
            medium=new WeatherOptics((Texture3D)RuntimeSky.GetTexture("_NoiseField"));RuntimeSky.SetTexture("_MarineCells",medium.MarineCells);
            RuntimeSky.SetTexture("_CarSunMask",Resources.Load<Texture2D>("CarSunMask"));
            vehicle=new GameObject("Descending counterline car").transform;vehicle.SetParent(transform,false);
            Box("Pressure body",vehicle,Vector3.zero,new Vector3(2.4f,2.4f,3.9f),pearl);
            for(int side=-1;side<=1;side+=2) {
                Box("End band",vehicle,new Vector3(0,0,side*1.98f),new Vector3(2.37f,1.85f,.10f),graphite);
                Box("Glazed end",vehicle,new Vector3(0,.18f,side*2.035f),new Vector3(1.91f,.77f,.035f),glass);
                Box("Cantrail",vehicle,new Vector3(side*1.21f,.90f,0),new Vector3(.10f,.09f,3.89f),titanium);
                for(int k=0;k<5;k++)Box("Side glazing",vehicle,new Vector3(1.22f*side,.18f,-1.39f+k*.69f),new Vector3(.05f,.76f,.51f),glass);
                for(int k=-1;k<2;k++)Box("Guide bogie",vehicle,new Vector3(side*.72f,1.24f,k*1.22f),new Vector3(.34f,.25f,.55f),graphite);
                Box("Running light",vehicle,new Vector3(side*1.11f,-.49f,-2.05f),new Vector3(.11f,.09f,.045f),beacon);
                for(int bay=0;bay<6;bay++){
                    float z=-1.67f+bay*.66f;
                    Box("Pressure seam",vehicle,new Vector3(side*1.207f,-.56f,z),new Vector3(.018f,.74f,.018f),graphite);
                    Box("Roof radiator rib",vehicle,new Vector3(side*.69f,1.215f,z),new Vector3(.81f,.028f,.036f),titanium);
                    for(int vent=0;vent<4;vent++)Box("Exchanger slat",vehicle,new Vector3(side*1.215f,-.72f+vent*.065f,z+.25f),new Vector3(.025f,.025f,.33f),graphite);
                }
            }
            freightPallet=new GameObject("Shielded freight pallets").transform;freightPallet.SetParent(vehicle,false);
            for(int side=-1;side<=1;side+=2)for(int module=0;module<3;module++){
                float z=-1.32f+module*1.32f;
                Box("Vacuum cargo cask",freightPallet,new Vector3(side*1.28f,.04f,z),new Vector3(.37f,1.48f,1.17f),titanium);
                for(int j=0;j<5;j++)Box("Radiant fin",freightPallet,new Vector3(side*1.485f,.03f,z+(j-2)*.207f),new Vector3(.054f,1.32f,.032f),graphite);
                foreach(float y in new[]{-.54f,.59f})Box("Restraint rail",freightPallet,new Vector3(side*1.51f,y,z),new Vector3(.065f,.075f,1.21f),amber);
            }
            lastPass=vehicle;
            if(arrivalBay){
                Transform station=arrivalBay.transform;
                foreach(float s in new[]{-1f,1f}){
                    Beam(station,new Vector3(s*5.3f,-185,12),new Vector3(s*5.3f,-1.5f,12),.065f,titanium);
                    foreach(float y in new[]{-180f,-125f,-76f,-45f,-22f,-9f}){
                        var p=new Vector3(s*5.3f,y,12);
                        Beam(station,p+Vector3.up*.72f,p+new Vector3(-s*.52f,0,0),.07f,graphite);
                        Box("Capture range rail",station,p+new Vector3(-s*.25f,-.08f,0),new Vector3(.73f,.14f,.19f),titanium);
                        Box("Range index",station,p+new Vector3(-s*.40f,-.035f,-.108f),new Vector3(.29f,.074f,.026f),beacon);
                    }
                    foreach(float z in new[]{-5.8f,5.8f}){
                        Vector3 leg=new Vector3(s*3.78f,-5.4f,z);
                        Beam(station,leg+Vector3.down*6.4f,leg+Vector3.up*4.5f,.18f,titanium);
                        Beam(station,leg+Vector3.down*3.8f,leg+new Vector3(s*2.42f,4,0),.13f,graphite);
                        Box("Capture throat luminous index",station,leg+new Vector3(-s*.11f,1.34f,0),new Vector3(.088f,3.72f,.14f),rangeLamp);
                        var lampBase=Box("Underdeck flood housing",station,leg,new Vector3(.63f,.37f,.64f),rangePaint);
                        Box("Underdeck luminous optic",lampBase.transform,new Vector3(-s*.18f,.50f,0),new Vector3(.70f,.035f,.68f),rangeLamp);
                        var mount=new GameObject("Upward capture apron flood");mount.transform.SetParent(station,false);mount.transform.localPosition=leg+Vector3.up*.28f;
                        Vector3 aim=leg+new Vector3(s*3.1f,6.7f,z>0?1.2f:-1.2f);mount.transform.localRotation=Quaternion.LookRotation(aim-mount.transform.localPosition);
                        var light=mount.AddComponent<Light>();light.type=LightType.Spot;light.color=z>0?new Color(.68f,.84f,1):new Color(1,.83f,.58f);
                        light.intensity=7.6f;light.range=21;light.spotAngle=96;light.innerSpotAngle=46;light.shadows=LightShadows.Soft;light.shadowBias=.024f;
                        light.cullingMask=1<<ExteriorLayer;light.renderMode=LightRenderMode.ForcePixel;
                    }
                }
            }
            var camGo=new GameObject("Selected optical feed");camGo.transform.SetParent(transform,false);view=camGo.AddComponent<Camera>();
            view.cullingMask=1<<ExteriorLayer;view.clearFlags=CameraClearFlags.Skybox;view.nearClipPlane=.04f;view.farClipPlane=26000;view.depth=-2;view.allowHDR=false;view.fieldOfView=63;
            Feed=new RenderTexture(Passenger.SoftwareGraphics?272:568,Passenger.SoftwareGraphics?144:300,16){name="Exterior camera multiplex"};Feed.Create();view.targetTexture=Feed;view.enabled=false;Select(0);
            orbital=new OrbitalHardware(habitat,vehicle,arrivalBay.transform);
            harbor=new HarborFleet(anchorBay.transform);
            counterSurfaces=vehicle.GetComponentsInChildren<Renderer>(true);
        }
        void Start(){
            if(!Passenger.SoftwareGraphics)return;
            foreach(var l in FindObjectsByType<Light>(FindObjectsInactive.Include)){
                if(l==sun){l.shadows=LightShadows.Hard;l.shadowResolution=LightShadowResolution.Low;continue;}
                l.shadows=LightShadows.None;l.renderMode=LightRenderMode.Auto;
            }
            foreach(var probe in roomReflections)if(probe)probe.resolution=32;
        }
        public void Select(int channel) {
            detent=channel;
            if(sensorView>0)channel=sensorView==3?1:sensorView==4?2:0;
            Vector3 eye,aim;
            if(channel==1){eye=new Vector3(-2.53f,.82f,3.82f);aim=new Vector3(-3.42f,1.82f,4.87f);}
            // The nose-corner counterline head clears both of Car 07's own bogies.
            // Its oblique line of sight also reveals the side windows and cargo restraints.
            else if(channel==2){eye=new Vector3(2.44f,2.22f,5.91f);aim=Counter+Vector3.up*1.5f;}
            else{eye=new Vector3(2.43f,2.21f,5.82f);aim=eye+new Vector3(.02f,.035f,-1);}
            view.transform.SetPositionAndRotation(eye,Quaternion.LookRotation(aim-eye));
        }
        public void WatchSensor(int mode){
            sensorView=mode;feedClock=0;
            if(!view)return;
            // The cabin monitor needs a small texture. A passenger looking
            // through the optics gets a fresh frame at display resolution.
            view.enabled=false;view.targetTexture=mode>0?null:Feed;view.ResetAspect();
            Select(detent);view.enabled=mode>0;
        }
        void TrackCounterCar(){
            var envelope=new Bounds(vehicle.position,Vector3.zero);bool seen=false;
            foreach(var surface in counterSurfaces){
                if(!surface.enabled||!surface.gameObject.activeInHierarchy)continue;
                if(seen)envelope.Encapsulate(surface.bounds);else{envelope=surface.bounds;seen=true;}
            }
            CounterEnvelope=envelope;
            var camera=view.transform;camera.rotation=Quaternion.LookRotation(envelope.center-camera.position);
            if(!seen){view.fieldOfView=30;return;}
            float tangent=0,aspect=Mathf.Max(.1f,view.aspect);
            for(int i=0;i<8;i++){
                var side=new Vector3((i&1)==0?-1:1,(i&2)==0?-1:1,(i&4)==0?-1:1);
                var point=camera.InverseTransformPoint(envelope.center+Vector3.Scale(envelope.extents,side));
                tangent=Mathf.Max(tangent,Mathf.Max(Mathf.Abs(point.x)/aspect,Mathf.Abs(point.y))/Mathf.Max(.1f,point.z));
            }
            // Allow the approaching vehicle to grow, but retain both end caps and its outer cargo racks.
            view.fieldOfView=Mathf.Clamp(2*Mathf.Atan(tangent/.87f)*Mathf.Rad2Deg,21,108);
        }
        public void SetProgress(double seconds,double altitude,float speed,float dt,float? weatherEpoch=null) {
            bool seek=Math.Abs(seconds-lastRoute)>1.5||seconds<lastRoute-.002;lastRoute=seconds;
            if(weatherEpoch.HasValue){weatherTime=weatherEpoch.Value;lightClock=0;}
            else if(seconds<AscentRoute.Duration||seek){
                // The cloud deck advects during the voyage's compressed ship time.
                // A held optical test can still provide its own fixed weather epoch.
                weatherTime=(float)(seconds*1.2+CarriageForces.At(altitude).ShipSeconds*(2200.0/3600.0));
            }else weatherTime+=dt;
            Vector3 day=AscentRoute.Sun(altitude);
            double remaining=(AscentRoute.Terminal-altitude)*1000;
            anchorBay?.SetState(seconds,altitude,0,dt);arrivalBay?.SetState(seconds,altitude,ClampTurns,dt);
            float seaTime=harbor.Update(seconds,altitude);
            if(seek||lightClock<=0){
                lightClock=.22f;CloudTransmission=medium.Transmission(altitude,weatherTime,day);
                SolarVisibility=WeatherOptics.Visibility(altitude,day);
                LocalDensity=medium.Density(new Vector3(0,(float)altitude,0),weatherTime);
            }
            lightClock-=dt;
            RuntimeSky.SetFloat("_HeightKm",(float)altitude+.007f);RuntimeSky.SetFloat("_WeatherSeconds",weatherTime);RuntimeSky.SetVector("_SunLocal",day);
            smoothedFrame=Mathf.Lerp(smoothedFrame,Time.unscaledDeltaTime,.024f);
            int normalSteps=Application.platform==RuntimePlatform.WebGLPlayer?22:32;
            RuntimeSky.SetFloat("_Samples",smoothedFrame>.080f?14:normalSteps);
            float dip=(float)Math.Acos(6371/(6371+altitude));
            if(sensorView==5){
                view.transform.rotation=Quaternion.LookRotation(new Vector3(day.x>=0?-.72f:.72f,.16f,.70f));
                view.fieldOfView=61;
            }else if(sensorView==6){
                var relay=orbital?.HabitatRelay;
                view.transform.position=remaining<=.10&&relay?relay.position:new Vector3(2.43f,2.21f,5.82f);
                var settlement=new Vector3(1060,(float)remaining+988,7900)-view.transform.position;
                view.transform.rotation=Quaternion.LookRotation(settlement);
                view.fieldOfView=Mathf.Clamp(2*Mathf.Atan(2560/(settlement.magnitude*Mathf.Min(1,view.aspect)))*Mathf.Rad2Deg,2.1f,96);
            }else if(sensorView==2){
                var eye=new Vector3(.43f,2.77f,5.84f);
                if(remaining>2500000){
                    // Before acquisition the forward sensor watches through and over the cloud deck.
                    float pitch=Mathf.Min(83f,dip*Mathf.Rad2Deg+5f)*Mathf.Deg2Rad;
                    var track=new Vector3(.28f*Mathf.Cos(pitch),-Mathf.Sin(pitch),Mathf.Cos(pitch));
                    view.transform.SetPositionAndRotation(eye,Quaternion.LookRotation(track,Vector3.up));view.fieldOfView=61;
                }else{
                var throat=new Vector3(.30f,(float)remaining+4.6f,1.05f)-eye;
                var settlement=new Vector3(1060,(float)remaining+988,7900)-eye;
                Vector3 dir=Vector3.Slerp(throat.normalized,settlement.normalized,Mathf.SmoothStep(0,1,Mathf.InverseLerp(380,1400,(float)remaining)));
                if(remaining<2)dir=Vector3.Slerp(dir,settlement.normalized,1-Mathf.SmoothStep(0,1,Mathf.InverseLerp(.2f,2,(float)remaining)));
                float fov=remaining>400?Mathf.Clamp(2*Mathf.Atan(1900/settlement.magnitude)*Mathf.Rad2Deg*1.35f,1.6f,34):Mathf.Lerp(69,27,Mathf.InverseLerp(30,190,(float)remaining));
                if(remaining<2)fov=Mathf.Lerp(30,fov,Mathf.InverseLerp(.2f,2,(float)remaining));
                view.transform.SetPositionAndRotation(eye,Quaternion.LookRotation(dir,Mathf.Abs(dir.y)>.982f?Vector3.back:Vector3.up));view.fieldOfView=fov;
                }
            } else if(sensorView==1||(sensorView==0&&detent==0)){
                if(sensorView==1)view.transform.position=new Vector3(.11f,-.28f,5.83f);
                float tilt=sensorView==1?Mathf.Lerp(dip,Mathf.PI*.5f,Mathf.InverseLerp(70,2200,(float)altitude)):dip;
                view.transform.rotation=Quaternion.LookRotation(new Vector3(0,-Mathf.Sin(tilt),-Mathf.Max(.0003f,Mathf.Cos(tilt))),Vector3.up);
                float disk=2*Mathf.Asin(6371/(6371+(float)altitude))*Mathf.Rad2Deg;
                if(sensorView==1){
                    float apparentRadius=.5f*disk*Mathf.Deg2Rad;
                    float fit=Mathf.Clamp(2*Mathf.Atan(Mathf.Tan(apparentRadius)/(.78f*Mathf.Min(1,view.aspect)))*Mathf.Rad2Deg,16,133);
                    view.fieldOfView=Mathf.Lerp(Mathf.Clamp(disk*1.25f,20,68),fit,Mathf.SmoothStep(0,1,Mathf.InverseLerp(2800,4300,(float)altitude)));
                    float harborView=1-Mathf.SmoothStep(0,1,Mathf.InverseLerp(.43f,1.5f,(float)altitude));
                    if(harborView>0){
                        float metres=(float)(altitude*1000),clear=Mathf.SmoothStep(0,1,Mathf.InverseLerp(8,105,metres));
                        view.transform.position=Vector3.Lerp(view.transform.position,new Vector3(3.45f,-.38f,-1.9f),harborView);
                        Vector3 bearing=new Vector3(23-14*clear,-7-metres+3*clear,24+57*clear)-view.transform.position;
                        float emerged=Mathf.SmoothStep(0,1,Mathf.InverseLerp(5.5f,18,metres));
                        Vector3 well=new Vector3(0,-7-metres,3.2f)-view.transform.position;
                        var aim=Vector3.Lerp(well.normalized,bearing.normalized,emerged).normalized;
                        view.transform.rotation=Quaternion.LookRotation(Vector3.Lerp(view.transform.forward,aim,harborView),Vector3.up);
                        view.fieldOfView=Mathf.Lerp(view.fieldOfView,49+4*clear,harborView);
                    }
                }else view.fieldOfView=LensAngle;
            }
            else if(sensorView==3){view.transform.SetPositionAndRotation(new Vector3(-2.63f,.65f,3.63f),Quaternion.LookRotation(new Vector3(-.28f,1.12f,.36f)));view.fieldOfView=72;}
            else view.fieldOfView=LensAngle;
            // The nadir pupil is physically below the hull. Keep continuous rails rather
            // than chopping their silhouettes across the planetary disc with a distant near plane.
            view.nearClipPlane=.045f;
            guideway.Move(seconds,altitude,speed/3.6f,dt,seek);
            var own=CarriageForces.At(altitude);var contact=AscentRoute.Counterline(altitude,own);
            freightPallet.gameObject.SetActive(contact.Service.Kind=="freight");
            vehicle.gameObject.SetActive(contact.InRange);
            vehicle.position=Counter+new Vector3(1.671f,1.52f+(float)contact.Separation,-.015f);
            orbital.Update(seconds,own.ShipSeconds,remaining,dt,contact);
            if(sensorView==4)TrackCounterCar();
            if(habitat){
                habitat.gameObject.SetActive(remaining<2500000);
                if(habitat.gameObject.activeSelf){var physical=new Vector3(1060,(float)remaining+988,7900);float ratio=Mathf.Min(1,21800/physical.magnitude);
                    habitat.position=physical*ratio;habitat.localScale=Vector3.one*(315*ratio);
                    habitat.rotation=Quaternion.Euler(-14,64,-7);}
            }
            if(sensorView==8&&remaining<=.10)orbital.AimValleyCamera(view);
            sun.transform.rotation=Quaternion.LookRotation(-day,Mathf.Abs(day.y)>.98f?Vector3.forward:Vector3.up);
            float mass=1/Mathf.Max(.047f,day.y+.06f),air=Mathf.Exp(-(float)altitude/8);
            Color direct=new Color(Mathf.Exp(-mass*.052f*air),Mathf.Exp(-mass*.113f*air),Mathf.Exp(-mass*.255f*air));
            sun.color=direct;sun.intensity=3.35f*SolarVisibility*CloudTransmission;
            Shader.SetGlobalVector("_UpwellSun",day);Shader.SetGlobalFloat("_UpwellSolarPower",SolarVisibility*CloudTransmission);Shader.SetGlobalFloat("_UpwellWaterTime",seaTime);
            harbor.SampleDaylight(RuntimeSky,seconds,altitude);
            double sidereal=2.8*Math.PI/12+own.ShipSeconds*7.292115e-5;
            skyPresentation.SetVector("_SiderealBasis",new Vector4((float)Math.Cos(sidereal),(float)Math.Sin(sidereal),0,0));
            float inAir=1-Mathf.SmoothStep(0,1,Mathf.InverseLerp(13,150,(float)altitude)),dayFill=Mathf.Clamp01(day.y*1.8f+.20f);
            float groundReflect=Mathf.Clamp01((float)(6371/(6371+altitude)))*Mathf.Clamp01(day.y+.25f);
            float scattered=inAir*(.18f+.82f*dayFill)*(.70f+.30f*(1-CloudTransmission));
            float terminalBounce=1-Mathf.SmoothStep(0,1,Mathf.InverseLerp(14,90,(float)remaining));
            RenderSettings.ambientSkyColor=Color.Lerp(new Color(.067f,.083f,.099f),new Color(.38f,.47f,.55f),Mathf.Clamp01(scattered+.10f*groundReflect+.69f*terminalBounce));
            RenderSettings.ambientEquatorColor=Color.Lerp(new Color(.065f,.074f,.081f),new Color(.25f,.31f,.36f),Mathf.Clamp01(scattered+.22f*groundReflect+.77f*terminalBounce));
            RenderSettings.ambientGroundColor=Color.Lerp(new Color(.051f,.053f,.052f),new Color(.14f,.15f,.15f),groundReflect);
            if(windowBounce!=null)for(int i=0;i<windowBounce.Length;i++){
                var light=windowBounce[i];if(!light)continue;light.color=Color.Lerp(new Color(.58f,.72f,1),new Color(.85f,.92f,1),scattered);
                light.intensity=i==3?.045f+.74f*(scattered+groundReflect):.16f+.98f*scattered+.52f*groundReflect;
            }
            RenderSettings.fog=altitude<16;RenderSettings.fogMode=FogMode.Linear;
            RenderSettings.fogColor=Color.Lerp(new Color(.34f,.43f,.53f),new Color(.72f,.80f,.88f),Mathf.Clamp01(LocalDensity));
            RenderSettings.fogStartDistance=12;RenderSettings.fogEndDistance=Mathf.Lerp(14000,95,1-Mathf.Exp(-LocalDensity*3));
            if(roomReflections!=null&&roomReflections.Length==3&&Camera.main){
                float z=Camera.main.transform.position.z;int room=z>1.9f?0:z< -1.9f?2:1;
                var circuits=Shader.GetGlobalVector("_UpwellPracticalState");
                float gain=Shader.GetGlobalFloat("_UpwellGlassPanelGain"),film=Shader.GetGlobalFloat("_UpwellSolarFilm");
                bool changed=circuits!=probeCircuits||gain!=probeGain||film!=probeFilm;
                reflectionClock-=dt;bool idle=previousProbe<0||probeJob<0||roomReflections[previousProbe].IsFinishedRendering(probeJob);
                if(idle&&(seek||changed||room!=previousProbe||reflectionClock<=0||Vector3.Dot(day,probeSun)<.984f)){
                    probeCircuits=circuits;probeGain=gain;probeFilm=film;
                    previousProbe=room;probeSun=day;probeJob=roomReflections[room].RenderProbe();reflectionClock=Passenger.SoftwareGraphics?28:Application.platform==RuntimePlatform.WebGLPlayer?12:6.5f;
                }
            }
            feedClock-=dt;if(sensorView==0&&(seek||feedClock<=0)){feedClock=Passenger.SoftwareGraphics?.62f:.15f;RenderFeed();}
        }
        void OnDestroy(){if(Feed)Feed.Release();if(RuntimeSky)Destroy(RuntimeSky);if(skyPresentation)Destroy(skyPresentation);if(medium!=null&&medium.MarineCells)Destroy(medium.MarineCells);
            harbor?.Dispose();if(starCatalogue)Destroy(starCatalogue);if(galaxy)Destroy(galaxy);
            foreach(var res in skyBuffers.Values)if(res){res.Release();Destroy(res);}}
    }
}
