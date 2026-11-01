#!/usr/bin/env python3
"""Preserve stock vessel enums and actual SDK animation class layouts."""
from pathlib import Path
import re
import subprocess
ROOT=Path(__file__).resolve().parents[2]
PRIOR='5bb528d5'
def original():return subprocess.check_output(['git','-C',str(ROOT),'show',PRIOR+':Orbitersdk/include/OrbiterAPI.h']).replace(b'\r\n',b'\n')
def current(name):return (ROOT/name).read_bytes().replace(b'\r\n',b'\n')
def ranges(source):
    result=[]
    def group(name):
        position=source.index(b'\\defgroup '+name+b' ')
        return source.rfind(b'/************************************************************************/',0,position) if name==b'navmode' else source.rfind(b'// ===========================================================================',0,position)
    start=group(b'refframe');end=source.index(b'} ATTITUDEMODE;',start)+len(b'} ATTITUDEMODE;')
    result.append((start,end,b'#include "OrbiterVesselData.h"'))
    start=group(b'airfoilliftdir');end=source.index(b'//@}',source.index(b'#define AIRCTRL_AXIS_XNEG',start))+len(b'//@}')
    result.append((start,end,b''))
    start=group(b'navmode');end=source.index(b'//@}',source.index(b'#define NAVMODE_HOLDALT',start))+len(b'//@}')
    result.append((start,end,b''))
    start=source.rfind(b'#pragma pack(push,1)',0,source.index(b'} MESHGROUP_TRANSFORM;'))
    end=source.index(b'typedef struct {\n\tRECT pos;',start)
    result.append((start,end,b'#include "OrbiterAnimationData.h"\n\n'))
    result.extend(record_ranges(source))
    result.extend(extra_ranges(source))
    result.extend(simulation_ranges(source))
    result.append(light_range(source))
    return result

def light_range(source):
    start=source.index(b'class OAPIFUNC LightEmitter')
    end=source.index(b'//@}',start)
    return start,end,b'#include "OrbiterLightData.h"\n'

def simulation_ranges(source):
    result=[]
    block=re.search(rb'typedef struct \{(?:(?!typedef struct \{).)*?\} ENGINESTATUS;',source,re.S)
    result.append((block.start(),block.end(),b'#include "OrbiterSimulationData.h"'))
    for name in (b'ELEMENTS',b'ORBITPARAM',b'GROUPEDITSPEC',b'GROUPREQUESTSPEC'):
        block=re.search(rb'typedef struct \{(?:(?!typedef struct \{).)*?\} '+name+rb';',source,re.S)
        result.append((block.start(),block.end(),b''))
    for match in re.finditer(rb'^#define (?:EVENT_VESSEL_|NAVBIT_|PROP_|MESHVIS_|PANEL_REDRAW_|EXHAUST_|OPTCAT_|OPTITEM_)[^\n]*',source,re.M):
        result.append((match.start(),match.end(),b''))
    start=source.index(b'const UINT ALLDOCKS');end=source.index(b'\n',start)
    result.append((start,end,b''))
    return result

def extra_ranges(source):
    result=[]
    start=source.index(b'typedef double (*LiftCoeffFunc)')
    end=source.rfind(b'// ===========================================================================',0,source.index(b'\\defgroup airfoilliftdir '))
    result.append((start,end,b''))
    start=source.rfind(b'/**',0,source.index(b'#define MANCTRL_ATTMODE'))
    end=source.index(b'//@}',source.index(b'#define MANCTRL_ANYDEVICE'))+len(b'//@}')
    result.append((start,end,b''))
    start=source.index(b'enum AltitudeMode {');end=source.index(b'};',start)+2
    result.append((start,end,b''))
    return result

