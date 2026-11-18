using System;
using System.Globalization;
using System.IO;
using System.Text;
using UnityEngine;

namespace Upwell {
    public sealed partial class RideVerification {
        void CaptureAsterRelay() {
            Time.timeScale=0;ride.enabled=false;
            var exterior=ride.exterior;ride.Seek(359.99);ride.Seek(360);person.SetWatch(10);
            var camera=exterior.SensorCamera;
            var canvas=RenderTexture.GetTemporary(1280,720,24,RenderTextureFormat.ARGB32,RenderTextureReadWrite.sRGB,1);
            var active=RenderTexture.active;var previous=camera.targetTexture;int options=PlayerGraphics.Choices;
            var pose=new StringBuilder("frame,rotorX,rotorY,rotorZ,rotorW,lens\n");
            void Save(string file,Camera lens) {
                lens.targetTexture=canvas;lens.Render();RenderTexture.active=canvas;
                var image=new Texture2D(1280,720,TextureFormat.RGB24,false,false);
                try{image.ReadPixels(new Rect(0,0,1280,720),0,0);image.Apply(false);File.WriteAllBytes(Path.Combine(output,file),image.EncodeToPNG());}
                finally{Destroy(image);}
            }
            try {
                PlayerGraphics.Set(PlayerGraphics.Option.Edges,1,false);
                camera.targetTexture=canvas;camera.aspect=1280f/720;
                for(int i=0;i<24;i++){
                    exterior.SetProgress(360,AscentRoute.Terminal,0,i==0?0:1f/30f,360);
                    if(i==0){camera.Render();camera.Render();}
                    Save("frame-"+i.ToString("D3")+".png",camera);
                    var q=exterior.Orbital.Rotor.localRotation;
                    pose.AppendFormat(CultureInfo.InvariantCulture,"{0},{1:R},{2:R},{3:R},{4:R},{5:R}\n",i,q.x,q.y,q.z,q.w,camera.fieldOfView);
                }
                camera.fieldOfView*=.42f;Save("magnified.png",camera);
                camera.targetTexture=previous;person.SetWatch(1);var eye=person.eye;var target=eye.targetTexture;
                try{Save("physical-window.png",eye);}finally{eye.targetTexture=target;}
                File.WriteAllText(Path.Combine(output,"poses.csv"),pose.ToString());
            }finally{PlayerGraphics.ApplyPacked(options);camera.targetTexture=previous;RenderTexture.active=active;RenderTexture.ReleaseTemporary(canvas);}
        }
    }
}
