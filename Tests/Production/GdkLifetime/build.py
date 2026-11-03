#!/usr/bin/env python3
"""Build the pinned GDK backend-string ownership candidate in a private prefix."""
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
    for name in ('cache','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--meson',default='meson')
    p.add_argument('--jobs',type=int,default=4)
    p.add_argument('--baseline',action='store_true')
    p.add_argument('--sanitizers',action='store_true')
    a=p.parse_args()
    if sys.platform!='linux' or platform.machine()!='x86_64':raise ValueError('Qualified target is Linux x86-64')
    if a.jobs<1:raise ValueError('Positive job count required')
    meson=shutil.which(a.meson)
    if not meson:raise ValueError('Meson and GTK development dependencies are required')
    cache=a.cache.resolve();out=a.output.resolve()
    if out.exists():raise ValueError('Use fresh output; replacement is forbidden')
    cache.mkdir(parents=True,exist_ok=True);out.mkdir(parents=True)
    lock=json.loads((HERE/'source.lock.json').read_text());patch=HERE/lock['ownership_patch']
    if digest(patch)!=lock['ownership_patch_sha256']:raise ValueError('Ownership patch differs')
    report=dict(status='building',source_lock=lock,sanitizers=a.sanitizers,adaptation_applied=not a.baseline,
                commands=[],system_installation_modified=False)
    try:
        archives=[]
        for entry in [lock['dsc'],*lock['sources']]:
            target=cache/entry['name']
            if not target.exists():
                temporary=target.with_suffix(target.suffix+'.download')
                with urllib.request.urlopen(entry['url'],timeout=60) as response,temporary.open('wb') as stream:
                    shutil.copyfileobj(response,stream)
                if digest(temporary)!=entry['sha256']:raise ValueError('Downloaded source differs')
                temporary.replace(target)
            if digest(target)!=entry['sha256']:raise ValueError('Cached source differs: '+entry['name'])
            if entry!=lock['dsc']:archives.append(target)
        with tarfile.open(archives[0]) as archive:archive.extractall(out,filter='data')
        source=out/lock['source_directory']
        with tarfile.open(archives[1]) as archive:archive.extractall(source,filter='data')
        def run(label,argv,cwd=None):
            report['commands'].append(dict(label=label,argv=argv,cwd=str(cwd) if cwd else None))
            with (out/(label+'.log')).open('w') as log:
                subprocess.run(argv,cwd=cwd,stdout=log,stderr=subprocess.STDOUT,check=True)
        report['distribution_patches']=[]
        for line in (source/'debian/patches/series').read_text().splitlines():
            name=line.split('#',1)[0].strip()
            if not name:continue
            path=(source/'debian/patches'/name).resolve()
            if not path.is_relative_to(source/'debian/patches'):raise ValueError('Invalid distribution patch path')
            run('distribution-'+str(len(report['distribution_patches'])),['patch','--batch','-p1','-i',str(path)],source)
            report['distribution_patches'].append(dict(name=name,sha256=digest(path)))
        for name,checksum in lock['before_sha256'].items():
            if digest(source/name)!=checksum:raise ValueError('Original ownership source differs')
        if not a.baseline:run('ownership',['patch','--batch','-p1','-i',str(patch)],source)
        expected=lock['before_sha256'] if a.baseline else lock['after_sha256']
        for name,checksum in expected.items():
            if digest(source/name)!=checksum:raise ValueError('Effective ownership source differs')
        build=out/'build'
        # Compile the distro's actual runtime data/configuration paths. Never
        # run installation rules; only copy the completed GDK libraries below.
        run('configure',[meson,'setup',str(build),str(source),'--prefix=/usr',
            '--libdir=lib/x86_64-linux-gnu','--sysconfdir=/etc','--localstatedir=/var',
            '--buildtype=debug','--wrap-mode=nodownload',
            '-Db_sanitize='+('address,undefined' if a.sanitizers else 'none'),
            '-Dx11_backend=true','-Dwayland_backend=true','-Dbroadway_backend=true',
            '-Dwin32_backend=false','-Dquartz_backend=false','-Dintrospection=false',
            '-Dgtk_doc=false','-Dman=false','-Ddemos=false','-Dexamples=false',
            '-Dtests=false','-Dinstalled_tests=false','-Dprint_backends=file','-Dcolord=no'])
        run('build',[meson,'compile','-C',str(build),'-j',str(a.jobs),'gdk-3'])
        libraries=out/'install/lib/x86_64-linux-gnu';libraries.mkdir(parents=True)
        for path in sorted((build/'gdk').glob('libgdk-3.so*')):
            if path.is_file() or path.is_symlink():shutil.copy2(path,libraries/path.name,follow_symlinks=False)
        if not (libraries/'libgdk-3.so.0').is_file():raise ValueError('GDK SONAME missing')
        notices=out/'install/share/orbiter-gdk';notices.mkdir(parents=True)
        for path in (source/'COPYING',HERE/'source.lock.json',patch):shutil.copy2(path,notices/path.name)
        report.update(status='built',effective_source_sha256={name:digest(source/name) for name in expected},
            libraries={p.name:digest(p) for p in libraries.iterdir() if p.is_file() and not p.is_symlink()},
            runtime_environment=dict(LD_LIBRARY_PATH=str(libraries)))
    except BaseException as error:report.update(status='failed',error=str(error));raise
    finally:(out/'build.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report['runtime_environment']))


if __name__=='__main__':main()
