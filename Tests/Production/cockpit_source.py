#!/usr/bin/env python3
"""Conserve original cockpit algorithms while introducing real platform services."""
import subprocess
from pathlib import Path
from camera_source import windows
from vessel_runtime_source import equal,raw
ROOT=Path(__file__).resolve().parents[2]
BASE='f725194209634f7fd5d1d44d426cfa9b5e303e37'
FILES=('Pane.h','Pane.cpp','Mfd.h','Mfd.cpp','hud.h','hud.cpp','Panel.h')

def verify():
    header=windows(raw('Src/Orbiter/Production/CockpitGraphics.h'))
    equal('''#ifndef ORBITER_PRODUCTION_COCKPIT_GRAPHICS_H
#define ORBITER_PRODUCTION_COCKPIT_GRAPHICS_H
#include "GraphicsAPI.h"
namespace oapi {using CockpitClient=GraphicsClient;}
#endif''',header,'Windows cockpit graphics type identity')
    for name in FILES:
        path='Src/Orbiter/'+name
        original=subprocess.check_output(['git','-C',str(ROOT),'show',BASE+':'+path]).decode('cp1252').replace('\r\n','\n')
        current=windows(raw(path)).replace('oapi::CockpitClient','oapi::GraphicsClient')
        if name in ('Mfd.h','hud.h'):current=current.replace('#include "Production/CockpitGraphics.h"','#include "GraphicsAPI.h"')
        else:current=current.replace('#include "Production/CockpitGraphics.h"','')
        if name=='Mfd.h':current=current.replace('class Pane;','class Pane;\nclass oapi::GraphicsClient;',1)
        equal(original,current,'Original cockpit calculations, declarations and call order: '+name)
    print('Original Pane, HUD, MFD and panel algorithms conserved; Windows graphics pointer types unchanged')
if __name__=='__main__':verify()
