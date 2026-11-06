"""Probe the logged-in VM render session without showing or switching any UI."""
import base64,ctypes as C,json,os,subprocess,sys,time
from ctypes import wintypes as W
from pathlib import Path
k=C.WinDLL('kernel32',use_last_error=True);adv=C.WinDLL('advapi32',use_last_error=True);wts=C.WinDLL('wtsapi32',use_last_error=True);ue=C.WinDLL('userenv',use_last_error=True)
class STARTUPINFO(C.Structure):
 _fields_=[('cb',W.DWORD),('lpReserved',W.LPWSTR),('lpDesktop',W.LPWSTR),('lpTitle',W.LPWSTR),('dwX',W.DWORD),('dwY',W.DWORD),('dwXSize',W.DWORD),('dwYSize',W.DWORD),('dwXCountChars',W.DWORD),('dwYCountChars',W.DWORD),('dwFillAttribute',W.DWORD),('dwFlags',W.DWORD),('wShowWindow',W.WORD),('cbReserved2',W.WORD),('lpReserved2',C.POINTER(W.BYTE)),('hStdInput',W.HANDLE),('hStdOutput',W.HANDLE),('hStdError',W.HANDLE)]
class PROCESSINFO(C.Structure):_fields_=[('hProcess',W.HANDLE),('hThread',W.HANDLE),('dwProcessId',W.DWORD),('dwThreadId',W.DWORD)]
k.WTSGetActiveConsoleSessionId.restype=W.DWORD;k.CloseHandle.argtypes=[W.HANDLE];k.WaitForSingleObject.argtypes=[W.HANDLE,W.DWORD];k.WaitForSingleObject.restype=W.DWORD;k.GetExitCodeProcess.argtypes=[W.HANDLE,C.POINTER(W.DWORD)];k.GetExitCodeProcess.restype=W.BOOL
wts.WTSQueryUserToken.argtypes=[W.ULONG,C.POINTER(W.HANDLE)];wts.WTSQueryUserToken.restype=W.BOOL
ue.CreateEnvironmentBlock.argtypes=[C.POINTER(C.c_void_p),W.HANDLE,W.BOOL];ue.CreateEnvironmentBlock.restype=W.BOOL;ue.DestroyEnvironmentBlock.argtypes=[C.c_void_p]
adv.CreateProcessAsUserW.argtypes=[W.HANDLE,W.LPCWSTR,W.LPWSTR,C.c_void_p,C.c_void_p,W.BOOL,W.DWORD,C.c_void_p,W.LPCWSTR,C.POINTER(STARTUPINFO),C.POINTER(PROCESSINFO)];adv.CreateProcessAsUserW.restype=W.BOOL

k.CreateProcessW.argtypes=[W.LPCWSTR,W.LPWSTR,C.c_void_p,C.c_void_p,W.BOOL,W.DWORD,C.c_void_p,W.LPCWSTR,C.POINTER(STARTUPINFO),C.POINTER(PROCESSINFO)];k.CreateProcessW.restype=W.BOOL
u=C.WinDLL('user32',use_last_error=True)
u.CreateDesktopW.argtypes=[W.LPCWSTR,W.LPCWSTR,C.c_void_p,W.DWORD,W.DWORD,C.c_void_p];u.CreateDesktopW.restype=W.HANDLE
u.CloseDesktop.argtypes=[W.HANDLE];u.CloseDesktop.restype=W.BOOL
u.GetProcessWindowStation.restype=W.HANDLE;u.GetThreadDesktop.argtypes=[W.DWORD];u.GetThreadDesktop.restype=W.HANDLE;k.GetCurrentThreadId.restype=W.DWORD
u.GetUserObjectInformationW.argtypes=[W.HANDLE,C.c_int,C.c_void_p,W.DWORD,C.POINTER(W.DWORD)];u.GetUserObjectInformationW.restype=W.BOOL
k.GetCurrentProcessId.restype=W.DWORD;k.ProcessIdToSessionId.argtypes=[W.DWORD,C.POINTER(W.DWORD)];k.ProcessIdToSessionId.restype=W.BOOL
def object_name(handle):
 b=C.create_unicode_buffer(256);n=W.DWORD();assert u.GetUserObjectInformationW(handle,2,b,C.sizeof(b),C.byref(n)),C.WinError(C.get_last_error());return b.value
def context():
 sid=W.DWORD();assert k.ProcessIdToSessionId(k.GetCurrentProcessId(),C.byref(sid));return dict(session=sid.value,window_station=object_name(u.GetProcessWindowStation()),desktop=object_name(u.GetThreadDesktop(k.GetCurrentThreadId())))
def spawn(argv,desktop,cwd,token=None,environment=None):
 si=STARTUPINFO();si.cb=C.sizeof(si);si.lpDesktop=desktop;pi=PROCESSINFO();command=C.create_unicode_buffer(subprocess.list2cmdline(list(map(str,argv))));flags=0x400|0x08000000
 if token:ok=adv.CreateProcessAsUserW(token,str(argv[0]),command,None,None,False,flags,environment,str(cwd),C.byref(si),C.byref(pi))
 else:ok=k.CreateProcessW(str(argv[0]),command,None,None,False,flags,environment,str(cwd),C.byref(si),C.byref(pi))
 assert ok,C.WinError(C.get_last_error());return pi

def sha(path):return __import__('hashlib').sha256(Path(path).read_bytes()).hexdigest()
