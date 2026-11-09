"""Supply only the native package's declared GLU and source-matched decoration runtime core."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from hosted_native_package import ROOT,require,sha,load
from hosted_compositor_runtime import original_packages_unchanged

RUNTIME='ccc02c8a34bd1f227624d8778a141e8736ae8111'
SONAMES={'libglu1-mesa':'libGLU.so.1','libdecor-0-0':'libdecor-0.so.0'}


def contract(needed,glfw,plugin,lock,lock_sha,plugin_sha):
    require('Shared library: [libGLU.so.1]' in needed,'Actual immutable Dragonfly must declare GLU linkage')
    require(b'libdecor-0.so.0\x00' in glfw,'Actual immutable GLFW must declare its decoration runtime core')
    require(lock['package_version']=='0.2.5-1' and lock['automatic_refresh'] is False and
            plugin['status']=='built' and plugin['baseline'] is False and plugin['sanitizers'] is True and
            plugin['source_lock_sha256']==lock_sha and plugin['plugin_sha256']==plugin_sha,
            'Exact unchanged source-matched private GTK plugin required')
    return ['libglu1-mesa','libdecor-0-0='+lock['package_version']]


def inventory():return subprocess.check_output(['dpkg-query','-W','-f=${binary:Package}=${Version}\n'],text=True)


def install(providers,output,profile,run,inventory_reader,mesa):
    require(os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('RUNNER_OS')=='Linux',
            'Standard hosted native runtime dependency repair only')
    package=ROOT/'out/phase6-hosted-native'/profile;build=load(package/'build.json');engine=package/'engine'
    require(build['status']=='built' and build['source_base']==RUNTIME,'Exact immutable compiled native runtime required')
    targets={'dragonfly':engine/'NativeModules/Vessel/Dragonfly.so','graphics':engine/'NativeModules/Graphics/OGLClient.so'}
    for path in targets.values():
        require(build['runtime_files_sha256'][path.relative_to(ROOT).as_posix()]==sha(path),
                'Actual runtime dependency declaration differs from the immutable native package')
    lock_file=ROOT/'Tests/Production/WindowDecorationLifetime/libdecor-icon-source.lock.json';lock=load(lock_file)
    plugin=providers/'libdecor-candidate/build/src/plugins/gtk/libdecor-gtk.so';plugin_record=load(providers/'libdecor-candidate/build.json')
    needed=subprocess.check_output(['readelf','-d',str(targets['dragonfly'])],text=True)
    requested=contract(needed,targets['graphics'].read_bytes(),plugin_record,lock,sha(lock_file),sha(plugin))
    before_body=inventory();before=inventory_reader(before_body)
    (output/'native-runtime-before-packages.txt').write_text(before_body)
    run('supply-declared-native-runtime-dependencies',['apt-get','install','-y','--no-install-recommends','--no-upgrade',*requested],1200)
    after_body=inventory();after=inventory_reader(after_body)
    additions=original_packages_unchanged(before,after)
    require(not any(name.split(':')[0].startswith('libdecor-0-plugin-') for name in additions),
            'Patched private GTK plugin must not be replaced by an unpatched system plugin')
    full=output/'native-runtime-system-packages.txt';full.write_text(after_body)
    libraries={}
    for package_name,soname in SONAMES.items():
        names=[name for name in after if name in (package_name,package_name+':amd64')]
        require(len(names)==1,'Actual declared native runtime package missing or ambiguous')
        version=after[names[0]]
        if package_name=='libdecor-0-0':require(version==lock['package_version'],'Decoration runtime core and original plugin source version differ')
        members=subprocess.check_output(['dpkg-query','-L',names[0]],text=True).splitlines()
        aliases=[Path(name) for name in members if name.startswith('/usr/lib/') and Path(name).name==soname]
        require(len(aliases)==1 and aliases[0].is_file(),'Actual declared package does not own its required SONAME alias')
        path=aliases[0];actual=path.resolve()
        require(any(Path(name).is_file() and Path(name).resolve()==actual for name in members),
                'Actual runtime shared object escapes its declared package ownership')
        with actual.open('rb') as stream:require(stream.read(4)==b'\x7fELF','Declared runtime provider is not an ELF object')
        dynamic=subprocess.check_output(['readelf','-d',str(actual)],text=True)
        require('Library soname: ['+soname+']' in dynamic,'Actual runtime provider SONAME differs')
        libraries[soname]=dict(package=names[0],version=version,path=str(path),resolved_path=str(actual),sha256=sha(actual),dynamic_section=dynamic)
    environment=dict(os.environ,LD_LIBRARY_PATH=':'.join(map(str,[engine,
        providers/'fontconfig-candidate/install/lib/x86_64-linux-gnu',providers/'gdk-candidate/install/lib/x86_64-linux-gnu',
        mesa/'install/lib/x86_64-linux-gnu'])))
    environment.pop('LD_PRELOAD',None)
    resolutions={}
    for name,path in {**targets,'private-gtk':plugin}.items():
        label='resolve-native-runtime-'+name;run(label,['ldd',str(path)],600,environment)
        log=output/(label+'.log');text=log.read_text()
        require('not found' not in text,'Actual native runtime dependency remains unresolved: '+name)
        resolutions[name]=dict(path=str(path),sha256=sha(path),log_sha256=sha(log))
    helper=Path(__file__);source=os.environ['GITHUB_SHA']
    require(subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()==source and
            helper.read_bytes()==subprocess.check_output(['git','-C',str(ROOT),'show',source+':'+helper.relative_to(ROOT).as_posix()]),
            'Actual runtime installer differs from its immutable collector source')
    report=dict(protocol='phase6-hosted-declared-native-runtime-dependencies-v1',status='installed-declared-native-runtime-dependencies-only',
        collector_source=source,compiled_runtime_source=RUNTIME,helper_sha256=sha(helper),source_lock_sha256=sha(lock_file),
        private_gtk_sha256=sha(plugin),requested_packages=requested,actual_supplemental_packages=additions,
        previous_packages_and_versions_unchanged=True,full_inventory_sha256=sha(full),
        libraries=libraries,resolutions=resolutions,simulation_executed=False,phase6_complete=False,native_admission_qualified=False)
    path=output/'native-runtime-dependencies.json';path.write_text(json.dumps(report,indent=2)+'\n');verify(path)
    return report


def verify(path):
    report=load(path)
    require(report['status']=='installed-declared-native-runtime-dependencies-only' and
            report['protocol']=='phase6-hosted-declared-native-runtime-dependencies-v1' and
            report['collector_source']==os.environ['GITHUB_SHA'] and report['compiled_runtime_source']==RUNTIME and
            report['helper_sha256']==sha(Path(__file__)) and report['previous_packages_and_versions_unchanged'] is True and
            set(report['libraries'])==set(SONAMES.values()) and set(report['resolutions'])=={'dragonfly','graphics','private-gtk'} and
            report['simulation_executed'] is False and report['phase6_complete'] is False and report['native_admission_qualified'] is False and
            hashlib.sha256(inventory().encode()).hexdigest()==report['full_inventory_sha256'],
            'Actual recorded native dependency installer/packages changed')
    for item in report['libraries'].values():
        require(Path(item['path']).resolve()==Path(item['resolved_path']) and sha(item['path'])==item['sha256'],
                'Actual declared native runtime library changed')
    for item in report['resolutions'].values():require(sha(item['path'])==item['sha256'],'Actual owned runtime/plugin dependency input changed')
    return report
