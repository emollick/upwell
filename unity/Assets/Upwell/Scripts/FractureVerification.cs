using System;
using System.Collections;
using System.IO;
using UnityEngine;

namespace Upwell {
    public sealed partial class RideVerification {
        #if UNITY_WEBGL && !UNITY_EDITOR
        [System.Runtime.InteropServices.DllImport("__Internal")]static extern void UpwellCartridgeAudit(string focus,float yaw,float pitch,float distance,int card,int unlocked,float drawer,int inspecting,
            float force,float peak,float stroke,int broken,int breaks,int exchanges,float blinds,int contacts,float height,float g,float escape,float seconds,int moving);
        [System.Runtime.InteropServices.DllImport("__Internal")]static extern void UpwellCartridgeRestAudit(string detail);
        // Local verification reads the state of the actual rig. All actions still use the passenger controls.
        public void ReadCartridgeTarget(string id){
            var p=GetComponent<Passenger>();var transit=p.ride;var c=transit.fracture;var eye=p.eye.transform;
            Vector3 target;
            if(id=="crossway")target=new Vector3(.20f,eye.position.y,2.39f);
            else if(id=="berth-aisle")target=new Vector3(.23f,eye.position.y,.25f);
            else if(id=="reader-aisle")target=new Vector3(.20f,eye.position.y,-.78f);
            else if(id=="service-aisle")target=new Vector3(-.64f,eye.position.y,-4.18f);
            else if(transit.props.TryGetValue(id,out var prop))target=prop.Focus;
            else target=c.ViewCenter;
            Vector3 d=(target-eye.position).normalized,forward=eye.forward;
            float yaw=Mathf.DeltaAngle(Mathf.Atan2(forward.x,forward.z)*Mathf.Rad2Deg,Mathf.Atan2(d.x,d.z)*Mathf.Rad2Deg);
            float pitch=(Mathf.Asin(forward.y)-Mathf.Asin(d.y))*Mathf.Rad2Deg;
            int moving=0;if(c.Broken)foreach(var shard in c.Fragments)if(shard.linearVelocity.sqrMagnitude>.0001f)moving++;
            UpwellCartridgeAudit(p.Focus?p.Focus.id:"",yaw,pitch,Vector3.Distance(eye.position,target),transit.Has("access_card")?1:0,
                transit.Unlocked?1:0,transit.props["locker_drawer"].Position,p.Examined&&FractureCartridge.IsInstrument(p.Examined.id)?1:0,
                c.LoadNewton,c.PeakNewton,c.Stroke,c.Broken?1:0,c.BreakCount,c.ExchangeCount,c.ShutterCoverage,c.Impacts,
                c.Broken?ShardHeight(c):0,(float)transit.Forces.GravityG,c.EnclosureError,(float)transit.Seconds,moving);
            if(c.Broken)UpwellCartridgeRestAudit(string.Join(" | ",Array.ConvertAll(c.Fragments,b=>b.GetComponent<FractureContact>().RestReading(b))));
        }
        #endif
        static float ShardHeight(FractureCartridge cell){
            float height=0,mass=0;foreach(var body in cell.Fragments){height+=body.mass*cell.transform.InverseTransformPoint(body.worldCenterOfMass).y;mass+=body.mass;}
            return height/mass;
        }
        void CompleteMagazine(FractureCartridge cell){
            Check(cell.Reload(),"The magazine exchanges a released spent specimen");
            cell.Advance(.37f);Check(cell.ShutterCoverage>.995f&&cell.Broken,"Exchange blinds fully close before releasing the spent insert");
            cell.Advance(.15f);Check(cell.ShutterCoverage>.995f&&!cell.Broken&&cell.PeakNewton==0,"The fresh intact coupon replaces its shards behind the closed blinds");
            cell.Advance(.51f);Check(!cell.Reloading&&cell.ShutterCoverage<.001f,"The exchange clears the guard for the next test");
        }
        void VerifyScaleBacklight(FractureCartridge cell){
            Material printed=null;
            foreach(var renderer in cell.GetComponentsInChildren<Renderer>())foreach(var m in renderer.sharedMaterials)
                if(m&&m.name=="FC_Markings")printed=m;
            Check(printed&&printed.HasProperty("_DialLume")&&printed.GetTexture("_DialLume"),"Calibrated dial has its registered independent paper backlight");
            var original=printed.GetTexture("_DialLume");var cam=person.eye;var prior=cam.targetTexture;var active=RenderTexture.active;
            var frame=RenderTexture.GetTemporary(1100,720,24,RenderTextureFormat.ARGB32,RenderTextureReadWrite.sRGB,1);
            try{
                cam.targetTexture=frame;cam.Render();var center=cam.WorldToViewportPoint(cell.transform.Find("fracture_needle").position);
                printed.SetTexture("_DialLume",Texture2D.blackTexture);var a=ReadFinishFrame(cam,frame,RegisteredFinish.FinishWeight);
                printed.SetTexture("_DialLume",original);var b=ReadFinishFrame(cam,frame,RegisteredFinish.FinishWeight);
                var before=a.GetPixels32();var after=b.GetPixels32();int lifted=0,other=0;
                for(int y=0;y<frame.height;y++)for(int x=0;x<frame.width;x++){
                    int n=y*frame.width+x,d=(after[n].r-before[n].r)+(after[n].g-before[n].g)+(after[n].b-before[n].b);
                    if(d<12)continue;
                    if(Mathf.Abs(x-center.x*frame.width)<frame.width*.09f&&Mathf.Abs(y-center.y*frame.height)<frame.height*.15f)lifted++;else other++;
                }
                Destroy(a);Destroy(b);Check(lifted>300&&other<lifted/8,"Under the 22-second tower shadow the registered dial light lifts "+lifted+" dial pixels and "+other+" outside its measured face");
            }finally{printed.SetTexture("_DialLume",original);cam.targetTexture=prior;RenderTexture.active=active;RenderTexture.ReleaseTemporary(frame);}
        }
        IEnumerator FractureSurvey(){
            var cell=ride.fracture;Directory.CreateDirectory(Path.Combine(output,"fracture"));
            Check(cell&&cell.Fragments.Length==5,"The guarded ceramic test cell contains five matched Blender fracture pieces");
            ride.Seek(0);person.Place(new Vector3(-.86f,.033f,-4.02f),180,2);person.VisitFixture("fracture_cell");
            yield return Photo("fracture/00-ready");
            ride.Seek(22);yield return Photo("fracture/06-tower-shadow");VerifyScaleBacklight(cell);person.CloseInspect();
            foreach(var control in new[]{cell.Cell,cell.Lever,cell.Magazine})
                Check(Reachable(control,-3.8f),"Real compartment sightlines reach "+control.id);
            ride.Seek(0);person.Place(new Vector3(-.88f,.03f,-4.04f),180,2);person.VisitFixture("fracture_cell");
            Check(person.Examined==cell.Cell,"B's service bench view inspects the installed cell from the aisle");
            var specimen=Array.Find(cell.GetComponentsInChildren<SkinnedMeshRenderer>(true),r=>r.name=="fracture_coupon");
            Check(specimen&&specimen.sharedMesh.blendShapeCount>0,"Blender coupon contains its physical BeamFlex shape");
            var rest=new Mesh();var loaded=new Mesh();specimen.BakeMesh(rest);var before=rest.vertices;
            var ram=cell.transform.Find("fracture_punch");Vector3 unpressed=ram.position;
            Check(cell.BeginPress(),"Intact coupon accepts the guarded press");cell.Advance(.48f);float partial=cell.LoadNewton;
            Check(partial>65&&partial<260&&!cell.Broken,"Part stroke registers "+partial.ToString("0.0")+" N without breaking the coupon");
            specimen.BakeMesh(loaded);var after=loaded.vertices;float deflection=0;
            for(int n=0;n<before.Length;n++)deflection=Mathf.Max(deflection,specimen.transform.TransformVector(after[n]-before[n]).magnitude);
            Destroy(rest);Destroy(loaded);float applied=.0007f*partial/320;
            Check(Mathf.Abs(deflection-applied)<.000085f&&Mathf.Abs(Vector3.Distance(ram.position,unpressed)-.0029f-applied)<.00007f,
                "Measured loaded Blender ceramic deflection "+(deflection*1000).ToString("F3")+" mm after 2.9 mm of punch take-up");
            yield return Photo("fracture/01-loaded");cell.ReleasePress();cell.Advance(.45f);
            Check(!cell.Broken&&cell.LoadNewton<.005f,"Releasing a partial stroke unloads the intact ceramic");
            cell.BeginPress();cell.Advance(.84f);cell.ReleasePress();float anchorStart=ShardHeight(cell);
            Check(cell.Broken&&cell.BreakCount==1&&cell.PeakNewton==320,"Snapping stores the 320 N maximum witness and releases the actual five bodies");
            for(int i=0;i<55;i++)yield return new WaitForFixedUpdate();
            float anchorFall=ShardHeight(cell)-anchorStart;
            Check(anchorFall<-.026f&&cell.Impacts>0&&cell.EnclosureError<.0015f,"At the anchor gravity moves the fragments "+(anchorFall*1000).ToString("F1")+" mm downward and they collide inside the guard");
            yield return Photo("fracture/02-anchor-settled");
            for(int step=0;step<160&&!Array.TrueForAll(cell.Fragments,b=>b.isKinematic||b.IsSleeping());step++)yield return new WaitForFixedUpdate();
            string restStates=string.Join(" / ",Array.ConvertAll(cell.Fragments,b=>b.GetComponent<FractureContact>().RestReading(b)));
            Check(Array.TrueForAll(cell.Fragments,b=>b.isKinematic||b.IsSleeping()),"All five ceramic pieces come to supported mechanical rest under Earth gravity ("+restStates+")");
            Vector3 entry=default;bool found=false;
            foreach(var retained in cell.Fragments){
                var local=cell.transform.InverseTransformPoint(retained.worldCenterOfMass);local.y=cell.ChamberBounds.max.y-.012f;var startPoint=cell.transform.TransformPoint(local);
                if(Physics.Raycast(startPoint,Vector3.down,out var hit,.20f,1<<19,QueryTriggerInteraction.Ignore)&&hit.rigidbody&&Array.IndexOf(cell.Fragments,hit.rigidbody)>=0){entry=startPoint;found=true;break;}
            }
            Check(found,"A seated ceramic fragment has an unobstructed impact path");
            var striker=new GameObject("Verification ceramic impactor");striker.layer=19;striker.transform.position=entry;
            var tip=striker.AddComponent<SphereCollider>();tip.radius=.0035f;tip.contactOffset=.0002f;
            var incoming=striker.AddComponent<Rigidbody>();incoming.mass=.006f;incoming.useGravity=false;incoming.collisionDetectionMode=CollisionDetectionMode.ContinuousDynamic;
            incoming.linearVelocity=Vector3.down*.62f;bool dislodged=false;
            for(int step=0;step<20&&!dislodged;step++){yield return new WaitForFixedUpdate();dislodged=Array.Exists(cell.Fragments,b=>!b.isKinematic&&!b.IsSleeping());}
            striker.SetActive(false);Destroy(striker);
            Check(dislodged,"A moving 6 g impactor dislodges a supported fragment through its actual contact");
            for(int step=0;step<160&&!Array.TrueForAll(cell.Fragments,b=>b.isKinematic||b.IsSleeping());step++)yield return new WaitForFixedUpdate();
            Check(Array.TrueForAll(cell.Fragments,b=>b.isKinematic||b.IsSleeping()),"The disturbed pieces return to the support patch and rest again");
            float rested=ShardHeight(cell);ride.Seek(350);
            for(int step=0;step<20;step++)yield return new WaitForFixedUpdate();
            Check(Array.TrueForAll(cell.Fragments,b=>!b.isKinematic&&!b.IsSleeping())&&ShardHeight(cell)>rested+.002f,"The same grounded fragments wake and lift when terminal braking reverses their load");
            CompleteMagazine(cell);
            ride.Seek(350);cell.BeginPress();cell.Advance(.84f);cell.ReleasePress();float brakeStart=ShardHeight(cell);
            for(int i=0;i<61;i++)yield return new WaitForFixedUpdate();
            float brakeRise=ShardHeight(cell)-brakeStart;
            Check(ride.Forces.Apparent.y>.08f&&brakeRise>.015f&&cell.EnclosureError<.0015f,"During terminal braking the fragments travel "+(brakeRise*1000).ToString("F1")+" mm toward the opposite wall");
            yield return Photo("fracture/03-braking-retained");CompleteMagazine(cell);
            ride.Seek(360);cell.BeginPress();cell.Advance(.84f);cell.ReleasePress();var start=new Vector3[cell.Fragments.Length];
            for(int i=0;i<start.Length;i++)start[i]=cell.Fragments[i].worldCenterOfMass;
            for(int i=0;i<16;i++)yield return new WaitForFixedUpdate();
            int moving=0;for(int i=0;i<start.Length;i++)if(Vector3.Distance(start[i],cell.Fragments[i].worldCenterOfMass)>.005f&&cell.Fragments[i].angularVelocity.magnitude>.04f)moving++;
            Check(moving>=3&&ride.Forces.GravityG<.002f&&cell.EnclosureError<.0015f,"At the dock "+moving+" retained pieces translate and spin independently in near-zero g");
            yield return Photo("fracture/04-dock-coast");cell.Advance(.4f);cell.Reload();cell.Advance(.38f);yield return Photo("fracture/05-magazine");cell.Advance(1);
            person.CloseInspect();
        }
    }
}
