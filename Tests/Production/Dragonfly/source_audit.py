#!/usr/bin/env python3
"""Conserve original calculations around declared WGL, initial-current and initial-reference-request repairs."""
from pathlib import Path
import hashlib
import re
from functools import lru_cache
import subprocess

ROOT=Path(__file__).resolve().parents[3]
BASE='f725194209634f7fd5d1d44d426cfa9b5e303e37'



@lru_cache(maxsize=1)
def gauge_unit_capacity():
    paths=subprocess.check_output(['git','-C',str(ROOT),'ls-tree','-r','--name-only',BASE,'--','Src/Vessel/Dragonfly'],text=True).splitlines()
    labels=[];calls=0
    for path in paths:
        if Path(path).suffix.lower() not in ('.cpp','.h'):continue
        text=subprocess.check_output(['git','-C',str(ROOT),'show',BASE+':'+path]).decode('cp1252')
        calls+=len(re.findall(r'\bnew\s+EGauge\s*\(',text))
        labels+=re.findall(r'\bnew\s+EGauge\s*\(\s*[^,]+,\s*[^,]+,\s*[^,]+,\s*"([^"\\]*)"',text)
    if calls!=len(labels) or set(labels)!={'%','Amps','V','YAW','PITCH','SGN'}:
        raise ValueError('Complete original EGauge label literal closure differs')
    capacity=max(len(value.encode('cp1252')) for value in labels)+1
    if capacity!=6:raise ValueError('Original longest gauge label and terminator capacity differs')
    return capacity


def adapted(name,source):
    if name=='Src/Vessel/Dragonfly/Esystems.cpp':
        anchor='  Volts=28.8;\n  power_load=r_amp;'
        if source.count(anchor)!=1:raise ValueError('Original fuel-cell constructor boundary differs')
        return source.replace(anchor,'  Volts=28.8;\n  Amperes=0; // No previous current before the first refresh.\n  power_load=r_amp;',1)
    if name=='Src/Vessel/Dragonfly/instruments.h':
        anchor='char unit[5];'
        if source.count(anchor)!=1:raise ValueError('Original gauge unit storage boundary differs')
        source=source.replace(anchor,'char unit['+str(gauge_unit_capacity())+'];',1)
        source=source.replace('class Panel;','class Panel;\nnamespace dragonfly {class WglBitmapTarget;}')
        return source.replace('   HBITMAP hBMP_old;','   HBITMAP hBMP_old;\n   dragonfly::WglBitmapTarget* bitmap_target;')
    if name!='Src/Vessel/Dragonfly/instruments.cpp':return source
    # The old bitmap pixel-format setup is unsupported by the actual Mesa WGL
    # provider. Replace only that exact platform block, not any GL geometry,
    # attitude calculation, lighting, projection, display-list or SDK blit.
    start=source.index('GLuint      PixelFormat;',source.index('void ADI::InitGL()'))
    end=source.index('//We load the texture',start)
    if hashlib.sha256(source[start:end].encode('cp1252')).hexdigest()!=\
            '23bf423fc4c6006f95f5a629c4dc799f3d9c0afc6be5086a9602ffafe15c7a76':
        raise ValueError('Original ADI bitmap platform block differs')
    source=source[:start]+('bitmap_target=new dragonfly::WglBitmapTarget(160,160);\n'
        'hDC2=bitmap_target->BitmapDC();\nhRC=bitmap_target->Context();\n'
        'hBMP=bitmap_target->Bitmap();\nhBMP_old=(HBITMAP)bitmap_target->PreviousBitmap();\n'
        'bitmap_target->Activate();\n\n')+source[end:]
    start=source.index('wglMakeCurrent(NULL,NULL);',source.index('ADI::~ADI()'))
    end=source.index('\n};\nvoid ADI::RegisterMe',start)
    source=source[:start]+'delete bitmap_target;\nbitmap_target=nullptr;\nhRC=NULL;\nhDC2=NULL;\n'+source[end:]
    changes=[('#include "dragonfly.h"','#include "dragonfly.h"\n#include "WglBitmapTarget.h"'),
        ('init=0;\nradius=10;','init=0;\nbitmap_target=nullptr;\nradius=10;'),
        ('void ADI::InitGL()\n{','void ADI::InitGL()\n{\ndragonfly::WglContextRestore restore;'),
        ('\tif (!init) InitGL();','\tif (!init) InitGL();\n\t{\n\tdragonfly::WglContextRestore active(bitmap_target->RenderDC(),hRC);'),
        ('\tglFinish();','\tglFinish();\n\tbitmap_target->Readback();\n\t}')]
    changes.append(('function_mode=0;//GDC;\norbital_ecliptic=-1;',
                    'function_mode=0;//GDC;\nref_handle=0; // No pending reference capture before user input.\norbital_ecliptic=-1;'))
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
            raise ValueError('Dragonfly source differs beyond declared WGL ownership and initial-state repairs: '+name)
        checked.append(name)
    if len(checked)!=23:raise ValueError('Incomplete original Dragonfly source closure')
    print('Conserved all '+str(len(checked))+' original Dragonfly source/header/resource files; only ADI context/bitmap ownership, initial fuel-cell current, initial ADI request and complete gauge-label storage are repaired; all update formulas, ordering, attitude calculations and GL drawing commands retained')


if __name__=='__main__':verify()
