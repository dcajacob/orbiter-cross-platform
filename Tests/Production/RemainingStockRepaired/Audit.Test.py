#!/usr/bin/env python3
"""Exercise the independent auditor against retained real failures and damaged copies."""
import argparse
import copy
import json
from pathlib import Path
import shutil
import sys
import tempfile

import audit


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('failed-build-artifact','preserved','mesa-runtime','original-artifact-root','data-root','planet-root','output'):
        p.add_argument('--'+name,type=lambda value:Path(value).resolve(),required=True)
    a=p.parse_args();audit.require(not a.output.exists(),'Fresh independent reader-control output required')
    failed=a.failed_build_artifact;download=json.loads((failed/'download.json').read_text())
    producer=download['source_commit'];archives=list(failed.glob('*.zip'))
    audit.require(len(archives)==1 and archives[0].stat().st_size==download['bytes'] and
                  audit.sha(archives[0])==download['sha256'],'Retained failed-build artifact transport differs')
    members=audit.archive_members(archives[0],failed/'decoded')
    audit.require(members==download['members_sha256'],'Retained failed-build members differ')
    root=failed/'decoded/remaining-stock-repaired-build';build=json.loads((root/'build.json').read_text())
    audit.require(build['status']=='failed' and build['configuration']=='Debug','Actual failed Debug build required')
    staged=audit.source_variant(root/'module-sources',producer)
    # This failed build has no successful build hashes. Bind this sub-reader
    # directly to the actual compile files in the independently pinned ZIP.
    compiled=dict(build,cmake_cache_sha256=members['remaining-stock-repaired-build/cmake/CMakeCache.txt'],
        compile_commands_sha256=members['remaining-stock-repaired-build/cmake/compile_commands.json'])
    compiler=audit.compile_evidence(root,compiled,'Debug')
    retained_original=audit.preserved(a.preserved);mesa,imports=audit.independent_mesa(a.mesa_runtime,producer)
    original_root=a.original_artifact_root;capture_root=original_root/'remaining-stock-original'
    capture=json.loads((capture_root/'capture.json').read_text());case_id='remaining_stock_014'
    config=audit.capture.settings();case=next(c for c in config['cases'] if c['id']==case_id)
    observed=capture_root/(case_id+'-1');recorded=capture['cases'][case_id]['runs'][0]['loaded_modules']
    actual_observer=original_root/'remaining-stock-original-runtime'/audit.OBSERVER
    audit.require(audit.sha(actual_observer)==capture['observer_sha256'],'Actual retained original observer differs')
    original=dict(retained_original);original[audit.OBSERVER]=audit.sha(actual_observer)
    providers=audit.loaded_modules(observed,recorded,original,case,config,mesa,imports,a.preserved)
    controls=[]
    def rejects(name,reader):
        try:reader()
        except (ValueError,OSError,KeyError) as error:controls.append(dict(control=name,reason=str(error)))
        else:raise ValueError('Damaged or failed evidence accepted: '+name)
    actual_data=audit.capture.data_inputs.inspect(a.data_root,a.planet_root)
    audit.capture.data_inputs.validate(actual_data)
    for name in ('changed_actual_data_hash','missing_actual_planet_archive','wrong_actual_data_lock'):
        damaged=copy.deepcopy(actual_data)
        if name=='changed_actual_data_hash':next(iter(damaged['files'].values()))['sha256']='0'*64
        elif name=='missing_actual_planet_archive':
            del damaged['files'][next(v for v in damaged['files'] if v.startswith('Textures/'))]
        else:damaged['lock_sha256_lf']['stock-data.lock.json']='0'*64
        rejects(name,lambda damaged=damaged:audit.capture.data_inputs.validate(damaged))
    with tempfile.TemporaryDirectory(prefix='orbiter-repaired-audit-controls-') as temporary:
        temporary=Path(temporary)
        for name in ('changed_original_header','changed_tank_and_forged_manifest','unrecorded_module_source','wrong_source_producer'):
            folder=temporary/name;shutil.copytree(root/'module-sources',folder,copy_function=shutil.copy2)
            report=json.loads((folder/'source-variant.json').read_text())
            if name=='wrong_source_producer':report['producer_commit']='0'*40
            elif name=='unrecorded_module_source':(folder/'source/Unrecorded.cpp').write_text('void unrecorded() {}\n')
            else:
                path='Src/Vessel/Atlantis/'+('Atlantis/Atlantis.h' if name=='changed_original_header' else 'Atlantis_Tank/Atlantis_Tank.cpp')
                source=folder/'source'/path;source.write_bytes(source.read_bytes()+b'\n// damaged control\n')
                if name=='changed_tank_and_forged_manifest':
                    report['staged_files_sha256'][path]=audit.sha(source)
                    report['declared_changes'][path]['repaired_sha256']=audit.sha(source)
            (folder/'source-variant.json').write_text(json.dumps(report))
            rejects(name,lambda folder=folder:audit.source_variant(folder,producer))
        for name in ('wrong_actual_crt','missing_original_tank_translation_unit','missing_actual_client_forced_include','wrong_actual_configuration'):
            folder=temporary/name;(folder/'cmake').mkdir(parents=True)
            shutil.copy2(root/'cmake/CMakeCache.txt',folder/'cmake/CMakeCache.txt')
            entries=json.loads((root/'cmake/compile_commands.json').read_text())
            if name=='wrong_actual_crt':entries[0]['command']=entries[0]['command'].replace('-MDd','-MD')
            elif name=='missing_original_tank_translation_unit':
                entries=[e for e in entries if not e['file'].endswith('Atlantis_Tank.cpp')]
            elif name=='missing_actual_client_forced_include':
                entry=next(e for e in entries if 'OGLClient.dir' in e['command'])
                entry['command']=entry['command'].replace('PreservedSdkTypes.h','UnrecordedTypes.h')
            else:
                path=folder/'cmake/CMakeCache.txt';path.write_text(path.read_text().replace('CMAKE_BUILD_TYPE:STRING=Debug','CMAKE_BUILD_TYPE:STRING=Release'))
            (folder/'cmake/compile_commands.json').write_text(json.dumps(entries))
            changed=dict(compiled,cmake_cache_sha256=audit.sha(folder/'cmake/CMakeCache.txt'),
                         compile_commands_sha256=audit.sha(folder/'cmake/compile_commands.json'))
            rejects(name,lambda folder=folder,changed=changed:audit.compile_evidence(folder,changed,'Debug'))
        for name in ('changed_loaded_observer','unrecorded_external_provider','missing_loaded_factory',
                     'changed_mesa_binding','duplicate_loaded_module'):
            folder=temporary/name;folder.mkdir()
            for file in ('invocation.json','mesa-bindings.json','renderer-modules.txt'):shutil.copy2(observed/file,folder/file)
            values=copy.deepcopy(recorded)
            if name=='changed_loaded_observer':
                next(v for v in values if v['path'].lower().endswith('productioncockpitdriver.dll'))['sha256']='0'*64
            elif name=='unrecorded_external_provider':
                row=next(v for v in values if v['path'].lower().startswith('c:\\windows\\'))
                row['path']='D:\\Unrecorded\\Provider.dll'
            elif name=='missing_loaded_factory':values=[v for v in values if not v['path'].lower().endswith('productioncockpitdriver.dll')]
            elif name=='changed_mesa_binding':
                path=folder/'mesa-bindings.json';value=json.loads(path.read_text())
                value['bindings'].setdefault('zlib1.dll',{})['effective_sha256']='0'*64;path.write_text(json.dumps(value))
            else:values.append(copy.deepcopy(values[0]))
            (folder/'renderer-modules.txt').write_text('\n'.join(v['path'] for v in values)+'\n')
            rejects(name,lambda folder=folder,values=values:audit.loaded_modules(folder,values,original,case,config,mesa,imports,a.preserved))
        rejects('actual_failed_build_cannot_qualify',lambda:audit.runtime_variant(root,producer,'Debug',a.preserved))
        incomplete=temporary/'incomplete-download.json'
        incomplete.write_text(json.dumps(dict(status='passed',source_commit=producer,artifacts=[dict(
            profile='Debug-sse2',name='repaired-remaining-stock-v1-Debug-sse2',path=archives[0].relative_to(audit.ROOT).as_posix(),
            bytes=download['bytes'],sha256=download['sha256'])])))
        argv=sys.argv
        try:
            sys.argv=['audit.py','--artifacts',str(failed/'decoded'),'--download-manifest',str(incomplete),
                '--preserved-debug',str(a.preserved),'--preserved-release',str(a.preserved),
                '--mesa-runtime',str(a.mesa_runtime),'--producer-commit',producer,'--output',str(temporary/'rejected-matrix.json')]
            rejects('actual_single_failed_artifact_cannot_form_four_profile_matrix',audit.main)
        finally:sys.argv=argv
        rejected=json.loads((temporary/'rejected-matrix.json').read_text())
        audit.require(rejected['status']=='failed' and not rejected['profiles'] and not rejected['native_admission_qualified'],
                      'Incomplete matrix did not retain an explicit failed record')
    audit.require(audit.archive_members(archives[0],failed/'decoded')==members,'Retained failed evidence changed during controls')
    audit.require(audit.preserved(a.preserved)==retained_original,'Independent original package changed during controls')
    audit.require(audit.capture.data_inputs.inspect(a.data_root,a.planet_root)==actual_data,'Actual original data changed during controls')
    result=dict(status='passed',source_sha256=audit.sha(Path(__file__)),auditor_sha256=audit.sha(Path(audit.__file__)),
        actual_failed_artifact_sha256=download['sha256'],actual_failed_producer=producer,
        actual_compiler_subreader=compiler,actual_source_subreader=staged,actual_recorded_system_providers=len(providers),
        actual_original_data_files_verified=len(actual_data['files']),
        controls=controls,owning_evidence_unchanged=True,full_repaired_matrix_audited=False,
        native_admission_qualified=False,phase6_complete=False,
        scope='Sub-reader positives from retained real Windows artifacts and damaged copies. '
              'The failed build remains failed; no complete repaired reference exists in these controls.')
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(len(controls),'independent source/CRT/DLL/provider/incomplete-matrix controls rejected; full repaired matrix remains pending')


if __name__=='__main__':main()
