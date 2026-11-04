#!/usr/bin/env python3
"""Conserve the original key map and immediate/buffered control algorithms."""
import re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
BASE='889360f0516001d3261c1cce471229995c4f6c9b'
def old(name):return subprocess.check_output(['git','-C',str(ROOT),'show',BASE+':'+name]).decode().replace('\r\n','\n')
def read(name):return (ROOT/name).read_text()
def body(source,name):
    begin=source.index('{',source.index(name));end=begin+1;depth=1
    while depth:
        if source[end]=='{':depth+=1
        elif source[end]=='}':depth-=1
        end+=1
    return source[begin+1:end-1]
def verify():
    for name in ('Src/Orbiter/Keymap.cpp','Src/Orbiter/Keymap.h'):
        original=old(name);current=read(name)
        if name.endswith('.cpp'):
            current=current.replace('#include "Production/Text.h"\n#include <cstdint>\n#include <cstring>\n','')
            current=current.replace('std::uint8_t','BYTE').replace('orbiter::production::CompareText','_stricmp')
        else:
            current=current.replace('#ifdef _WIN32\n#include "windows.h"\n#include "Orbitersdk.h"\n#else\n#include "Production/FlightKeys.h"\n#endif\n#include "Production/CoreTypes.h"','#include "windows.h"\n#include "Orbitersdk.h"')
        current=current.replace('orbiter::production::UInt32','DWORD').replace('orbiter::production::UInt16','WORD')
        if current.rstrip()!=original.rstrip():raise ValueError('Key mapping formula/default/layout changed: '+name)
    api=read('Orbitersdk/include/OrbiterAPI.h')
    expected=[line for line in api.splitlines() if re.match(r'#define (?:OAPI_KEY_|OAPI_LKEY_|KEYDOWN|RESETKEY|KEYMOD_|LKEY_COUNT)',line)]
    actual=[line for line in read('Src/Orbiter/Production/FlightKeys.h').splitlines() if line.startswith('#define')]
    if expected!=actual:raise ValueError('Native key codes differ from Windows SDK')
    original=old('Src/Orbiter/Orbiter.cpp');current=read('Src/Orbiter/Production/FlightControls.cpp')
    begin=original.index('\t\t// shift 2-D panels',original.index('void Orbiter::KbdInputImmediate_System'))
    end=original.index('\n\t}',begin)
    if read('Src/Orbiter/Production/CockpitPanelInput.inc').rstrip()!=original[begin:end]:
        raise ValueError('Original immediate panel directions/key mapping/order changed')
    system=read('Src/Orbiter/Production/CockpitSystemInput.inc')
    system=system.replace('#include "CockpitPanelInput.inc"',read('Src/Orbiter/Production/CockpitPanelInput.inc').rstrip())
    if system!=body(original,'void Orbiter::KbdInputImmediate_System'):
        raise ValueError('Original complete system camera/panel/FOV input changed')
    if read('Src/Orbiter/Production/CockpitFovInput.inc')!=body(original,'VOID Orbiter::IncFOV'):
        raise ValueError('Original FOV update and forced refresh changed')
    from vessel_runtime_source import equal,span
    steps=[]
    for name in ('StepIncFOV','StepDecFOV'):
        match=re.search(r'else if \((keymap\.IsLogicalKey\(key, kstate, OAPI_LKEY_'+name+r'\))\)\s+(SetFOV\([^\n]+);',original)
        if not match:raise ValueError('Original stepped FOV key is missing: '+name)
        steps.append('if ('+match[1]+') { '+match[2]+'; return true; }')
    expected='''bool HandleCockpitStepFov(const Keymap& keymap,UInt32& key,char* kstate) {
        auto* g_camera=GetNativeRenderContext().camera;
        auto SetFOV=[](double value){GetCameraServices().SetFOV(value);};
        '''+'\n'.join(steps)+'''\nreturn false;
    }'''
    source=read('Src/Orbiter/Production/NativeCameraMouse.cpp');a,b=span(source,'HandleCockpitStepFov')
    equal(expected,source[a:b],'Original stepped FOV bindings, rounding, constants and update calls')
    begin=original.index('\t// main/retro/hover thruster settings',original.index('void Orbiter::KbdInputImmediate_OnRunning'))
    end=original.index('\n\t// left/right MFD control',begin)
    cbegin=current.index('\t// main/retro/hover thruster settings');cend=current.index('\n    }\n\tif (bEnableAtt)',cbegin)
    if current[cbegin:cend].replace('keyboard[','ctrlKeyboard[')!=original[begin:end]:raise ValueError('Immediate control formulas/order changed')
    begin=original.index('\tif (bEnableAtt) {',original.index('void Orbiter::UserJoyInput_OnRunning'))
    end=original.index('\n\tif (pDI->joyprop.bThrottle)',begin)
    begin2=current.index('\tif (bEnableAtt) {\n\t\tif (input.x)')
    end2=current.index('\n    if(input.throttle',begin2)
    joystick=current[begin2:end2].replace('joystick[','ctrlJoystick[').replace('input.alternate','js->rgbButtons[2]').replace('input.x','js->lX').replace('input.y','js->lY').replace('input.rz','js->lRz')
    if joystick.rstrip()!=original[begin:end].rstrip():raise ValueError('Joystick direction/control formulas changed')
    original=old('Src/Orbiter/VesselApplication.cpp');begin=original.index('\t// Navigation computer modes');end=original.index('\n\t// HUD control',begin)
    begin2=current.index('\t// Navigation computer modes');end2=current.index('\n#ifdef ORBITER_NATIVE_COCKPIT',begin2)
    canonical=current[begin2:end2].replace('vessel.AttMode()','attmode').replace('vessel.','')
    if canonical.rstrip()!=original[begin:end].rstrip():raise ValueError('Buffered flight controls changed')
    begin=original.index('\t// HUD control (internal view only)');end=original.index('\n\tif (KEYMOD_CONTROL (kstate))',begin)
    if read('Src/Orbiter/Production/CockpitHudInput.inc').rstrip()!=original[begin:end].rstrip():
        raise ValueError('Original default internal-view HUD key handler changed')
    call='''#ifdef ORBITER_NATIVE_COCKPIT
    auto* g_camera=CockpitCamera();
    auto* g_pane=CockpitPane();
#include "CockpitHudInput.inc"
#endif'''
    if current.count(call)!=1 or current.index(call)<end2:
        raise ValueError('Original HUD defaults must follow module and navigation handlers')
    begin=original.index('\t\tcase OAPI_KEY_DIVIDE:');end=original.index('\n\t\t}',begin)
    begin2=current.index('\t\tcase OAPI_KEY_DIVIDE:');end2=current.index('\n\t\t}',begin2)
    if current[begin2:end2].replace('vessel.','')!=original[begin:end]:raise ValueError('Original aerodynamic mode command changed')
if __name__=='__main__':verify();print('Original key map, SDK key codes, complete system camera/panel/FOV input and flight controls conserved')
