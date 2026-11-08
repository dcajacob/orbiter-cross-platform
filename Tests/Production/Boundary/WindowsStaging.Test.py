#!/usr/bin/env python3
"""Verify the actual DLL staging function across a Windows incremental relink."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('source','output','cmake','ninja','compiler-environment'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    assert sys.platform=='win32' and not a.output.exists()
    a.output.mkdir(parents=True)
    source=a.source.read_text()
    function=source[source.index('function(orbiter_stage_core_runtime target)'):]
    function=function[:function.index('endfunction()')+len('endfunction()')]
    fix='''        set_property(TARGET ${target} APPEND PROPERTY LINK_DEPENDS
            "$<TARGET_FILE:orbiter_production_boundary>")
'''
    assert function.count(fix)==1
    environment={k.upper():v for k,v in os.environ.items()}
    command=Path(os.environ['SystemRoot'])/'System32/cmd.exe'
    text=subprocess.check_output([str(command),'/d','/c',str(a.compiler_environment)],text=True)
    for line in text.splitlines():
        key,sep,value=line.partition('=')
        if sep and key and not key.startswith('='):environment[key.upper()]=value
    environment['PATH']=str(a.ninja.parent)+';'+environment['PATH']
    record=dict(status='running',source_sha256=sha(a.source),controls={},commands=[])
    def run(label,argv,cwd):
        entry=dict(label=label,argv=list(map(str,argv)),cwd=str(cwd))
        record['commands'].append(entry)
        r=subprocess.run(entry['argv'],cwd=cwd,env=environment,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        (a.output/(label+'.log')).write_bytes(r.stdout)
        entry.update(actual_exitcode=r.returncode,output_sha256=hashlib.sha256(r.stdout).hexdigest())
        return r
    for name,body in [('current',function),('original',function.replace(fix,''))]:
        root=a.output/name;root.mkdir();build=root/'build'
        (root/'CMakeLists.txt').write_text('''cmake_minimum_required(VERSION 3.20)
project(WindowsStagingControl LANGUAGES CXX)
configure_file(CoreBuild.h.in CoreBuild.h @ONLY)
add_library(orbiter_production_boundary SHARED Core.cpp)
target_include_directories(orbiter_production_boundary PRIVATE "${CMAKE_BINARY_DIR}")
set_target_properties(orbiter_production_boundary PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/core"
    ARCHIVE_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/core")
add_executable(fixture Main.cpp)
target_link_libraries(fixture PRIVATE orbiter_production_boundary)
set_target_properties(fixture PROPERTIES RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/nested")
'''+body+'\norbiter_stage_core_runtime(fixture)\n')
        (root/'CoreBuild.h.in').write_text('#define CORE_TOKEN @TOKEN@\n')
        (root/'Core.cpp').write_text('#include "CoreBuild.h"\nextern "C" __declspec(dllexport) int Token() { return CORE_TOKEN; }\n')
        (root/'Main.cpp').write_text('''#include <cstdio>
#include <cstdlib>
extern "C" __declspec(dllimport) int Token();
int main(int argc,char** argv) { int value=Token();std::printf("%d\\n",value);return argc==2 && value==std::atoi(argv[1]) ? 0 : 1; }
''')
        rounds=[]
        for token in (1,2):
            label=name+'-'+str(token)
            assert run(label+'-configure',[a.cmake,'-S',root,'-B',build,'-G','Ninja',
                '-DCMAKE_MAKE_PROGRAM='+str(a.ninja),'-DCMAKE_BUILD_TYPE=Release','-DTOKEN='+str(token)],root).returncode==0
            assert run(label+'-build',[a.cmake,'--build',build,'--target','fixture','--parallel','2'],root).returncode==0
            exe=build/'nested/fixture.exe';dll=build/'core/orbiter_production_boundary.dll'
            staged=exe.parent/dll.name
            result=run(label+'-execute',[exe,str(token)],root)
            rounds.append(dict(token=token,actual_exitcode=result.returncode,
                actual_stdout=result.stdout.decode().strip(),core_sha256=sha(dll),staged_sha256=sha(staged),
                import_library_sha256=sha(build/'core/orbiter_production_boundary.lib'),
                executable_modified_ns=exe.stat().st_mtime_ns))
        assert rounds[0]['actual_exitcode']==0 and rounds[0]['actual_stdout']=='1'
        assert rounds[0]['core_sha256']!=rounds[1]['core_sha256']
        assert rounds[0]['import_library_sha256']==rounds[1]['import_library_sha256']
        if name=='current':
            assert rounds[1]['actual_exitcode']==0 and rounds[1]['actual_stdout']=='2'
            assert rounds[1]['core_sha256']==rounds[1]['staged_sha256']
            assert rounds[1]['executable_modified_ns']>rounds[0]['executable_modified_ns']
        else:
            assert rounds[1]['actual_exitcode']==1 and rounds[1]['actual_stdout']=='1'
            assert rounds[1]['core_sha256']!=rounds[1]['staged_sha256']
        record['controls'][name]=rounds
    assert sha(a.source)==record['source_sha256']
    record.update(status='passed-actual-Windows-incremental-DLL-staging',
                  original_failure_reproduced=True,source_unchanged=True,phase6_complete=False)
    (a.output/'verification.json').write_text(json.dumps(record,indent=2)+'\n')
    print(record['status'])


if __name__=='__main__':main()
