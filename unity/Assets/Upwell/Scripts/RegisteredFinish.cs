using UnityEngine;

namespace Upwell {
    // Project high-frequency material detail into modeled rest space, once per renderer.
    // The decal test uses the surveyed depth, so a lifted handle keeps the texture on its own surface.
    [DefaultExecutionOrder(-120)]
    public sealed class RegisteredFinish : MonoBehaviour {
        public string room;
        public Texture2D detail,depth;
        public Matrix4x4 webToClip;
        public const float FinishWeight=.88f;
        static readonly Matrix4x4 UnityToWeb=Matrix4x4.Scale(new Vector3(1,1,-1));
        static readonly int Activation=Shader.PropertyToID("_FinishActive"),Projector=Shader.PropertyToID("_RestProjector"),Details=Shader.PropertyToID("_FinishMap"),Depth=Shader.PropertyToID("_FinishDepth");
        public static void Weight(float amount)=>Shader.SetGlobalFloat("_UpwellFinishWeight",amount);
        public Vector3 ReferenceEye {
            get {Vector4 v=webToClip.inverse*new Vector4(0,0,1,0);return UnityToWeb.MultiplyPoint3x4(new Vector3(v.x,v.y,v.z)/v.w);}
        }
        public Vector3 ReferenceDirection {get{Vector4 z=webToClip.GetRow(3);return UnityToWeb.MultiplyVector(new Vector3(z.x,z.y,z.z)).normalized;}}
        public Vector3 ReferenceUp {get{Vector4 y=webToClip.GetRow(1);return UnityToWeb.MultiplyVector(new Vector3(y.x,y.y,y.z)).normalized;}}
        public float ReferenceFov {get{Vector4 y=webToClip.GetRow(1);return 2*Mathf.Atan(1/new Vector3(y.x,y.y,y.z).magnitude)*Mathf.Rad2Deg;}}
        void Awake(){
            Weight(FinishWeight);
            foreach(var rend in GetComponentsInChildren<MeshRenderer>(true)){
                if(rend.GetComponentInParent<FurnishingSurface>())continue;
                var prop=rend.GetComponentInParent<TransitProp>();
                if(prop&&(prop.portable||prop.id=="accelerometer"||prop.id=="accel_test"||prop.id=="capillary_cell"||prop.id=="capillary_primer"))continue;
                var matrix=webToClip*UnityToWeb*rend.localToWorldMatrix;
                var mats=rend.sharedMaterials;
                for(int slot=0;slot<mats.Length;slot++){
                    var m=mats[slot];if(!m||!m.HasProperty("_FinishEligible")||m.GetFloat("_FinishEligible")<.5f)continue;
                    var block=new MaterialPropertyBlock();rend.GetPropertyBlock(block,slot);block.SetFloat(Activation,1);
                    block.SetMatrix(Projector,matrix);block.SetTexture(Details,detail);block.SetTexture(Depth,depth);rend.SetPropertyBlock(block,slot);
                }
            }
        }
    }
}
