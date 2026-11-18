using UnityEngine;
namespace Upwell{
    [RequireComponent(typeof(MeshFilter))]
    public sealed class FlexibleTail:MonoBehaviour{
        public string partId;public Vector3[] rest;public int[] pinned;public float limit,support,width,thickness;public bool hasSupport,roundCord;
        public Vector3 widthGuide=Vector3.forward;public Material strandMaterial;
        public Mesh source;Mesh live;TransitRide ride;Vector3[] pos,prev,draw,drawNormals;float[] lengths,freedom;bool[] locked;
        public float Displacement{get;private set;}public float PinError{get;private set;}
        void Start(){Initialize();}
        void Initialize(){
            if(live||!source||rest==null||rest.Length<3)return;ride=FindFirstObjectByType<TransitRide>();
            live=new Mesh{name=source.name+" · compliant"};live.MarkDynamic();GetComponent<MeshFilter>().sharedMesh=live;
            if(strandMaterial)GetComponent<MeshRenderer>().sharedMaterials=new[]{strandMaterial};
            pos=(Vector3[])rest.Clone();prev=(Vector3[])rest.Clone();locked=new bool[rest.Length];foreach(int i in pinned)locked[i]=true;
            lengths=new float[rest.Length-1];for(int i=0;i<lengths.Length;i++)lengths[i]=Vector3.Distance(rest[i],rest[i+1]);
            freedom=new float[rest.Length];for(int i=0;i<rest.Length;i++){int k=rest.Length;foreach(int v in pinned)k=Mathf.Min(k,Mathf.Abs(v-i));freedom[i]=Mathf.Clamp01(k*.44f);}
            int rows=lengths.Length*6+1;draw=new Vector3[rows*9];drawNormals=new Vector3[draw.Length];var uv=new Vector2[draw.Length];var tris=new int[(rows-1)*8*6];int n=0;
            for(int row=0;row<rows;row++)for(int j=0;j<9;j++){int i=row*9+j;uv[i]=new Vector2(j/8f,row*.024f);
                if(row+1<rows&&j<8){tris[n++]=i;tris[n++]=i+1;tris[n++]=i+9;tris[n++]=i+1;tris[n++]=i+10;tris[n++]=i+9;}}
            Skin();live.uv=uv;live.triangles=tris;live.RecalculateBounds();
        }
        public void CopyTo(GameObject instance){
            var f=instance.AddComponent<FlexibleTail>();f.partId=partId;f.rest=rest;f.pinned=pinned;f.limit=limit;f.support=support;f.hasSupport=false;f.source=source;
            f.width=width;f.thickness=thickness;f.widthGuide=widthGuide;f.roundCord=roundCord;f.strandMaterial=strandMaterial;
            instance.GetComponent<MeshFilter>().sharedMesh=source;
        }
        public void Simulate(float dt){
            Initialize();if(!ride||!live)return;float step=Mathf.Clamp(dt,.006f,.019f);
            var localForce=transform.InverseTransformDirection(ride.Forces.Apparent+ride.StructureImpulse);
            Vector3 up=Vector3.up;float spring=85;float strength=limit*spring/9.80f;
            float release=Mathf.Clamp01(1-(float)ride.Forces.Down/9.80665f);
            for(int i=0;i<pos.Length;i++){
                if(locked[i]){pos[i]=prev[i]=rest[i];continue;}
                Vector3 neutral=rest[i]+(up+Vector3.right*.48f*release+Vector3.forward*.27f*release)*limit*freedom[i];
                var cur=pos[i];var velocity=(cur-prev[i])*Mathf.Exp(-4.3f*step);
                pos[i]=cur+velocity+((neutral-cur)*spring+localForce*(strength*freedom[i]))*step*step;prev[i]=cur;
            }
            for(int k=0;k<6;k++){
                for(int i=0;i<lengths.Length;i++){
                    Vector3 d=pos[i+1]-pos[i];float distance=d.magnitude;if(distance<.00001f)continue;var correction=d*(1-lengths[i]/distance);
                    float weight=locked[i]?0:locked[i+1]?1:.5f;if(!locked[i])pos[i]+=correction*weight;if(!locked[i+1])pos[i+1]-=correction*(1-weight);
                }
                for(int i=0;i<pos.Length;i++){if(locked[i]){pos[i]=rest[i];continue;}pos[i]=rest[i]+Vector3.ClampMagnitude(pos[i]-rest[i],limit);if(hasSupport)pos[i].y=Mathf.Max(support,pos[i].y);}
            }
            PinError=0;Displacement=0;for(int i=0;i<pos.Length;i++){float delta=Vector3.Distance(pos[i],rest[i]);if(locked[i])PinError=Mathf.Max(PinError,delta);else Displacement=Mathf.Max(Displacement,delta);}
            Skin();live.RecalculateBounds();
        }
        void Skin(){
            int rows=draw.Length/9;Vector3 previous=widthGuide;
            for(int row=0;row<rows;row++){
                int seg=Mathf.Min(row/6,pos.Length-2);float t=row/6f-seg,t2=t*t,t3=t2*t;
                Vector3 a=pos[Mathf.Max(0,seg-1)],b=pos[seg],c=pos[seg+1],d=pos[Mathf.Min(pos.Length-1,seg+2)];
                Vector3 aa=2*a-5*b+4*c-d,bb=-a+3*b-3*c+d;
                Vector3 point=.5f*(2*b+(-a+c)*t+aa*t2+bb*t3);
                Vector3 tangent=((-a+c)+2*aa*t+3*bb*t2).normalized;
                var across=Vector3.ProjectOnPlane(previous,tangent);if(across.sqrMagnitude<.001f)across=Vector3.Cross(tangent,Mathf.Abs(tangent.y)<.88f?Vector3.up:Vector3.right);
                across.Normalize();previous=across;var face=Vector3.Cross(tangent,across).normalized;
                for(int j=0;j<9;j++){float angle=j*Mathf.PI/4,cs=Mathf.Cos(angle),sn=Mathf.Sin(angle);int idx=row*9+j;
                    draw[idx]=point+(across*(cs*width)+face*(sn*(roundCord?width:thickness)))*.5f;
                    drawNormals[idx]=(across*(cs/Mathf.Max(.0001f,width))+face*(sn/Mathf.Max(.0001f,roundCord?width:thickness))).normalized;
                }
            }live.vertices=draw;live.normals=drawNormals;
        }
        void LateUpdate(){Simulate(Time.deltaTime);}
        void OnDestroy(){if(live)Destroy(live);}
    }
}
