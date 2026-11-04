#!/usr/bin/env python3
"""Conserve original Dragonfly calculations around explicit WGL ownership repair."""
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[3]
BASE='f725194209634f7fd5d1d44d426cfa9b5e303e37'


def adapted(name,source):
    if name!='Src/Vessel/Dragonfly/instruments.cpp':return source
    changes=[('#include "dragonfly.h"','#include "dragonfly.h"\n#include "WglContext.h"'),
        ('void ADI::InitGL()\n{','void ADI::InitGL()\n{\ndragonfly::WglContextRestore restore;'),
        ('ADI::~ADI()\n{','ADI::~ADI()\n{\nif (!init) return;\ndragonfly::WglContextRestore restore;\nrestore.Discard(hRC);'),
        ('\tif (!init) InitGL();','\tif (!init) InitGL();\n\t{\n\tdragonfly::WglContextRestore active(hDC2,hRC);'),
        ('\tglFinish();','\tglFinish();\n\t}')]
    for old,new in changes:
        if source.count(old)!=1:raise ValueError('Original ADI WGL binding anchor changed: '+old)
        source=source.replace(old,new)
    return source


def verify():
    paths=subprocess.check_output(['git','-C',str(ROOT),'ls-tree','-r','--name-only',BASE,'--','Src/Vessel/Dragonfly'],text=True).splitlines()
    checked=[]
    for name in paths:
        if Path(name).suffix.lower() not in ('.cpp','.h','.rc'):continue
        original=subprocess.check_output(['git','-C',str(ROOT),'show',BASE+':'+name]).decode('cp1252').replace('\r\n','\n')
        current=(ROOT/name).read_bytes().decode('cp1252').replace('\r\n','\n')
        if adapted(name,original)!=current:
            raise ValueError('Dragonfly source differs beyond declared WGL ownership repair: '+name)
        checked.append(name)
    if len(checked)!=23:raise ValueError('Incomplete original Dragonfly source closure')
    print('Conserved all '+str(len(checked))+' original Dragonfly source/header/resource files; only ADI WGL acquisition, restoration and unused-context teardown are adapted')


if __name__=='__main__':verify()
