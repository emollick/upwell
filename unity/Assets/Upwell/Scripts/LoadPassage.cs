using System;
using System.Collections.Generic;
using UnityEngine;

namespace Upwell {
    public sealed partial class TransitRide {
        readonly List<LooseItemBody> releasedGear=new List<LooseItemBody>(5);
        Passenger passenger;
        public bool ReplayingLoads {get;private set;}
        public int LastLoadSteps {get;private set;}

        void AdvanceLoosePassage(double from,double to){
            LastLoadSteps=0;releasedGear.Clear();
            foreach(var p in props.Values)if(p.portable&&p.TryGetComponent<LooseItemBody>(out var item)&&item.Free)releasedGear.Add(item);
            if(!passenger)passenger=FindFirstObjectByType<Passenger>();
            bool floating=passenger&&passenger.CanReplayMotion,pieces=fracture&&fracture.Broken;
            if(to<=from){
                if(to<from)foreach(var item in releasedGear)item.Body.WakeUp();
                return;
            }
            if(releasedGear.Count==0&&!pieces&&!floating)return;
            // Advance the same cabin colliders and dynamic bodies a passenger would have seen
            // during these presentation seconds. A seek never reconstructs inventory or fittings.
            var saved=Physics.simulationMode;Physics.SyncTransforms();
            ReplayingLoads=true;Physics.simulationMode=SimulationMode.Script;
            try{
                double time=from;
                while(to-time>.00001){
                    double interval=Math.Min(1,to-time);
                    var current=CarriageForces.At(AscentRoute.Height(time)).Apparent;
                    var next=CarriageForces.At(AscentRoute.Height(time+interval)).Apparent;
                    if(interval>.1&&(!floating||!passenger.Drifting)&&current.y<-.012f&&next.y<-.012f&&Vector3.Dot(current.normalized,next.normalized)>.997f){
                        bool supported=!pieces||fracture.AllPiecesSupported;
                        for(int i=0;supported&&i<releasedGear.Count;i++)supported=releasedGear[i].SupportedByDeck();
                        if(supported){if(pieces)fracture.SkipSupportedTime((float)interval);time+=interval;continue;}
                    }
                    float step=(float)Math.Min(Time.fixedDeltaTime,to-time);
                    SetClock(time+step*.5);var field=Forces.Apparent;
                    foreach(var item in releasedGear)item.ApplyField(field);
                    if(pieces)fracture.AdvanceSkippedField(field,step);
                    if(floating)passenger.AdvanceUnrestrained(field,step);
                    if(pieces||releasedGear.Count>0)Physics.Simulate(step);
                    LastLoadSteps++;time+=step;
                }
            } finally {Physics.simulationMode=saved;ReplayingLoads=false;}
        }
    }
}
