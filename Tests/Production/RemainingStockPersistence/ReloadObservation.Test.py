#!/usr/bin/env python3
"""Verify complete reload file/observation boundaries against actual Windows data."""
import argparse
import copy
import importlib.util
import json
from pathlib import Path

from observations import bind_owner,require,sha

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('complete_persistence_reload_gate',HERE/'audit.py')
gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('native-owner','output'):p.add_argument('--'+name,type=lambda v:Path(v).resolve(),required=True)
    p.add_argument('--windows',action='append',required=True,help='Exactly four PROFILE=decoded-artifact-root entries')
    a=p.parse_args();require(not a.output.exists(),'Fresh reload-observation controls required')
    roots=gate.profile_paths(a.windows);first=json.loads((roots['Debug-automatic']/'remaining-stock-persistence/capture.json').read_text())
    reader=bind_owner(a.native_owner,first['producer_commit']);config=reader.windows.settings(reader.protocols.V2)
    report=dict(status='failed',positives=[],controls=[],native_admission_qualified=False,phase6_complete=False,
        scope='Actual four-profile Windows reload observation/file-boundary controls only; original package/source/transport and complete persistence qualification remain separate.')
    protected={}
    try:
        for profile,root in sorted(roots.items()):
            manifest=root/'remaining-stock-persistence/capture.json';capture=json.loads(manifest.read_text());protected[str(manifest)]=sha(manifest)
            require(capture['configuration']+'-'+capture['math_profile']==profile and capture['producer_commit']==first['producer_commit'] and not capture['failures'],
                    'Actual same-source Windows reload observations required')
            for identity,case_record in capture['cases'].items():
                case=next(c for c in config['cases'] if c['id']==identity)
                require(len(case_record['runs'])==2,'Both actual reload repetitions required')
                for repeat,recorded in enumerate(case_record['runs'],1):
                    saved=root/'remaining-stock-repaired'/(identity+'-'+str(repeat))/gate.CURRENT
                    executed,_=reader.derived_case(case,config,saved,sha(saved))
                    folder=root/'remaining-stock-persistence'/(identity+'-'+str(repeat))
                    actual=reader.windows.inspect_artifacts(folder,executed,config)
                    gate.check_windows_reload_observation(folder,recorded,actual)
                    protected.update({str(folder/n):v for n,v in recorded['files_sha256'].items()})
                    report['positives'].append(dict(profile=profile,case=identity,repeat=repeat,raw_files=len(recorded['files_sha256'])))
                    if len(report['positives'])!=1:continue
                    for name,mutate,reason in (
                        ('omitted_saved_output',lambda d:d['files_sha256'].pop(gate.CURRENT),'file closure differs'),
                        ('omitted_input_provenance',lambda d:d['files_sha256'].pop('persistence-input.json'),'file closure differs'),
                        ('omitted_actual_clock_file',lambda d:d['files_sha256'].pop('stock-clock.csv'),'file closure differs'),
                        ('unexpected_existing_file',lambda d:d['files_sha256'].update({'scene.png':sha(folder/'scene.png')}),'file closure differs'),
                        ('changed_saved_output_hash',lambda d:d['files_sha256'].update({gate.CURRENT:'0'*64}),'Actual captured bytes changed'),
                        ('changed_input_provenance_hash',lambda d:d['files_sha256'].update({'persistence-input.json':'0'*64}),'Actual captured bytes changed'),
                        ('changed_observed_math',lambda d:d.update(actual_math='unobserved'),'observation differs'),
                        ('omitted_startup_witness',lambda d:d.pop('configuration_input'),'configuration_input'),
                    ):
                        damaged=copy.deepcopy(recorded);mutate(damaged)
                        try:gate.check_windows_reload_observation(folder,damaged,actual)
                        except (ValueError,KeyError) as error:
                            require(reason in str(error),'Wrong actual reload rejection: '+name+' '+str(error))
                            report['controls'].append(dict(control=name,reason=str(error)))
                        else:raise ValueError('Damaged actual Windows reload accepted: '+name)
        require(len(report['positives'])==16 and len(report['controls'])==8 and all(sha(Path(n))==v for n,v in protected.items()),
                'Complete sixteen actual diagnostic reload observations/controls required')
        report.update(status='passed-actual-windows-reload-observation-controls',owning_bytes_unchanged=True,
            reader_sha256=sha(HERE/'audit.py'),test_sha256=sha(Path(__file__)),actual_existing_windows_reload_processes_read=16)
    except BaseException as error:report['error']=str(error);raise
    finally:
        a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n')
    print(len(report['positives']),'actual Windows reload observations;',len(report['controls']),'damaged boundaries rejected',flush=True)


if __name__=='__main__':main()
