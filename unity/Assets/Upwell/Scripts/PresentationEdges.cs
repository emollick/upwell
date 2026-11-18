using UnityEngine;

namespace Upwell {
    // This is the last scene pass. Unity draws the passenger's IMGUI controls afterwards.
    [RequireComponent(typeof(Camera))]
    public sealed class PresentationEdges : MonoBehaviour {
        public ExteriorRig opticalRig;
        public System.Action<RenderTexture,Material> shutter;
        Material filter;
        Camera lens;
        public int SourceSamples { get; private set; }
        public int LastFilteredFrame { get; private set; } = -1;
        public int LastSceneFrame { get; private set; } = -1;
        void Awake(){lens=GetComponent<Camera>();lens.allowMSAA=false;}
        void OnRenderImage(RenderTexture source, RenderTexture destination) {
            // The small MFD feed is rendered into the cabin, and is filtered with the complete cabin image.
            if(opticalRig && lens.targetTexture==opticalRig.Feed){Graphics.Blit(source,destination);return;}
            SourceSamples=source.antiAliasing;
            LastSceneFrame=Time.frameCount;
            Material pass=null;
            if(PlayerGraphics.Edges!=0 && PlayerGraphics.CanFilter) {
                if(!filter)filter=new Material(PlayerGraphics.EdgeShader){hideFlags=HideFlags.HideAndDontSave};
                pass=filter;Graphics.Blit(source,destination,pass);
                LastFilteredFrame=Time.frameCount;
            } else Graphics.Blit(source,destination);
            if(shutter!=null&&lens.enabled&&lens.targetTexture==null)shutter(source,pass);
        }
        void OnDestroy(){if(filter)Destroy(filter);}
    }
}
