#!/usr/bin/env python3
"""Conserve the original key map and immediate/buffered control algorithms."""
import re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
BASE='889360f0516001d3261c1cce471229995c4f6c9b'
def old(name):return subprocess.check_output(['git','-C',str(ROOT),'show',BASE+':'+name]).decode().replace('\r\n','\n')
def read(name):return (ROOT/name).read_text()
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
    begin2=current.index('\t// Navigation computer modes');end2=current.index('\n    // Aerodynamic control surfaces:',begin2)
    canonical=current[begin2:end2].replace('vessel.AttMode()','attmode').replace('vessel.','')
    if canonical.rstrip()!=original[begin:end].rstrip():raise ValueError('Buffered flight controls changed')
    begin=original.index('\t\tcase OAPI_KEY_DIVIDE:');end=original.index('\n\t\t}',begin)
    begin2=current.index('\t\tcase OAPI_KEY_DIVIDE:');end2=current.index('\n\t\t}',begin2)
    if current[begin2:end2].replace('vessel.','')!=original[begin:end]:raise ValueError('Original aerodynamic mode command changed')
if __name__=='__main__':verify();print('Original key map, SDK key codes and flight controls conserved')
