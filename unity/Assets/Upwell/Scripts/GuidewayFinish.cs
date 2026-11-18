using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;

namespace Upwell {
    // Local guideway finishes. Each replacement is shared across every
    // instance of this part; the vehicle's original materials stay shared.
    sealed class GuidewayFinish : IDisposable {
        readonly Shader surface=Resources.Load<Shader>("GuidewayFinish/GuideSurface");
        readonly Shader sweep=Resources.Load<Shader>("GuidewayFinish/SpokeSweep");
        readonly Dictionary<(Material,int,float),Material> materials=new Dictionary<(Material,int,float),Material>();
        readonly Dictionary<float,Mesh> annuli=new Dictionary<float,Mesh>();
        readonly Dictionary<float,Material> sweepFinishes=new Dictionary<float,Material>();
        readonly List<Material> farFinishes=new List<Material>();
        readonly Dictionary<string,Material> journalFinishes=new Dictionary<string,Material>();
        readonly GameObject journals=Resources.Load<GameObject>("GuidewayFinish/journal-caps");
        public readonly Material[] Horizon;
        static Color32 Swatch(int n) => new Color32((byte)(n>>16),(byte)(n>>8),(byte)n,255);
        static readonly int ShutterProperty=Shader.PropertyToID("_UpwellGuideShutter");
        public static void PublishShutter(float metres) => Shader.SetGlobalFloat(ShutterProperty,metres);
        public GuidewayFinish() {
            if(!surface||!sweep||!journals)throw new InvalidOperationException("The guideway's bearing hardware or surface shaders are unavailable");
            var standard=Shader.Find("Standard");
            Material Far(int rgb,float metal,float rough){
                var m=new Material(standard){color=Swatch(rgb),enableInstancing=true};
                m.SetFloat("_Metallic",metal);m.SetFloat("_Glossiness",1-rough);farFinishes.Add(m);return m;
            }
            Horizon=new[]{Far(0x30383a,.42f,.45f),Far(0x848c90,.84f,.38f),Far(0x343b40,.41f,.57f),Far(0xa4522a,.12f,.64f),Far(0x337083,.18f,.59f)};
            journalFinishes.Add("Journal_Black",Far(0x30383d,.77f,.43f));journalFinishes.Add("Journal_Nickel",Far(0x849196,.81f,.36f));
            journalFinishes.Add("Journal_Edge",Far(0x9da3a0,.84f,.32f));journalFinishes.Add("Journal_Recess",Far(0x272e30,.57f,.58f));
            journalFinishes.Add("Journal_Seal",Far(0xb7763d,.13f,.63f));
        }
        public void MountJournals(Transform bogie){
            var kit=UnityEngine.Object.Instantiate(journals,bogie,false);
            foreach(var r in kit.GetComponentsInChildren<MeshRenderer>(true)){
                r.gameObject.layer=ExteriorRig.ExteriorLayer;var slots=r.sharedMaterials;
                for(int i=0;i<slots.Length;i++){string key=slots[i].name.Replace(" (Instance)","");slots[i]=journalFinishes[key];}
                r.sharedMaterials=slots;r.receiveShadows=true;
            }
        }
        public void Dress(GameObject mount,float radius=0) {
            foreach(var r in mount.GetComponentsInChildren<MeshRenderer>(true)){
                var slots=r.sharedMaterials;
                for(int i=0;i<slots.Length;i++){
                    var original=slots[i];int mode,swatch;
                    switch(original.name){
                        case "Tow_Carbon" when radius==0:mode=1;swatch=0x2f3739;break;
                        case "Precision_Titanium" when radius==0:mode=2;swatch=0x8f979a;break;
                        case "Titanium" when radius>0:mode=3;swatch=0x8e9699;break;
                        case "Signal_Orange" when radius>0:mode=4;swatch=0xb74926;break;
                        default:continue;
                    }
                    var key=(original,mode,radius);
                    if(!materials.TryGetValue(key,out var finish)){
                        finish=new Material(surface);finish.CopyPropertiesFromMaterial(original);
                        finish.name=original.name+" · running guide";finish.SetColor("_GuideMean",Swatch(swatch));
                        finish.SetFloat("_GuideKind",mode);finish.SetFloat("_GuideRadius",Mathf.Max(.001f,radius));finish.enableInstancing=true;
                        materials.Add(key,finish);
                    }
                    slots[i]=finish;
                }
                r.sharedMaterials=slots;
            }
        }
        static Mesh RotationalEnvelope(float radius){
            var v=new List<Vector3>();var n=new List<Vector3>();var colors=new List<Color>();var indices=new List<int>();
            void Ring(float inner,float outer,float z,int rgb){
                int start=v.Count;Color tint=((Color)Swatch(rgb)).linear;
                for(int i=0;i<=56;i++){
                    float a=i*2*Mathf.PI/56;var axis=new Vector3(Mathf.Cos(a),Mathf.Sin(a),0);
                    foreach(float r in new[]{inner,outer}){v.Add(axis*r+Vector3.forward*z);n.Add(Vector3.back);colors.Add(tint);}
                    if(i<56){int j=start+2*i;indices.AddRange(new[]{j,j+3,j+1,j,j+2,j+3});}
                }
            }
            Ring(radius*.22f,radius*.755f,0,0x8e9699);
            float width=radius>.18f?.123f:.100f;
            // glTF +Z maps to Unity -Z. The three painted witness ticks are on this face only.
            Ring(radius*.71f-.009f,radius*.71f+.009f,-width*.56f-.0026f,0xb74926);
            var mesh=new Mesh{name="Swept volume of six spokes and three witness marks"};
            mesh.SetVertices(v);mesh.SetNormals(n);mesh.SetColors(colors);mesh.SetTriangles(indices,0);mesh.RecalculateBounds();return mesh;
        }
        public MeshRenderer MountWheel(GameObject wheel,float radius){
            Dress(wheel,radius);
            if(!annuli.TryGetValue(radius,out var mesh)){mesh=RotationalEnvelope(radius);annuli.Add(radius,mesh);}
            if(!sweepFinishes.TryGetValue(radius,out var mat)){
                mat=new Material(sweep){enableInstancing=true};mat.SetFloat("_GuideRadius",radius);sweepFinishes.Add(radius,mat);
            }
            var g=new GameObject("Swept spoke and paint coverage");g.layer=ExteriorRig.ExteriorLayer;g.transform.SetParent(wheel.transform,false);
            g.AddComponent<MeshFilter>().sharedMesh=mesh;var renderer=g.AddComponent<MeshRenderer>();
            renderer.sharedMaterial=mat;renderer.shadowCastingMode=ShadowCastingMode.Off;renderer.enabled=false;return renderer;
        }
        public void Dispose(){
            foreach(var m in materials.Values)UnityEngine.Object.Destroy(m);
            foreach(var m in sweepFinishes.Values)UnityEngine.Object.Destroy(m);
            foreach(var m in farFinishes)UnityEngine.Object.Destroy(m);
            foreach(var mesh in annuli.Values)UnityEngine.Object.Destroy(mesh);
        }
    }
}
