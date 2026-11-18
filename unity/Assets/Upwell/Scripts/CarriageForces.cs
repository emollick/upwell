using System;
using UnityEngine;

namespace Upwell {
    public readonly struct CarriageForces {
        public readonly double Velocity,Drive,ShipSeconds,EarthGravity,Centrifugal,EffectiveDown,Down,West,GravityG;
        public Vector3 Apparent=>new Vector3((float)-West,(float)-Down,0);
        const double R=6378137,Mu=3.986004418e14,Omega=7.292115e-5,Cruise=170;
        static readonly double Distance=Math.Pow(Mu/(Omega*Omega),1.0/3.0)-R;
        public static readonly double SynchronousAltitude=Distance/1000;
        readonly struct Ramp {
            public readonly double A,JerkTime,Time,Distance;
            public Ramp(double a,double j){A=a;JerkTime=j;Time=Cruise/a+j;Distance=Cruise*Time/2;}
        }
        static readonly Ramp Launch=new Ramp(.30,4),Braking=new Ramp(.14,7);
        public static readonly double TripSeconds=Launch.Time+Braking.Time+(Distance-Launch.Distance-Braking.Distance)/Cruise;
        CarriageForces(double v,double a,double time,double height){
            Velocity=v;Drive=a;ShipSeconds=time;double radius=R+height;
            EarthGravity=Mu/(radius*radius);Centrifugal=Omega*Omega*radius;EffectiveDown=EarthGravity-Centrifugal;
            Down=EffectiveDown+a;West=2*Omega*v;GravityG=Math.Sqrt(Down*Down+West*West)/9.80665;
        }
        static (double x,double v,double a) RampAt(double t,Ramp r){
            double j=r.A/r.JerkTime,remain=r.Time-t;
            if(t<r.JerkTime)return(j*t*t*t/6,j*t*t/2,j*t);
            if(remain<r.JerkTime)return(r.Distance-Cruise*remain+j*remain*remain*remain/6,Cruise-j*remain*remain/2,j*remain);
            double u=t-r.JerkTime,v0=.5*r.A*r.JerkTime;
            return(r.A*r.JerkTime*r.JerkTime/6+v0*u+r.A*u*u/2,v0+r.A*u,r.A);
        }
        static (double t,double v,double a) Invert(double x,Ramp ramp){
            if(x<=0)return(0,0,0);double lo=0,hi=ramp.Time;
            for(int i=0;i<40;i++){double t=(lo+hi)/2;if(RampAt(t,ramp).x<x)lo=t;else hi=t;}
            double time=(lo+hi)/2;var q=RampAt(time,ramp);return(time,q.v,q.a);
        }
        public static double HeightAtShipTime(double time){
            if(time<=0)return 0;if(time>=TripSeconds)return SynchronousAltitude;
            if(time<Launch.Time)return RampAt(time,Launch).x/1000;
            double left=TripSeconds-time;
            if(left<Braking.Time)return (Distance-RampAt(left,Braking).x)/1000;
            return (Launch.Distance+Cruise*(time-Launch.Time))/1000;
        }
        public static (double time,double velocity) BrakingTimeForRemainingMetres(double metres){
            var q=Invert(Math.Max(0,metres),Braking);return (q.t,q.v);
        }
        public static double BrakingDistanceAtTime(double timeLeft)=>RampAt(timeLeft,Braking).x;
        public static CarriageForces At(double km){
            double h=Math.Min(Distance,Math.Max(0,km*1000)),remain=Distance-h;
            if(h<Launch.Distance){var q=Invert(h,Launch);return new CarriageForces(q.v,q.a,q.t,h);}
            if(remain<Braking.Distance){var q=Invert(remain,Braking);return new CarriageForces(q.v,-q.a,TripSeconds-q.t,h);}
            return new CarriageForces(Cruise,0,Launch.Time+(h-Launch.Distance)/Cruise,h);
        }
    }
}
