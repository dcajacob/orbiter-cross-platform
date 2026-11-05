#!/usr/bin/env python3
"""Conserve original Lua Terminal drawing/commands/repository and Windows callbacks."""
from pathlib import Path
import subprocess,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path.insert(0,str(HERE.parent))
from camera_source import windows
from vessel_runtime_source import aliases,equal
ORIGINAL='684bd5b27005feecfa9effe796bd216f85e3392f'
FILES=('LuaMFD.cpp','LuaMFD.h','MfdInterpreter.cpp','MfdInterpreter.h')


def original(name):
    return subprocess.check_output(['git','-C',str(ROOT),'show',ORIGINAL+':Src/Plugin/LuaMFD/'+name]).decode('cp1252')


def once(text,before,after):
    if text.count(before)!=1:raise ValueError('Missing/ambiguous declared LuaMFD adapter: '+before)
    return text.replace(before,after)


def restore(name,source):
    source=source.replace('#ifdef ORBITER_NATIVE_MODULE','#ifndef _WIN32').replace('#ifndef ORBITER_NATIVE_MODULE','#ifdef _WIN32')
    source=windows(source)
    for modern,old in (('oapi::CockpitMessageResult','OAPI_MSGTYPE'),('oapi::CockpitUnsignedParam','WPARAM'),('oapi::CockpitSignedParam','LPARAM')):source=source.replace(modern,old)
    source=aliases(source).replace('DWORD col','COLORREF col')
    if name=='LuaMFD.cpp':
        source=source.replace('#include <algorithm>','').replace('#include <cstring>','')
        source=once(source,'oapiCreateFont (-h, true, "Courier New", FONT_NORMAL);','oapiCreateFont (-h, true, "Courier New");')
        source=once(source,"strncpy (env->cmd, line, sizeof(env->cmd)-1);\n\tenv->cmd[sizeof(env->cmd)-1] = '\\0';",'strncpy (env->cmd, line, 1024);')
        source=once(source,'return reinterpret_cast<OAPI_MSGTYPE>(new ScriptMFD(\n            DWORD(wparam & 0xffff), DWORD((wparam >> 16) & 0xffff), reinterpret_cast<VESSEL*>(lparam)));','return (OAPI_MSGTYPE) new ScriptMFD(LOWORD(wparam), HIWORD(wparam), (VESSEL*)lparam);')
    elif name=='LuaMFD.h':source=source.replace('#include "MFDAPI.h"','')
    elif name=='MfdInterpreter.cpp':
        source=once(source,'MFDInterpreter::~MFDInterpreter ()\n{\n    term_clear();\n}\n','')
        canonical='''    VESSEL *vessel = oapiGetVesselInterface(hV);
    // Use the SDK's canonical userdata factory, which also registers this
    // interface for the interpreter's existing vessel-validity checks.
    lua_pushvessel(L, vessel);
    lua_setfield(L, LUA_GLOBALSINDEX, "V");
    InitialiseVessel(L, vessel);'''
        original_binding='''\tVESSEL **pv = (VESSEL**)lua_newuserdata (L, sizeof(VESSEL*));
\t*pv = oapiGetVesselInterface (hV);
\tluaL_getmetatable (L, "VESSEL.vtable");  // push metatable
\tlua_setmetatable (L, -2);               // set metatable for user data
\tLoadVesselExtensions (L, *pv);
\tlua_setfield (L, LUA_GLOBALSINDEX, "V");
\tInitialiseVessel (L, *pv);'''
        source=once(source,canonical,original_binding)
    elif name=='MfdInterpreter.h':source=once(source,'\t~MFDInterpreter () override;','')
    return source


def verify():
    for name in FILES:
        current=(ROOT/'Src/Plugin/LuaMFD'/name).read_text()
        equal(original(name),restore(name,current),'Complete original LuaMFD '+name)
    host=subprocess.check_output(['git','-C',str(ROOT),'show',ORIGINAL+':Src/Orbiter/Orbiter.cpp']).decode('cp1252')
    fragment=host.split('} else if (KEYMOD_SHIFT (kstate)) {  // Shift-key combinations (reserved for MFD control)',1)[1].split('} else if (KEYMOD_ALT',1)[0]
    actual=(ROOT/'Src/Orbiter/Production/CockpitMfdInput.inc').read_text().replace('OAPI_KEY_LSHIFT','DIK_LSHIFT')
    equal(fragment,actual,'Original left/right Shift MFD keyboard selection')
    print('Conserved all four original LuaMFD files: drawing, commands, terminal pages, interpreter registration, Windows callbacks and update order; declared native thread/lifetime/failed-construction bindings, canonical vessel-userdata registration, terminal-buffer cleanup and bounded command termination only')


if __name__=='__main__':verify()
