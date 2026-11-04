#!/usr/bin/env python3
"""Exercise the independent reader against real generated source and mutations."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(HERE.parent))
from Dragonfly.native_source_audit import BASE,PREFIX,verify,verify_text


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--generated',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    a=parser.parse_args()
    if a.output.exists():raise ValueError('Fresh control record required')
    paths=verify(a.generated)
    before={p.relative_to(a.generated).as_posix():digest(p) for p in a.generated.rglob('*') if p.is_file()}
    names={Path(p).name.casefold():Path(p).name for p in paths}
    controls=[('thermal-initial-state','Thermal.cpp','energy=0;','energy=1;'),
        ('physical-size','Dragonfly.cpp','SetSize (4.0);','SetSize (4.01);'),
        ('attitude-formula','instruments.cpp','glRotatef(-now.z/Pi*180.0','glRotatef(-now.z/Pi*180.1'),
        ('original-gl-command','instruments.cpp','glLightfv(GL_LIGHT0,GL_DIFFUSE,light_diffuse);','glLightfv(GL_LIGHT1,GL_DIFFUSE,light_diffuse);'),
        ('physical-state-initialization','Thermal.cpp','Temp=_en;','Temp=0;'),
        ('undeclared-include','Thermal.cpp','#include "Thermal.h"','#include "NativeDrawing.h"'),
        ('nonvirtual-hydraulic-destruction','Hsystems.h','virtual ~h_object()=default;','~h_object()=default;'),
        ('missing-electrical-destruction','Esystems.h','virtual ~e_object()=default;',''),
        ('missing-warning-list-cleanup','instruments.cpp',
         'while (b_list.next) {bounds* gone=b_list.next;b_list.next=gone->next;delete gone;}','')]
    results=[]
    for label,name,anchor,replacement in controls:
        original=(ROOT/PREFIX/name).read_bytes().decode('cp1252').replace('\r\n','\n')
        actual=(a.generated/name).read_bytes().decode('cp1252').replace('\r\n','\n')
        if actual.count(anchor)!=1:raise ValueError('Actual control anchor differs: '+label)
        try:verify_text(name,original,actual.replace(anchor,replacement,1),names)
        except ValueError as error:results.append(dict(control=label,status='rejected',reason=str(error)))
        else:raise ValueError('Independent source reader accepted mutation: '+label)
    if before!={p.relative_to(a.generated).as_posix():digest(p) for p in a.generated.rglob('*') if p.is_file()}:
        raise ValueError('Actual generated source changed during in-memory controls')
    report=dict(status='passed',original_source=BASE,producer_commit=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(),
        generated=str(a.generated.resolve()),generated_files_sha256=before,original_source_streams=len(paths),
        independent_reader_sha256=digest(HERE/'native_source_audit.py'),test_sha256=digest(Path(__file__)),controls=results,
        original_and_generated_files_unchanged=True,native_admission_qualified=False,phase6_complete=False)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n')
    print('Independent original/native source conservation passed; all',len(results),'real damaged-source controls rejected')


if __name__=='__main__':main()
