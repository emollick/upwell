using System;
using System.Collections.Generic;
using System.IO;
using UnityEngine;
using UnityEngine.Rendering;

namespace Upwell {
    // One draw covers the projected cross-sections of the original Blender
    // members. The original manufactured surfaces take over under magnification.
    public sealed class HabitatMembers : MonoBehaviour {
        readonly List<Material> owned=new List<Material>();Mesh coverage;
        static Vector3 SurveyVector(BinaryReader r) => new Vector3(-r.ReadSingle(),r.ReadSingle(),r.ReadSingle());
        public void Mount(Transform originals,IReadOnlyList<Material> finishes) {
            const string path="OrbitalHardware/";
            var distant=Resources.Load<Shader>(path+"MemberCoverage");var close=Resources.Load<Shader>(path+"MemberNear");
            var data=Resources.Load<TextAsset>(path+"members");
            if(!data||!distant||!close)throw new InvalidOperationException("The pressure-member survey or optical shaders are unavailable");
            var cutovers=new Dictionary<Material,Material>();
            foreach(var renderer in originals.GetComponentsInChildren<MeshRenderer>(true)){
                var slots=renderer.sharedMaterials;for(int i=0;i<slots.Length;i++){
                    var original=slots[i];
                    if(!cutovers.TryGetValue(original,out var mat)){
                        mat=new Material(close);mat.CopyPropertiesFromMaterial(original);mat.name=original.name+" · resolved member";
                        mat.renderQueue=2990;cutovers[original]=mat;owned.Add(mat);
                    }
                    slots[i]=mat;
                }
                renderer.sharedMaterials=slots;
            }
            var p=new List<Vector3>();var b=new List<Vector3>();var u=new List<Vector3>();var v=new List<Vector3>();
            var corners=new List<Vector2>();var settings=new List<Vector3>();var colors=new List<Color>();var indices=new List<int>();
            var bounds=new Bounds();var quad=new[]{new Vector2(0,-1),new Vector2(1,-1),new Vector2(1,1),new Vector2(0,1)};
            using(var stream=new BinaryReader(new MemoryStream(data.bytes))){
                if(stream.ReadUInt32()!=0x31525341u)throw new InvalidDataException("Unsupported Aster beam survey");
                uint count=stream.ReadUInt32();
                for(int i=0;i<count;i++){
                    var a=SurveyVector(stream);var end=SurveyVector(stream);var sectionU=SurveyVector(stream);var sectionV=SurveyVector(stream);
                    int shape=stream.ReadByte(),slot=stream.ReadByte();stream.ReadUInt16();
                    var f=finishes[slot];var mr=new Vector3(f.GetFloat("_Metallic"),1-f.GetFloat("_Glossiness"),shape);
                    bounds.Encapsulate(a);bounds.Encapsulate(end);var color=f.color.linear;
                    for(int j=0;j<4;j++){p.Add(a);b.Add(end);u.Add(sectionU);v.Add(sectionV);corners.Add(quad[j]);settings.Add(mr);colors.Add(color);}
                    int k=i*4;indices.AddRange(new[]{k,k+1,k+2,k,k+2,k+3});
                }
            }
            coverage=new Mesh{name="Pressure member section survey"};coverage.SetVertices(p);coverage.SetUVs(0,b);coverage.SetUVs(1,u);
            coverage.SetUVs(2,v);coverage.SetUVs(3,corners);coverage.SetUVs(4,settings);coverage.SetColors(colors);coverage.SetTriangles(indices,0);
            bounds.Expand(.5f);coverage.bounds=bounds;
            var mount=new GameObject("Spatially integrated pressure members");mount.layer=ExteriorRig.ExteriorLayer;
            mount.transform.SetParent(originals.parent,false);mount.transform.localPosition=originals.localPosition;mount.transform.localRotation=originals.localRotation;mount.transform.localScale=originals.localScale;
            mount.AddComponent<MeshFilter>().sharedMesh=coverage;var proxy=mount.AddComponent<MeshRenderer>();
            var material=new Material(distant);owned.Add(material);proxy.sharedMaterial=material;proxy.shadowCastingMode=ShadowCastingMode.Off;
        }
        void OnDestroy(){if(coverage)Destroy(coverage);foreach(var material in owned)if(material)Destroy(material);}
    }
}
