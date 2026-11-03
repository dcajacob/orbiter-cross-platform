#!/usr/bin/env python3
"""Preserve Windows cockpit SDK types while sharing their native declarations."""
import subprocess
from pathlib import Path
from camera_source import windows
from vessel_runtime_source import equal
ROOT=Path(__file__).resolve().parents[2]
BASE='f725194209634f7fd5d1d44d426cfa9b5e303e37'

def original():return subprocess.check_output(['git','-C',str(ROOT),'show',BASE+':Orbitersdk/include/OrbiterAPI.h']).decode('cp1252').replace('\r\n','\n')
def ranges(source):
    a=source.index('typedef struct {\n\tRECT pos;');b=source.index('#pragma pack(pop)',a)+len('#pragma pack(pop)')
    x=source.rfind('// ===========================================================================',0,source.index('\\defgroup hudmode '))
    y=source.index('//@}',source.index('#define MFD_USER10',x))+len('//@}')
    m=source.index('#define PANEL_MOUSE_IGNORE');n=source.index('\n',source.index('#define PANEL_MOUSE_ONREPLAY',m))
    p=source.index('#define PANEL_MAP_NONE');q=source.index('\n',source.index('#define PANEL_MOVEOUT_RIGHT',p))
    return [(a,b,'#include "OrbiterCockpitData.h"'),(x,y,''),(m,n,''),(p,q,'')]

def verify_values():
    source=original();blocks=ranges(source)
    header=(ROOT/'Orbitersdk/include/OrbiterCockpitData.h').read_text()
    win=windows(header)
    prefix=win[:win.index('typedef struct {')]
    equal('''#ifndef ORBITER_COCKPIT_DATA_H
#define ORBITER_COCKPIT_DATA_H
#include "OrbiterValueTypes.h"
#include "OrbiterSdkDrawingTypes.h"
#include "OrbiterGeometry.h"
#include "OrbiterHandles.h"
namespace oapi {
#ifdef _WIN64
using CockpitMessageResult=LRESULT;
#else
using CockpitMessageResult=int;
#endif
using CockpitUnsignedParam=WPARAM;
using CockpitSignedParam=LPARAM;
}''',prefix,'Windows MFD callback scalar identities')
    body=win[len(prefix):].rsplit('#endif',1)[0]
    for a,b in [('oapi::CockpitMessageResult','OAPI_MSGTYPE'),('oapi::CockpitUnsignedParam','WPARAM'),('oapi::CockpitSignedParam','LPARAM'),('oapi::UInt32','DWORD'),('oapi::UInt','UINT'),('oapi::SdkRectangle','RECT')]:body=body.replace(a,b)
    equal('\n'.join(source[a:b] for a,b,_ in blocks),body,'Complete original cockpit SDK records, packing, field order and mode values')

def restore_gui(text):
    if '#include "OrbiterGuiData.h"' not in text:return text
    source=original();a=source.index('class OAPIFUNC ImGuiDialog {');b=source.index('\n};',a)+len('\n};')
    x=source.index('typedef struct {\n\tchar *helpfile;');y=source.index('} HELPCONTEXT;',x)+len('} HELPCONTEXT;')
    header=(ROOT/'Orbitersdk/include/OrbiterGuiData.h').read_text()
    body=header[header.index('typedef struct {'):].rsplit('#endif',1)[0]
    equal(source[x:y]+source[a:b],body,'Original ImGui dialog declarations, vtable order, inline methods and help record')
    text=text.replace('#include "OrbiterGuiData.h"',source[a:b],1)
    following=source[y:y+512]
    if text.count(following)!=1:raise ValueError('GUI SDK extraction anchor differs')
    return text.replace(following,source[x:y]+following,1)

def restore_api(actual):
    binary=isinstance(actual,bytes);text=actual.decode('cp1252') if binary else actual;text=text.replace('\r\n','\n')
    if '#include "OrbiterCockpitData.h"' not in text:return actual
    verify_values();source=original()
    if '#include "OrbiterMfdMessages.h"' in text:
        start=source.index('// Custom MFD message identifiers')
        messages=source[start:source.index('\n\n',start)]
        header=(ROOT/'Orbitersdk/include/OrbiterMfdMessages.h').read_text()
        if header.split('#define ORBITER_MFD_MESSAGES_H\n',1)[1].split('\n#endif',1)[0]!=messages:
            raise ValueError('Original MFD message identities changed')
        text=text.replace('#include "OrbiterMfdMessages.h"',messages)
    for a,b,replacement in sorted(ranges(source),reverse=True):
        following=source[b:b+512];needle=replacement+following
        if text.count(needle)!=1:raise ValueError('Cockpit SDK extraction anchor differs')
        text=text.replace(needle,source[a:b]+following,1)
    text=restore_gui(text)
    if text!=source:raise ValueError('Windows SDK changed beyond the declared cockpit data extraction')
    return text.encode('cp1252') if binary else text

def verify():
    restore_api((ROOT/'Orbitersdk/include/OrbiterAPI.h').read_bytes())
    name='Orbitersdk/include/MFDAPI.h'
    sdk=windows((ROOT/name).read_text()).replace('class Instrument_User;','',1)
    for portable,original_type in [('oapi::UInt32','DWORD'),('oapi::SdkFont','HFONT'),('oapi::SdkDrawContext','HDC')]:
        sdk=sdk.replace(portable,original_type)
    equal(subprocess.check_output(['git','-C',str(ROOT),'show',BASE+':'+name]).decode('cp1252'),sdk,'Original Windows MFD and MFD2 SDK interfaces')

    print('Original Windows cockpit SDK records, message types, packing and mode constants conserved')
if __name__=='__main__':verify()
