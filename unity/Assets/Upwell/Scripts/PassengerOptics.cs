using UnityEngine;
namespace Upwell {
    [RequireComponent(typeof(Camera))]
    public sealed class PassengerOptics : MonoBehaviour {
        public Shader optics;
        public float FocusDistance;
        Material film;
        Camera lens;
        void OnEnable(){lens=GetComponent<Camera>();if(optics&&optics.isSupported)film=new Material(optics){hideFlags=HideFlags.HideAndDontSave};}
        void OnPreCull(){
            var mode=DepthTextureMode.None;
            if(!Passenger.SoftwareGraphics){
                if(PlayerGraphics.Contact!=0)mode=DepthTextureMode.Depth|DepthTextureMode.DepthNormals;
                else if(FocusDistance>0)mode=DepthTextureMode.Depth;
            }
            if(lens.depthTextureMode!=mode)lens.depthTextureMode=mode;
        }
        void OnRenderImage(RenderTexture src,RenderTexture dst){if(film){film.SetFloat("_FocusDistance",FocusDistance);Graphics.Blit(src,dst,film);}else Graphics.Blit(src,dst);}
        void OnDisable(){if(film)Destroy(film);}
    }
}
