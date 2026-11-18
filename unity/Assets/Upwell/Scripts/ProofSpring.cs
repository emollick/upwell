using UnityEngine;

namespace Upwell {
    public sealed class ProofSpring : MonoBehaviour {
        public float restLength,coilRadius=.0092f;public int turns,sign;
        Mesh mesh;Vector3[] source,sourceNormals,draw,normals;float[] parameter;
        Matrix4x4 fromMesh,toMesh;
        float previous=-1;
        Vector3 Path(float t,float length) {
            float angle=2*Mathf.PI*turns*t;
            return new Vector3(coilRadius*Mathf.Cos(angle),sign*length*t,sign*coilRadius*Mathf.Sin(angle));
        }
        Vector3 Tangent(float t,float length) {
            float rate=2*Mathf.PI*turns,angle=rate*t;
            return new Vector3(-coilRadius*rate*Mathf.Sin(angle),sign*length,sign*coilRadius*rate*Mathf.Cos(angle)).normalized;
        }
        public void Length(float length) {
            if(Mathf.Abs(previous-length)<.000007f)return;
            if(!mesh){
                var mf=GetComponentInChildren<MeshFilter>();if(!mf)return;
                var original=mf.sharedMesh;mesh=Instantiate(original);mesh.name="Constant-gauge helical wire";mesh.MarkDynamic();mf.sharedMesh=mesh;
                fromMesh=transform.worldToLocalMatrix*mf.transform.localToWorldMatrix;toMesh=fromMesh.inverse;
                source=original.vertices;sourceNormals=original.normals;draw=new Vector3[source.Length];normals=new Vector3[source.Length];parameter=new float[source.Length];
                var collar=new bool[source.Length];var renderer=mf.GetComponent<MeshRenderer>();var slots=renderer.sharedMaterials;
                for(int s=0;s<original.subMeshCount;s++)if(slots[s].name.StartsWith("Anodized_Frame"))
                    foreach(int vertex in original.GetIndices(s))collar[vertex]=true;
                for(int i=0;i<source.Length;i++){
                    source[i]=fromMesh.MultiplyPoint3x4(source[i]);sourceNormals[i]=fromMesh.MultiplyVector(sourceNormals[i]).normalized;
                    if(collar[i]){parameter[i]=source[i].y*sign<restLength*.5f?-1:-2;continue;}
                    float approx=Mathf.Clamp01(source[i].y*sign/restLength);
                    // Identify the nearest point on the original centreline. The radial wire offset is transported separately.
                    float lo=Mathf.Max(0,approx-.55f/turns),hi=Mathf.Min(1,approx+.55f/turns);
                    for(int j=0;j<17;j++){float a=(2*lo+hi)/3,b=(lo+2*hi)/3;
                        if((source[i]-Path(a,restLength)).sqrMagnitude<(source[i]-Path(b,restLength)).sqrMagnitude)hi=b;else lo=a;}
                    parameter[i]=(lo+hi)*.5f;
                }
            }
            previous=length;
            for(int i=0;i<source.Length;i++){
                float t=parameter[i];Vector3 p,n;
                if(t<0){p=source[i]+Vector3.up*(t< -1?sign*(length-restLength):0);n=sourceNormals[i];}
                else{var q=Quaternion.FromToRotation(Tangent(t,restLength),Tangent(t,length));p=Path(t,length)+q*(source[i]-Path(t,restLength));n=q*sourceNormals[i];}
                draw[i]=toMesh.MultiplyPoint3x4(p);normals[i]=toMesh.MultiplyVector(n).normalized;
            }
            mesh.vertices=draw;mesh.normals=normals;mesh.RecalculateBounds();
        }
        void OnDestroy(){if(mesh)Destroy(mesh);}
    }
}
