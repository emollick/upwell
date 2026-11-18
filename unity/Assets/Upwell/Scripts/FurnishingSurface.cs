using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;

namespace Upwell {
    // A metre-scale compliance cage carries the original high-resolution fabric, piping and cable jackets.
    // The mounting clips and retainers remain fixed in the carriage reference frame.
    [DefaultExecutionOrder(42)]
    public sealed class FurnishingSurface : MonoBehaviour {
        public string partId;
        public enum FabricType { Quilt, Curtain, Cable }
        public FabricType type;
        public TransitProp control;
        public TransitRide ride;
        public float[] u, v;
        public Vector3[] rest, extended;
        public int[] pinned, beltRows;
        public Transform[] runners;
        public float[] runnerWeights;
        public bool hasClearance;
        public bool flipBindingV;
        public FurnishingSurface quilt;
        public float cableTravel=.17f;
        public Vector3 clearanceMin, clearanceMax;
        public float radius = .009f;
        public bool IsQuilt => type==FabricType.Quilt;
        public bool IsCurtain => type==FabricType.Curtain;
        public bool IsCable => type==FabricType.Cable;
        public string Gesture => IsQuilt ? "Brush quilt" : IsCurtain ? "Move hem" : "Pluck service loop";
        public string DisplayName=>IsQuilt?"Berth restraint quilt":IsCurtain?"Privacy screen hem":partId=="loom_service_power"?"Power service loop":"Fiber service loop";
        public bool Accessible => !IsCable || control.Position > .60f;
        public float PinError { get; private set; }
        public float Deflection { get; private set; }
        public int Contacts { get; private set; }
        public float RunnerTravel=>runnerHome==null||runnerHome.Length==0?0:Mathf.Abs(runners[runners.Length-1].localPosition.z-runnerHome[runnerHome.Length-1].z);
        const float Step = 1f/90;
        struct Link {public int a,b;public float lo,hi,stiff,length;}
        struct Binding {public int a,b,c,d;public Vector4 weights;public Vector3 offset,normal;}
        sealed class Skin {public Mesh mesh;public Binding[] binds;public Matrix4x4 toMesh;public Vector3[] vertices,normals;}
        readonly List<Skin> skins=new List<Skin>();
        Link[] links;
        Vector3[] points,old,reference,neutral,runnerHome,gripHome,collisionVertices;
        Quaternion[] inverseFrames,frames;
        float[] loft,imprint,gripWeight,closedX,openX,hemClearance;
        bool[] pin,belt;
        int nu,nv;
        float accumulated,lastRail=-1,previousDoor,occupied,colliderClock,skinClock;
        bool gripped;
        Vector3 pullDelta;
        Mesh collisionMesh;MeshCollider shell;int[] collisionIndices;
        Passenger passenger;
        Quaternion Frame(Vector3[] p,int i) {
            int col=i%nu,row=i/nu;var across=p[i+(col<nu-1?1:0)]-p[i-(col>0?1:0)];
            if(IsCable)return Quaternion.FromToRotation(Vector3.right,across.normalized);
            var along=p[i+(row<nv-1?nu:0)]-p[i-(row>0?nu:0)];
            var normal=Vector3.Cross(across,along).normalized;
            return Quaternion.LookRotation(normal,Vector3.Cross(normal,across).normalized);
        }
        static int Interval(float[] knots,float value,out float frac) {
            int lo=0,hi=knots.Length-1;
            while(hi-lo>1){int mid=(lo+hi)/2;if(value<knots[mid])hi=mid;else lo=mid;}
            frac=Mathf.Clamp01((value-knots[lo])/Mathf.Max(.000001f,knots[lo+1]-knots[lo]));return lo;
        }
        void Setup() {
            if(points!=null||rest==null||rest.Length<2)return;
            passenger=FindFirstObjectByType<Passenger>();nu=IsCable?rest.Length:u.Length;nv=IsCable?1:v.Length;
            int count=rest.Length;points=(Vector3[])rest.Clone();old=(Vector3[])rest.Clone();reference=(Vector3[])rest.Clone();neutral=(Vector3[])rest.Clone();
            pin=new bool[count];belt=new bool[nv];foreach(int k in pinned)pin[k]=true;if(beltRows!=null)foreach(int row in beltRows)belt[row]=true;
            inverseFrames=new Quaternion[count];frames=new Quaternion[count];loft=new float[count];imprint=new float[count];gripWeight=new float[count];gripHome=new Vector3[count];
            hemClearance=new float[count];
            closedX=new float[nv];openX=new float[nv];runnerHome=new Vector3[runners?.Length??0];
            for(int i=0;i<runnerHome.Length;i++)runnerHome[i]=runners[i].localPosition;
            var axis=(rest[count-1]-rest[0]).normalized;
            float curlSign=Vector3.Cross(axis,rest[count/2]-rest[0]).x>0?-1:1;
            for(int row=0;row<nv;row++){
                float low=float.MaxValue,high=float.MinValue,loOpen=float.MaxValue,hiOpen=float.MinValue;
                for(int col=0;col<nu;col++){
                    int i=row*nu+col;inverseFrames[i]=Quaternion.Inverse(Frame(rest,i));
                    float uu=IsCable?(float)col/(nu-1):u[col],vv=IsCable?0:v[row],distance=1;
                    if(beltRows!=null)foreach(int j in beltRows)distance=Mathf.Min(distance,Mathf.Abs(vv-v[j]));
                    loft[i]=(.055f+.074f*uu+.023f*Mathf.Cos(vv*6.3f))*Mathf.SmoothStep(0,1,Mathf.Clamp01(distance/.125f));
                    float x=(uu-.52f)/.32f,z=(vv-.37f)/.31f,h=(uu-.49f)/.24f,s=(vv-.77f)/.23f;
                    imprint[i]=Mathf.Min(1,Mathf.Exp(-(x*x+z*z)*1.37f)+.58f*Mathf.Exp(-(h*h+s*s)*1.45f));
                    if(IsCable)neutral[i]=rest[0]+Quaternion.AngleAxis(curlSign*.91f*Mathf.Rad2Deg*Mathf.Min(1,Mathf.Sin(uu*Mathf.PI)*2.8f),axis)*(rest[i]-rest[0]);
                    low=Mathf.Min(low,rest[i].x);high=Mathf.Max(high,rest[i].x);
                    if(extended!=null&&extended.Length==count){loOpen=Mathf.Min(loOpen,extended[i].x);hiOpen=Mathf.Max(hiOpen,extended[i].x);}
                }
                closedX[row]=(low+high)/2;openX[row]=(loOpen+hiOpen)/2;
            }
            var bars=new List<Link>();
            void Add(int a,int b,float low,float high,float stiff){bars.Add(new Link{a=a,b=b,lo=low,hi=high,stiff=stiff,length=Vector3.Distance(rest[a],rest[b])});}
            for(int row=0;row<nv;row++)for(int col=0;col<nu;col++){
                int i=row*nu+col;
                if(col+1<nu)Add(i,i+1,IsCable?.999f:.94f,IsCable?1.001f:IsQuilt?1.045f:1.014f,.94f);
                if(row+1<nv)Add(i,i+nu,.974f,IsQuilt?1.045f:1.009f,.94f);
                if(row+1<nv&&col+1<nu){Add(i,i+nu+1,.94f,1.055f,.65f);Add(i+1,i+nu,.94f,1.055f,.65f);}
                if(col+2<nu)Add(i,i+2,IsCable?.91f:.88f,IsCable?1.018f:1.065f,.49f);
                if(row+2<nv)Add(i,i+2*nu,.947f,1.04f,.55f);
            }
            links=bars.ToArray();
            foreach(var mf in GetComponentsInChildren<MeshFilter>(true))Bind(mf);
            shell=gameObject.AddComponent<MeshCollider>();gameObject.layer=Passenger.PropRay;
            collisionMesh=new Mesh{name=partId+" contact surface"};collisionMesh.MarkDynamic();MakeContactMesh();SkinMesh(true);
        }
        Binding Map(Vector3 p,Vector2 uv,bool secondary) {
            if(IsCable){
                float best=float.MaxValue,k=0;int at=0;
                for(int j=0;j+1<nu;j++){var d=rest[j+1]-rest[j];float t=Mathf.Clamp01(Vector3.Dot(p-rest[j],d)/Mathf.Max(1e-10f,d.sqrMagnitude));float err=(rest[j]+d*t-p).sqrMagnitude;if(err<best){best=err;at=j;k=t;}}
                return new Binding{a=at,b=at+1,c=at,d=at,weights=new Vector4(1-k,k,0,0)};
            }
            if(secondary&&flipBindingV)uv.y=1-uv.y;
            if(!secondary){
                Vector3 a=rest[0],b=rest[rest.Length-1];
                uv=IsQuilt?new Vector2((p.x-a.x)/(b.x-a.x),(p.z-a.z)/(b.z-a.z)):new Vector2((p.z-a.z)/(b.z-a.z),(p.y-a.y)/(b.y-a.y));
            }
            int x=Interval(u,uv.x,out float s),y=Interval(v,uv.y,out float t2),i=y*nu+x;
            return new Binding{a=i,b=i+1,c=i+nu,d=i+nu+1,weights=new Vector4((1-s)*(1-t2),s*(1-t2),(1-s)*t2,s*t2)};
        }
        static Vector3 Weighted(Vector3[] p,Binding b)=>p[b.a]*b.weights.x+p[b.b]*b.weights.y+p[b.c]*b.weights.z+p[b.d]*b.weights.w;
        void Bind(MeshFilter filter) {
            var mesh=Instantiate(filter.sharedMesh);mesh.name=partId+" skin";mesh.MarkDynamic();filter.sharedMesh=mesh;
            var src=mesh.vertices;var n=mesh.normals;var uv2=mesh.uv2;
            var from=transform.worldToLocalMatrix*filter.transform.localToWorldMatrix;
            var skin=new Skin{mesh=mesh,toMesh=from.inverse,binds=new Binding[src.Length],vertices=new Vector3[src.Length],normals=new Vector3[src.Length]};
            for(int i=0;i<src.Length;i++){
                var p=from.MultiplyPoint3x4(src[i]);var bind=Map(p,uv2.Length==src.Length?uv2[i]:Vector2.zero,uv2.Length==src.Length);
                bind.offset=p-Weighted(rest,bind);bind.normal=from.MultiplyVector(n[i]).normalized;skin.binds[i]=bind;
            }
            var bounds=mesh.bounds;bounds.Expand(.6f);if(IsCurtain)bounds.Expand(new Vector3(.4f,.2f,5));mesh.bounds=bounds;skins.Add(skin);
        }
        void MakeContactMesh(){
            var tris=new List<int>();
            if(IsCable){
                collisionIndices=new int[nu];for(int i=0;i<nu;i++)collisionIndices[i]=i;
                collisionVertices=new Vector3[nu*6];
                for(int i=0;i+1<nu;i++)for(int j=0;j<6;j++){int a=i*6+j,b=i*6+(j+1)%6;tris.AddRange(new[]{a,b,a+6,b,b+6,a+6});}
            }else{
                int nx=Mathf.Min(16,nu),ny=Mathf.Min(16,nv);collisionIndices=new int[nx*ny];collisionVertices=new Vector3[nx*ny];
                for(int y=0;y<ny;y++)for(int x=0;x<nx;x++){
                    int j=y*nx+x;collisionIndices[j]=Mathf.RoundToInt((float)y/(ny-1)*(nv-1))*nu+Mathf.RoundToInt((float)x/(nx-1)*(nu-1));
                    if(x<nx-1&&y<ny-1)tris.AddRange(new[]{j,j+1,j+nx,j+1,j+nx+1,j+nx,j,j+nx,j+1,j+1,j+nx,j+nx+1});
                }
            }
            collisionMesh.vertices=collisionVertices;collisionMesh.triangles=tris.ToArray();
        }
        void SetRail(float travel) {
            if(!IsCurtain||extended==null||extended.Length!=rest.Length||Mathf.Abs(travel-lastRail)<.000001f)return;
            lastRail=travel;float start=rest[nu-1].z-rest[0].z,end=extended[nu-1].z-extended[0].z;
            float span=Mathf.Lerp(start,end,travel),q=Mathf.Clamp01((span*span-start*start)/(end*end-start*start));
            for(int i=0;i<rest.Length;i++){
                int row=i/nu;var a=rest[i];var b=extended[i];var p=Vector3.Lerp(a,b,travel);
                float aa=a.x-closedX[row],bb=b.x-openX[row];
                if(aa*bb>=0)p.x=Mathf.Lerp(closedX[row],openX[row],travel)+Mathf.Sign(Mathf.Abs(aa)>.00001f?aa:bb)*Mathf.Sqrt(Mathf.Lerp(aa*aa,bb*bb,q));
                reference[i]=p;
            }
            for(int j=0;j<links.Length;j++)links[j].length=Vector3.Distance(reference[links[j].a],reference[links[j].b]);
            for(int i=0;i<runnerHome.Length;i++)runners[i].localPosition=runnerHome[i]+Vector3.forward*runnerWeights[i]*(span-start);
        }
        void Lengths() {
            foreach(var link in links){
                var d=points[link.b]-points[link.a];float sq=d.sqrMagnitude;
                float lo=link.lo*link.length,hi=link.hi*link.length;
                if(sq<1e-12f||sq>=lo*lo&&sq<=hi*hi)continue;
                int free=(pin[link.a]?0:1)+(pin[link.b]?0:1);if(free==0)continue;
                float length=Mathf.Sqrt(sq);var delta=d*((length-Mathf.Clamp(length,lo,hi))*link.stiff/(length*free));
                if(!pin[link.a])points[link.a]+=delta;if(!pin[link.b])points[link.b]-=delta;
            }
        }
        void Tick(Vector3 force,float fan,float travel,float cover,float doorSpeed,float time,bool sitting) {
            SetRail(travel);
            occupied=Mathf.Lerp(occupied,sitting?1:0,1-Mathf.Exp(-8*Step));
            float load=Mathf.Clamp01(-force.y/9.80665f)*occupied;
            float memory=IsQuilt?25:IsCurtain?5.2f:5.6f,drag=Mathf.Exp(-Step*(IsQuilt?5.3f:IsCurtain?6.7f:3.05f));
            Vector3 origin=transform.position;float range=IsQuilt?.175f:IsCurtain?.205f:cableTravel;
            for(int i=0;i<points.Length;i++){
                var current=points[i];var target=reference[i];
                if(pin[i]){points[i]=old[i]=target;continue;}
                float uu=IsCable?(float)i/(nu-1):u[i%nu],vv=IsCable?0:v[i/nu];
                if(IsQuilt){target.y+=loft[i];target.x+=.13f*uu*loft[i];}
                else if(IsCurtain){float curl=Mathf.Sin(uu*Mathf.PI)*vv*vv;target+=new Vector3(.086f,.031f,0)*curl;}
                else target=neutral[i];
                var world=transform.TransformPoint(current);float wz=-world.z,drop=2.58f-world.y,roomZ=IsCable?3.8f:0;
                if(IsCurtain&&quilt)hemClearance[i]=quilt.HemLimit(world)-origin.x;
                float dz=Mathf.Min(Mathf.Abs(wz-roomZ+.4715f),Mathf.Abs(wz-roomZ-1.4145f));
                float jet=(Mathf.Abs(world.x)-.80f*drop)/(.29f+.23f*drop),az=dz/(.45f+.18f*drop);
                float air=fan*(IsCable?cover:1)*Mathf.Exp(-.5f*(jet*jet+az*az));
                float gust=air*(1+.28f*Mathf.Sin(time*4.4f-world.y*3+wz*2.1f)+.13f*Mathf.Sin(time*7.1f-wz*3.3f));
                float wind=gust*(IsQuilt?.29f:IsCurtain?.78f:.16f);
                var local=force+(target-current)*memory+new Vector3(Mathf.Sign(world.x)*wind-(IsCable?.74f*doorSpeed:0),-.22f*wind-(IsQuilt?load*imprint[i]*15:0),-.31f*wind);
                points[i]=current+(current-old[i])*drag+local*(Step*Step);old[i]=current;
            }
            for(int pass=0;pass<7;pass++){
                Lengths();
                for(int i=0;i<points.Length;i++){
                    if(pin[i])continue;var home=reference[i];var p=home+Vector3.ClampMagnitude(points[i]-home,range);
                    if(IsQuilt){
                        p.y=Mathf.Max(p.y,home.y-.040f*load*imprint[i]);if(belt[i/nu])p.y=Mathf.Min(p.y,home.y+.0015f);
                    }else if(IsCurtain){
                        if(p.y+origin.y<1.08f)p.x=Mathf.Max(p.x,-1.322f-origin.x);
                        p.x=Mathf.Clamp(p.x,-1.355f-origin.x,-.98f-origin.x);p.z=Mathf.Clamp(p.z,-1.213f-origin.z,1.208f-origin.z);
                        if(quilt)p.x=Mathf.Max(p.x,hemClearance[i]);
                        if(i%nu>0){float gap=.24f*(home.z-reference[i-1].z);if(gap<0)p.z=Mathf.Min(p.z,points[i-1].z+gap);else p.z=Mathf.Max(p.z,points[i-1].z+gap);}
                    }else{
                        if(hasClearance)p=Vector3.Max(clearanceMin,Vector3.Min(clearanceMax,p));
                        p.x=Mathf.Clamp(p.x,1.805f-.065f*cover-origin.x,2.042f-origin.x);p.y=Mathf.Max(p.y,.982f-origin.y);
                    }
                    if(gripped&&gripWeight[i]>0)p=Vector3.Lerp(p,gripHome[i]+pullDelta,.46f*gripWeight[i]);
                    points[i]=p;
                }
            }
        }
        float HemLimit(Vector3 world) {
            Setup();float z=-world.z;
            if(z<-.625f||z>1.033f||world.y>1.33f)return -1.355f;
            float q=Mathf.InverseLerp(-.605f,1.013f,z);int row=Interval(v,q,out float weight);
            var edge=transform.TransformPoint(Vector3.Lerp(points[row*nu+nu-1],points[(row+1)*nu+nu-1],weight));
            float amount=1-Mathf.SmoothStep(0,1,Mathf.InverseLerp(edge.y+.015f,edge.y+.065f,world.y));
            float limit=Mathf.Lerp(-1.355f,edge.x+.015f,amount);
            if(Mathf.Abs(z+.461f)<.052f||Mathf.Abs(z-.533f)<.052f)
                limit=Mathf.Max(limit,Mathf.Lerp(-1.355f,-1.237f,1-Mathf.SmoothStep(0,1,Mathf.InverseLerp(1.065f,1.105f,world.y))));
            return limit;
        }
        static Quaternion Blend(Quaternion[] q,Binding b) {
            var a=q[b.a];var c=q[b.b];var d=q[b.c];var e=q[b.d];var w=b.weights;
            return Quaternion.Normalize(new Quaternion(a.x*w.x+c.x*w.y+d.x*w.z+e.x*w.w,a.y*w.x+c.y*w.y+d.y*w.z+e.y*w.w,a.z*w.x+c.z*w.y+d.z*w.z+e.z*w.w,a.w*w.x+c.w*w.y+d.w*w.z+e.w*w.w));
        }
        void SkinMesh(bool cook,bool updateSkin=true){
            PinError=0;Deflection=0;
            for(int i=0;i<points.Length;i++){
                if(updateSkin){var q=Frame(points,i)*inverseFrames[i];if(q.w<0)q=new Quaternion(-q.x,-q.y,-q.z,-q.w);frames[i]=q;}
                float move=Vector3.Distance(points[i],reference[i]);if(pin[i])PinError=Mathf.Max(PinError,move);else Deflection=Mathf.Max(Deflection,move);
            }
            if(updateSkin)foreach(var s in skins){
                for(int i=0;i<s.binds.Length;i++){
                    var b=s.binds[i];var q=Blend(frames,b);
                    s.vertices[i]=s.toMesh.MultiplyPoint3x4(Weighted(points,b)+q*b.offset);
                    s.normals[i]=s.toMesh.MultiplyVector(q*b.normal).normalized;
                }
                s.mesh.SetVertices(s.vertices,0,s.vertices.Length,MeshUpdateFlags.DontRecalculateBounds);
                s.mesh.SetNormals(s.normals,0,s.normals.Length,MeshUpdateFlags.DontRecalculateBounds);
            }
            if(!cook)return;
            if(IsCable){
                for(int i=0;i<nu;i++){var t=(points[Mathf.Min(nu-1,i+1)]-points[Mathf.Max(0,i-1)]).normalized;
                    var a=Vector3.Cross(t,Mathf.Abs(t.y)<.9f?Vector3.up:Vector3.forward).normalized;var b=Vector3.Cross(t,a);
                    for(int j=0;j<6;j++){float k=j*Mathf.PI/3;collisionVertices[i*6+j]=points[i]+radius*(a*Mathf.Cos(k)+b*Mathf.Sin(k));}}
            }else for(int i=0;i<collisionIndices.Length;i++)collisionVertices[i]=points[collisionIndices[i]];
            shell.sharedMesh=null;collisionMesh.vertices=collisionVertices;collisionMesh.RecalculateBounds();shell.sharedMesh=collisionMesh;
        }
        public void Advance(float dt) {
            Setup();if(points==null||!ride||ride.props.Count==0)return;
            accumulated+=Mathf.Clamp(dt,0,.12f);int count=Mathf.FloorToInt((accumulated+.0000001f)/Step);if(count<1)return;
            float door=ride.props["service_cabinet"].Position,rail=ride.props["privacy_curtain"].Position,start=lastRail<0?rail:lastRail;
            float doorSpeed=Mathf.Clamp((door-previousDoor)/(count*Step),-5,5);
            var force=transform.InverseTransformDirection(ride.Forces.Apparent-ride.StructureImpulse);
            for(int i=1;i<=count;i++){
                float f=(float)i/count;
                Tick(force,ride.systems.FanRPM/840,Mathf.Lerp(start,rail,f),Mathf.Lerp(previousDoor,door,f),doorSpeed,(float)ride.Seconds-(count-i)*Step,passenger&&passenger.InBerth);
            }
            previousDoor=door;accumulated=Mathf.Max(0,accumulated-count*Step);
            bool cook=(colliderClock-=dt)<=0;if(cook)colliderClock=.09f;
            bool updateSkin=(skinClock-=dt)<=0||gripped;
            if(updateSkin){
                float distance=passenger?Vector3.Distance(passenger.eye.transform.position,transform.position):20;
                float eyeZ=passenger?passenger.eye.transform.position.z:0;
                bool inside=IsCable?eyeZ< -1.72f:eyeZ> -2.05f&&eyeZ<2.05f;
                skinClock=gripped?0:!inside||distance>4.2f?.24f:Passenger.SoftwareGraphics?.095f:1/42f;
            }
            SkinMesh(cook,updateSkin);
        }
        public Vector3 Sample(float along,float down){
            Setup();if(IsCable){float pos=Mathf.Clamp01(along)*(nu-1);int j=Mathf.Min(nu-2,(int)pos);return transform.TransformPoint(Vector3.Lerp(points[j],points[j+1],pos-j));}
            int col=Interval(u,along,out float s),row=Interval(v,down,out float t),i=row*nu+col;
            return transform.TransformPoint(Vector3.Lerp(Vector3.Lerp(points[i],points[i+1],s),Vector3.Lerp(points[i+nu],points[i+nu+1],s),t));
        }
        public Vector3 TouchPoint=>Sample(IsQuilt?.76f:.52f,IsQuilt?.88f:.78f);
        public bool Impulse(Vector3 worldPoint,Vector3 velocity,float width) {
            Setup();if(!Accessible)return false;var p=transform.InverseTransformPoint(worldPoint);var speed=transform.InverseTransformDirection(velocity);
            float max=0;for(int i=0;i<points.Length;i++){if(pin[i])continue;float w=Mathf.Exp(-(points[i]-p).sqrMagnitude/(width*width));old[i]-=speed*(w*Step);max=Mathf.Max(max,w);}return max>.10f;
        }
        public bool Brush(Vector3 point)=>Impulse(point,IsQuilt?new Vector3(.34f,.94f,-.17f):IsCurtain?new Vector3(.91f,.19f,-.15f):new Vector3(-1.05f,.27f,-.10f),IsCable?.104f:.225f);
        public bool Grip(Vector3 point){
            Setup();if(!Accessible)return false;point=transform.InverseTransformPoint(point);int best=-1;float distance=.17f*.17f;
            for(int i=0;i<points.Length;i++){if(pin[i])continue;float d=(point-points[i]).sqrMagnitude;if(d<distance){distance=d;best=i;}}
            if(best<0)return false;float width=IsCable?.075f:.13f;int row=best/nu,col=best%nu;
            for(int i=0;i<points.Length;i++){
                float w=pin[i]||Mathf.Abs((i%nu)-col)>.238f*nu||Mathf.Abs(i/nu-row)>.25f*nv?0:Mathf.Exp(-(points[i]-points[best]).sqrMagnitude/(width*width*.55f));
                gripWeight[i]=w>.06f?w:0;gripHome[i]=points[i];
            }
            gripped=true;pullDelta=Vector3.zero;return true;
        }
        public void Pull(Vector3 worldDelta){pullDelta=Vector3.ClampMagnitude(transform.InverseTransformDirection(worldDelta),IsCable?.12f:IsQuilt?.145f:.19f);}
        public void Release(){gripped=false;pullDelta=Vector3.zero;}
        public void React(Vector3 point,Vector3 velocity){if(Impulse(point,velocity,IsCable?.072f:.145f))Contacts++;}
        void Update()=>Advance(Time.unscaledDeltaTime);
        void OnDestroy(){foreach(var s in skins)if(s.mesh)Destroy(s.mesh);if(collisionMesh)Destroy(collisionMesh);}
    }
}
