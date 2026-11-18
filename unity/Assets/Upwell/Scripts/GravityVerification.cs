using System;
using System.Collections;
using System.IO;
using UnityEngine;

namespace Upwell {
    public sealed partial class RideVerification {
#if UNITY_WEBGL && !UNITY_EDITOR
        [System.Runtime.InteropServices.DllImport("__Internal")]static extern void UpwellLoadAudit(string reading);
        [Serializable] sealed class LoadReading {
            public Vector3 eye,velocity,item,itemVelocity;
            public string held,focus;
            public bool drifting,free;
            public float g,down;
            public int steps;
        }
        public void ReadLoadTarget(string id){
            var p=GetComponent<Passenger>();var transit=p.ride;
            if(!transit.props.TryGetValue(id,out var item))return;
            var loose=item.GetComponent<LooseItemBody>();bool free=loose&&loose.Free;
            UpwellLoadAudit(JsonUtility.ToJson(new LoadReading{eye=p.eye.transform.position,velocity=p.CabinVelocity,drifting=p.Drifting,
                held=p.Examined?p.Examined.id:"",focus=p.Focus?p.Focus.id:"",free=free,item=free?loose.Body.worldCenterOfMass:item.transform.position,
                itemVelocity=free?loose.Body.linearVelocity:Vector3.zero,g=(float)transit.Forces.GravityG,down=(float)transit.Forces.Down,steps=transit.LastLoadSteps}));
        }
#endif
        IEnumerator GravityInputs(){
#if UNITY_STANDALONE_WIN
            Directory.CreateDirectory(Path.Combine(output,"gravity"));
            var window=OwnPlayerWindow();Check(window!=IntPtr.Zero,"Located the active passenger input window");
            PostWindowMessage(window,0x1C,(IntPtr)1,IntPtr.Zero);PostWindowMessage(window,7,IntPtr.Zero,IntPtr.Zero);
            yield return new WaitForSecondsRealtime(.33f);
            yield return KeyMessage(window,0x4E);Check(ride.Seconds>=32&&ride.Seconds<35,"N advances one stage from the anchor");
            yield return KeyMessage(window,0x50);Check(ride.Seconds<3&&ride.Forces.GravityG>.98,"P restores the anchor stage and terrestrial load");
            person.SetFollowMomentView(true);person.GoToMoment(0);
            for(int i=1;i<person.MomentCount-1;i++)yield return KeyMessage(window,0xDD);
            Check(person.MomentIndex==11&&person.Examined==ride.props["capillary_cell"],"An initially walking passenger reaches the suggested galley with repeated physical bracket input");
            while(ride.Seconds<360)yield return null;
            yield return KeyMessage(window,0xDD);
            Check(person.MomentIndex==12&&person.SelectedView==0&&!person.Examined&&person.Drifting&&person.eye.transform.position.y>2.27f,"Before any push, the tour returns the original walking passenger to the free, braking-elevated aisle");
            yield return Photo("gravity/00-boarding-to-dock");
            yield return KeyMessage(window,0x31);var explicitEye=person.eye.transform.position;
            yield return KeyMessage(window,0xDB);yield return KeyMessage(window,0xDD);
            Check(person.MomentIndex==12&&person.SelectedView==1&&!person.Drifting&&Vector3.Distance(person.eye.transform.position,explicitEye)<.003f,"A manually selected 1 window station survives the same galley-to-dock handoff at its anchored pose");
            yield return KeyMessage(window,0x30);ride.Seek(0);person.Place(new Vector3(.24f,.034f,2.66f),0,0);
            person.GoToMoment(10);ride.Seek(359.85);while(ride.Seconds<360)yield return null;
            yield return KeyMessage(window,0xDD);
            Check(person.MomentIndex==12&&person.SelectedView==0&&person.Drifting,"Next from a suggested exterior camera after the natural stop also returns the original free body");
            ride.Seek(0);
            person.Place(new Vector3(.22f,.034f,2.66f),0,0);person.SetFollowMomentView(true);
            var glasses=ride.props["field_glasses"];var mount=glasses.transform.position;
            var mug=ride.props["mug"];ride.Use(mug,person);yield return new WaitForSecondsRealtime(.36f);
            yield return KeyMessage(window,0x47);var free=mug.GetComponent<LooseItemBody>();
            yield return new WaitForSecondsRealtime(1.25f);Check(free&&free.Free&&free.Body.worldCenterOfMass.y<.26f,"G releases the held vessel and it settles on the anchor deck");
            float deckHeight=free.Body.worldCenterOfMass.y;var before=person.eye.transform.position;
            Vector3 restPosition=free.Body.position;Quaternion restRotation=free.Body.rotation;
            person.GoToMoment(person.MomentCount-1);yield return new WaitForSecondsRealtime(.26f);
            float skipped=free.Body.worldCenterOfMass.y;
            var arrivalEye=person.eye.transform.position;
            Check(person.SelectedView==0&&arrivalEye.y>before.y+.52f&&arrivalEye.y<2.60f,"The free passenger stays in the aisle and rides terminal braking from eye height "+before.y.ToString("F3")+" to "+arrivalEye.y.ToString("F3")+" m");
            Check(ride.Forces.GravityG<.00001&&free.Free&&skipped>deckHeight+.55f,"Skipped braking lifts the already-settled vessel from "+deckHeight.ToString("F3")+" to "+skipped.ToString("F3")+" m");
            Check(Vector3.Distance(glasses.transform.position,mount)<.009f,"Secured optics stay in their mount through the skipped load history");
            yield return Photo("gravity/01-braced-at-dock");
            yield return KeyMessage(window,0x20);float pushed=person.eye.transform.position.y;
            var impulse=person.CabinVelocity;float coastEnd=Time.time+.42f;while(Time.time<coastEnd)yield return null;float coast=person.eye.transform.position.y;
            Check(person.Drifting&&pushed<arrivalEye.y-.025f&&coast<pushed-.08f&&impulse.y<-.38f,"Space pushed away from the headliner by "+(arrivalEye.y-pushed).ToString("F3")+" m at "+impulse.y.ToString("F3")+" m/s and coasted another "+(pushed-coast).ToString("F3")+" m without input");
            yield return Photo("gravity/02-free-above-deck");
            float ceilingTimeout=Time.time+3.2f;
            while(Mathf.Abs(person.CabinVelocity.y)>.02f&&Time.time<ceilingTimeout)yield return null;
            float deck=person.eye.transform.position.y;
            Check(deck<1.69f&&deck>1.53f&&Mathf.Abs(person.CabinVelocity.y)<.03f,"The real deck stops the floating passenger at eye height "+deck.ToString("F3")+" m");
            yield return KeyMessage(window,0x20);Check(person.eye.transform.position.y>deck+.10f,"Space pushes back off the deck");
            yield return KeyMessage(window,0x4E);Check(ride.Seconds==360,"Forward at the dock stays at the dock");
            for(int n=1;n<AscentRoute.StageSeconds.Length;n++)yield return KeyMessage(window,0x50);
            // Physics contact and drag advance on fixed simulation ticks. A flask that
            // drifted over a shelf can settle on it when the downward load returns.
            double settleStart=Time.fixedTimeAsDouble;
            while(Time.fixedTimeAsDouble-settleStart<3.2&&
                (person.Drifting||person.eye.transform.position.y>=1.67f||!free.SupportedByDeck()||
                 free.Body.worldCenterOfMass.y>skipped-.45f))yield return null;
            var flaskCenter=free.Body.worldCenterOfMass;
            bool onSupport=free.SupportedByDeck();
            var supportName=Physics.Raycast(flaskCenter+Vector3.up*.004f,Vector3.down,out var supportHit,3f,1,QueryTriggerInteraction.Ignore)
                ?supportHit.collider.name+" at "+supportHit.point.y.ToString("F3")+" m":"unresolved beneath center";
            string state=" at route "+ride.Seconds.ToString("F3")+" s, signed load "+(ride.Forces.Down/9.80665).ToString("F5")+" g"+
                ", eye "+person.eye.transform.position.ToString("F3")+", drifting "+person.Drifting+
                ", flask "+flaskCenter.ToString("F3")+", speed "+free.Body.linearVelocity.magnitude.ToString("F4")+" m/s"+
                ", angular speed "+free.Body.angularVelocity.magnitude.ToString("F4")+" rad/s, support "+supportName+
                ", fixed settling time "+(Time.fixedTimeAsDouble-settleStart).ToString("F3")+" s";
            Check(ride.Seconds<5&&ride.Forces.Down/9.80665>.98,"Backward stage input restores the anchor and terrestrial load"+state);
            Check(person.SelectedView==0&&!person.Drifting&&person.eye.transform.position.y<1.67f,"The free passenger resumes walking"+state);
            Check(free.Free&&onSupport&&skipped-flaskCenter.y>.45f,"The same loose vessel falls "+(skipped-flaskCenter.y).ToString("F3")+" m and reaches stable physical support"+state);
            // Freeze the initial conditions for the comparison. On the return trip the
            // vessel may have slipped beneath a different shelf. Keep the observer in their seat.
            person.Rest(ride.props["lounge_seat"]);ride.Seek(304);
            free.LetGo(restPosition,restRotation,Vector3.zero,Vector3.zero);ride.Seek(360);
            float sameStartSkipped=free.Body.worldCenterOfMass.y;
            ride.Seek(304);free.LetGo(restPosition,restRotation,Vector3.zero,Vector3.zero);
            while(ride.Seconds<360)yield return null;
            float natural=free.Body.worldCenterOfMass.y;
            Check(natural>deckHeight+.55f&&sameStartSkipped>deckHeight+.55f&&Mathf.Abs(natural-sameStartSkipped)<.20f,"From the identical 304 s vessel pose: natural approach "+natural.ToString("F3")+" m, direct seek "+sameStartSkipped.ToString("F3")+" m");
            person.Rise();person.Place(new Vector3(.22f,.034f,2.66f),0,0);
            person.Inspect(mug);yield return new WaitForSecondsRealtime(.32f);yield return KeyMessage(window,0x47);
            var initial=free.Body.worldCenterOfMass;yield return new WaitForSecondsRealtime(.35f);
            Check(free.Free&&Mathf.Abs(free.Body.worldCenterOfMass.y-initial.y)<.06f,"Opening a stationary hand at the dock preserves the vessel's height");
            person.SetWatch(1);yield return KeyMessage(window,0x20);
            Check(person.SelectedView==0&&person.Drifting,"Space leaves deliberate window observation and pushes into the cabin");
#else
            yield break;
#endif
        }
    }
}
