using System.Collections.Generic;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

namespace Upwell.Editor {
    // One revolute assembly: six alternating habitat/lighting sectors and three sun mirrors.
    static class HabitatFabrication {
        sealed class MeshSet {
            readonly List<Vector3> vertices=new List<Vector3>();
            readonly List<Vector3> normals=new List<Vector3>();
            readonly List<Vector2> uv=new List<Vector2>();
            readonly List<int>[] indices;
            public MeshSet(int count){indices=new List<int>[count];for(int i=0;i<count;i++)indices[i]=new List<int>();}
            static Vector2 HullUV(Vector3 point,float initialAngle) {
                float angle=Mathf.Atan2(point.y,point.x)*Mathf.Rad2Deg;
                float around=(initialAngle+Mathf.DeltaAngle(initialAngle,angle))/360f+.171f;
                return new Vector2(around,(point.z+3.7f)/7.4f);
            }
            public void Quad(Vector3 a,Vector3 b,Vector3 c,Vector3 d,Vector3 outward,int material,bool pressureHull=false) {
                if(Vector3.Dot(Vector3.Cross(b-a,c-a),outward)<0){var tmp=b;b=d;d=tmp;}
                int n=vertices.Count;vertices.Add(a);vertices.Add(b);vertices.Add(c);vertices.Add(d);
                if(pressureHull) {
                    float start=Mathf.Atan2(a.y,a.x)*Mathf.Rad2Deg;
                    uv.Add(HullUV(a,start));uv.Add(HullUV(b,start));uv.Add(HullUV(c,start));uv.Add(HullUV(d,start));
                } else {
                    for(int j=0;j<4;j++)uv.Add(Vector2.zero);
                }
                Vector3 normal=Vector3.Cross(b-a,c-a).normalized;
                for(int j=0;j<4;j++)normals.Add(normal);
                indices[material].AddRange(new[]{n,n+1,n+2,n,n+2,n+3});
            }
            public void Tube(Vector3 a,Vector3 b,float r,int mat,int sides=6) {
                Vector3 t=(b-a).normalized,r0=Vector3.Cross(t,Mathf.Abs(t.y)>.75f?Vector3.right:Vector3.up).normalized*r,r1=Vector3.Cross(t,r0);
                for(int j=0;j<sides;j++) {
                    float u=j*2*Mathf.PI/sides,v=(j+1)*2*Mathf.PI/sides;
                    Vector3 p=Mathf.Cos(u)*r0+Mathf.Sin(u)*r1,q=Mathf.Cos(v)*r0+Mathf.Sin(v)*r1;
                    Quad(a+p,b+p,b+q,a+q,p+q,mat);
                }
            }
            public Mesh Finish(string name){
                var mesh=new Mesh{name=name,indexFormat=IndexFormat.UInt32};
                mesh.SetVertices(vertices);mesh.SetNormals(normals);mesh.SetUVs(0,uv);mesh.subMeshCount=indices.Length;
                for(int k=0;k<indices.Length;k++)mesh.SetTriangles(indices[k],k,false);mesh.RecalculateBounds();return mesh;
            }
        }
        static Vector3 C(float phi,float rad,float z)=>new Vector3(Mathf.Cos(phi)*rad,Mathf.Sin(phi)*rad,z);
        static void Band(MeshSet g,float z,float radius,float width,int m){
            for(int j=0;j<96;j++){float a=j*Mathf.PI/48,b=(j+1)*Mathf.PI/48;g.Quad(C(a,radius,z-width),C(b,radius,z-width),C(b,radius,z+width),C(a,radius,z+width),C((a+b)/2,1,0),m);}
        }
        public static Mesh Build() {
            var g=new MeshSet(6);
            for(int a=0;a<96;a++){
                float p=a*Mathf.PI/48, q=(a+1)*Mathf.PI/48;int sector=a/16;
                for(int j=0;j<36;j++) {
                    float za=-3.7f+j*7.4f/36,zb=za+7.4f/36-.009f;float radius=(sector%2==0)?1.35f:1.29f;
                    g.Quad(C(p,radius,za),C(q-.003f,radius,za),C(q-.003f,radius,zb),C(p,radius,zb),C((p+q)*.5f,1,0),3,true);
                    if(sector%2!=0&&j%4==0)g.Tube(C(p,1.32f,za),C(q,1.32f,za),.009f,2,4);
                }
                for(int sign=-1;sign<=1;sign+=2) {
                    for(int k=0;k<16;k++){
                        float t=k/16f,t2=(k+1)/16f;float r=1.35f*Mathf.Cos(t*Mathf.PI*.47f),r2=1.35f*Mathf.Cos(t2*Mathf.PI*.47f);
                        float z=sign*(3.7f+.68f*Mathf.Sin(t*Mathf.PI*.5f)),z2=sign*(3.7f+.68f*Mathf.Sin(t2*Mathf.PI*.5f));
                        g.Quad(C(p,r,z),C(q,r,z),C(q,r2,z2),C(p,r2,z2),C((p+q)*.5f,.5f,sign*.5f),k%3==2?1:0);
                    }
                }
                if(a%2==0)g.Tube(C(p,1.364f,-3.69f),C(p,1.364f,3.69f),.012f,2,5);
                if(a%16==3||a%16==13){
                    for(int bay=0;bay<19;bay++){
                        float z=-3.44f+bay*.378f;
                        g.Quad(C(p,1.356f,z),C(p+.012f,1.356f,z),C(p+.012f,1.356f,z+.23f),C(p,1.356f,z+.23f),C(p,1,0),5);
                    }
                }
            }
            for(int j=0;j<=12;j++)Band(g,-3.7f+j*7.4f/12,1.385f,j%3==0?.034f:.014f,j%3==0?0:2);
            for(int side=0;side<3;side++) {
                float angle=side*Mathf.PI*2/3+.37f;Vector3 normal=C(angle,1,0),tan=C(angle+Mathf.PI/2,1,0);
                for(int j=0;j<18;j++) {
                    float z=-3.4f+j*.39f;
                    Vector3 ctr=normal*(2.16f+(z+3.4f)*.14f)+Vector3.forward*z;
                    Vector3 following=ctr+Vector3.forward*.38f+normal*.053f;
                    for(int k=0;k<6;k++) {
                        float x=-.82f+k*.275f;
                        g.Quad(ctr+tan*x,ctr+tan*(x+.26f),following+tan*(x+.26f),following+tan*x,normal,4);
                    }
                    g.Tube(ctr-tan*.85f,ctr+tan*.85f,.014f,2);
                    foreach(float edge in new[]{-.85f,.85f})g.Tube(ctr+tan*edge,following+tan*edge,.021f,1);
                    if(j%3==0){
                        Vector3 foot=C(angle,1.36f,z-.25f);
                        g.Tube(foot,ctr-tan*.64f,.022f,0);g.Tube(foot,ctr+tan*.64f,.022f,0);
                    }
                }
            }
            for(int side=-1;side<=1;side+=2){
                for(int j=0;j<60;j++){
                    float a=j*Mathf.PI/30,b=(j+1)*Mathf.PI/30;
                    g.Tube(C(a,.83f,side*4.65f),C(b,.83f,side*4.65f),.035f,0);
                    g.Tube(C(a,.71f,side*4.94f),C(b,.71f,side*4.94f),.031f,1);
                    if(j%2==0)g.Tube(C(a,.83f,side*4.65f),C(b,.71f,side*4.94f),.017f,2);
                    if(j%6==0){
                        g.Tube(C(a,.37f,side*4.21f),C(a,.83f,side*4.65f),.025f,0);
                        g.Tube(C(a,.83f,side*4.65f),C(a,.84f,side*4.70f),.026f,5);
                    }
                }
                g.Tube(new Vector3(0,0,side*4.31f),new Vector3(0,0,side*5.22f),.16f,2,16);
            }
            return g.Finish("Aster Reach light collectors and pressure cylinder");
        }
    }
}

