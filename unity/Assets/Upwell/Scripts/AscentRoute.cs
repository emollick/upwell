using System;
using System.Collections.Generic;
using UnityEngine;

namespace Upwell {
    public static class AscentRoute {
        public const double Duration=360, Radius=6371;
        public static readonly double Terminal=CarriageForces.SynchronousAltitude;
        static readonly double[] t={0,9,12,16,22,32,44,58,75,92,108,135,154,184,213,244,267,290,305,315,323,330,339,345,351,360};
        static readonly double[] h={0,0,.0025,.012,.040,.150,.55,1.48,3.35,6.4,12,35,100,660,3900,12600,22500,32000,35500,Terminal-6,Terminal-.180,Terminal-.095,Terminal-.046,Terminal-.021,Terminal-.006,Terminal};
        static readonly double[] slopes=Slopes();
        public const double DispatchInterval=8*3600,EncounterInterval=DispatchInterval/2,FleetCycle=18*DispatchInterval;
        static readonly string[] fleet={"C12","F18","F26","C19","F11","T03","C21","F22","F16","C25","F28","T06","C15","F31","F24","C07","F35","T09"};
        public sealed class Service {
            public string Car,Kind,Type;
            public double Seconds,Progress,ShipSeconds,DispatchShipSeconds,ArrivalShipSeconds,ApproachSeconds;
            public double? UpDispatchShipSeconds;
            public bool Extra,Featured,Recommended;
        }
        static readonly double firstDispatch=2*ShipClock(129.6).time-CarriageForces.TripSeconds;
        public static readonly double OrbitTurn=firstDispatch+15*DispatchInterval-CarriageForces.TripSeconds;
        public static readonly double AnchorTurn=FleetCycle-2*CarriageForces.TripSeconds-OrbitTurn;
        public static readonly Service[] Services=MakeServices();
        public static readonly double[] PassSeconds=Array.ConvertAll(Services,s=>s.Seconds);
        static readonly double[] protectedMoments={142,148,223.5,226.5,233.7,236,238.3,240.3,310};
        const double PassRate=.05;
        sealed class Encounter {
            internal double center,start,end,innerStart,innerEnd,ship;
            internal (double time,double rate) entry,exit;
            internal double Clock(double seconds)=>ship+(seconds-center)*PassRate;
        }
        static readonly Encounter[] encounters=MakeEncounters();
        public static readonly double[] ApproachSeconds=MakeApproachTimes();
        public static readonly float[] StageSeconds={0,32,58,108,135,154,184,(float)SecondsAtShipTime(9+CarriageForces.At(12600).ShipSeconds),305,339,360};
        public static readonly string[] Stages={"Equatorial anchor","Tower clearance","Cloud field","Cloud tops","Stratosphere","Kármán line","Earth limb","High orbit","Terminal approach","Receiving bay","Aster Reach"};
        static double[] Slopes(){
            int n=t.Length;var m=new double[n];double[] d=new double[n-1],l=new double[n-1];
            for(int i=0;i<n-1;i++){l[i]=t[i+1]-t[i];d[i]=(h[i+1]-h[i])/l[i];}
            for(int i=1;i<n-1;i++){
                if(d[i-1]*d[i]<=0)continue;
                double a=2*l[i]+l[i-1],b=l[i]+2*l[i-1];m[i]=(a+b)/(a/d[i-1]+b/d[i]);
            }
            return m;
        }
        static double Cubic(double y0,double m0,double y1,double m1,double width,double u){
            double u2=u*u,u3=u2*u;
            return (2*u3-3*u2+1)*y0+(u3-2*u2+u)*width*m0+(-2*u3+3*u2)*y1+(u3-u2)*width*m1;
        }
        static (double metres,double rate) FinalApproach(double seconds){
            int i=t.Length-2;double span=t[i+1]-t[i],left=(t[i+1]-seconds)/span;
            double root0=Math.Pow(h[i+1]-h[i],1.0/3),b=slopes[i]*span/(3*root0*root0),root=left*(root0+(b-root0)*(left-1));
            return (1000*root*root*root,3*root*root*(root0+(b-root0)*(2*left-1))/span);
        }
        static (double height,double rate) Survey(double seconds){
            if(seconds<=0)return (0,0);if(seconds>=Duration)return (Terminal,0);
            int i=0;while(seconds>t[i+1])i++;
            double width=t[i+1]-t[i],u=(seconds-t[i])/width,a=slopes[i],b=slopes[i+1];
            if(seconds>9&&seconds<=12){
                double root1=Math.Pow(h[i+1],1.0/3),endSlope=b*width/(3*root1*root1),root=u*(root1+(endSlope-root1)*(u-1));
                return (root*root*root,3*root*root*(root1+(endSlope-root1)*(2*u-1))/width);
            }
            if(i==t.Length-2){
                var final=FinalApproach(seconds);return (Terminal-final.metres/1000,final.rate);
            }
            return (Cubic(h[i],a,h[i+1],b,width,u),6*u*(1-u)*(h[i+1]-h[i])/width+(3*u*u-4*u+1)*a+(3*u*u-2*u)*b);
        }
        static (double time,double rate) ShipClock(double seconds){
            if(seconds>=351&&seconds<Duration){
                var final=FinalApproach(seconds);var r=CarriageForces.BrakingTimeForRemainingMetres(final.metres);
                return (CarriageForces.TripSeconds-r.time,r.velocity>0?final.rate*1000/r.velocity:0);
            }
            var survey=Survey(seconds);var f=CarriageForces.At(survey.height);
            return (f.ShipSeconds,f.Velocity>0?survey.rate*1000/f.Velocity:0);
        }
        static double SurveySeconds(double km){
            double lo=9,hi=Duration;
            for(int i=0;i<44;i++){double m=(lo+hi)/2;if(Survey(m).height<km)lo=m;else hi=m;}
            return (lo+hi)/2;
        }
        static Service MakeService(string car,double departure,bool extra=false,double? featuredSeconds=null){
            double ship=(departure+CarriageForces.TripSeconds)/2,seconds=featuredSeconds??(car=="T03"?244.15:SurveySeconds(CarriageForces.HeightAtShipTime(ship)));
            return new Service{Car=car,Kind=car[0]=='C'?"passenger":car[0]=='F'?"freight":"tender",
                Type=car[0]=='C'?"Passenger":car[0]=='F'?"Freight":"Cable tender",Extra=extra,Featured=featuredSeconds.HasValue,Recommended=car=="T03",
                Seconds=seconds,Progress=seconds/Duration,ShipSeconds=ship,DispatchShipSeconds=departure,
                ArrivalShipSeconds=departure+CarriageForces.TripSeconds,UpDispatchShipSeconds=extra?(double?)null:departure-OrbitTurn-CarriageForces.TripSeconds};
        }
        static Service[] MakeServices(){
            var result=new List<Service>();
            for(int i=0;firstDispatch+i*DispatchInterval<CarriageForces.TripSeconds;i++)
                result.Add(MakeService(fleet[i%fleet.Length],firstDispatch+i*DispatchInterval,false,i==0?(double?)129.6:null));
            result.Add(MakeService("F04",2*ShipClock(194.4).time-CarriageForces.TripSeconds,true,194.4));
            result.Sort((a,b)=>a.ShipSeconds.CompareTo(b.ShipSeconds));return result.ToArray();
        }
        static Encounter[] MakeEncounters(){
            var result=new Encounter[PassSeconds.Length];
            for(int j=0;j<result.Length;j++){
                var service=Services[j];double c=service.Seconds,extent=service.Featured?8:1.12,core=service.Featured?5:.52;
                if(service.Recommended){
                    result[j]=new Encounter{center=c,start=240.3,end=248.7,innerStart=240.90,innerEnd=247.45,ship=service.ShipSeconds,
                        entry=ShipClock(240.3),exit=ShipClock(248.7)};continue;
                }
                double start=Math.Max(c-extent,((j>0?PassSeconds[j-1]:0)+c)/2),end=Math.Min(c+extent,((j+1<result.Length?PassSeconds[j+1]:Duration)+c)/2);
                foreach(double mark in t){if(mark<c-1e-7)start=Math.Max(start,mark);if(mark>c+1e-7)end=Math.Min(end,mark);}
                foreach(double mark in protectedMoments){if(mark<c-1e-7)start=Math.Max(start,mark);if(mark>c+1e-7)end=Math.Min(end,mark);}
                result[j]=new Encounter{center=c,start=start,end=end,innerStart=c-Math.Min(core,(c-start)*.65),
                    innerEnd=c+Math.Min(core,(end-c)*.65),ship=service.ShipSeconds,entry=ShipClock(start),exit=ShipClock(end)};
            }
            return result;
        }
        static Encounter Window(double seconds){
            foreach(var w in encounters){
                if(seconds>w.start&&seconds<w.end)return w;
            }return null;
        }
        static (double time,double rate) EncounterClock(Encounter w,double seconds){
            double a,m,b,n,width,u;
            if(seconds<w.innerStart){a=w.entry.time;m=w.entry.rate;b=w.Clock(w.innerStart);n=PassRate;width=w.innerStart-w.start;u=(seconds-w.start)/width;}
            else if(seconds>w.innerEnd){a=w.Clock(w.innerEnd);m=PassRate;b=w.exit.time;n=w.exit.rate;width=w.end-w.innerEnd;u=(seconds-w.innerEnd)/width;}
            else return (w.Clock(seconds),PassRate);
            return (Cubic(a,m,b,n,width,u),6*u*(1-u)*(b-a)/width+(3*u*u-4*u+1)*m+(3*u*u-2*u)*n);
        }
        public static double Height(double seconds){
            var w=Window(seconds);return w!=null?CarriageForces.HeightAtShipTime(EncounterClock(w,seconds).time):Survey(seconds).height;
        }
        public static double ShipTimeAt(double seconds){
            if(seconds<=9)return Math.Max(0,seconds);if(seconds>=Duration)return CarriageForces.TripSeconds+9;
            var w=Window(seconds);return 9+(w!=null?EncounterClock(w,seconds).time:ShipClock(seconds).time);
        }
        public static double ShipRateAt(double seconds){
            if(seconds<=9)return 1;if(seconds>=Duration)return 0;
            var w=Window(seconds);return w!=null?EncounterClock(w,seconds).rate:ShipClock(seconds).rate;
        }
        public static double SecondsAtShipTime(double time){
            if(time<=9)return Math.Max(0,time);if(time>=CarriageForces.TripSeconds+9)return Duration;
            double drive=time-9,km=CarriageForces.HeightAtShipTime(drive),lo=9,hi=Duration;
            if(drive>CarriageForces.TripSeconds-CarriageForces.BrakingTimeForRemainingMetres(6).time){
                double remaining=CarriageForces.BrakingDistanceAtTime(CarriageForces.TripSeconds-drive);lo=351;
                for(int i=0;i<36;i++){double m=(lo+hi)/2;
                    if(FinalApproach(m).metres>remaining)lo=m;else hi=m;}
                return (lo+hi)/2;
            }
            Encounter window=null;
            foreach(var w in encounters){
                if(drive<=w.entry.time||drive>=w.exit.time)continue;
                if(drive>=w.Clock(w.innerStart)&&drive<=w.Clock(w.innerEnd))return w.center+(drive-w.ship)/PassRate;
                window=w;lo=w.start;hi=w.end;break;
            }
            for(int i=0;i<36;i++){double m=(lo+hi)/2;if(window!=null?EncounterClock(window,m).time<drive:Survey(m).height<km)lo=m;else hi=m;}
            return (lo+hi)/2;
        }
        public readonly struct CounterCar {
            public readonly int Index;
            public Service Service=>Services[Index];
            public readonly double ShipSeconds,Eta,Altitude,Separation,ClosingMps;
            public bool InRange=>Math.Abs(Separation)<1100;
            internal CounterCar(int index,double km,CarriageForces own){
                Index=index;ShipSeconds=encounters[index].ship;Eta=ShipSeconds-own.ShipSeconds;
                Altitude=CarriageForces.HeightAtShipTime(ShipSeconds+Eta);
                Separation=(Altitude-km)*1000;ClosingMps=own.Velocity+CarriageForces.At(Altitude).Velocity;
            }
        }
        public static CounterCar Counterline(double km,CarriageForces own){
            int index=0;
            for(int j=1;j<encounters.Length;j++)if(Math.Abs(encounters[j].ship-own.ShipSeconds)<Math.Abs(encounters[index].ship-own.ShipSeconds))index=j;
            return new CounterCar(index,km,own);
        }
        static double[] MakeApproachTimes(){
            var times=new double[encounters.Length];
            for(int i=0;i<times.Length;i++){
                var w=encounters[i];double low=w.start,high=w.center;
                for(int step=0;step<34;step++){
                    double time=(low+high)/2,km=Height(time);var contact=Counterline(km,CarriageForces.At(km));
                    if(contact.Separation>1100)low=time;else high=time;
                }
                Services[i].ApproachSeconds=times[i]=high;
            }
            return times;
        }
        public static Vector3 Sun(double km){
            double dec=-Math.PI/15,angle=2*Math.PI*((6.58+CarriageForces.At(km).ShipSeconds/3600)/24-.5);
            // The carriage's native +Z points south. Local east/up remain +X/+Y.
            return new Vector3((float)(-Math.Cos(dec)*Math.Sin(angle)),(float)(Math.Cos(dec)*Math.Cos(angle)),(float)-Math.Sin(dec));
        }
        public static float Command(double altitude){
            return (float)(CarriageForces.At(altitude).Velocity*3.6);
        }
        public static int Stage(double sec){int stage=0;while(stage<StageSeconds.Length-1&&sec>=StageSeconds[stage+1]-.0001)stage++;return stage;}
        public static string AltitudeText(double km)=>km<1?Math.Round(km*1000)+" m":Math.Round(km).ToString("N0")+" km";
    }
}
