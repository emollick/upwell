"""Run the actual player on a private Windows desktop for unattended input/GPU checks.

Real keyboard messages go to the player's own window; the user's foreground desktop
and its UI Automation clients remain independent. The program returns the unmodified
Windows process exit code, including native engine faults.
"""
import ctypes as C
from ctypes import wintypes as W
import os
import argparse
import subprocess
import sys
import time
import uuid

if os.name != "nt":
    raise SystemExit("The Windows player test requires Windows.")

class Startup(C.Structure):
    _fields_=[("cb",W.DWORD),("reserved",W.LPWSTR),("desktop",W.LPWSTR),("title",W.LPWSTR),
              ("x",W.DWORD),("y",W.DWORD),("width",W.DWORD),("height",W.DWORD),
              ("xchars",W.DWORD),("ychars",W.DWORD),("fill",W.DWORD),("flags",W.DWORD),
              ("show",W.WORD),("resCount",W.WORD),("resBytes",C.c_void_p),("stdin",W.HANDLE),
              ("stdout",W.HANDLE),("stderr",W.HANDLE)]

class Process(C.Structure):
    _fields_=[("process",W.HANDLE),("thread",W.HANDLE),("pid",W.DWORD),("tid",W.DWORD)]

user=C.WinDLL("user32",use_last_error=True)
kernel=C.WinDLL("kernel32",use_last_error=True)
user.CreateDesktopW.argtypes=[W.LPCWSTR,W.LPCWSTR,C.c_void_p,W.DWORD,W.DWORD,C.c_void_p]
user.CreateDesktopW.restype=W.HANDLE
user.CloseDesktop.argtypes=[W.HANDLE]
kernel.CreateProcessW.argtypes=[W.LPCWSTR,W.LPWSTR,C.c_void_p,C.c_void_p,W.BOOL,W.DWORD,C.c_void_p,W.LPCWSTR,
                                C.POINTER(Startup),C.POINTER(Process)]
kernel.WaitForSingleObject.argtypes=[W.HANDLE,W.DWORD]
kernel.GetExitCodeProcess.argtypes=[W.HANDLE,C.POINTER(W.DWORD)]
kernel.CloseHandle.argtypes=[W.HANDLE]
def check(ok):
    if not ok: raise C.WinError(C.get_last_error())

name="UpwellVerification-"+uuid.uuid4().hex
args=argparse.ArgumentParser(description=__doc__)
args.add_argument("--close-after",type=float,default=0, help="Send a normal close-window message after the specified seconds.")
args.add_argument("--uia-probe",action="store_true",help="Before closing, request the Windows accessibility root of this test window.")
args.add_argument("player");args.add_argument("player_args",nargs=argparse.REMAINDER);args=args.parse_args()
desktop=user.CreateDesktopW(name,None,None,0,0x000F01FF,None)
check(desktop)
process=Process()
try:
    info=Startup();info.cb=C.sizeof(info);info.desktop=name;info.flags=1;info.show=0
    command=C.create_unicode_buffer(subprocess.list2cmdline([args.player,*args.player_args]))
    check(kernel.CreateProcessW(args.player,command,None,None,False,0,None,None,C.byref(info),C.byref(process)))
    if args.close_after:
        time.sleep(args.close_after)
        callback=C.WINFUNCTYPE(W.BOOL,W.HWND,W.LPARAM)
        user.EnumDesktopWindows.argtypes=[W.HANDLE,callback,W.LPARAM]
        user.GetWindowThreadProcessId.argtypes=[W.HWND,C.POINTER(W.DWORD)]
        user.GetClassNameW.argtypes=[W.HWND,W.LPWSTR,C.c_int]
        user.PostMessageW.argtypes=[W.HWND,W.UINT,W.WPARAM,W.LPARAM]
        user.SendMessageTimeoutW.argtypes=[W.HWND,W.UINT,W.WPARAM,W.LPARAM,W.UINT,W.UINT,C.POINTER(C.c_size_t)]
        found=[]
        def window(hwnd,_):
            pid=W.DWORD();user.GetWindowThreadProcessId(hwnd,C.byref(pid));cls=C.create_unicode_buffer(128);user.GetClassNameW(hwnd,cls,128)
            if pid.value==process.pid and cls.value=="UnityWndClass":found.append(hwnd)
            return True
        user.EnumDesktopWindows(desktop,callback(window),0)
        if not found:raise RuntimeError("Could not locate the launched player's own window.")
        if args.uia_probe:
            result=C.c_size_t();user.SendMessageTimeoutW(found[0],0x003D,0,-25,2,3000,C.byref(result))
            time.sleep(.25)
        check(user.PostMessageW(found[0],0x10,0,0))
    check(kernel.WaitForSingleObject(process.process,0xffffffff)==0)
    code=W.DWORD();check(kernel.GetExitCodeProcess(process.process,C.byref(code)))
    print(f"Windows process {process.pid} exited with 0x{code.value:08X}.",flush=True)
finally:
    if process.thread: kernel.CloseHandle(process.thread)
    if process.process: kernel.CloseHandle(process.process)
    user.CloseDesktop(desktop)
raise SystemExit(C.c_int32(code.value).value)
