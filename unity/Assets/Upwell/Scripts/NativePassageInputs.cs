using System;
using System.Collections;
using System.Runtime.InteropServices;
using UnityEngine;

namespace Upwell {
    public sealed partial class RideVerification {
#if UNITY_STANDALONE_WIN
        delegate bool WindowProbe(IntPtr window,IntPtr data);
        [DllImport("user32.dll")]static extern bool EnumWindows(WindowProbe callback,IntPtr data);
        [DllImport("user32.dll")]static extern uint GetWindowThreadProcessId(IntPtr window,out uint process);
        [DllImport("user32.dll",CharSet=CharSet.Unicode)]static extern int GetClassName(IntPtr window,System.Text.StringBuilder buffer,int max);
        [DllImport("user32.dll",EntryPoint="PostMessageW")]static extern bool PostWindowMessage(IntPtr window,uint command,IntPtr key,IntPtr data);
        [DllImport("user32.dll")]static extern uint MapVirtualKey(uint key,uint conversion);
        static IntPtr OwnPlayerWindow(){
            var pid=(uint)System.Diagnostics.Process.GetCurrentProcess().Id;var result=IntPtr.Zero;
            EnumWindows((window,data)=>{
                GetWindowThreadProcessId(window,out uint owner);if(owner!=pid)return true;
                var name=new System.Text.StringBuilder(128);GetClassName(window,name,name.Capacity);
                if(name.ToString()!="UnityWndClass")return true;result=window;return false;
            },IntPtr.Zero);
            return result;
        }
        static IEnumerator KeyMessage(IntPtr window,uint key){
            var scan=MapVirtualKey(key,0);var down=1u|(scan<<16);
            if(key>=0x25&&key<=0x28)down|=1u<<24; // Dedicated cursor keys are extended scan codes, unlike the numeric keypad.
            PostWindowMessage(window,0x100,(IntPtr)key,(IntPtr)down);yield return new WaitForSecondsRealtime(.19f);
            PostWindowMessage(window,0x101,(IntPtr)key,(IntPtr)(long)(down|0xC0000000u));yield return new WaitForSecondsRealtime(.15f);
        }
#endif
        IEnumerator NativePassageInputs(){
#if UNITY_STANDALONE_WIN
            var window=OwnPlayerWindow();Check(window!=IntPtr.Zero,"Located this Windows player's own input window");
            // Post to this process alone. The verification does not take the desktop's foreground or send global keyboard events.
            PostWindowMessage(window,0x1C,(IntPtr)1,IntPtr.Zero);PostWindowMessage(window,7,IntPtr.Zero,IntPtr.Zero);
            yield return new WaitForSecondsRealtime(.25f);yield return KeyMessage(window,0x71);
            Check(person.GraphicsMenuVisible,"F2 opens the native graphics panel");
            PlayerGraphics.RestoreDefaults();yield return KeyMessage(window,0x25);
            Check(PlayerGraphics.Edges==0,"Windows left arrow switches final antialiasing off");
            yield return KeyMessage(window,0x28);yield return KeyMessage(window,0x25);yield return KeyMessage(window,0x25);
            Check(QualitySettings.shadows==ShadowQuality.Disable,"Native keyboard turns off the actual shadow system");
            yield return KeyMessage(window,0x28);yield return KeyMessage(window,0x27);
            Check(PlayerGraphics.Atmosphere==2,"Native keyboard selects High atmosphere");
            yield return KeyMessage(window,0x28);yield return KeyMessage(window,0x25);
            Check(PlayerGraphics.Contact==0,"Native keyboard switches cabin contact shading off");
            yield return KeyMessage(window,0x4D);Check(!person.MomentMenuVisible&&person.GraphicsMenuVisible,"Gameplay shortcuts do not move the passenger underneath Graphics");
            yield return KeyMessage(window,0x1B);Check(!person.GraphicsMenuVisible,"Escape returns from Graphics to the same camera");
            yield return new WaitForSecondsRealtime(.30f);yield return KeyMessage(window,0x4D);
            Check(person.MomentMenuVisible,"Windows received M and opened the actual passage list");
            yield return KeyMessage(window,0x71);yield return KeyMessage(window,0x71);Check(person.MomentMenuVisible&&!person.GraphicsMenuVisible,"F2 returns to the passage menu that opened Graphics");
            yield return KeyMessage(window,0x1B);Check(!person.MomentMenuVisible,"Windows received Escape and closed the list");
            person.SetFollowMomentView(true);person.GoToMoment(0);
            for(int i=1;i<person.MomentCount;i++){yield return KeyMessage(window,0xDD);Check(person.MomentIndex==i,"Windows right bracket selected "+person.MomentAt(i).id);}
            Check(person.SelectedView==0&&person.Drifting,"Repeated Windows right brackets leave an initially free passenger off the floor at the dock before pushing");
            yield return KeyMessage(window,0xDB);
            Check(person.MomentIndex==11&&person.Examined==ride.props["capillary_cell"],"Windows left bracket returned to the galley from dock");
            yield return KeyMessage(window,0xDD);
            Check(ride.Seconds==360&&person.MomentIndex==12,"Windows right bracket returned to the terminal stop");
            person.SetWatch(0);yield return KeyMessage(window,0x42);
            Check(!person.Examined,"The native B shortcut respects the locked service hatch");
            ride.Use(ride.props["locker_drawer"],person);yield return new WaitForSecondsRealtime(.75f);
            ride.Pickup(ride.props["access_card"]);ride.Use(ride.props["card_reader"],person);yield return new WaitForSecondsRealtime(1.9f);
            yield return KeyMessage(window,0x42);Check(person.Examined==ride.fracture.Cell,"The actual B key opens the authorized service inspection");
            var scan=MapVirtualKey(0x51,0);uint qDown=1u|(scan<<16);
            PostWindowMessage(window,0x100,(IntPtr)0x51,(IntPtr)qDown);yield return new WaitForSecondsRealtime(.46f);
            Check(ride.fracture.LoadNewton>40&&!ride.fracture.Broken,"Holding Q in the Windows inspection loads the real proof cam");
            yield return new WaitForSecondsRealtime(.58f);PostWindowMessage(window,0x101,(IntPtr)0x51,(IntPtr)(long)(qDown|0xC0000000u));yield return new WaitForSecondsRealtime(.45f);
            Check(ride.fracture.Broken&&!ride.fracture.Pressed&&ride.fracture.PeakNewton==320,"Physical key-up unloads the cam after the retained 320 N snap");
            yield return KeyMessage(window,0x52);yield return new WaitForSecondsRealtime(1);Check(!ride.fracture.Broken&&ride.fracture.ExchangeCount==1,"Windows R exchanges the guarded ceramic specimen");
            yield return KeyMessage(window,0x45);Check(!person.Examined,"Windows E returns from the materials bench");
#else
            yield break;
#endif
        }
        IEnumerator ReloadGraphics(){
            Check(PlayerGraphics.Edges==0 && PlayerGraphics.Shadows==0 && PlayerGraphics.Atmosphere==2 && PlayerGraphics.Contact==0,
                "A fresh Windows process restores all four choices written through ordinary F2 keyboard input in the previous process");
            PlayerGraphics.RestoreDefaults();
            Check(PlayerGraphics.Edges==1 && QualitySettings.shadows==ShadowQuality.All && PlayerGraphics.Atmosphere==1 && PlayerGraphics.Contact==1,
                "Defaults immediately restores the hardware renderer profile");
            yield break;
        }
    }
}
