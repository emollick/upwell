using System;
using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
namespace Upwell.Editor {
    public static class SkySurvey {
        public static void Render(){
            EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);
            string path=Path.GetFullPath("Logs/sky-survey");Directory.CreateDirectory(path);
            var material=new Material(AssetDatabase.LoadAssetAtPath<Material>("Assets/Upwell/Materials/RouteSky.mat"));RenderSettings.skybox=material;
            var go=new GameObject("Sky sampler");var cam=go.AddComponent<Camera>();cam.clearFlags=CameraClearFlags.Skybox;cam.cullingMask=0;cam.allowHDR=false;cam.fieldOfView=64;cam.farClipPlane=26000;
            var target=new RenderTexture(800,450,24,RenderTextureFormat.ARGB32,RenderTextureReadWrite.sRGB);target.Create();cam.targetTexture=target;
            var image=new Texture2D(800,450,TextureFormat.RGB24,false,false);
            foreach(var t in new[]{22,58,78,105,135,184,224,249,360}){
                double km=AscentRoute.Height(t);float dip=(float)Math.Acos(6371/(6371+km));
                material.SetFloat("_HeightKm",(float)km+.007f);material.SetFloat("_WeatherSeconds",t);material.SetFloat("_Samples",32);material.SetVector("_SunLocal",AscentRoute.Sun(km));
                foreach(int tilt in new[]{0,1}){
                    cam.transform.rotation=Quaternion.Euler(tilt==0?(float)(dip*Mathf.Rad2Deg)+6:88,0,0);
                    var tr=cam.transform;float f=Mathf.Tan(cam.fieldOfView*.5f*Mathf.Deg2Rad);
                    Shader.SetGlobalVector("_SkyForward",tr.forward);Shader.SetGlobalVector("_SkyUp",tr.up*f);Shader.SetGlobalVector("_SkyRight",tr.right*f*cam.aspect);Shader.SetGlobalVector("_SkyEye",new Vector3(0,1.6f,0));
                    int limit=t==224&&tilt==1?3:0;
                    for(int mode=0;mode<=limit;mode++){Shader.SetGlobalFloat("_SurveyMode",mode);cam.Render();RenderTexture.active=target;image.ReadPixels(new Rect(0,0,800,450),0,0);image.Apply();
                        File.WriteAllBytes(Path.Combine(path,t+"-"+tilt+"-"+mode+".jpg"),image.EncodeToJPG(94));}
                }
            }
            Shader.SetGlobalFloat("_SurveyMode",0);RenderTexture.active=null;cam.targetTexture=null;target.Release();
        }
    }
}
