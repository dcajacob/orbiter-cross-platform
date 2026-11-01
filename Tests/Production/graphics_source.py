#!/usr/bin/env python3
"""Preserve Windows drawing declarations and original celestial-sphere math."""
import re
from camera_source import old,raw,windows
from vessel_runtime_source import equal

def verify():
    aliases=[('oapi::SdkRectanglePtr','LPRECT'),('oapi::SdkSizePtr','LPSIZE'),('oapi::SdkWideText','LPWSTR'),('oapi::SdkRectangle','RECT'),('oapi::SdkPoint','POINT'),('oapi::SdkDrawContext','HDC'),('oapi::SdkFont','HFONT'),('oapi::SdkCoordinate','long'),('oapi::UInt32','DWORD'),('oapi::UInt16','WORD')]
    path='Orbitersdk/include/DrawAPI.h';actual=windows(raw(path))
    for a,b in aliases:actual=actual.replace(a,b)
    actual=actual.replace('#include "OrbiterSdkDrawingTypes.h"','').replace('#include "OrbiterValueTypes.h"','').replace('alignas(16)','__declspec(align(16))')
    equal(old(path),actual,'Complete Windows drawing SDK declarations, method order and formulas')
    path='Src/Orbiter/DrawAPI.cpp';equal(old(path),raw(path).replace('oapi::UInt32','DWORD'),'Original shared Sketchpad algorithms')
    path='Orbitersdk/include/CelSphereAPI.h';actual=windows(raw(path)).replace('using SphereClient=GraphicsClient;','').replace('SphereClient','GraphicsClient').replace('oapi::UInt32','DWORD').replace('oapi::UInt16','WORD')
    # COLORREF and DWORD have the exact same underlying Windows type. Compare
    # both original spellings after that declared canonicalization.
    equal(old(path).replace('COLORREF','DWORD'),actual,'Complete Windows celestial-sphere SDK declarations/layout')
    path='Src/Orbiter/CelSphereAPI.cpp';actual=windows(raw(path)).replace('SphereClient','GraphicsClient').replace('oapi::UInt32','DWORD').replace('oapi::UInt16','WORD')
    equal(old(path).replace('COLORREF','DWORD'),actual,'Original star/constellation loading, conversion, grid and label algorithms')
    print('Complete Windows drawing API conserved; original production celestial-sphere algorithms shared unchanged')
if __name__=='__main__':verify()
