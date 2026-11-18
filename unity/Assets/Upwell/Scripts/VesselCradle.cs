using UnityEngine;

namespace Upwell {
    public sealed class VesselCradle {
        readonly TransitRide ride;
        readonly TransitProp vessel;
        readonly Transform parent;
        readonly Vector3 rest, foot;
        readonly Quaternion restAngle;
        readonly AudioSource contact;
        readonly AudioClip seatSound;
        Vector3 start;
        Quaternion startAngle;
        float t=1;
        public bool Moving=>t<1;
        public VesselCradle(TransitRide ride){
            this.ride=ride;
            vessel=ride.props["mug"];parent=vessel.transform.parent;
            rest=vessel.transform.localPosition;restAngle=vessel.transform.localRotation;
            foot=vessel.transform.position-Vector3.up*.0508f;
            var source=Resources.Load<GameObject>("Docking/VesselCradle");
            var rack=Object.Instantiate(source,foot,Quaternion.identity,ride.transform);
            foreach(var mesh in rack.GetComponentsInChildren<Renderer>()){
                var slots=mesh.sharedMaterials;
                for(int i=0;i<slots.Length;i++){
                    string id=slots[i].name.ToLowerInvariant();
                    bool dark=id.Contains("carbon"),brass=id.Contains("bronze"),mark=id.Contains("ivory"),bright=id.Contains("pin");
                    var mat=new Material(Shader.Find("Upwell/Carriage finish")){name=slots[i].name};
                    ColorUtility.TryParseHtmlString(dark?"#333637":brass?"#ad8861":mark?"#c8c7b7":bright?"#a4abad":"#929898",out var tint);
                    mat.color=tint;mat.SetFloat("_Metallic",dark?.22f:mark?.13f:.88f);
                    mat.SetFloat("_Roughness",dark?.48f:bright?.23f:.35f);mat.SetFloat("_FinishEligible",0);slots[i]=mat;
                }
                mesh.sharedMaterials=slots;
            }
            contact=rack.AddComponent<AudioSource>();contact.spatialBlend=.84f;contact.minDistance=.65f;contact.dopplerLevel=0;
            seatSound=Resources.Load<AudioClip>("Docking/VesselImpact");
        }
        public bool InReach(Vector3 eye)=>Vector3.Distance(eye,foot)<=1.24f;
        public void Park(Vector3 from,Quaternion angle){
            start=parent.InverseTransformPoint(from);startAngle=Quaternion.Inverse(parent.rotation)*angle;t=0;
            var body=vessel.GetComponent<LooseItemBody>();if(body)body.Recover();
            vessel.transform.SetParent(parent,false);vessel.gameObject.SetActive(true);
            vessel.transform.SetLocalPositionAndRotation(start,startAngle);
        }
        public void Step(float dt){
            if(t>=1)return;
            t=Mathf.Min(1,t+dt/.72f);
            float approach=Mathf.SmoothStep(0,1,Mathf.Min(1,t/.83f));
            float seat=t>.83f?1-Mathf.Pow((t-.83f)/.17f,2):Mathf.Sin(approach*Mathf.PI*.5f);
            vessel.transform.SetLocalPositionAndRotation(Vector3.Lerp(start,rest,approach)+Vector3.up*(.045f*seat),
                Quaternion.Slerp(startAngle,restAngle,approach));
            if(t>=1){
                var body=vessel.GetComponent<Rigidbody>();
                if(body){
                    // A recovered flask still has an interpolated body. Seat its physics pose with the mesh.
                    vessel.transform.GetPositionAndRotation(out var position,out var rotation);
                    body.position=position;
                    body.rotation=rotation;
                }
                var mount=vessel.GetComponentInChildren<EquipmentMount>(true);if(mount)mount.enabled=true;
                if(seatSound)contact.PlayOneShot(seatSound,.32f);if(ride.latch)contact.PlayOneShot(ride.latch,.28f);
                ride.Say("Flask secured in the galley cradle.");
            }
        }
    }
}
