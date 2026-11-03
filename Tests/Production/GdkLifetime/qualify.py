#!/usr/bin/env python3
"""Distinguish backend-string ownership from real leaks using the public GDK API."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

HERE=Path(__file__).resolve().parent


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('baseline','candidate','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--cc',default='cc')
    a=p.parse_args();out=a.output.resolve()
    if out.exists():raise ValueError('Use fresh qualification output')
    out.mkdir(parents=True)
    lock=json.loads((HERE/'source.lock.json').read_text());libraries={};hashes={}
    for name in ('baseline','candidate'):
        folder=getattr(a,name).resolve();record=json.loads((folder/'build.json').read_text())
        if record['status']!='built' or not record['sanitizers'] or record['source_lock']!=lock:
            raise ValueError('Unverified or uninstrumented build: '+name)
        if record['adaptation_applied']!=(name=='candidate'):raise ValueError('Incorrect baseline/candidate source')
        library=Path(record['runtime_environment']['LD_LIBRARY_PATH']).resolve()
        if not library.is_relative_to(folder) or not record['libraries']:raise ValueError('Invalid private library prefix')
        for filename,checksum in record['libraries'].items():
            if digest(library/filename)!=checksum:raise ValueError('GDK library drift')
            hashes[str(library/filename)]=checksum
        dynamic=subprocess.check_output(['readelf','-d',str(library/'libgdk-3.so.0')],text=True)
        if 'libasan.so' not in dynamic or 'libubsan.so' not in dynamic:raise ValueError('Expected GNU sanitizer runtimes missing')
        libraries[name]=library
    cc=shutil.which(a.cc)
    if not cc:raise ValueError('C compiler required')
    subprocess.run([cc,'-std=c11','-g','-O1','-fsanitize=address,undefined','-fno-omit-frame-pointer',
        str(HERE/'Backend.Test.c'),'-L'+str(libraries['candidate']),'-lgdk-3','-ldl','-pthread',
        '-o',str(out/'backend-test')],check=True)
    report=dict(status='failed',phase6_complete=False,results={},libraries_sha256=hashes,
        source_sha256={p.name:digest(p) for p in (Path(__file__),HERE/'Backend.Test.c',HERE/'source.lock.json')})
    try:
        exports={}
        for name in ('system','baseline','candidate'):
            report['results'][name]={}
            for mode in ('once','repeat','borrowed-default','lost'):
                target=out/(name+'-'+mode);target.mkdir()
                env=dict(os.environ,ASAN_OPTIONS='detect_leaks=1:fast_unwind_on_malloc=0',LSAN_OPTIONS='',
                         UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
                for variable in ('LD_LIBRARY_PATH','LD_PRELOAD'):env.pop(variable,None)
                if name!='system':env['LD_LIBRARY_PATH']=str(libraries[name])
                with (target/'data.txt').open('w') as data,(target/'console.log').open('w') as log:
                    process=subprocess.run([out/'backend-test',mode],env=env,stdout=data,stderr=log,timeout=60)
                text=(target/'console.log').read_text()
                if 'runtime error:' in text or 'ERROR: AddressSanitizer:' in text:raise ValueError('Invalid access: '+name+'-'+mode)
                match=re.search(r'SUMMARY: AddressSanitizer: (\d+) byte\(s\) leaked in (\d+) allocation',text)
                actual=(int(match[1]),int(match[2])) if match else (0,0)
                wanted=(0,0) if mode=='once' or (name=='candidate' and mode!='lost') else (
                    (73,1) if name=='candidate' else ((225,20) if mode=='lost' else (152,19)))
                if actual!=wanted or process.returncode!=(0 if wanted==(0,0) else 1):
                    raise ValueError('Unexpected ownership control: '+name+'-'+mode)
                loaded=Path((target/'data.txt').read_text().splitlines()[0].split('=',1)[1]).resolve()
                if name!='system' and loaded.parent!=libraries[name]:raise ValueError('Wrong GDK loaded')
                report['results'][name][mode]=dict(returncode=process.returncode,bytes=actual[0],allocations=actual[1],
                    loaded_library=str(loaded),library_sha256=digest(loaded))
            symbols=subprocess.check_output(['nm','-D','--defined-only',str(loaded)],text=True).splitlines()
            exports[name]=sorted(' '.join(line.split()[1:]) for line in symbols if line.split()[-1].startswith(('gdk_','_gdk')))
        if not exports['system'] or not exports['system']==exports['baseline']==exports['candidate']:
            raise ValueError('GDK symbol names/types differ from installed system or baseline')
        if any(digest(Path(name))!=checksum for name,checksum in hashes.items()):raise ValueError('GDK libraries changed during qualification')
        report.update(status='passed',repeated_setter_leak_fixed=True,borrowed_default_not_freed=True,
            genuine_lost_allocation_still_detected=True,gdk_symbol_names_and_types_identical=True,
            gdk_symbol_count=len(exports['system']))
    finally:(out/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Repeated setter ownership, borrowed default, genuine leak controls and GDK exports passed')


if __name__=='__main__':main()