def record_ranges(source):
    result=[]
    for index,name in enumerate((b'EXHAUSTSPEC',b'PARTICLESTREAMSPEC',b'BEACONLIGHTSPEC')):
        block=re.search(rb'typedef struct \{(?:(?!typedef struct \{).)*?\} '+name+rb';',source,re.S)
        if block is None:raise ValueError('Original vessel record is missing')
        start=source.rfind(b'/**',0,block.start());end=block.end()
        result.append((start,end,b'#include "OrbiterVesselRecords.h"' if index==0 else b''))
    block=re.search(rb'typedef struct \{(?:(?!typedef struct \{).)*?\} VESSELSTATUS;',source,re.S)
    start=source.rfind(b'/**',0,block.start())
    end=source.index(b'\n',source.index(b'#define VS_DOCKINFOLIST',start))+1
    result.append((start,end,b''))
    return result

def restore_api(actual):
    source=original()
    if (ROOT/'Orbitersdk/include/OrbiterCameraData.h').exists():
        from camera_source import restore_api as restore_camera
        actual=restore_camera(actual)
    # Use original offsets only to locate immutable extraction blocks; restore
    # each exact replacement once, in the already-extracted API's text.
    blocks=ranges(source)
    # Empty replacements keep the original following context as an anchor.
    for start,end,replacement in sorted(blocks,reverse=True):
        following=source[end:end+512]
        needle=replacement+following
        if actual.count(needle)!=1:raise ValueError('Vessel SDK extraction anchor differs')
        actual=actual.replace(needle,source[start:end]+following,1)
    return actual
def verify():
    source=original();blocks=ranges(source)
    values=current('Orbitersdk/include/OrbiterVesselData.h')
    for start,end,_ in blocks[:3]+extra_ranges(source):
        if values.count(source[start:end].rstrip())!=1:raise ValueError('Stock flight enum values changed')
    start,end,_=blocks[3]
    animation=current('Orbitersdk/include/OrbiterAnimationData.h').replace(b'oapi::AnimationIndex',b'UINT')
    if source[start:end].rstrip() not in animation:raise ValueError('SDK animation data/classes changed beyond exact unsigned-int alias')
    records=current('Orbitersdk/include/OrbiterVesselRecords.h').replace(b'oapi::UInt32',b'DWORD').replace(b'oapi::UInt',b'UINT')
    for start,end,_ in record_ranges(source):
        if source[start:end].rstrip() not in records:raise ValueError('Vessel status/particle/exhaust/beacon records changed beyond exact scalar aliases')
    simulation=current('Orbitersdk/include/OrbiterSimulationData.h').replace(b'oapi::UInt32',b'DWORD').replace(b'oapi::UInt16',b'WORD').replace(b'oapi::UInt',b'UINT')
    for start,end,_ in simulation_ranges(source):
        if source[start:end] not in simulation:raise ValueError('Simulation SDK flags or engine status changed')
    start,end,_=light_range(source)
    if source[start:end].rstrip() not in current('Orbitersdk/include/OrbiterLightData.h'):
        raise ValueError('Original SDK logical light classes changed')
    if restore_api(current('Orbitersdk/include/OrbiterAPI.h'))!=source:raise ValueError('SDK changed beyond declared vessel value extraction')
    vessel=current('Orbitersdk/include/VesselAPI.h')
    for name in (b'OrbiterValueTypes.h',b'OrbiterSdkDrawingTypes.h'):
        vessel=vessel.replace(b'#include "'+name+b'"\n',b'',1)
    for before,after in ((b'oapi::UInt32',b'DWORD'),(b'oapi::UInt16',b'WORD'),
                         (b'oapi::UInt',b'UINT'),(b'oapi::SdkRectangle',b'RECT'),
                         (b'oapi::SdkDrawContext',b'HDC')):
        vessel=vessel.replace(before,after)
    original_vessel=subprocess.check_output(['git','-C',str(ROOT),'show',PRIOR+':Orbitersdk/include/VesselAPI.h']).replace(b'\r\n',b'\n')
    if vessel!=original_vessel:raise ValueError('Vessel SDK declarations changed beyond exact Windows aliases')
    print('Stock flight enums and animation classes preserved with original Windows scalar identity')
if __name__=='__main__':verify()
