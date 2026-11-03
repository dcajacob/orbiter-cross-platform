#!/usr/bin/env python3
"""Reject forged decoded references, producer sources, actual CRT and module data."""
import argparse
import copy
import json
from pathlib import Path
import tempfile

from audit_original import audit_profile,digest,legacy,producer_sources,require,verify_archive


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('profile','archive','preserved','output'):p.add_argument('--'+name,type=lambda v:Path(v).resolve(),required=True)
    p.add_argument('--producer-commit',required=True)
    a=p.parse_args();require(not a.output.exists(),'Legacy original identity control output exists')
    report_path=a.profile/'legacy-stations-original/capture.json';report=json.loads(report_path.read_text())
    require(report['configuration']=='Debug' and report['math_profile']=='automatic','Controls require Debug automatic original profile')
    before={str(p.relative_to(a.profile)):digest(p) for p in a.profile.rglob('*') if p.is_file()}
    producer_sources(report,a.producer_commit);verify_archive(a.archive,a.profile)
    result=dict(status='failed',source_sha256=digest(Path(__file__)),capture_sha256=digest(report_path),controls=[])
    def rejected(name,action):
        try:action()
        except (ValueError,OSError,KeyError) as error:
            result['controls'].append(dict(control=name,reason=str(error)));return
        raise ValueError('Forged original legacy reference accepted: '+name)
    forged=copy.deepcopy(report)
    forged['source_sha256_lf']['Tests/Production/StockVessels/Observation.h']='0'*64
    rejected('forged_observer_source',lambda:producer_sources(forged,a.producer_commit))
    missing=copy.deepcopy(report);del missing['source_sha256_lf']['Tests/Production/StockVessels/Observation.h']
    rejected('missing_observer_source',lambda:producer_sources(missing,a.producer_commit))
    with tempfile.TemporaryDirectory(prefix='orbiter-original-legacy-identity-') as temporary:
        root=Path(temporary)
        for control in ('forged_decoded_capture','wrong_build_CRT','forged_reported_CRT','forged_raw_CRT',
                        'forged_actual_scenario_argument','forged_loaded_application'):
            out=root/control;out.mkdir()
            for file in a.profile.rglob('*'):
                if file.is_file():
                    target=out/file.relative_to(a.profile);target.parent.mkdir(parents=True,exist_ok=True);target.symlink_to(file)
            def replace(name,data):
                target=out/name;target.unlink();target.write_bytes(data)
            forged=copy.deepcopy(report)
            relative='legacy-stations-original/capture.json'
            first=legacy.settings()['cases'][0]['id']
            recorded=forged['cases'][first]['runs'][0]
            if control=='forged_decoded_capture':
                forged['cases'][first]['runs'][0]['declared_vessels']=999
                replace(relative,(json.dumps(forged,indent=2)+'\n').encode())
                rejected(control,lambda:verify_archive(a.archive,out));continue
            if control=='wrong_build_CRT':
                name='legacy-station-driver/compile_commands.json'
                commands=json.loads((out/name).read_text())
                require('MDd' in commands[0]['command'],'Real Debug compiler CRT flag missing')
                commands[0]['command']=commands[0]['command'].replace('MDd','MD')
                replace(name,(json.dumps(commands,indent=2)+'\n').encode())
            elif control=='forged_reported_CRT':recorded['actual_math']='sse2' if recorded['actual_math']=='fma3' else 'fma3'
            elif control=='forged_raw_CRT':
                name='legacy-stations-original/'+first+'-1/math-profile.txt'
                value='sse2' if recorded['actual_math']=='fma3' else 'fma3'
                replace(name,(value+'\n').encode());recorded['files_sha256']['math-profile.txt']=digest(out/name)
            elif control=='forged_actual_scenario_argument':
                name='legacy-stations-original/'+first+'-1/invocation.json'
                invocation=json.loads((out/name).read_text())
                invocation['argv']=[('--scenariox=Other' if value.startswith('--scenariox=') else value)
                                    for value in invocation['argv']]
                replace(name,(json.dumps(invocation,indent=2)+'\n').encode())
                recorded['files_sha256']['invocation.json']=digest(out/name)
            else:
                application=next(item for item in recorded['loaded_modules'] if Path(item['path'].replace('\\','/')).name.lower()=='orbiter.exe')
                application['sha256']='0'*64
            if control!='wrong_build_CRT':replace(relative,(json.dumps(forged,indent=2)+'\n').encode())
            rejected(control,lambda:audit_profile(out,'Debug-automatic',legacy.settings(),a.producer_commit,a.preserved))
    require(before=={str(p.relative_to(a.profile)):digest(p) for p in a.profile.rglob('*') if p.is_file()},
            'Original legacy identity controls changed the owning reference')
    result.update(status='passed',rejected_controls=len(result['controls']),original_capture_unchanged=True)
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print('Eight original legacy reference identity controls rejected; owning reference unchanged')


if __name__=='__main__':main()
