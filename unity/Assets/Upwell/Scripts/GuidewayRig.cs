using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;
namespace Upwell{
    public sealed class GuidewayRig:MonoBehaviour{
        [Serializable] public class Roller{public string id;public GameObject mesh;public Vector3 pivot;public float radius,sign;}
        public GameObject span,splice,bogie;public Roller[] rollers;
        public Vector3[] lanes;public Material tow,rail;public float repeat=8,spliceEvery=16;
        readonly List<Light> headlamps=new List<Light>();
        readonly List<Transform> spans=new List<Transform>(),splices=new List<Transform>(),wheels=new List<Transform>();
        readonly List<Roller> wheelInfo=new List<Roller>();
        readonly List<MeshRenderer> spinCoverage=new List<MeshRenderer>();
        readonly List<Transform> horizon=new List<Transform>();
        double lastAltitude=-1,travel;Mesh horizonMesh;GuidewayFinish finish;
        public double DistanceTravelled=>travel;
        public int ContactRollers=>wheels.Count;
        GameObject Copy(GameObject template,Transform root,Vector3 p){var g=Instantiate(template,root,false);g.transform.localPosition=p;g.name=template.name;g.SetActive(true);return g;}
        Mesh FarGeometry(){
            var vv=new List<Vector3>();var nn=new List<Vector3>();var slots=new List<int>[5];for(int j=0;j<slots.Length;j++)slots[j]=new List<int>();
            float cut=11*repeat*.5f;var levels=new[]{-25500f,-cut,cut,25500f};
            void Cable(float x,float z,float rx,float rz,int sides,int slot,bool lens=false){
                int start=vv.Count;
                for(int j=0;j<sides;j++){
                    float a=2*Mathf.PI*j/sides,c=Mathf.Cos(a),s=Mathf.Sin(a);
                    float dx=rx*c*(lens?.67f+.33f*Mathf.Abs(c):1),dz=rz*(lens?Mathf.Sign(s)*Mathf.Pow(Mathf.Abs(s),.77f):s);
                    var n=new Vector3(dx/(rx*rx),0,-dz/(rz*rz)).normalized;
                    foreach(float y in levels){vv.Add(new Vector3(x+dx,y,-(z+dz)));nn.Add(n);}
                }
                for(int j=0;j<sides;j++)for(int side=0;side<4;side+=2){
                    int a=start+j*4+side,b=start+(j+1)%sides*4+side;
                    // Imported glTF Z is mirrored into the Unity carriage survey.
                    slots[slot].AddRange(new[]{a,b+1,a+1,a,b,b+1});
                }
            }
            Cable(0,0,.108f,.376f,40,0,true);
            foreach(int side in new[]{-1,1}){
                for(int k=-4;k<=4;k++){float z=k*.076f;Cable(side*.094f*Mathf.Sqrt(1-z*z/(.383f*.383f)),z,.0185f,.044f,12,0,true);}
                Cable(.059f,side*.485f,.063f,.063f,22,1);Cable(-.062f,side*.401f,.028f,.028f,12,2);
            }
            Cable(-.121f,.607f,.049f,.049f,14,1);Cable(-.124f,-.516f,.033f,.033f,13,3);
            Cable(-.171f,-.464f,.037f,.037f,13,2);Cable(-.172f,-.555f,.024f,.024f,13,4);
            var m=new Mesh{name="Continuous distant cable survey"};m.SetVertices(vv);m.SetNormals(nn);m.subMeshCount=slots.Length;
            for(int i=0;i<slots.Length;i++)m.SetTriangles(slots[i],i);m.RecalculateBounds();return m;
        }
        void Awake(){
            finish=new GuidewayFinish();horizonMesh=FarGeometry();
            for(int lane=0;lane<lanes.Length;lane++){
                var root=new GameObject(lane==2?"Counterline guideway":"Paired ascender guideway").transform;root.SetParent(transform,false);root.localPosition=lanes[lane];
                for(int j=0;j<11;j++){var section=Copy(span,root,Vector3.up*(j-5)*repeat);finish.Dress(section);spans.Add(section.transform);}
                for(int j=0;j<6;j++)splices.Add(Copy(splice,root,Vector3.up*(j-2)*spliceEvery).transform);
                var distant=new GameObject("Continuous guide rails");distant.layer=ExteriorRig.ExteriorLayer;distant.transform.SetParent(root,false);horizon.Add(distant.transform);
                distant.AddComponent<MeshFilter>().sharedMesh=horizonMesh;var r=distant.AddComponent<MeshRenderer>();r.sharedMaterials=finish.Horizon;r.shadowCastingMode=ShadowCastingMode.Off;
                if(lane==2)continue;Copy(bogie,root,Vector3.zero);finish.MountJournals(root);
                var lamp=new GameObject("Bogie inspection flood");lamp.transform.SetParent(root,false);lamp.transform.localPosition=new Vector3(.73f,.53f,.62f);
                lamp.transform.localRotation=Quaternion.LookRotation(new Vector3(-.73f,-.47f,-.35f));var flood=lamp.AddComponent<Light>();
                flood.type=LightType.Spot;flood.range=7;flood.intensity=6.3f;flood.spotAngle=85;flood.innerSpotAngle=44;flood.color=new Color(.81f,.91f,1);
                flood.cullingMask=1<<ExteriorRig.ExteriorLayer;flood.shadows=LightShadows.Soft;flood.shadowBias=.012f;flood.enabled=false;headlamps.Add(flood);
                foreach(var w in rollers){var wheel=Copy(w.mesh,root,w.pivot);wheels.Add(wheel.transform);wheelInfo.Add(w);spinCoverage.Add(finish.MountWheel(wheel,w.radius));}
            }
        }
        public void Flood(bool on){foreach(var l in headlamps)l.enabled=on;}
        static double Wrap(double x,double l)=>x-Math.Floor(x/l)*l;
        public void Move(double seconds,double km,double metersPerSecond,float dt,bool seek){
            travel=km*1000;
            float speed=lastAltitude<0||seek||dt<.001f?0:(float)(Math.Abs(km-lastAltitude)*1000/dt);
            lastAltitude=km;
            float shutter=Mathf.Min(79,speed*Mathf.Min(1f/30,Mathf.Max(0,dt)*.5f));GuidewayFinish.PublishShutter(shutter);
            float wind=Mathf.Exp(-(float)km/6)*.0065f;
            float phase=(float)Wrap(travel,repeat),collar=(float)Wrap(travel,spliceEvery);
            foreach(var far in horizon)far.localPosition=Vector3.down*phase;
            for(int i=0;i<spans.Count;i++){float y=((i%11)-5)*repeat-phase;
                // Keep the near/far seam on the survey datum at both extremes.
                float contact=Mathf.SmoothStep(0,1,Mathf.Clamp01((Mathf.Abs(y)-4)/7))*Mathf.Clamp01((34-Mathf.Abs(y))/8);
                spans[i].localPosition=new Vector3(wind*contact*Mathf.Sin(y*.073f+(float)seconds*.38f),y,0);}
            for(int i=0;i<splices.Count;i++){float y=((i%6)-2)*spliceEvery-collar;
                splices[i].localPosition=new Vector3(wind*Mathf.SmoothStep(0,1,Mathf.Clamp01((Mathf.Abs(y)-4)/7))*Mathf.Sin(y*.073f+(float)seconds*.38f),y,0);}
            for(int i=0;i<wheels.Count;i++){var w=wheelInfo[i];float angle=(float)Wrap(w.sign*travel/w.radius*(180/Math.PI),360);
                wheels[i].localRotation=Quaternion.AngleAxis(angle,Vector3.forward);spinCoverage[i].enabled=shutter/w.radius>.24f;}
        }
        void OnDestroy(){finish?.Dispose();if(horizonMesh)Destroy(horizonMesh);}
    }
}
