using System.Runtime.InteropServices;
using UnityEngine;

namespace Upwell {
    public sealed partial class Passenger {
        public bool GraphicsMenuVisible { get; private set; }
        public PresentationEdges CabinEdges { get; private set; }
        public PresentationEdges SensorEdges { get; private set; }
        static readonly string[][] graphicsChoices={
            new[]{"Off","FXAA"},new[]{"Off","Hard","Soft"},new[]{"Low","Balanced","High"},new[]{"Off","On"}
        };
        static readonly string[] graphicsNames={"Anti-aliasing","Cast shadows","Atmosphere detail","Cabin contact shading"};
        int graphicsRow;
        GUIStyle graphicsButtonLabel;

        void InstallGraphics(){
            PlayerGraphics.Install();
            CabinEdges=eye.gameObject.AddComponent<PresentationEdges>();
            SensorEdges=ride.exterior.SensorCamera.gameObject.AddComponent<PresentationEdges>();
            SensorEdges.opticalRig=ride.exterior;
        }
        public void SetGraphicsMenu(bool open,bool closedByMouse=false) {
            GraphicsMenuVisible=open;
            if(open){FinishPassageGesture();graphicsRow=0;}
            bool pointer=open||momentsOpen||Help;
            SetPassengerPointer(pointer,closedByMouse);
        }
        void GraphicsKeys(){
            if(Input.GetKeyDown(KeyCode.Escape)){SetGraphicsMenu(false);return;}
            if(Input.GetKeyDown(KeyCode.UpArrow))graphicsRow=(graphicsRow+3)%4;
            if(Input.GetKeyDown(KeyCode.DownArrow))graphicsRow=(graphicsRow+1)%4;
            var option=(PlayerGraphics.Option)graphicsRow;
            if(Input.GetKeyDown(KeyCode.LeftArrow))PlayerGraphics.Set(option,PlayerGraphics.Value(option)-1);
            if(Input.GetKeyDown(KeyCode.RightArrow))PlayerGraphics.Set(option,PlayerGraphics.Value(option)+1);
        }
        static void GraphicsPanel(Rect rect,Color color){
            Color previous=GUI.color;GUI.color=color;GUI.DrawTexture(rect,Texture2D.whiteTexture);GUI.color=previous;
        }
        bool GraphicsButton(Rect rect,string label,bool selected=false,bool available=true){
            bool hover=available && rect.Contains(Event.current.mousePosition);
            var fill=selected?new Color(.105f,.242f,.237f):hover?new Color(.14f,.20f,.21f):new Color(.085f,.123f,.132f);
            if(!available)fill=new Color(.060f,.079f,.083f);
            GraphicsPanel(rect,fill);
            if(selected)GraphicsPanel(new Rect(rect.x,rect.yMax-2,rect.width,2),new Color(.54f,.86f,.81f));
            if(graphicsButtonLabel==null)graphicsButtonLabel=new GUIStyle(center){fontSize=15,wordWrap=false};
            graphicsButtonLabel.normal.textColor=available?new Color(.90f,.94f,.94f):new Color(.46f,.52f,.53f);
            bool pressed=available&&GUI.Button(rect,GUIContent.none,GUIStyle.none);
            GUI.Label(rect,label,graphicsButtonLabel);return pressed;
        }
        void DrawGraphicsMenu(float w,float h){
            float width=Mathf.Min(420,w-24),height=Mathf.Min(402,h-16),x=(w-width)*.5f,y=(h-height)*.5f;
            float row=(height-124)/4,left=x+18,inner=width-36;
            GraphicsPanel(new Rect(x,y,width,height),new Color(.030f,.052f,.061f,.985f));
            GUI.Label(new Rect(left,y+11,inner-80,34),"Graphics",heading);
            if(GraphicsButton(new Rect(x+width-79,y+12,61,28),"Close")){SetGraphicsMenu(false,true);return;}
            for(int i=0;i<graphicsChoices.Length;i++){
                var option=(PlayerGraphics.Option)i;
                string[] choices=graphicsChoices[i];
                float top=y+51+i*row,bw=(inner-(choices.Length-1)*4)/choices.Length;
                GUI.Label(new Rect(left,top,inner,24),graphicsNames[i],normal);
                if(graphicsRow==i)GraphicsPanel(new Rect(left-8,top+5,2,15),new Color(.46f,.84f,.81f));
                for(int k=0;k<choices.Length;k++){
                    bool selected=PlayerGraphics.Value(option)==k;
                    var rect=new Rect(left+k*(bw+4),top+24,bw,Mathf.Min(30,row-25));
                    if(GraphicsButton(rect,choices[k],selected,k<=PlayerGraphics.Maximum(option))){graphicsRow=i;if(!selected)PlayerGraphics.Set(option,k);}
                }
            }
            GUI.Label(new Rect(left,y+height-66,inner,24),SoftwareGraphics?"Software renderer · reduced detail":"Up/down to select · Left/right to change",small);
            if(GraphicsButton(new Rect(left,y+height-41,94,28),"Defaults"))PlayerGraphics.RestoreDefaults();
            GUI.Label(new Rect(x+width-187,y+height-38,170,23),"Saved on this device",small);
        }
        #if UNITY_WEBGL && !UNITY_EDITOR
        [DllImport("__Internal")] static extern void UpwellGraphicsSample(int visible,int choices,int software,int cast,int aa,int cabinSamples,int opticSamples,int cabinScene,int cabinFiltered,int sensorScene,int sensorFiltered,int sky,int steps);
        void ReportGraphics(){
            UpwellGraphicsSample(GraphicsMenuVisible?1:0,PlayerGraphics.Choices,SoftwareGraphics?1:0,(int)QualitySettings.shadows,QualitySettings.antiAliasing,
                CabinEdges.SourceSamples,SensorEdges.SourceSamples,CabinEdges.LastSceneFrame,CabinEdges.LastFilteredFrame,
                SensorEdges.LastSceneFrame,SensorEdges.LastFilteredFrame,ride.exterior.PassengerRadianceWidth,ride.exterior.PassengerAtmosphereSteps);
        }
        #endif
    }
}
