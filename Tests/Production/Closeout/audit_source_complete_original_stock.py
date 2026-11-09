#!/usr/bin/env python3
"""Independently audit the complete original Windows writer/reload cohort on Actions."""
import argparse
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

from contracts import ROOT,require,sha,load,atomic_json

PRODUCER='ba38a7efccb5f770e87add95f5e966aa40270756'
PROFILES={c+'-'+m for c in ('Debug','Release') for m in ('automatic','sse2')}


def writer_result(report,transport_sha):
    require(report['status']=='passed' and report['producer_commit']==PRODUCER and
            report['protocol']=='remaining-stock-matched-clock-v2' and report['download_manifest_sha256']==transport_sha and
            report['processes']==304 and report['presentations']==304*960 and set(report['profiles'])==PROFILES and
            report['phase6_complete'] is False and report['native_admission_qualified'] is False,
            'Complete unchanged independently audited original writer matrix required')
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('transport','decoded','preserved-debug','preserved-release','mesa','output'):
        parser.add_argument('--'+name,type=lambda x:Path(x).resolve(),required=True)
    a=parser.parse_args();require(not a.output.exists(),'Fresh independent original audit output required');a.output.mkdir(parents=True)
    report=dict(protocol='phase6-source-complete-original-windows-persistence-audit-v2',status='running',profiles={},build_pairs={},
        observer_source=PRODUCER,auditor_source=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(),
        wrapper_sha256=sha(__file__),phase6_complete=False,native_admission_qualified=False,commands=[])
    def save():atomic_json(a.output/'original-persistence-audit.json',report)
    save()
    try:
        sys.path[:0]=[str(ROOT/'Tests/Production/RemainingStockPersistence')]
        from observations import bind_owner
        import source_complete_original_transport as hosted_transport
        spec=importlib.util.spec_from_file_location('independent_original_persistence',ROOT/'Tests/Production/RemainingStockPersistence/audit.py')
        audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)
        transport=load(a.transport);transport_sha=sha(a.transport);decoded={profile:a.decoded/profile for profile in PROFILES}
        bindings=hosted_transport.inspect_matrix(transport,ROOT,decoded,PRODUCER)
        reader=bind_owner(ROOT,report['auditor_source']);config=reader.native.settings(reader.protocols.V2)
        guards=reader.original_audit.verifier_inputs();report['unchanged_reader_sources_sha256']=guards
        report['transport_sha256']=transport_sha;report['windows_transport']=bindings
        writer=a.output/'writer-audit.json'
        command=[sys.executable,'-B',str(ROOT/'Tests/Production/RemainingStockRepaired/audit.py'),
            '--artifacts',str(a.decoded),'--download-manifest',str(a.transport),
            '--preserved-debug',str(a.preserved_debug),'--preserved-release',str(a.preserved_release),
            '--mesa-runtime',str(a.mesa),'--producer-commit',PRODUCER,'--protocol',reader.protocols.V2,'--output',str(writer)]
        process=dict(argv=command,started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat());report['commands'].append(process)
        with (a.output/'writer-audit.log').open('w') as log:
            child=subprocess.Popen(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT);process['actual_pid']=child.pid;save()
            process['actual_returncode']=child.wait()
        process['log_sha256']=sha(a.output/'writer-audit.log');save()
        require(process['actual_returncode']==0,'Original writer audit failed; all raw failures remain preserved')
        writer_result(load(writer),transport_sha);report['writer_audit_sha256']=sha(writer)
        mesa,imports=reader.original_audit.independent_mesa(a.mesa,PRODUCER)
        for profile in sorted(PROFILES):
            original=a.preserved_debug if profile.startswith('Debug-') else a.preserved_release
            observed=audit.inspect_windows(decoded[profile],profile,reader,original,mesa,imports)
            report['profiles'][profile]=observed;save()
            print(profile,'independently audited 76 stock writers and 76 exact-save reloads',flush=True)
        for mode in ('automatic','sse2'):
            pairs={}
            require(report['profiles']['Debug-'+mode]['stock']['actual_math']==report['profiles']['Release-'+mode]['stock']['actual_math'],
                    'Original Debug/Release writers selected different CRT modes')
            for phase,relative in (('stock-writer','remaining-stock-repaired'),('reload','remaining-stock-persistence')):
                phase_pairs={}
                for case in config['cases']:
                    comparisons=[]
                    for repeat in (1,2):
                        left=decoded['Debug-'+mode]/relative/(case['id']+'-'+str(repeat))
                        right=decoded['Release-'+mode]/relative/(case['id']+'-'+str(repeat))
                        state=reader.original_audit.compare_state(left,right,config)
                        camera=reader.original_audit.camera_comparison(left,right,config)
                        similarity=reader.windows.image_ssim((left/'scene.rgba').read_bytes(),(right/'scene.rgba').read_bytes(),1280,720)
                        require(similarity>=config['image_ssim_minimum'],'Original Debug/Release complete frame exceeds unchanged budget')
                        comparisons.append(dict(state=state,camera=camera,ssim=similarity,
                            detail_calibration_only=reader.original_audit.detail_calibration(left,right)))
                    phase_pairs[case['id']]=comparisons
                pairs[phase]=phase_pairs
            report['build_pairs'][mode]=pairs;save()
        require(sha(a.transport)==transport_sha and reader.original_audit.verifier_inputs()==guards and sha(__file__)==report['wrapper_sha256'],
                'Independent audit sources or API-bound transport changed')
        for profile,binding in bindings.items():
            require(sha(binding['archive'])==binding['archive_sha256'],'Original API ZIP changed during independent audit')
            audit.check_files(decoded[profile],binding['decoded_members_sha256'])
        report.update(status='passed-source-complete-original-Windows-writer-and-exact-save-reload-audit',actual_windows_processes=608,
            actual_windows_presentations=608*960,writer_processes=304,reload_processes=304,
            scope='Original Windows cohort only. Native/current Windows comparisons, source-specific final candidate, hardware and hands-on acceptance remain pending.')
    except BaseException as error:report.update(status='failed',error=str(error));raise
    finally:save()
    print(report['status'])


if __name__=='__main__':main()
