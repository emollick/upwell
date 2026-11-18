using UnityEngine;

namespace Upwell {
    public sealed class CurtainHandle : MonoBehaviour {
        public TransitProp control;
        public Vector3 gripCenter=new Vector3(.046f,.022f,0);
        public Vector3 fullTravel=Vector3.back*1.86f;
        public Vector3 Grip=>transform.TransformPoint(gripCenter);
        public float ScreenTravel(Camera eye) {
            Vector3 p=Grip,v=eye.WorldToScreenPoint(p),q=eye.WorldToScreenPoint(p+fullTravel*.075f);
            float projected=(q.x-v.x)/.075f;
            return Mathf.Sign(Mathf.Abs(projected)>.01f?projected:Vector3.Dot(eye.transform.right,fullTravel))*
                Mathf.Clamp(Mathf.Abs(projected),eye.pixelWidth*.16f,eye.pixelWidth*.96f);
        }
    }
}
