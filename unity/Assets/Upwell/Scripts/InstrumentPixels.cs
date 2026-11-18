using UnityEngine;
namespace Upwell{
    internal static class DisplayLettering{
        const string Extra="°²±×∞Á";
        static readonly int Characters=95+Extra.Length;
        static byte[] coverage;
        public static void Draw(Color32[] destination,int width,int height,string text,int x,int y,int size,Color32 ink){
            if(coverage==null)coverage=Resources.Load<TextAsset>("DisplayLettering").bytes;
            int w=6*size,h=9*size;
            int start=size==1?0:size==2?54*Characters:270*Characters;
            foreach(char raw in text){
                char c=char.ToUpperInvariant(raw);int index=c-32;
                if(index<0||index>=95){int extra=Extra.IndexOf(c);index=extra<0?'?'-32:95+extra;}
                int offset=start+index*w*h;
                for(int yy=0;yy<h;yy++){
                    int row=y+yy;if((uint)row>=height)continue;
                    for(int xx=0;xx<w;xx++){
                        int column=x+xx;if((uint)column>=width)continue;
                        int alpha=coverage[offset+yy*w+xx];if(alpha==0)continue;
                        int pixel=(height-1-row)*width+column;var bg=destination[pixel];int inv=255-alpha;
                        destination[pixel]=new Color32((byte)((ink.r*alpha+bg.r*inv+127)/255),
                            (byte)((ink.g*alpha+bg.g*inv+127)/255),(byte)((ink.b*alpha+bg.b*inv+127)/255),255);
                    }
                }
                x+=w;if(x>=width)break;
            }
        }
    }
    public sealed class InstrumentPixels{
        public readonly Texture2D texture;readonly Color32[] data;readonly int width,height;
        string lastTitle,lastValue,lastDetail;int lastBars=-1,lastValveTenth=-1,lastLoadHundredth=-1;
        public readonly Color32 ink=new Color32(165,226,211,255),muted=new Color32(72,124,123,255),amber=new Color32(252,178,79,255);
        public InstrumentPixels(string title,int w=320,int h=136){width=w;height=h;data=new Color32[w*h];texture=new Texture2D(w,h,TextureFormat.RGBA32,true){name=title+" live readout",filterMode=FilterMode.Trilinear,anisoLevel=8,wrapMode=TextureWrapMode.Clamp};}
        void Dot(int x,int y,Color32 c){if((uint)x<width&&(uint)y<height)data[(height-1-y)*width+x]=c;}
        public void Clear(){System.Array.Fill(data,new Color32(5,15,18,255));}
        public void Line(int x,int y,int xx,int yy,Color32 c){int n=Mathf.Max(Mathf.Abs(xx-x),Mathf.Abs(yy-y));if(n<1)return;for(int i=0;i<=n;i++)Dot(x+(xx-x)*i/n,y+(yy-y)*i/n,c);}
        public void Text(string text,int x,int y,int size,Color32 color){
            DisplayLettering.Draw(data,width,height,text,x,y,size,color);
        }
        public void Vessel(float travel,float g){
            // The silicone seat lies 22 mm from the thumb lever's transverse pin.
            float lift=22*Mathf.Sin(Mathf.Deg2Rad*38*travel);
            int tenths=Mathf.RoundToInt(lift*10),hundredths=Mathf.RoundToInt(g*100);
            if(tenths==lastValveTenth&&hundredths==lastLoadHundredth)return;
            lastValveTenth=tenths;lastLoadHundredth=hundredths;
            Panel("DRINK VALVE",lift<.2f?"SEALED":lift<2.4f?"UNSEATING":"PORT OPEN",
                "LIFT "+lift.ToString("0.0")+" MM  /  "+g.ToString("0.00")+" G",lift/13.55f);
        }
        public void Panel(string upper,string value,string lower,float reading){
            int bars=Mathf.CeilToInt(30*Mathf.Clamp01(reading));
            if(upper==lastTitle&&value==lastValue&&lower==lastDetail&&bars==lastBars)return;
            lastTitle=upper;lastValue=value;lastDetail=lower;lastBars=bars;
            Clear();Text(upper,9,7,2,muted);Line(9,28,width-9,28,muted);Text(value,9,39,value.Length>16?2:3,ink);
            Text(lower,9,77,lower.Length>24?1:2,amber);for(int i=0;i<30;i++){int x=10+i*10;for(int j=0;j<6;j++)Line(x+j,104,x+j,114,i<bars?ink:muted);}
            texture.SetPixels32(data);texture.Apply(true,false);
        }
    }
}
