using System;
using System.Collections;
using System.IO;
using System.Linq;
using UnityEngine;

namespace Upwell {
    public sealed partial class RideVerification {
        void PortraitOptics(string name,bool earth){
            var rig=ride.exterior;var cam=rig.SensorCamera;var previous=cam.targetTexture;var active=RenderTexture.active;
            var target=RenderTexture.GetTemporary(720,1200,24,RenderTextureFormat.ARGB32,RenderTextureReadWrite.sRGB);
            try{
                cam.targetTexture=target;cam.aspect=.60f;rig.SetProgress(ride.Seconds,ride.PreciseAltitude,ride.Velocity,0);
                if(earth){
                    float radius=Mathf.Asin(6371f/(6371f+ride.Altitude));
                    float share=Mathf.Tan(radius)/(Mathf.Tan(cam.fieldOfView*.5f*Mathf.Deg2Rad)*cam.aspect);
                    Check(Mathf.Abs(share-.78f)<.0025f,"Portrait Earth optics preserve 78% of the shorter dimension across the full planetary disc");
                }else{
                    var h=rig.habitat;var center=cam.WorldToViewportPoint(h.position);
                    Check(center.z>0&&Mathf.Abs(center.x-.5f)<.02&&Mathf.Abs(center.y-.5f)<.02,"Portrait colony optics retains the settlement in the optical centre");
                }
                var image=ReadFinishFrame(cam,target,RegisteredFinish.FinishWeight);
                File.WriteAllBytes(Path.Combine(output,name+".jpg"),image.EncodeToJPG(92));Destroy(image);
            }finally{cam.targetTexture=previous;cam.ResetAspect();RenderTexture.active=active;RenderTexture.ReleaseTemporary(target);rig.SetProgress(ride.Seconds,ride.PreciseAltitude,ride.Velocity,0);}
        }
        IEnumerator PassageMoments(){
            string[] ids={"liftoff","pier","crest","passenger","stars","freight","terminator","night","sunrise","colony","receiving","bubble","dock"};
            int[] watches={1,6,4,8,9,8,3,6,3,10,4,0,0};
            var sensor=ride.exterior.SensorCamera;
            bool preference=person.FollowsMomentView;
            var aisle=new Vector3(.17f,.037f,.43f);person.SetWatch(0);person.Place(aisle,152,7);ride.Seek(0);
            person.SetFollowMomentView(true);
            Check(person.MomentCount==ids.Length&&Enumerable.Range(0,ids.Length).All(i=>person.MomentAt(i).id==ids[i]),"Unity loads all 13 named moments from the shared route survey");
            person.ToggleMoments();Check(person.MomentMenuVisible,"Passage list opens in the normal passenger controller");
            person.GoToMoment(0);Check(!person.MomentMenuVisible&&person.LastMoment=="liftoff","Selecting a departure closes the moment list");
            person.StepMoment(-1);Check(person.MomentIndex==0&&ride.Seconds<.1,"Previous at departure stays at the equatorial anchor");
            try{
                for(int i=0;i<ids.Length;i++){
                    if(i>0)person.StepMoment(1);
                    var m=person.MomentAt(i);
                    Check(person.MomentIndex==i&&Math.Abs(ride.Seconds-m.start)<.05&&person.SelectedView==watches[i],
                        "Selecting "+m.name+" seeks its lead-in and physical viewpoint");
                    ride.Seek(m.@event);yield return null;
                    bool external=watches[i]==3||watches[i]==4||watches[i]>=8;
                    if(external){
                        Check(sensor.enabled&&!person.eye.enabled&&sensor.targetTexture==null&&sensor.pixelWidth==Screen.width&&sensor.pixelHeight==Screen.height,
                            m.name+" renders directly to the player display at "+sensor.pixelWidth+"×"+sensor.pixelHeight);
                        if(i==2)Check(sensor.fieldOfView>48&&sensor.transform.forward.y<.1f&&sensor.transform.forward.y>-.37f,"Cloud crest sees the sky and the top of the deck together through a wide forward lens");
                        if(i==3||i==5){
                            var passing=ride.exterior.lastPass;var envelope=ride.exterior.CounterEnvelope;var center=sensor.WorldToViewportPoint(envelope.center);
                            Check(passing.gameObject.activeInHierarchy&&center.z>0&&Mathf.Abs(center.x-.5f)<.055f&&Mathf.Abs(center.y-.5f)<.055f,m.name+" tracks the actual descending car on the other ribbon");
                            bool fits=true;for(int k=0;k<8;k++){var corner=envelope.center+Vector3.Scale(envelope.extents,new Vector3((k&1)==0?-1:1,(k&2)==0?-1:1,(k&4)==0?-1:1));var point=sensor.WorldToViewportPoint(corner);fits&=point.x>.045f&&point.x<.955f&&point.y>.045f&&point.y<.955f;}
                            Check(fits,m.name+" keeps both endcaps and the outermost racks inside the lens");
                        }
                        if(i==4)Check(sensor.transform.forward.y>.05f&&sensor.transform.forward.y<.4f&&sensor.fieldOfView>44,"Star-field optics compose dark sky above the atmospheric limb");
                        if(i==6||i==8)Check(Vector3.Dot(sensor.transform.forward,Vector3.down)>.98f,"Earth optics follows the actual nadir disc during "+m.name);
                        if(i==9){
                            var h=ride.exterior.habitat;var orbital=ride.exterior.Orbital;
                            Check(h.gameObject.activeSelf&&Vector3.Dot(sensor.transform.forward,(h.position-sensor.transform.position).normalized)>.999f,"Colony optics frames the physical settlement as its range closes");
                            Check(orbital.Rotor&&orbital.Train&&orbital.Scanner&&orbital.Rotor.GetComponentsInChildren<MeshRenderer>(true).Any(r=>r.enabled),"Habitat bearings, valley train and the receiving optical scanner are live scene objects");
                        }
                        if(i==10)Check(ride.exterior.arrivalBay.DockDistance<49&&sensor.transform.forward.y>.84f,"Receiving optics looks into the approaching capture throat");
                        yield return Photo("moment-"+m.id,sensor);
                        Check(ride.exterior.SensorRadianceWidth>=(ride.PreciseAltitude>95?1200:900),m.name+" samples high-resolution live radiance for the external optics");
                        if(i==6||i==9)PortraitOptics("portrait-"+m.id,i==6);
                    }else {
                        if(i==11){
                            Check(person.Examined==ride.props["capillary_cell"]&&person.eye.enabled,"The galley moment uses its actual in-cabin optical vessel");
                            yield return new WaitForSecondsRealtime(2.4f);
                            Check(ride.Progress==1&&ride.experiments.fluid.GasCenter.magnitude<.40f,"At the end of the galley moment the gas pocket releases from the lower wall into the capillary trap");
                        }
                        if(i==7||i==11||i==12)yield return Photo("moment-"+m.id);
                    }
                    if(i<ids.Length-1)ride.Seek(m.start);
                }
                person.StepMoment(1);Check(person.MomentIndex==12&&ride.Seconds==360,"The final Next input holds at the docking stop");
                person.SetWatch(1);var dockEye=person.eye.transform.position;person.SetWatch(10);ride.exterior.SetProgress(360,ride.PreciseAltitude,0,0);
                Check(ride.exterior.OnHabitatRelay&&Vector3.Distance(sensor.transform.position,ride.exterior.Orbital.HabitatRelay.position)<.005f,"The optional dock telescope hands the image to the real Aster hub optical head");
                yield return Photo("moment-hub-relay",sensor);person.SetWatch(1);
                Check(Vector3.Distance(dockEye,person.eye.transform.position)<.005f,"Leaving the hub relay returns to the unchanged passenger glazing sightline");
                ride.SecureTurn();ride.SecureTurn();ride.SecureTurn();
                person.StepMoment(-1);
                Check(person.LastMoment=="bubble"&&person.Examined==ride.props["capillary_cell"]&&!ride.Docked,"Reverse from hard dock releases the clamp and replays the galley lead-in");
                person.SetFollowMomentView(false);var tracked=person.eye.transform.position;person.StepMoment(-1);
                Check(person.LastMoment=="receiving"&&person.Examined==ride.props["capillary_cell"]&&Vector3.Distance(tracked,person.eye.transform.position)<.001f,"Disabling suggested views preserves the passenger's current fixture while changing route time");
                person.CloseInspect();person.SetWatch(0);ride.Seek(0);person.Place(aisle,152,7);person.SetFollowMomentView(true);person.GoToMoment(3);person.SetWatch(0);
                Check((new Vector2(person.transform.position.x-aisle.x,person.transform.position.z-aisle.z)).magnitude<.025f,"Returning from a suggested sensor restores the passenger's original aisle position");
                var mug=ride.props["mug"];person.Inspect(mug);var held=person.CarriedModel;person.GoToMoment(8);
                Check(person.Examined==mug&&person.CarriedModel==held&&ride.Seconds==person.MomentAt(8).start,"Manual inspection keeps the physical item in hand while time changes");
                var radiators=mug.GetComponentsInChildren<MeshRenderer>(true).SelectMany(r=>r.sharedMaterials).Where(m=>m).Select(m=>m.name).ToArray();
                Check(radiators.Contains("Vessel_Enamel")&&radiators.Any(n=>n.Contains("Grip")||n.Contains("Rubber")||n.Contains("Elastomer")),"The operated galley vessel carries its enamel and elastomer handgrip materials");
                var colliders=mug.GetComponentsInChildren<MeshCollider>(true);int capped=0;
                foreach(var delta in new[]{Vector3.zero,Vector3.right*.012f,Vector3.left*.012f,Vector3.forward*.012f}){
                    var ray=new Ray(mug.transform.position+delta+Vector3.down*.095f,Vector3.up);
                    if(colliders.Any(c=>c.Raycast(ray,out var hit,.10f)&&hit.normal.y<-.4f))capped++;
                }
                Check(capped==4,"The enamel vessel has a physically closed magnetic foot across its centre and annulus");
                ride.Seek(105);person.Place(new Vector3(-.12f,.03f,3.32f),176,3);person.RotateItem(0,97);
                yield return new WaitForSecondsRealtime(.30f);yield return Photo("held-mug-magnetic-foot");
                person.CloseInspect();person.GoToMoment(0);person.SetWatch(0);
            }finally{person.SetFollowMomentView(preference);ride.Seek(0);}
        }
    }
}
