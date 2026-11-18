using System;
using System.Collections.Generic;
using System.Globalization;
using System.Runtime.InteropServices;
using UnityEngine;

namespace Upwell {
    public sealed partial class Passenger {
        const int PhotoLimit=6;
        const string PhotoKey="Upwell.PassengerJournal.Photo.";
        static readonly CultureInfo PhotoCulture=CultureInfo.InvariantCulture;
        [Serializable] sealed class PassagePhoto {
            public long order;
            public string viewpoint,jpeg;
            public double passage,km,load;
            [NonSerialized] public int slot;
            [NonSerialized] public Texture2D preview;
        }
        readonly List<PassagePhoto> photos=new List<PassagePhoto>(PhotoLimit);
        bool journalLoaded,journalOpen,shutterPending,journalButtonDown;
        int photoIndex=-1;
        string shutterNotice="";
        float shutterNoticeUntil;
        Vector2 journalScroll;
        #if UNITY_WEBGL && !UNITY_EDITOR
        [DllImport("__Internal")] static extern void UpwellPhotoStatus(string message,int count,int open);
        #endif
        void PhotoStatus(string message){
            shutterNotice=message;shutterNoticeUntil=Time.unscaledTime+3.2f;
            #if UNITY_WEBGL && !UNITY_EDITOR
            UpwellPhotoStatus(message,photos.Count,journalOpen?1:0);
            #endif
        }
        void LoadPhotos(){
            if(journalLoaded)return;
            journalLoaded=true;
            for(int i=0;i<PhotoLimit;i++){
                string raw=PlayerPrefs.GetString(PhotoKey+i,"");if(string.IsNullOrEmpty(raw))continue;
                try{
                    var photo=JsonUtility.FromJson<PassagePhoto>(raw);
                    if(photo==null||string.IsNullOrEmpty(photo.jpeg)||string.IsNullOrEmpty(photo.viewpoint))continue;
                    photo.slot=i;photos.Add(photo);
                }catch(ArgumentException){/* A damaged slot can be reused independently. */}
            }
            photos.Sort((a,b)=>b.order.CompareTo(a.order));
        }
        public void TakePassagePhoto(){
            if(!boarded||journalOpen||GraphicsMenuVisible||momentsOpen||shutterPending)return;
            LoadPhotos();
            if(photos.Count>=PhotoLimit){PhotoStatus("Journal full. Delete a photo to make room.");return;}
            shutterPending=true;CabinEdges.shutter=CapturePassagePhoto;SensorEdges.shutter=CapturePassagePhoto;
        }
        static byte[] SmallJpeg(RenderTexture source,Material edgeFilter){
            // All six encoded slots stay well inside the WebGL preference budget.
            foreach(int longest in new[]{832,640,448,320}){
                float scale=Mathf.Min(1,longest/(float)Mathf.Max(source.width,source.height));
                int w=Mathf.Max(1,Mathf.RoundToInt(source.width*scale)),h=Mathf.Max(1,Mathf.RoundToInt(source.height*scale));
                var target=RenderTexture.GetTemporary(w,h,0,RenderTextureFormat.ARGB32,RenderTextureReadWrite.sRGB);
                var previous=RenderTexture.active;Texture2D shot=null;
                try{
                    if(edgeFilter)Graphics.Blit(source,target,edgeFilter);else Graphics.Blit(source,target);
                    RenderTexture.active=target;shot=new Texture2D(w,h,TextureFormat.RGB24,false,false);
                    shot.ReadPixels(new Rect(0,0,w,h),0,0,false);shot.Apply(false,false);
                    byte[] bytes=shot.EncodeToJPG(longest>=640?76:64);
                    if(bytes!=null&&bytes.Length<=72*1024)return bytes;
                }finally{RenderTexture.active=previous;if(shot)Destroy(shot);RenderTexture.ReleaseTemporary(target);}
            }
            throw new InvalidOperationException("Journal frame did not fit its local slot");
        }
        string PhotoView(){
            if(Examined)return Examined.title;
            switch(watchView){
                case 1:return "Forward window";case 2:return "Sunward window";case 3:return "Earth camera";
                case 4:return "Forward camera";case 5:return "Guide rollers";case 6:return "Floor port";
                case 7:return "Berth screen";case 8:return "Counterline";case 9:return "Star field";
                case 10:return ride.exterior.OnHabitatRelay?"Aster hub relay":"Colony optics";
                case 11:return "Shaded side window";
                case 12:return "Aster valley gallery";
            }
            if(Resting)return InBerth?"Crew berth":"Window seat";
            return transform.position.z>1.9f?"Observation saloon":transform.position.z> -1.9f?"Crew sleeper":"Service bay";
        }
        void CapturePassagePhoto(RenderTexture frame,Material edgeFilter){
            if(!shutterPending)return;
            shutterPending=false;CabinEdges.shutter=null;SensorEdges.shutter=null;
            int slot=0;while(photos.Exists(p=>p.slot==slot))slot++;
            try{
                var photo=new PassagePhoto{slot=slot,order=photos.Count==0?1:photos[0].order+1,
                    passage=ride.Seconds,km=ride.PreciseAltitude,load=ride.Forces.Down/9.80665,viewpoint=PhotoView(),
                    jpeg=Convert.ToBase64String(SmallJpeg(frame,edgeFilter))};
                PlayerPrefs.SetString(PhotoKey+slot,JsonUtility.ToJson(photo));PlayerPrefs.Save();photos.Insert(0,photo);
                PhotoStatus("Photo saved  ·  "+photos.Count+" / "+PhotoLimit);
            }catch(Exception e){
                Debug.LogWarning("Photo journal: "+e.Message);PhotoStatus("Could not save this photo on this device.");
            }
        }
        Texture2D Preview(PassagePhoto photo){
            if(photo.preview)return photo.preview;
            var image=new Texture2D(2,2,TextureFormat.RGB24,false,false);
            try{
                if(image.LoadImage(Convert.FromBase64String(photo.jpeg),true)){
                    image.wrapMode=TextureWrapMode.Clamp;photo.preview=image;return image;
                }
            }catch(FormatException){/* Keep the slot removable. */}
            Destroy(image);return null;
        }
        public void TogglePhotoJournal(){
            if(!boarded||GraphicsMenuVisible||momentsOpen)return;
            LoadPhotos();journalOpen=!journalOpen;photoIndex=-1;journalScroll=Vector2.zero;
            if(journalOpen)FinishPassageGesture();
            else foreach(var p in photos){if(p.preview)Destroy(p.preview);p.preview=null;}
            SetPassengerPointer(journalOpen||Help,!journalOpen&&!Help);PhotoStatus("");
        }
        void DeletePhoto(){
            if(photoIndex<0||photoIndex>=photos.Count)return;
            var p=photos[photoIndex];
            try{PlayerPrefs.DeleteKey(PhotoKey+p.slot);PlayerPrefs.Save();}
            catch(Exception){PhotoStatus("Could not delete this photo on this device.");return;}
            if(p.preview)Destroy(p.preview);photos.RemoveAt(photoIndex);photoIndex=-1;PhotoStatus("Photo deleted");
        }
        bool JournalInput(){
            if(journalOpen){
                if(Input.GetKeyDown(KeyCode.J))TogglePhotoJournal();
                else if(Input.GetKeyDown(KeyCode.Escape)){if(photoIndex>=0)photoIndex=-1;else TogglePhotoJournal();}
                else if(photoIndex>=0&&Input.GetKeyDown(KeyCode.Delete))DeletePhoto();
                else if(photos.Count>0){
                    if(Input.GetKeyDown(KeyCode.RightArrow))photoIndex=Mathf.Min(photos.Count-1,photoIndex+1);
                    if(Input.GetKeyDown(KeyCode.LeftArrow))photoIndex=Mathf.Max(0,photoIndex-1);
                    if(Input.GetKeyDown(KeyCode.Return)&&photoIndex<0)photoIndex=0;
                }
                return true;
            }
            if(GraphicsMenuVisible||momentsOpen||Input.GetKey(KeyCode.LeftControl)||Input.GetKey(KeyCode.RightControl))return false;
            if(Input.GetKeyDown(KeyCode.K)){TakePassagePhoto();return true;}
            if(Input.GetKeyDown(KeyCode.J)){TogglePhotoJournal();return true;}
            #if !UNITY_WEBGL || UNITY_EDITOR
            var u=Mathf.Clamp(Screen.height/850f,.74f,1.6f);
            var mouse=new Vector2(Input.mousePosition.x/u,(Screen.height-Input.mousePosition.y)/u);
            if(Input.GetMouseButtonDown(0)&&new Rect(Screen.width/u-200,Screen.height/u-48,184,34).Contains(mouse))journalButtonDown=true;
            if(journalButtonDown){if(!Input.GetMouseButton(0))journalButtonDown=false;return true;}
            #endif
            return false;
        }
        void DrawShutter(float w,float h){
            #if !UNITY_WEBGL || UNITY_EDITOR
            if(GUI.Button(new Rect(w-200,h-48,88,34),"K   Photo"))TakePassagePhoto();
            if(GUI.Button(new Rect(w-108,h-48,92,34),"J   Journal"))TogglePhotoJournal();
            if(!string.IsNullOrEmpty(shutterNotice)&&Time.unscaledTime<shutterNoticeUntil){
                float width=Mathf.Min(w-32,362);var r=new Rect(w-width-16,h-84,width,30);
                Plate(r);GUI.Label(r,shutterNotice,center);
            }
            #endif
        }
        static string PhotoCaption(PassagePhoto p){
            int sec=(int)Math.Floor(p.passage);
            double g=Math.Abs(p.load)<.0005?0:p.load;
            return "Route "+(sec/60).ToString("00")+":"+(sec%60).ToString("00")+"   ·   "+
                AscentRoute.AltitudeText(p.km)+"   ·   "+g.ToString("+0.000;-0.000;0.000",PhotoCulture)+" g";
        }
        void PhotoImage(Rect r,PassagePhoto p){
            GraphicsPanel(r,new Color(.025f,.035f,.04f));var image=Preview(p);
            if(image)GUI.DrawTexture(r,image,ScaleMode.ScaleToFit,false);
            else GUI.Label(r,"Photo unavailable",center);
        }
        void DrawPhotoJournal(float w,float h){
            bool detail=photoIndex>=0&&photoIndex<photos.Count;
            float sheetWidth=detail||photos.Count>=3?850:photos.Count==2?620:410;
            float width=Mathf.Min(sheetWidth,w-18),inset=16,inside=width-2*inset;
            int cols=Mathf.Min(Mathf.Max(1,photos.Count),width>=600?3:width>=420?2:1);
            float area=inside-16,gap=10,cell=(area-(cols-1)*gap)/cols,imgH=Mathf.Min(164,cell*.58f),row=imgH+60;
            float rowsHeight=Mathf.CeilToInt(photos.Count/(float)cols)*row;
            float height=Mathf.Min(h-18,detail?710:photos.Count==0?163:94+rowsHeight);
            float left=(w-width)*.5f,top=(h-height)*.5f;
            GraphicsPanel(new Rect(left,top,width,height),new Color(.042f,.071f,.083f,.99f));
            GUI.Label(new Rect(left+16,top+12,width-98,36),"Photo journal",heading);
            if(GUI.Button(new Rect(left+width-78,top+11,64,32),"Close")){TogglePhotoJournal();return;}
            if(detail){
                var p=photos[photoIndex];PhotoImage(new Rect(left+inset,top+57,inside,height-160),p);
                GUI.Label(new Rect(left+inset,top+height-97,inside,26),p.viewpoint,normal);
                GUI.Label(new Rect(left+inset,top+height-70,inside,23),PhotoCaption(p),small);
                if(GUI.Button(new Rect(left+inset,top+height-41,88,29),"All photos"))photoIndex=-1;
                if(GUI.Button(new Rect(left+width-121,top+height-41,105,29),"Delete photo"))DeletePhoto();
                return;
            }
            GUI.Label(new Rect(left+inset,top+51,inside,25),photos.Count+" / "+PhotoLimit+" photos",small);
            if(photos.Count==0){GUI.Label(new Rect(left+inset,top+95,inside,62),"Use the shutter to save a view of your passage.",normal);return;}
            journalScroll=GUI.BeginScrollView(new Rect(left+inset,top+81,inside,height-93),journalScroll,
                new Rect(0,0,area,rowsHeight));
            int selected=-1;
            for(int i=0;i<photos.Count;i++){
                var p=photos[i];float x=(i%cols)*(cell+gap),y=(i/cols)*row;
                var image=new Rect(x,y,cell,imgH);PhotoImage(image,p);
                GUI.Label(new Rect(x,y+imgH+1,cell,23),p.viewpoint,normal);
                GUI.Label(new Rect(x,y+imgH+23,cell,32),PhotoCaption(p),small);
                if(GUI.Button(new Rect(x,y,cell,row-6),GUIContent.none,GUIStyle.none))selected=i;
            }
            GUI.EndScrollView();if(selected>=0)photoIndex=selected;
        }
    }
}
