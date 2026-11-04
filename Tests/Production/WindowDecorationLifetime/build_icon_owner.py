#!/usr/bin/env python3
"""Build a private source-pinned libdecor GTK icon-owner baseline or candidate."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import tarfile
import urllib.request

HERE=Path(__file__).resolve().parent


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def require(value,message):
    if not value:raise ValueError(message)


def files(folder):
    return {path.relative_to(folder).as_posix():sha(path) for path in sorted(folder.rglob('*')) if path.is_file()}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('cache','output','meson','development-prefix'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--baseline',action='store_true')
    p.add_argument('--sanitizers',action='store_true')
    p.add_argument('--meson-pythonpath',type=Path)
    a=p.parse_args()
    for name in ('cache','output','meson','development_prefix','meson_pythonpath'):
        if getattr(a,name) is not None:setattr(a,name,getattr(a,name).resolve())
    require(not a.output.exists(),'Private plugin output exists; replacement is forbidden')
    lock_path=HERE/'libdecor-icon-source.lock.json';lock=json.loads(lock_path.read_text())
    a.cache.mkdir(parents=True,exist_ok=True)
    archives=[]
    for name,item in lock['archives'].items():
        target=a.cache/name
        if not target.exists():
            temporary=target.with_name(target.name+'.partial')
            try:
                with urllib.request.urlopen(item['url'],timeout=60) as source,temporary.open('wb') as output:
                    shutil.copyfileobj(source,output)
                require(temporary.stat().st_size==item['bytes'] and sha(temporary)==item['sha256'],
                        'Distribution source archive differs: '+name)
                temporary.replace(target)
            finally:temporary.unlink(missing_ok=True)
        require(target.stat().st_size==item['bytes'] and sha(target)==item['sha256'],'Cached source archive differs: '+name)
        archives.append(target)
    a.output.mkdir(parents=True)
    staging=a.output/'unpacked';staging.mkdir()
    for archive_path in archives:
        with tarfile.open(archive_path) as archive:
            for member in archive.getmembers():
                path=PurePosixPath(member.name)
                require(not path.is_absolute() and '..' not in path.parts and (member.isdir() or member.isfile()),
                        'Invalid source archive member: '+member.name)
            archive.extractall(staging,filter='data')
    source=staging/lock['upstream_directory']
    shutil.move(str(staging/'debian'),str(source/'debian'))
    require(files(source)==lock['source_files_sha256'],'Complete distribution source tree differs')
    require(not (source/'debian/patches/series').exists(),'Unexpected distribution source patch queue')
    original=source/lock['patched_file']
    if not a.baseline:
        subprocess.run(['patch','--batch','--forward','--fuzz=0','-p1','-i',str(HERE/'libdecor-icon-owner.patch')],
                       cwd=source,check=True,stdout=subprocess.DEVNULL)
        require(sha(original)==lock['patched_file_sha256'],'Icon owner patch differs')
    after=files(source)
    changed=[name for name in after if after[name]!=lock['source_files_sha256'][name]]
    require(changed==([] if a.baseline else [lock['patched_file']]) and set(after)==set(lock['source_files_sha256']),
            'Undeclared libdecor source change')
    environment=dict(os.environ,PKG_CONFIG_PATH=str(a.development_prefix/'lib/x86_64-linux-gnu/pkgconfig')+
                     ':'+str(a.development_prefix/'share/pkgconfig'))
    if a.meson_pythonpath:environment['PYTHONPATH']=str(a.meson_pythonpath)
    commands=[[str(a.meson),'setup',str(a.output/'build'),str(source),'-Dbuildtype=debug',
               '-Db_sanitize='+('address,undefined' if a.sanitizers else 'none'),'-Ddemo=false','-Dgtk=enabled',
               '--prefix='+str(a.output/'unused-install-prefix')],
              ['ninja','-C',str(a.output/'build'),'src/plugins/gtk/libdecor-gtk.so']]
    report=dict(status='building',package_version=lock['package_version'],baseline=a.baseline,
                sanitizers=a.sanitizers,commands=commands,source_lock_sha256=sha(lock_path),
                builder_sha256=sha(Path(__file__)),patch_sha256=sha(HERE/'libdecor-icon-owner.patch'),
                original_files_sha256=lock['source_files_sha256'],built_source_files_sha256=after,
                qualified=False,scope='Private GTK decoration plugin build; no system installation or application qualification.')
    manifest=a.output/'build.json'
    def save():manifest.write_text(json.dumps(report,indent=2)+'\n')
    save()
    try:
        for index,argv in enumerate(commands):
            with (a.output/('command-'+str(index)+'.log')).open('w') as log:
                subprocess.run(argv,env=environment,stdout=log,stderr=subprocess.STDOUT,check=True)
        plugin=a.output/'build/src/plugins/gtk/libdecor-gtk.so'
        require(plugin.is_file(),'Actual GTK plugin not built')
        symbols=subprocess.check_output(['nm','-D','--defined-only',str(plugin)],text=True)
        exports={line.split()[2]:line.split()[1] for line in symbols.splitlines()}
        require(exports.pop('libdecor_plugin_description',None)=='D','GTK plugin descriptor export differs')
        require(not exports or a.sanitizers and exports=={'__odr_asan.libdecor_plugin_description':'B'},
                'Unexpected GTK plugin public exports')
        linked=subprocess.check_output(['readelf','-d',str(plugin)],text=True)
        require(('libasan.so' in linked)==a.sanitizers and ('libubsan.so' in linked)==a.sanitizers,
                'Actual plugin sanitizer linkage differs')
        require(files(source)==after,'Private source changed while building')
        report.update(status='built',plugin=str(plugin),plugin_sha256=sha(plugin),
                      public_exports={'libdecor_plugin_description':'D'},
                      compile_commands_sha256=sha(a.output/'build/compile_commands.json'))
        shutil.copy2(source/'LICENSE',a.output/'libdecor-MIT-LICENSE')
    except BaseException as error:report.update(status='failed',error=str(error));raise
    finally:save()
    print('Built source-pinned private GTK plugin; runtime qualification remains required')


if __name__=='__main__':main()
