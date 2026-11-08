"""Read the inherited Windows rendering context and actual child creation time.

This helper does not acquire user tokens, change accounts, create desktops, or
select a desktop for a child. Children use ordinary subprocess inheritance.
"""
import ctypes as C
from ctypes import wintypes as W
import hashlib
from pathlib import Path
import subprocess
import sys
import uuid


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def context():
    require(sys.platform == 'win32', 'Actual Windows rendering session required')
    kernel = C.WinDLL('kernel32', use_last_error=True)
    user = C.WinDLL('user32', use_last_error=True)
    kernel.GetCurrentProcessId.restype = W.DWORD
    kernel.GetCurrentThreadId.restype = W.DWORD
    kernel.ProcessIdToSessionId.argtypes = [W.DWORD, C.POINTER(W.DWORD)]
    kernel.ProcessIdToSessionId.restype = W.BOOL
    user.GetProcessWindowStation.restype = W.HANDLE
    user.GetThreadDesktop.argtypes = [W.DWORD]
    user.GetThreadDesktop.restype = W.HANDLE
    user.GetUserObjectInformationW.argtypes = [W.HANDLE, C.c_int, C.c_void_p, W.DWORD, C.POINTER(W.DWORD)]
    user.GetUserObjectInformationW.restype = W.BOOL

    def name(handle):
        buffer = C.create_unicode_buffer(256)
        size = W.DWORD()
        require(user.GetUserObjectInformationW(handle, 2, buffer, C.sizeof(buffer), C.byref(size)),
                'Cannot observe actual Windows desktop/window station')
        return buffer.value

    session = W.DWORD()
    require(kernel.ProcessIdToSessionId(kernel.GetCurrentProcessId(), C.byref(session)),
            'Cannot observe actual Windows session')
    return dict(session=session.value, window_station=name(user.GetProcessWindowStation()),
                desktop=name(user.GetThreadDesktop(kernel.GetCurrentThreadId())))


def elevated():
    require(sys.platform == 'win32', 'Actual Windows user context required')
    shell = C.WinDLL('shell32', use_last_error=True)
    shell.IsUserAnAdmin.restype = W.BOOL
    return bool(shell.IsUserAnAdmin())


def machine_uuid():
    require(sys.platform == 'win32', 'Actual local Windows VM identity required')
    value = subprocess.check_output(['powershell.exe', '-NoLogo', '-NoProfile', '-NonInteractive', '-Command',
        '(Get-CimInstance -ClassName Win32_ComputerSystemProduct -ErrorAction Stop).UUID'], text=True)
    return str(uuid.UUID(value.strip()))


def start_identity(process):
    require(sys.platform == 'win32', 'Actual Windows child creation time required')
    kernel = C.WinDLL('kernel32', use_last_error=True)
    kernel.GetProcessTimes.argtypes = [W.HANDLE, *([C.POINTER(W.FILETIME)] * 4)]
    kernel.GetProcessTimes.restype = W.BOOL
    values = [W.FILETIME() for unused in range(4)]
    require(kernel.GetProcessTimes(int(process._handle), *(C.byref(value) for value in values)),
            'Cannot observe actual Windows child creation time')
    creation = values[0]
    return dict(kind='windows-process-creation-filetime',
                value=(creation.dwHighDateTime << 32) | creation.dwLowDateTime)
