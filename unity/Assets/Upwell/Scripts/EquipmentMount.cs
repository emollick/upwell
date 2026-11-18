using UnityEngine;
namespace Upwell {
    public sealed class EquipmentMount : MonoBehaviour {
        TransitRide ride;Vector3 rest,offset,velocity;
        void Start(){ride=FindFirstObjectByType<TransitRide>();rest=transform.localPosition;}
        void LateUpdate(){
            if(!ride)return;float dt=Mathf.Min(.025f,Time.deltaTime);
            var force=ride.Forces;var target=new Vector3((float)-force.West*.015f,(float)(9.76-force.Down)*.00013f,0)+ride.StructureImpulse*.0038f;
            velocity+=(target-offset)*170*dt;velocity*=Mathf.Exp(-17*dt);offset=Vector3.ClampMagnitude(offset+velocity*dt,.0045f);transform.localPosition=rest+offset;
        }
    }
}
