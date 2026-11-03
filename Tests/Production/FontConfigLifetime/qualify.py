#!/usr/bin/env python3
"""Check real ownership, font results, ABI and cache compatibility without suppressions."""
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
    if out.exists():raise ValueError('Use a fresh qualification output')
    out.mkdir(parents=True)
    lock=json.loads((HERE/'source.lock.json').read_text())
    builds={};libraries={};library_hashes={}
    for name in ('baseline','candidate'):
        folder=getattr(a,name).resolve();record=json.loads((folder/'build.json').read_text())
        if record['status']!='built' or not record['sanitizers'] or record['source_lock']!=lock:
            raise ValueError('Unverified or uninstrumented build: '+name)
        if record['adaptation_applied']!=(name=='candidate'):raise ValueError('Wrong baseline/candidate source')
        library=Path(record['runtime_environment']['LD_LIBRARY_PATH'])
        if not library.is_relative_to(folder):raise ValueError('Library is outside its build')
        for filename,checksum in record['libraries'].items():
            if digest(library/filename)!=checksum:raise ValueError('Build library drift')
            library_hashes[str(library/filename)]=checksum
        builds[name]=folder;libraries[name]=library
    cc=shutil.which(a.cc)
    if not cc:raise ValueError('C compiler required')
    for source,binary in [('Ownership.Test.c','ownership'),('Data.Test.c','data')]:
        command=[cc,'-std=c11','-g','-O1','-fsanitize=address,undefined','-fno-omit-frame-pointer',
            '-I',str(builds['candidate']/'build'),str(HERE/source),'-L',str(libraries['candidate']),
            '-lfontconfig','-pthread','-o',str(out/binary)]
        subprocess.run(command,check=True)
    report=dict(status='failed',phase6_complete=False,ownership={},data={},libraries_sha256=library_hashes,source_sha256={
        p.name:digest(p) for p in (HERE/'qualify.py',HERE/'Ownership.Test.c',HERE/'Data.Test.c',HERE/'source.lock.json')})
    def run(build,binary,arguments,label,expected=None):
        target=out/label;target.mkdir()
        environment=dict(os.environ,ASAN_OPTIONS='detect_leaks=1:fast_unwind_on_malloc=0',
                         LSAN_OPTIONS='',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
        for variable in ('LD_PRELOAD','LD_LIBRARY_PATH'):environment.pop(variable,None)
        if build!='system':environment['LD_LIBRARY_PATH']=str(libraries[build])
        with (target/'data.txt').open('w') as data,(target/'console.log').open('w') as log:
            result=subprocess.run([out/binary,*arguments],env=environment,stdout=data,stderr=log,timeout=120)
        text=(target/'console.log').read_text()
        if 'runtime error:' in text or 'ERROR: AddressSanitizer:' in text:raise ValueError('Memory/undefined access: '+label)
        if expected is not None and result.returncode!=expected:raise ValueError('Unexpected control exit: '+label)
        return target,result.returncode,text
    try:
        for build in ('baseline','candidate'):
            report['ownership'][build]={}
            for mode in ('retained','released','lost'):
                expected=1 if mode=='lost' or (build=='baseline' and mode=='retained') else 0
                target,code,text=run(build,'ownership',[mode],build+'-'+mode,expected)
                match=re.search(r'SUMMARY: AddressSanitizer: (\d+) byte\(s\) leaked in (\d+) allocation',text)
                measured=(int(match[1]),int(match[2])) if match else (0,0)
                wanted=(2992,82) if mode=='lost' else ((2968,81) if expected else (0,0))
                if measured!=wanted:raise ValueError('Wrong retained/lost ownership result: '+build+'-'+mode)
                report['ownership'][build][mode]=dict(returncode=code,bytes=measured[0],allocations=measured[1])
        outputs=[]
        for build in ('baseline','candidate','system'):
            target,code,text=run(build,'data',['system'],build+'-font-data',0)
            if 'data-complete' not in text:raise ValueError('Incomplete font data')
            outputs.append((target/'data.txt').read_bytes())
            report['data'][build]=dict(sha256=digest(target/'data.txt'))
        if not outputs[0]==outputs[1]==outputs[2]:raise ValueError('Font metadata or match results changed')
        report['system_font_count']=int(outputs[0].splitlines()[0].split(b'=')[1])
        report['font_metadata_scope']='17 selected fields for every system font and fourteen real font queries'
        fontdir=out/'fonts';fontdir.mkdir();cache=out/'cache';cache.mkdir()
        shutil.copy2(builds['baseline']/lock['source_directory']/'test/4x6.pcf',fontdir/'4x6.pcf')
        config=out/'fonts.conf';config.write_text(f'<fontconfig><dir>{fontdir}</dir><cachedir>{cache}</cachedir></fontconfig>\n')
        run('baseline','data',['cache',fontdir,config],'cache-warmup',0)
        os.utime(fontdir,(1700000000,1700000000))
        caches=[];cache_results=[]
        for build,label in [('baseline','baseline-cache-1'),('baseline','baseline-cache-2'),('candidate','candidate-cache')]:
            target,code,text=run(build,'data',['cache',fontdir,config],label,0)
            payload={p.name:p.read_bytes() for p in cache.glob('*.cache-9')}
            if not payload:raise ValueError('No serialized cache produced')
            caches.append(payload);cache_results.append((target/'data.txt').read_bytes())
            for name,data in payload.items():(target/name).write_bytes(data)
        if not caches[0]==caches[1]==caches[2] or not cache_results[0]==cache_results[1]==cache_results[2]:
            raise ValueError('Cache bytes or cached font data changed')
        for producer,reader in [('baseline-cache-1','candidate'),('candidate-cache','baseline')]:
            for path in (out/producer).glob('*.cache-9'):(cache/path.name).write_bytes(path.read_bytes())
            before={p.name:(p.read_bytes(),p.stat().st_mtime_ns) for p in cache.glob('*.cache-9')}
            target,code,text=run(reader,'data',['cache-read',fontdir,config],reader+'-cross-reader',0)
            if before!={p.name:(p.read_bytes(),p.stat().st_mtime_ns) for p in cache.glob('*.cache-9')}:
                raise ValueError('Cross-reader rebuilt its cache')
            if (target/'data.txt').read_bytes()!=cache_results[0]:raise ValueError('Cross-reader data differs')
        symbols=[]
        for build in ('baseline','candidate'):
            text=subprocess.check_output(['nm','-D','--defined-only',libraries[build]/'libfontconfig.so.1'],text=True)
            symbols.append('\n'.join(' '.join(line.split()[1:]) for line in text.splitlines()))
        if symbols[0]!=symbols[1]:raise ValueError('Dynamic ABI symbol names/types differ')
        if any(digest(Path(path))!=checksum for path,checksum in library_hashes.items()):
            raise ValueError('Libraries changed during qualification')
        report.update(status='passed',retained_owner_false_positive_removed=True,genuine_lost_owner_still_detected=True,
            serialized_cache_bytes_identical=True,cross_readers_without_rebuild=True,dynamic_symbol_names_and_types_identical=True,
            cache_scope='One original 4x6 PCF fixture, two baseline cache rebuilds and one candidate cache rebuild')
    finally:(out/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Ownership controls, installed-system font results, dynamic ABI and binary cache compatibility passed')


if __name__=='__main__':main()
