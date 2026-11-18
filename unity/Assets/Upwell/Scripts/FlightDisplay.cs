using System;
using System.Collections.Generic;
using UnityEngine;

namespace Upwell {
    public sealed class FlightDisplay {
        const int W=512,H=224,Left=18,Right=491,Top=151,Bottom=193;
        const float HistorySeconds=24;
        readonly Texture2D screen;
        readonly List<(MeshRenderer r,int slot)> bindings=new List<(MeshRenderer,int)>();
        readonly Color32[] pixels=new Color32[W*H];
        readonly Color32 ink=new Color32(204,235,224,255),dim=new Color32(117,157,150,255),
            rule=new Color32(48,72,73,255),amber=new Color32(249,185,82,255);
        readonly Vector3[] plan=new Vector3[181];
        readonly (float time,float pressure,float carrier,float load)[] history=new (float,float,float,float)[160];
        static readonly float[] loadRanges={.002f,.020f,.12f,1.2f};
        float loadRange;
        readonly double tripTime=CarriageForces.At(AscentRoute.Terminal).ShipSeconds;
        int head,count;

        public FlightDisplay(TransitProp prop,RenderTexture feed) {
            screen=new Texture2D(W,H,TextureFormat.RGBA32,true,false) {
                wrapMode=TextureWrapMode.Clamp,filterMode=FilterMode.Trilinear,anisoLevel=8,name="Car 07 live navigation"
            };
            Shader.SetGlobalTexture("_UpwellGlassPanel",screen);
            Shader.SetGlobalTexture("_UpwellGlassFeed",feed);
            foreach(var r in prop.GetComponentsInChildren<MeshRenderer>()) {
                var mats=r.sharedMaterials;
                for(int k=0;k<mats.Length;k++) if(mats[k]!=null&&mats[k].name=="Nav_Active_Pixels") {
                    var block=new MaterialPropertyBlock();r.GetPropertyBlock(block,k);
                    block.SetTexture("_MainTex",screen);block.SetTexture("_Feed",feed);r.SetPropertyBlock(block,k);
                    bindings.Add((r,k));
                }
            }
            for(int j=0;j<plan.Length;j++){
                double altitude=AscentRoute.Height(AscentRoute.Duration*j/(plan.Length-1));
                var forces=CarriageForces.At(altitude);
                plan[j]=new Vector3((float)(forces.ShipSeconds/tripTime),
                    (float)(Math.Log(1+altitude)/Math.Log(1+AscentRoute.Terminal)),
                    (float)(forces.Down/9.80665));
            }
        }
        public void Settings(int page,float gain){
            Shader.SetGlobalFloat("_UpwellGlassPanelGain",gain);
            Shader.SetGlobalFloat("_UpwellGlassPanelPage",page);
            foreach(var q in bindings){
                var block=new MaterialPropertyBlock();q.r.GetPropertyBlock(block,q.slot);
                block.SetFloat("_PanelGain",gain);block.SetFloat("_Page",page);q.r.SetPropertyBlock(block,q.slot);
            }
        }
        public void ResetHistory(){head=0;count=0;loadRange=0;}
        void Dot(int x,int y,Color32 c){if((uint)x<W&&(uint)y<H)pixels[(H-1-y)*W+x]=c;}
        void Line(int x,int y,int xx,int yy,Color32 c){
            int n=Math.Max(Math.Abs(xx-x),Math.Abs(yy-y));if(n==0){Dot(x,y,c);return;}
            for(int i=0;i<=n;i++)Dot(x+(xx-x)*i/n,y+(yy-y)*i/n,c);
        }
        void Text(string s,int x,int y,int size,Color32 c){DisplayLettering.Draw(pixels,W,H,s,x,y,size,c);}
        static int PlotX(float fraction)=>Left+Mathf.RoundToInt(Mathf.Clamp01(fraction)*(Right-Left));
        static int PlotY(float fraction)=>Bottom-Mathf.RoundToInt(Mathf.Clamp01(fraction)*(Bottom-Top));
        void Grid(){
            for(int k=0;k<=4;k++){int x=PlotX(k/4f);Line(x,Top,x,Bottom,rule);}
            for(int k=0;k<=2;k++){int y=PlotY(k/2f);Line(Left,y,Right,y,rule);}
        }
        void RoutePlot(int mode,float current){
            for(int i=1;i<plan.Length;i++){
                var a=plan[i-1];var b=plan[i];
                float ay=mode==0?a.y:(a.z+.045f)/1.10f,by=mode==0?b.y:(b.z+.045f)/1.10f;
                Line(PlotX(a.x),PlotY(ay),PlotX(b.x),PlotY(by),b.x<=current?ink:dim);
            }
            int marker=PlotX(current);Line(marker,Top-2,marker,Bottom+3,amber);
            Text("0 H",Left,205,1,dim);Text("SHIP ELAPSED",220,205,1,dim);
            Text((tripTime/3600).ToString("0.0")+" H",456,205,1,dim);
        }
        void LivePlot(int mode,float now){
            int px=-1,py=0;
            for(int i=0;i<count;i++){
                var sample=history[(head-count+i+history.Length)%history.Length];
                float age=now-sample.time;if(age>HistorySeconds)continue;
                int x=PlotX(1-age/HistorySeconds),y=PlotY(mode==2?sample.pressure/.4f:.12f+.75f*sample.carrier);
                if(px>=0){if(mode==5)Line(px,py,x,py,ink);Line(mode==5?x:px,py,x,y,ink);}
                Dot(x,y,amber);px=x;py=y;
            }
            Text("-24 S",Left,205,1,dim);Text(mode==2?"0 TO 0.40 KPA":"CARRIER OFF / ON",199,205,1,dim);Text("NOW",474,205,1,amber);
        }
        void TrafficPlot(double altitude){
            int row=PlotY(.57f);Line(Left,row,Right,row,dim);
            for(int j=0;j<ExteriorRig.Passes.Length;j++){
                double h=AscentRoute.Height(ExteriorRig.Passes[j]*AscentRoute.Duration);
                int x=PlotX((float)(Math.Log(1+h)/Math.Log(1+AscentRoute.Terminal)));
                Line(x,row-4,x,row+4,ink);
            }
            int now=PlotX((float)(Math.Log(1+altitude)/Math.Log(1+AscentRoute.Terminal)));Line(now,Top,now,Bottom,amber);
            Text("ANCHOR",Left,205,1,dim);Text("CROSSING ALTITUDES   /   LOG KM",166,205,1,dim);Text("ASTER",463,205,1,dim);
        }
        static string LoadValue(double g,bool signed=true){
            bool milli=Math.Abs(g)<.1;double value=milli?g*1000:g;
            double resolution=milli?.1:.001;
            if(Math.Abs(value)<resolution*.5)return milli?"0.0 MG":"0.000 G";
            return (signed&&value>0?"+":"")+value.ToString(milli?"0.0":"0.000")+(milli?" MG":" G");
        }
        void LoadWatch(TransitRide ride,float now){
            const int x0=230,x1=491,mid=116,half=40;
            double current=ride.Forces.Down/9.80665,mag=Math.Abs(current);
            float desired=loadRanges[loadRanges.Length-1];
            foreach(float r in loadRanges)if(mag<=r*.90){desired=r;break;}
            if(loadRange==0||desired>loadRange||mag<desired*.78)loadRange=desired;
            string direction=mag<.00005?"NEUTRAL":current<0?"TOWARD CEILING":"TOWARD DECK";
            Text(direction,14,49,2,current<-.00005?amber:ink);
            Text(LoadValue(current),13,77,3,ink);
            Text("WEST "+(ride.Forces.West*1000/9.80665).ToString("0.00")+" MG",15,126,2,dim);
            if(ride.experiments){
                Text((ride.experiments.Testing?"TEST ":"PROOF ")+LoadValue(ride.experiments.IndicatedG),15,153,2,ride.experiments.Testing?amber:dim);
            }
            string scale=loadRange>=1?"1.2 G":(loadRange*1000).ToString("0")+" MG";
            Text("LAST 24 S",x0,50,2,dim);Text("±"+scale,x1-12*(scale.Length+1),50,2,ink);
            for(int j=0;j<5;j++){int x=x0+(x1-x0)*j/4;Line(x,mid-half,x,mid+half,rule);}
            Line(x0,mid-half,x1,mid-half,rule);Line(x0,mid,x1,mid,dim);Line(x0,mid+half,x1,mid+half,rule);
            double? reference=ride.systems.LoadReference;
            if(reference.HasValue&&Math.Abs(reference.Value)<=loadRange){
                int y=mid+Mathf.RoundToInt((float)reference.Value/loadRange*half);
                for(int x=x0;x<x1;x+=8)Line(x,y,Math.Min(x+3,x1),y,amber);
            }
            float px=0,py=0;bool hasPrevious=false;
            for(int i=0;i<count;i++){
                var s=history[(head-count+i+history.Length)%history.Length];
                float age=now-s.time;if(age>HistorySeconds)continue;
                float x=x1-(x1-x0)*age/HistorySeconds,y=s.load/loadRange;
                if(hasPrevious&&Mathf.Min(py,y)<=1&&Mathf.Max(py,y)>=-1){
                    float a=Mathf.Clamp(py,-1,1),b=Mathf.Clamp(y,-1,1);
                    float xa=px,xb=x;
                    if(Mathf.Abs(y-py)>.000001f){xa=Mathf.Lerp(px,x,(a-py)/(y-py));xb=Mathf.Lerp(px,x,(b-py)/(y-py));}
                    int ay=mid+Mathf.RoundToInt(a*half),by=mid+Mathf.RoundToInt(b*half);
                    Line(Mathf.RoundToInt(xa),ay,Mathf.RoundToInt(xb),by,ink);
                    Line(Mathf.RoundToInt(xa),ay+1,Mathf.RoundToInt(xb),by+1,ink);
                }
                px=x;py=y;hasPrevious=true;
            }
            int indicator=mid+Mathf.RoundToInt(Mathf.Clamp((float)current/loadRange,-1,1)*half);
            for(int k=0;k<4;k++)Line(x1-k,indicator-k,x1-k,indicator+k,ink);
            Text("CEILING -  /  + DECK",x0,164,1,dim);Text("NOW",x1-17,164,1,ink);
            Line(14,182,498,182,rule);
            if(reference.HasValue){
                Text("MARK "+LoadValue(reference.Value),14,192,2,amber);
                Text("CHANGE "+LoadValue(current-reference.Value),215,192,2,ink);
                Text("LOAD / CLEAR",425,199,1,dim);
            }else Text("PRESS LOAD TO MARK THIS READING",14,193,2,amber);
        }
        public void Draw(TransitRide ride){
            int mode=ride.DisplayMode,detent=ride.Feeds;
            var forces=ride.Forces;float current=(float)(forces.ShipSeconds/tripTime),now=Time.unscaledTime;
            float pressure=ride.systems.IndicatedPressure;
            history[head]=(now,pressure,ride.RadioPlaying?1:0,(float)(forces.Down/9.80665));head=(head+1)%history.Length;count=Math.Min(count+1,history.Length);
            Array.Fill(pixels,new Color32(8,22,25,255));
            Text(mode==3?"CAR 07  /  VERTICAL LOAD":"CAR 07  /  ASTER REACH",14,12,2,ink);
            Text("LINK OK",413,12,2,amber);Line(14,36,498,36,rule);
            if(mode==1){
                Text("CAM 0"+(detent+1)+"  "+TransitRide.Channels[detent],17,203,2,ink);
            }else if(mode==3){
                LoadWatch(ride,now);
            }else{
                string label,value,chart;
                switch(mode){
                    case 0: label="ALTITUDE";value=AscentRoute.AltitudeText(ride.PreciseAltitude);chart="UPBOUND   /   LOG KM";break;
                    case 2: label="SEAL DIFFERENTIAL";value=pressure.ToString("0.00")+" KPA";chart="PRESSURE TRANSDUCER   /   LIVE";break;
                    case 4: label="DOWNBOUND CONTACT";value=ride.systems.NextTraffic;chart="COUNTERLINE   /   CAR 07 UPBOUND";break;
                    default:label="DISPATCH";value=ride.RadioPlaying?"RECEIVING":"STANDBY";chart="CHANNEL 07   /   RX CARRIER";break;
                }
                Text(label,16,50,label.Length>21?1:2,dim);
                Text(value,15,78,value.Length>14?2:3,ink);
                if(mode==0){
                    int elapsed=(int)(ride.AboardSeconds/60),left=(int)(Math.Max(0,tripTime+9-ride.AboardSeconds)/60);
                    Text("TIME ABOARD",333,48,1,dim);
                    Text((elapsed/60)+"H "+(elapsed%60).ToString("00")+"M",331,62,2,ink);
                    Text("TO DOCK",333,89,1,dim);
                    Text((left/60)+"H "+(left%60).ToString("00")+"M",331,103,2,amber);
                }else if(mode==4){
                    Text("8 H DISPATCH",379,48,1,dim);Text("4 H CROSSINGS",379,63,1,ink);
                    Text("5 PAX / 9 FREIGHT",379,90,1,dim);Text("2 CABLE TENDERS",379,105,1,dim);
                }
                Text(chart,17,128,2,dim);Grid();
                if(mode==2||mode==5)LivePlot(mode,now);
                else if(mode==4)TrafficPlot(ride.PreciseAltitude);
                else RoutePlot(mode,current);
            }
            screen.SetPixels32(pixels);screen.Apply(true,false);
        }
    }
}
