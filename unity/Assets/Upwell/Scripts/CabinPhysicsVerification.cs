using System;
using System.Collections;
using UnityEngine;

namespace Upwell {
    public sealed partial class RideVerification {
        IEnumerator FurnishingContacts(){
            ride.Seek(0);var quilt=Array.Find(FindObjectsByType<FurnishingSurface>(FindObjectsInactive.Exclude),f=>f.IsQuilt);
            var mug=ride.props["mug"];int previous=quilt.Contacts;
            Vector3 point=quilt.TouchPoint;ride.Release(mug,point+Vector3.up*.24f,Quaternion.identity,Vector3.down*.12f,Vector3.zero);
            yield return new WaitForSecondsRealtime(.95f);
            Check(quilt.Contacts>previous&&mug.GetComponent<LooseItemBody>().Impacts>0,"Released drink equipment strikes and transfers momentum to the quilt surface");
            ride.Pickup(mug);
            var drawer=ride.props["locker_drawer"];var card=ride.props["access_card"];drawer.SetTarget(.70f);
            yield return new WaitForSecondsRealtime(.45f);Physics.SyncTransforms();
            Vector3 drop=Vector3.zero;bool trayFound=false;
            foreach(float x in new[]{.24f,.31f,.15f,.39f})foreach(float z in new[]{.04f,-.12f,.13f}){
                var test=drawer.transform.TransformPoint(new Vector3(x,.155f,z));
                if(Physics.Raycast(test,Vector3.down,out var hit,.30f,1<<Passenger.PropRay,QueryTriggerInteraction.Ignore)&&hit.collider.GetComponentInParent<TransitProp>()==drawer&&hit.normal.y>.85f){
                    drop=hit.point;trayFound=true;break;
                }if(trayFound)break;
            }
            Check(trayFound,"The physical locker tray has a load-bearing upward-facing surface");
            ride.Release(card,drop+Vector3.up*.025f,Quaternion.identity,Vector3.zero,Vector3.zero);
            yield return new WaitForSecondsRealtime(.42f);
            var loose=card.GetComponent<LooseItemBody>();var start=loose.Body.position;var startTray=drawer.transform.position;
            for(int i=1;i<=30;i++){drawer.SetTarget(Mathf.Lerp(.70f,.97f,i/30f));yield return new WaitForFixedUpdate();yield return new WaitForFixedUpdate();}
            yield return new WaitForSecondsRealtime(.18f);
            Vector3 delta=drawer.transform.position-startTray;Vector3 travel=loose.Body.position-start;
            Check(delta.x<-.075f&&travel.x<-.04f&&Mathf.Abs(travel.y)<.08f,
                "Released credential rides the kinematic drawer through a gentle slide (tray "+delta.x.ToString("F3")+" m, key "+travel.x.ToString("F3")+" m)");
            ride.Pickup(card);
        }
        IEnumerator CabinPhysicsSurvey(){
            var bench=ride.experiments;
            Check(bench&&bench.proofMass&&bench.upperSpring&&bench.lowerSpring&&bench.fluid&&bench.fluid.volume,"Surveyed proof-mass, two springs and enclosed optical instrument are installed");
            foreach(string id in new[]{"accelerometer","accel_test","capillary_cell","capillary_primer"}){
                var device=ride.props[id];Check(Reachable(device,device.room=="observation"?3.8f:0),"Passenger can aim directly at "+id);
            }
            var fluid=bench.fluid;var mass=ride.props["accelerometer"];var chamber=ride.props["capillary_cell"];var test=ride.props["accel_test"];
            ride.Seek(0);bench.Advance(.20f);
            float groundReading=bench.IndicatedG;var earthMass=bench.proofMass.position;
            Check(groundReading>.98f&&groundReading<1.01f&&fluid.Bond>900&&fluid.GasCenter.y>23,"Launch gravity sets the signed mass scale and the upper gas cap");
            Check(Mathf.Abs(fluid.MeasuredGasFraction-.23f)<.0002f,"Launch reservoir preserves its measured gas charge across nine depth slices");
            person.Place(new Vector3(-.70f,.04f,3.86f),0,10);person.Inspect(mass);yield return Photo("24-proof-mass-anchor");
            bench.HoldControl(test);bench.Advance(.36f);
            Check(bench.Preload>.095f&&bench.IndicatedG>groundReading+.06f&&test.Position>.97f,"Held calibration plunger travels 9 mm and physically loads the proof mass");
            Check(Math.Abs(ride.Forces.Down/9.80665-groundReading)<.004,"Calibrating the instrument leaves the actual car load unchanged");
            yield return Photo("25-proof-mass-calibration");bench.ReleaseControl(test);bench.Advance(1.4f);
            Check(bench.Preload<.002&&Math.Abs(bench.IndicatedG-groundReading)<.005,"Released plunger and opposing springs return to the unforced reading");
            person.CloseInspect();person.Place(new Vector3(.55f,.04f,.55f),89,8);person.Inspect(chamber);
            yield return Photo("26-capillary-anchor");
            ride.Seek(351);bench.Advance(.25f);
            Check(bench.IndicatedG<-.004f&&fluid.GasCenter.y<-.8f&&Mathf.Abs(fluid.MeasuredGasFraction-.23f)<.0002f,"Terminal braking reverses the pointer and moves the gas cap toward the other wall");
            yield return Photo("27-capillary-braking");
            ride.Seek(360);bench.Advance(.25f);var settled=fluid.GasCenter;
            Check(Mathf.Abs(bench.IndicatedG)<.002f&&bench.proofMass.position.y-earthMass.y>.158f&&fluid.Bond<.08f,"The geostationary mass hangs at zero and the bubble occupies its interior trap (g "+bench.IndicatedG.ToString("F5")+", travel "+(bench.proofMass.position.y-earthMass.y).ToString("F4")+" m, Bo "+fluid.Bond.ToString("F4")+")");
            Check(Mathf.Abs(fluid.MeasuredGasFraction-.23f)<.0002f&&(settled-new Vector2(.08f,.035f)).magnitude<.02f,"The low-g pocket conserves volume and remains attached to the capillary trap");
            yield return Photo("28-capillary-docked");ride.Use(ride.props["capillary_primer"],person);bench.Advance(.20f);
            Check(bench.PrimeCount>0&&Mathf.Abs(fluid.Slosh)>.09f&&Vector2.Distance(fluid.GasCenter,settled)>.065f,"A physical primer stroke displaces the confined low-g gas interface");
            yield return Photo("29-capillary-primer");bench.Advance(1.5f);bench.Advance(1.5f);bench.Advance(1.5f);
            Check(Vector2.Distance(fluid.GasCenter,settled)<.014f&&Mathf.Abs(fluid.MeasuredGasFraction-.23f)<.0002f,"The sealed primer disturbance decays without loss of charge");
            person.CloseInspect();person.Place(new Vector3(-.70f,.04f,3.86f),0,10);person.Inspect(mass);
            yield return Photo("30-proof-mass-docked");ride.Seek(350);bench.Advance(.25f);yield return Photo("34-proof-mass-braking");
            ride.Seek(244);bench.Advance(.25f);yield return Photo("37-proof-mass-orbital-night");
            float initialLight=bench.scaleLamp.intensity;ride.Use(ride.props["panel_gain"],person);bench.Advance(.02f);
            Check(Mathf.Abs(bench.scaleLamp.intensity-initialLight)>.1f&&bench.scaleLamp.range<=.53f,"Panel luminance also drives the localized mechanical scale light");
            for(int j=0;j<4;j++)ride.Use(ride.props["panel_gain"],person);person.CloseInspect();
            var textiles=FindObjectsByType<FurnishingSurface>(FindObjectsInactive.Exclude);
            Check(textiles.Length==4,"Separate quilt, curtain and two terminated service loops have compliant skins");
            FurnishingSurface quilt=null,curtain=null,cable=null;
            foreach(var f in textiles){if(f.IsQuilt)quilt=f;else if(f.IsCurtain)curtain=f;else if(f.partId=="loom_service_power")cable=f;}
            ride.Seek(0);
            for(int i=0;i<10;i++)foreach(var f in textiles)f.Advance(.10f);
            var groundQuilt=quilt.TouchPoint;var groundCable=cable.TouchPoint;var torso=quilt.Sample(.52f,.37f);
            var bunk=ride.props["bunk"];person.Rest(bunk);for(int i=0;i<14;i++)quilt.Advance(.10f);
            Check(torso.y-quilt.Sample(.52f,.37f).y>.015f,"The occupied quilt compresses under the passenger’s actual apparent weight");
            person.Rise();for(int i=0;i<11;i++)quilt.Advance(.10f);
            person.Place(new Vector3(.28f,.04f,.34f),-90,10);person.Inspect(bunk);yield return Photo("35-quilt-anchor");
            ride.Seek(360);
            for(int i=0;i<15;i++)foreach(var f in textiles)f.Advance(.10f);
            yield return Photo("31-berth-quilt");person.CloseInspect();
            Check(Vector3.Distance(groundQuilt,quilt.TouchPoint)>.012f&&Vector3.Distance(groundCable,cable.TouchPoint)>.006f,"Quilt loft and retained cable curvature respond to the unloading carriage");
            foreach(var f in textiles)Check(f.PinError<.00001f,f.partId+" keeps its surveyed pins and sockets attached");
            var rail=FindFirstObjectByType<CurtainHandle>();var screen=ride.props["privacy_curtain"];float from=screen.Position;
            person.SetWatch(7);Physics.SyncTransforms();
            Check(person.FindFocus()==screen&&person.RailFocus==rail,"Reticle over the physical black handle selects the moving carrier instead of the cloth");
            float width=rail.ScreenTravel(person.eye);person.BeginRail(person.RailFocus);person.DragRail(0,74);person.ReleaseRail(true);
            Check(Mathf.Abs(screen.Position-from)<.002f,"A purely vertical grip gesture leaves the curtain at its captured position");
            person.BeginRail(rail);person.DragRail(width*.36f,1);person.ReleaseRail(true);yield return new WaitForSecondsRealtime(.35f);
            Check(Mathf.Abs(screen.Position-.36f)<.007f&&Mathf.Abs(curtain.RunnerTravel-1.86f*.36f)<.012f,"Releasing a horizontal drag leaves the handle and its carriers parked partway");
            yield return Photo("38-curtain-handle-partway");
            person.SetWatch(7);Check(person.FindFocus()==screen&&person.RailFocus==rail,"A partially drawn black grip remains directly reachable at its new position");
            person.BeginRail(rail);person.DragRail(rail.ScreenTravel(person.eye)*1.32f,0);person.ReleaseRail(true);yield return new WaitForSecondsRealtime(.22f);
            Check(screen.Position>.999f&&curtain.RunnerTravel>1.85f,"Dragging the rigid grip to its forward end seats the drawn stop");
            person.SetWatch(7);person.BeginRail(rail);person.DragRail(-rail.ScreenTravel(person.eye)*1.42f,0);person.ReleaseRail(true);
            yield return new WaitForSecondsRealtime(.22f);Check(screen.Position<.001f&&curtain.RunnerTravel<.002f,"Reversing the horizontal drag returns the grip to its stowed stop");person.SetWatch(0);
            var hem=curtain.TouchPoint;Check(curtain.Grip(hem),"A passenger can take hold of the real privacy-hem surface");curtain.Pull(Vector3.right*.115f);
            for(int i=0;i<6;i++)curtain.Advance(.06f);Check(Vector3.Distance(hem,curtain.TouchPoint)>.022f&&curtain.PinError<.00001f&&screen.Position<.001f,"Dragging the hem displaces the loose pleats while the rail stays fixed");curtain.Release();
            ride.Use(ride.props["privacy_curtain"],person);yield return new WaitForSecondsRealtime(1.25f);
            Check(curtain.runners.Length==9&&curtain.RunnerTravel>.70f,"The moving stile and eight carriers extend the actual curtain along its rail");
            person.Place(new Vector3(.19f,.04f,.36f),-88,2);yield return Photo("32-extended-curtain");
            ride.Seek(103);yield return Photo("36-curtain-daylight");
            ride.Use(ride.props["privacy_curtain"],person);ride.Use(ride.props["service_cabinet"],person);yield return new WaitForSecondsRealtime(.85f);
            var wire=cable.TouchPoint;Check(cable.Brush(wire),"Opened cabinet exposes a pluckable terminated electrical loop");
            cable.Advance(.045f);Check(Vector3.Distance(wire,cable.TouchPoint)>.001f&&cable.PinError<.00001f,"Plucked service loop recoils between the fixed cable glands");
            person.Place(new Vector3(.45f,.035f,-3.46f),92,0);person.Inspect(ride.props["service_cabinet"]);yield return Photo("33-compliant-service-loops");person.CloseInspect();
            ride.Use(ride.props["service_cabinet"],person);ride.Seek(76);
        }
    }
}
