#!/usr/bin/env python3
"""Build the pinned Fontconfig heap-pointer candidate into a private prefix."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile
import urllib.request

HERE=Path(__file__).resolve().parent


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cache',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--meson',default='meson')
    p.add_argument('--jobs',type=int,default=2)
    p.add_argument('--sanitizers',action='store_true')
    p.add_argument('--baseline',action='store_true',help='Build unchanged distribution source for negative controls')
    a=p.parse_args()
    if sys.platform!='linux' or platform.machine()!='x86_64':raise ValueError('This qualification targets Linux x86-64')
    if a.jobs<1:raise ValueError('Positive job count required')
    meson=shutil.which(a.meson)
    if not meson:raise ValueError('Meson and documented build dependencies are required')
    lock=json.loads((HERE/'source.lock.json').read_text());patch=HERE/lock['heap_pointer_patch']
    if digest(patch)!=lock['heap_pointer_patch_sha256']:raise ValueError('Declared patch differs')
    cache=a.cache.resolve();output=a.output.resolve()
    if output.exists():raise ValueError('Use a fresh output directory; replacement is forbidden')
    cache.mkdir(parents=True,exist_ok=True);output.mkdir(parents=True)
    report=dict(status='building',source_lock=lock,adaptation_applied=not a.baseline,
                sanitizers=a.sanitizers,commands=[],system_configuration_modified=False)
    try:
        archives=[]
        for entry in [lock['dsc'],*lock['sources']]:
            target=cache/entry['name']
            if not target.exists():
                temporary=target.with_suffix(target.suffix+'.download')
                with urllib.request.urlopen(entry['url'],timeout=60) as response,temporary.open('wb') as stream:
                    shutil.copyfileobj(response,stream)
                if digest(temporary)!=entry['sha256']:raise ValueError('Downloaded source differs: '+entry['name'])
                temporary.replace(target)
            if digest(target)!=entry['sha256']:raise ValueError('Cached source differs: '+entry['name'])
            if entry!=lock['dsc']:archives.append(target)
        with tarfile.open(archives[0]) as archive:archive.extractall(output,filter='data')
        source=output/lock['source_directory']
        with tarfile.open(archives[1]) as archive:archive.extractall(source,filter='data')
        def run(argv,label,cwd=None):
            report['commands'].append(dict(command=argv,cwd=str(cwd) if cwd else None))
            with (output/(label+'.log')).open('w') as log:
                subprocess.run(argv,cwd=cwd,stdout=log,stderr=subprocess.STDOUT,check=True)
        report['distribution_patches']=[]
        for line in (source/'debian/patches/series').read_text().splitlines():
            name=line.split('#',1)[0].strip()
            if not name:continue
            path=(source/'debian/patches'/name).resolve()
            if not path.is_relative_to(source/'debian/patches'):raise ValueError('Invalid distribution patch path')
            run(['patch','--batch','-p1','-i',str(path)],'distribution-'+str(len(report['distribution_patches'])),source)
            report['distribution_patches'].append(dict(name=name,sha256=digest(path)))
        for name,expected in lock['before_sha256'].items():
            if digest(source/name)!=expected:raise ValueError('Original patch input differs: '+name)
        if not a.baseline:run(['patch','--batch','-p1','-i',str(patch)],'heap-pointers',source)
        expected=lock['before_sha256'] if a.baseline else lock['after_sha256']
        for name,checksum in expected.items():
            if digest(source/name)!=checksum:raise ValueError('Effective source differs: '+name)
        build=output/'build';prefix=output/'install'
        run([meson,'setup',str(build),str(source),'--prefix',str(prefix),'--sysconfdir=/etc',
            '--localstatedir=/var','--datadir=/usr/share','--buildtype=debug','--wrap-mode=nodownload',
            '-Db_sanitize='+('address,undefined' if a.sanitizers else 'none'),'-Ddoc=disabled','-Dnls=disabled',
            '-Dtests=enabled','-Dtools=enabled','-Dcache-build=disabled','-Dxml-backend=expat',
            '-Ddefault-sub-pixel-rendering=rgb','-Dadditional-fonts-dirs=/usr/local/share/fonts'],'configure')
        run([meson,'compile','-C',str(build),'-j',str(a.jobs)],'build')
        # Keep the distro's actual /etc/fonts and cache paths, without running
        # installation rules that could write to those system directories.
        libraries=prefix/'lib/x86_64-linux-gnu';libraries.mkdir(parents=True)
        for path in sorted(build.glob('libfontconfig.so*')):
            if path.is_file() or path.is_symlink():shutil.copy2(path,libraries/path.name,follow_symlinks=False)
        if not (libraries/'libfontconfig.so.1').is_file():raise ValueError('Expected Fontconfig SONAME missing')
        notices=prefix/'share/orbiter-fontconfig';notices.mkdir(parents=True)
        for path in (source/'COPYING',HERE/'source.lock.json',patch):shutil.copy2(path,notices/path.name)
        report.update(status='built',libraries={p.name:digest(p) for p in libraries.iterdir() if p.is_file() and not p.is_symlink()},
            effective_source_sha256={name:digest(source/name) for name in expected},
            runtime_environment=dict(LD_LIBRARY_PATH=str(libraries)))
        print(json.dumps(report['runtime_environment']))
    except BaseException as error:
        report.update(status='failed',error=str(error));raise
    finally:(output/'build.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
