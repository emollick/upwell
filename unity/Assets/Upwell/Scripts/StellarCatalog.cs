using System;
using UnityEngine;

namespace Upwell {
    public static class StellarCatalog {
        public static Texture2D LoadGalacticLight(){
            var source=Resources.Load<TextAsset>("GalacticLight");
            if(!source||source.bytes.Length!=360*180*4)throw new InvalidOperationException("Incomplete Galactic photometry");
            var texture=new Texture2D(360,180,TextureFormat.RGBA32,false,true){
                name="Pioneer Galactic photometry",filterMode=FilterMode.Bilinear,
                wrapModeU=TextureWrapMode.Repeat,wrapModeV=TextureWrapMode.Clamp,anisoLevel=0
            };
            texture.LoadRawTextureData(source.bytes);texture.Apply(false,true);return texture;
        }
        public static Texture2D Load() {
            var source=Resources.Load<TextAsset>("BrightStars");
            if(!source)throw new InvalidOperationException("Missing stellar catalogue");
            byte[] data=source.bytes;
            if(data.Length<12||data[0]!='Y'||data[1]!='S'||data[2]!='T'||data[3]!='1'||data[4]!=64||data[5]!=16)
                throw new InvalidOperationException("Unknown stellar catalogue format");
            byte[] texels=new byte[1024*384*4];
            int groups=data[8]+256*data[9],at=12;
            for(int i=0;i<groups;i++){
                int tile=data[at]+256*data[at+1],bytes=4*data[at+2];
                at+=3;Buffer.BlockCopy(data,at,texels,tile*16*4,bytes);at+=bytes;
            }
            if(at!=data.Length)throw new InvalidOperationException("Incomplete stellar catalogue");
            var texture=new Texture2D(1024,384,TextureFormat.RGBA32,false,true){
                name="Bright Star Catalogue",filterMode=FilterMode.Point,wrapMode=TextureWrapMode.Clamp,anisoLevel=0
            };
            texture.LoadRawTextureData(texels);texture.Apply(false,true);return texture;
        }

        public static float Adapt(float previous,bool saloonOn,int displayGain,float sunHeight,float sunlight,float dt){
            float glare=(saloonOn ? .76f : 0)+.032f*displayGain+.24f*sunlight*Mathf.Max(0,sunHeight);
            float target=Mathf.Clamp01(1-glare);
            return Mathf.Lerp(previous,target,1-Mathf.Exp(-Mathf.Max(0,dt)/(target>previous?4f:.38f)));
        }
    }
}
