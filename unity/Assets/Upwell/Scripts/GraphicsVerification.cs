using System;
using System.Collections;
using System.IO;
using UnityEngine;

namespace Upwell {
    public sealed partial class RideVerification {
        #if UNITY_WEBGL && !UNITY_EDITOR
        [System.Runtime.InteropServices.DllImport("__Internal")]
        static extern void UpwellEdgeAudit(int width,int height,int repeat,int changed,int samples,int held,int optical);
        [System.Runtime.InteropServices.DllImport("__Internal")]
        static extern void UpwellAimAudit(float horizontal,float vertical,int atOptic,int inHand,float lens,int zoomed);
        public void ReadVisibleAim(){
            var passenger=GetComponent<Passenger>();var glasses=passenger.ride.props["field_glasses"];
            Vector3 world=(glasses.Focus-passenger.eye.transform.position).normalized;var forward=passenger.eye.transform.forward;
            float yaw=Mathf.DeltaAngle(Mathf.Atan2(forward.x,forward.z)*Mathf.Rad2Deg,Mathf.Atan2(world.x,world.z)*Mathf.Rad2Deg);
            float pitch=(Mathf.Asin(forward.y)-Mathf.Asin(world.y))*Mathf.Rad2Deg;
            UpwellAimAudit(yaw,pitch,passenger.Focus==glasses?1:0,passenger.CarriedModel?1:0,passenger.eye.fieldOfView,passenger.GlazingMagnified?1:0);
        }
        // This readback is requested explicitly by the localhost QA harness.
        // Render both choices in one engine tick while geometry, light and weather are identical.
        public void VerifyVisibleEdges(){
            var passenger=GetComponent<Passenger>();var exterior=passenger.ride.exterior;
            Camera camera=passenger.eye.enabled?passenger.eye:exterior.SensorCamera;
            var previous=RenderTexture.active;var target=camera.targetTexture;int saved=PlayerGraphics.Choices;
            int w=640,h=Mathf.RoundToInt(w/Mathf.Max(.2f,camera.aspect));
            var frame=RenderTexture.GetTemporary(w,h,24,RenderTextureFormat.ARGB32,RenderTextureReadWrite.sRGB,1);
            Texture2D a=null,reference=null,b=null;
            try{
                camera.targetTexture=frame;PlayerGraphics.Set(PlayerGraphics.Option.Edges,0,false);
                a=ReadFinishFrame(camera,frame,RegisteredFinish.FinishWeight);
                reference=ReadFinishFrame(camera,frame,RegisteredFinish.FinishWeight);
                PlayerGraphics.Set(PlayerGraphics.Option.Edges,1,false);
                b=ReadFinishFrame(camera,frame,RegisteredFinish.FinishWeight);
                UpwellEdgeAudit(w,h,ChangedPixels(a,reference,6),ChangedPixels(reference,b,6),camera.GetComponent<PresentationEdges>().SourceSamples,passenger.CarriedModel?1:0,camera==exterior.SensorCamera?1:0);
            }finally{PlayerGraphics.ApplyPacked(saved);camera.targetTexture=target;RenderTexture.active=previous;RenderTexture.ReleaseTemporary(frame);if(a)Destroy(a);if(reference)Destroy(reference);if(b)Destroy(b);}
        }
        #endif
        int ChangedPixels(Texture2D a,Texture2D b,int threshold){
            var aa=a.GetPixels32();var bb=b.GetPixels32();int changed=0;
            for(int i=0;i<aa.Length;i++)
                if(Math.Abs(aa[i].r-bb[i].r)+Math.Abs(aa[i].g-bb[i].g)+Math.Abs(aa[i].b-bb[i].b)>=threshold)changed++;
            return changed;
        }
        void GraphicsPair(string label,Camera camera,PlayerGraphics.Option option,int low,int high){
            var target=camera.targetTexture;var previous=RenderTexture.active;int choices=PlayerGraphics.Choices;
            var frame=RenderTexture.GetTemporary(960,600,24,RenderTextureFormat.ARGB32,RenderTextureReadWrite.sRGB,1);
            var folder=Path.Combine(output,"graphics");Directory.CreateDirectory(folder);
            Texture2D a=null,b=null,control=null;
            try{
                camera.targetTexture=frame;
                PlayerGraphics.Set(option,low,false);
                // Complete pending reflection-probe and target-size work before taking either still.
                camera.Render();camera.Render();
                a=ReadFinishFrame(camera,frame,RegisteredFinish.FinishWeight);
                control=ReadFinishFrame(camera,frame,RegisteredFinish.FinishWeight);
                int natural=ChangedPixels(a,control,6),small=ride.exterior.PassengerRadianceWidth,steps=ride.exterior.PassengerAtmosphereSteps;
                PlayerGraphics.Set(option,high,false);
                b=ReadFinishFrame(camera,frame,RegisteredFinish.FinishWeight);
                var pass=camera.GetComponent<PresentationEdges>();
                int changed=ChangedPixels(control,b,6),pixels=frame.width*frame.height;
                File.WriteAllBytes(Path.Combine(folder,label+"-low.png"),control.EncodeToPNG());
                File.WriteAllBytes(Path.Combine(folder,label+"-high.png"),b.EncodeToPNG());
                Check(changed>natural+Math.Max(70,pixels/1900),label+" changes "+changed+" of "+pixels+" same-pose pixels at RGB delta 6; repeated control "+natural);
                if(option==PlayerGraphics.Option.Edges)
                    Check(pass.SourceSamples==1&&!camera.allowMSAA&&pass.LastFilteredFrame==Time.frameCount,label+" receives a single-sample scene and applies final FXAA");
                if(option==PlayerGraphics.Option.Atmosphere)
                    Check(ride.exterior.PassengerRadianceWidth>small&&ride.exterior.PassengerAtmosphereSteps>steps,
                        "Atmosphere increases actual trace from "+small+"px/"+steps+" to "+ride.exterior.PassengerRadianceWidth+"px/"+ride.exterior.PassengerAtmosphereSteps+" ray steps");
            }finally{PlayerGraphics.ApplyPacked(choices);camera.targetTexture=target;RenderTexture.active=previous;RenderTexture.ReleaseTemporary(frame);if(a)Destroy(a);if(b)Destroy(b);if(control)Destroy(control);}
        }
        void IsolatedStarTest(){
            const int width=144,height=96;
            var original=new Texture2D(width,height,TextureFormat.RGBA32,false,false){filterMode=FilterMode.Bilinear,wrapMode=TextureWrapMode.Clamp};
            var pixels=new Color32[width*height];for(int y=0;y<height;y++)for(int x=0;x<width;x++){
                byte c=(byte)(x>15&&x<78&&y<12+x*.53f?202:0);pixels[y*width+x]=new Color32(c,c,c,255);
            }
            pixels[28*width+116]=new Color32(255,246,221,255);pixels[72*width+101]=new Color32(170,199,255,255);
            original.SetPixels32(pixels);original.Apply(false);
            var filtered=new Material(PlayerGraphics.EdgeShader);var prev=RenderTexture.active;var canvas=RenderTexture.GetTemporary(width,height,0,RenderTextureFormat.ARGB32,RenderTextureReadWrite.sRGB,1);
            var a=new Texture2D(width,height,TextureFormat.RGB24,false,false);var b=new Texture2D(width,height,TextureFormat.RGB24,false,false);
            try{
                Graphics.Blit(original,canvas);RenderTexture.active=canvas;a.ReadPixels(new Rect(0,0,width,height),0,0);a.Apply(false);
                Graphics.Blit(original,canvas,filtered);RenderTexture.active=canvas;b.ReadPixels(new Rect(0,0,width,height),0,0);b.Apply(false);
                int changed=ChangedPixels(a,b,3),starDelta=0;var off=a.GetPixels32();var on=b.GetPixels32();
                for(int y=0;y<height;y++)for(int x=90;x<width;x++){int i=y*width+x;starDelta+=Math.Abs(off[i].r-on[i].r)+Math.Abs(off[i].g-on[i].g)+Math.Abs(off[i].b-on[i].b);}
                Check(changed>25 && starDelta==0,"FXAA smooths "+changed+" oblique test-edge pixels; two isolated star colors and all neighbouring black pixels match exactly");
                double raw=0,filteredError=0;int examined=0;float panel=Mathf.GammaToLinearSpace(202/255f);
                for(int x=24;x<67;x++)for(int y=14;y<56;y++){
                    if(Math.Abs(y-12-.53*x)>1.6)continue;
                    int coverage=0;const int grid=32;
                    for(int j=0;j<grid;j++)for(int i=0;i<grid;i++)
                        if(y+(j+.5)/grid-.5<12+.53*(x+(i+.5)/grid-.5))coverage++;
                    double truth=panel*coverage/(grid*grid);
                    int index=y*width+x;raw+=Math.Pow(Mathf.GammaToLinearSpace(off[index].r/255f)-truth,2);
                    filteredError+=Math.Pow(Mathf.GammaToLinearSpace(on[index].r/255f)-truth,2);examined++;
                }
                Check(filteredError<raw*.94,"Against 1,024 subpixel samples per slanted-edge pixel, measured linear RMS improves from "+
                    Math.Sqrt(raw/examined).ToString("F4")+" (Off) to "+Math.Sqrt(filteredError/examined).ToString("F4")+" (FXAA)");
            }finally{RenderTexture.active=prev;RenderTexture.ReleaseTemporary(canvas);Destroy(filtered);Destroy(original);Destroy(a);Destroy(b);}
        }
        IEnumerator GraphicsSurvey(){
            int initial=PlayerGraphics.Choices;
            try{
                Check(PlayerGraphics.CanFilter&&QualitySettings.antiAliasing==0,"Final FXAA shader is present and hardware multisampling is disabled");
                var passes=person.eye.GetComponents<MonoBehaviour>();Check(Array.IndexOf(passes,person.eye.GetComponent<PassengerOptics>())<Array.IndexOf(passes,person.CabinEdges),"Cabin grading and item focus precede edge filtering; IMGUI renders afterwards");
                IsolatedStarTest();
                ride.Seek(105);person.Place(new Vector3(-.56f,.034f,2.27f),9,4);yield return null;
                GraphicsPair("01-cabin-aa",person.eye,PlayerGraphics.Option.Edges,0,1);
                GraphicsPair("02-contact",person.eye,PlayerGraphics.Option.Contact,0,1);
                ride.Seek(15.6);yield return null;
                GraphicsPair("03-cast-shadows",person.eye,PlayerGraphics.Option.Shadows,0,2);
                GraphicsPair("04-hard-soft",person.eye,PlayerGraphics.Option.Shadows,1,2);
                ride.Seek(171);person.Place(new Vector3(.65f,.03f,3.03f),-76,5);person.Inspect(ride.props["mug"]);yield return new WaitForSecondsRealtime(.2f);
                GraphicsPair("05-held-aa",person.eye,PlayerGraphics.Option.Edges,0,1);person.CloseInspect();
                ride.Seek(76);person.SetWatch(5);yield return null;
                GraphicsPair("06-guide-optic-aa",ride.exterior.SensorCamera,PlayerGraphics.Option.Edges,0,1);
                ride.Seek(102);person.SetWatch(4);yield return null;
                GraphicsPair("07-cloud-detail",ride.exterior.SensorCamera,PlayerGraphics.Option.Atmosphere,0,2);
            }finally{PlayerGraphics.ApplyPacked(initial);if(person.Examined)person.CloseInspect();person.SetWatch(0);ride.Seek(0);}
        }
        IEnumerator SoftwareSurvey(){
            Check(Passenger.SoftwareGraphics,"Unity identifies the actual software adapter: "+SystemInfo.graphicsDeviceName);
            Check(PlayerGraphics.Edges==0&&PlayerGraphics.Shadows<=1&&PlayerGraphics.Atmosphere==0&&PlayerGraphics.Contact==0,"Software starts with single-sample edges, bounded shadows and low atmospheric detail");
            PlayerGraphics.Set(PlayerGraphics.Option.Atmosphere,2,false);PlayerGraphics.Set(PlayerGraphics.Option.Contact,1,false);PlayerGraphics.Set(PlayerGraphics.Option.Shadows,2,false);
            Check(PlayerGraphics.Atmosphere==0&&PlayerGraphics.Contact==0&&QualitySettings.shadows!=ShadowQuality.All,"Software requests cannot exceed the device budget");
            PlayerGraphics.Set(PlayerGraphics.Option.Edges,1,false);
            var camera=person.eye;var old=camera.targetTexture;var active=RenderTexture.active;
            var frame=RenderTexture.GetTemporary(448,280,24,RenderTextureFormat.ARGB32,RenderTextureReadWrite.sRGB,1);
            try{
                camera.targetTexture=frame;float now=Time.realtimeSinceStartup;const int frames=5;
                for(int j=0;j<frames;j++){
                    var shot=ReadFinishFrame(camera,frame,RegisteredFinish.FinishWeight);
                    if(j==frames-1)File.WriteAllBytes(Path.Combine(output,"graphics/native-software.jpg"),shot.EncodeToJPG(90));
                    Destroy(shot);yield return null;
                }
                Check(person.CabinEdges.SourceSamples==1&&person.CabinEdges.LastFilteredFrame>=0&&ride.exterior.PassengerAtmosphereSteps==24,
                    "Software FXAA rendered the single-sample cabin ("+person.CabinEdges.SourceSamples+" sample, "+ride.exterior.PassengerAtmosphereSteps+" volume steps). "+
                    (frames/(Time.realtimeSinceStartup-now)).ToString("0.0")+" fully read-back frames/sec at 448×280");
            }finally{camera.targetTexture=old;RenderTexture.active=active;RenderTexture.ReleaseTemporary(frame);}
            PlayerGraphics.RestoreDefaults();
        }
        IEnumerator InstrumentDisplaySurvey(){
            var system=ride.systems;ride.Seek(8);if(!system.Electrical)ride.Use(ride.props["diagnostic_screen"],person);
            Texture2D diagnostic=null;
            foreach(var renderer in ride.props["diagnostic_screen"].GetComponentsInChildren<MeshRenderer>())
                foreach(var mat in renderer.sharedMaterials)if(mat&&mat.name=="Pixels_Diagnostic")diagnostic=mat.mainTexture as Texture2D;
            if(!diagnostic)foreach(var renderer in FindObjectsByType<MeshRenderer>(FindObjectsInactive.Exclude)){
                foreach(var mat in renderer.sharedMaterials)if(mat&&mat.name=="Pixels_Diagnostic"){diagnostic=mat.mainTexture as Texture2D;break;}
                if(diagnostic)break;
            }
            Check(diagnostic&&diagnostic.mipmapCount>1&&diagnostic.filterMode==FilterMode.Trilinear&&diagnostic.anisoLevel>=4,"Diagnostic display has antialiased lettering and a trilinear anisotropic mip chain");
            Vector3 eye=new Vector3(.08f,1.42f,4.21f),target=ride.props["diagnostic_screen"].Focus;
            Vector3 aim=(target-eye).normalized;
            person.Place(eye-person.eye.transform.localPosition,Mathf.Atan2(aim.x,aim.z)*Mathf.Rad2Deg,-Mathf.Asin(aim.y)*Mathf.Rad2Deg);
            float previous=system.BusVoltage;var original=diagnostic.GetPixels32();
            yield return Photo("graphics/08-feeder-before");
            ride.Use(ride.props["guide_flood"],person);var updated=diagnostic.GetPixels32();int count=0;
            for(int j=0;j<original.Length;j++)if(!original[j].Equals(updated[j]))count++;
            Check(Mathf.Abs(previous-system.BusVoltage)>.15f&&count>100,"Guide flood changes the feeder from "+previous.ToString("0.00")+" to "+system.BusVoltage.ToString("0.00")+" V and rewrites "+count+" addressable diagnostic pixels");
            yield return Photo("graphics/09-feeder-after");
            ride.Use(ride.props["guide_flood"],person);ride.Use(ride.props["diagnostic_screen"],person);
            ride.Use(ride.props["service_cabinet"],person);yield return new WaitForSecondsRealtime(.85f);
            ride.Use(ride.props["key_seals"],person);ride.Use(ride.props["test_seal"],person);yield return new WaitForSecondsRealtime(1.15f);
            float peak=system.IndicatedPressure;Check(ride.DisplayMode==2&&peak>.10f,"The service seal stimulus drives the pressure transducer above 0.10 kPa on the selected seal page");
            eye=new Vector3(.58f,1.40f,4.42f);aim=(ride.props["nav_screen"].Focus-eye).normalized;
            person.Place(eye-person.eye.transform.localPosition,Mathf.Atan2(aim.x,aim.z)*Mathf.Rad2Deg,-Mathf.Asin(aim.y)*Mathf.Rad2Deg);
            yield return new WaitForSecondsRealtime(1.8f);
            Check(system.IndicatedPressure<.01f,"The pressure sample returns to baseline while its recent peak remains in the transducer history");
            yield return Photo("graphics/11-pressure-history");
            ride.Use(ride.props["service_cabinet"],person);ride.Use(ride.props["key_route"],person);
            ride.Seek(185);ride.Use(ride.props["guide_flood"],person);person.SetWatch(5);yield return new WaitForSecondsRealtime(.38f);
            yield return Photo("graphics/10-guide-drive",ride.exterior.SensorCamera);
            person.SetWatch(0);ride.Use(ride.props["guide_flood"],person);
        }
    }
}
