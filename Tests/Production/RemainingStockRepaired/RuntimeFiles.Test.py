#!/usr/bin/env python3
"""Check the actual built variant manifest and reject protected-runtime mutations."""
import argparse
import json
from pathlib import Path

from build import files,runtime_changes,require,sha


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build',type=lambda v:Path(v).resolve(),required=True)
    a=p.parse_args();report=json.loads((a.build/'build.json').read_text())
    require(report['status']=='built-awaiting-runtime-and-independent-audit','Actual completed variant build required')
    runtime=a.build/'runtime';before=report['preserved_package_sha256'];after=report['runtime_files_sha256']
    actual=files(runtime);actual.pop('runtime-variant.json')
    require(actual==after,'Actual built runtime changed before file controls')
    positive=runtime_changes(before,after)
    require(positive==report['declared_runtime_changes'],'Recorded runtime changes differ from actual build')
    header=next(name for name in before if name.startswith('Orbitersdk/include/') and name.endswith('.h'))
    config=next(name for name in before if name.startswith('Config/') and name.endswith('.cfg'))
    controls=[]
    for name,path in (('changed_application','Orbiter.exe'),('changed_original_srb','Modules/Atlantis_SRB.dll'),
                      ('changed_public_sdk',header),('missing_original_configuration',config),
                      ('unrecorded_vessel_module','Modules/Unrecorded.dll'),
                      ('unrecorded_root_library','Unrecorded.dll')):
        damaged=dict(after)
        if name=='missing_original_configuration':del damaged[path]
        else:damaged[path]='0'*64
        try:runtime_changes(before,damaged)
        except ValueError as error:controls.append(dict(control=name,reason=str(error)))
        else:raise ValueError('Damaged original runtime accepted: '+name)
    require(actual=={name:sha(runtime/name) for name in actual},'Built runtime changed during file controls')
    target=a.build/'runtime-file-controls.json';require(not target.exists(),'Fresh runtime file-control output required')
    target.write_text(json.dumps(dict(status='passed',controls=controls,actual_build_unchanged=True,
        actual_build_manifest_sha256=sha(a.build/'build.json'),source_sha256=sha(Path(__file__))),indent=2)+'\n')
    print('Actual built variant manifest checked; six protected application/SDK/SRB/configuration/module mutations rejected')


if __name__=='__main__':main()
