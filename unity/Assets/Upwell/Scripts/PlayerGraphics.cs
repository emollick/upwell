using UnityEngine;

namespace Upwell {
    public static class PlayerGraphics {
        public enum Option { Edges, Shadows, Atmosphere, Contact }
        public static int Edges { get; private set; }
        public static int Shadows { get; private set; }
        public static int Atmosphere { get; private set; } = 1;
        public static int Contact { get; private set; } = 1;
        public static Shader EdgeShader { get; private set; }
        public static bool CanFilter => EdgeShader && EdgeShader.isSupported;
        static readonly bool testInstallation=System.Array.IndexOf(System.Environment.GetCommandLineArgs(),"-verify-upwell")>=0;
        static string PrefKey => "Upwell.Graphics.1."+(Passenger.SoftwareGraphics?"software":"hardware")+(testInstallation?".verification":"");
        static int Defaults => Passenger.SoftwareGraphics ? 0x0010 : 0x1121;
        public static int Choices => Edges | (Shadows << 4) | (Atmosphere << 8) | (Contact << 12);

        public static void Install() {
            EdgeShader=Resources.Load<Shader>("Graphics/PassengerFXAA");
            QualitySettings.antiAliasing=0;
            ApplyPacked(PlayerPrefs.GetInt(PrefKey,Defaults));
        }

        public static int Maximum(Option option) {
            switch(option) {
                case Option.Edges: return CanFilter ? 1 : 0;
                case Option.Shadows: return SystemInfo.supportsShadows ? (Passenger.SoftwareGraphics ? 1 : 2) : 0;
                case Option.Atmosphere: return Passenger.SoftwareGraphics ? 0 : 2;
                default: return Passenger.SoftwareGraphics ? 0 : 1;
            }
        }
        public static int Value(Option option) => (Choices >> ((int)option*4)) & 15;
        public static void Set(Option option,int value,bool save=true) {
            int shift=(int)option*4;
            ApplyPacked((Choices & ~(15 << shift)) | (Mathf.Clamp(value,0,Maximum(option)) << shift));
            if(save){PlayerPrefs.SetInt(PrefKey,Choices);PlayerPrefs.Save();}
        }
        public static void RestoreDefaults() {
            PlayerPrefs.DeleteKey(PrefKey);PlayerPrefs.Save();ApplyPacked(Defaults);
        }
        public static void ApplyPacked(int choices) {
            Edges=Mathf.Min(choices&15,Maximum(Option.Edges));
            Shadows=Mathf.Min((choices>>4)&15,Maximum(Option.Shadows));
            Atmosphere=Mathf.Min((choices>>8)&15,Maximum(Option.Atmosphere));
            Contact=Mathf.Min((choices>>12)&15,Maximum(Option.Contact));
            QualitySettings.shadows=Shadows==2 ? ShadowQuality.All : Shadows==1 ? ShadowQuality.HardOnly : ShadowQuality.Disable;
            Shader.SetGlobalFloat("_UpwellContactShading",Contact);
        }
    }
}
