#!/usr/bin/env python3
"""Re-read full original SDK initial capabilities before any renewed native observer lanes."""
import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
from hosted_native_package import ROOT,require,sha,load
from contracts import atomic_json,PROFILES
from checklist import requirements
sys.path.insert(0,str(ROOT/'Tests/Production/RemainingVessels'))
import capabilities

COMPILED='ccc02c8a34bd1f227624d8778a141e8736ae8111'
CASES=['remaining_stock_'+n for n in ('003','009','013','014','017','018','022','026','032')]
ORIGINAL='ba38a7efccb5f770e87add95f5e966aa40270756'
FIELDS=capabilities.FIELDS


def sources():
    result={}
    for name in ('RemainingVessels/capabilities.py','RemainingVessels/native.py','RemainingVessels/lifetimes.py',
                 'RemainingVessels/NativeProbe.cpp','StockVessels/Observation.h','RemainingStock/Details.h','RemainingStock/cases.json','Closeout/class_eligibility.py'):
        relative='Tests/Production/'+name;body=subprocess.check_output(['git','-C',str(ROOT),'show',COMPILED+':'+relative])
        require((ROOT/relative).read_bytes()==body,'Original complete capability collector/observer/auditor changed: '+relative)
        result[relative]=hashlib.sha256(body).hexdigest()
    require(len(FIELDS)==17,'All original exact SDK capability fields required')
    return result


def validate_parent(parent,profile,cases):
    require(len(cases)==38 and parent['producer_commit']==ORIGINAL and parent['protocol']=='remaining-stock-matched-clock-v2' and
            parent['host']=='repaired-original-windows' and parent['status']=='captured-awaiting-independent-audit' and
            parent['diagnostic_only'] is False and not parent['failures'] and
            parent['cases_requested']==list(cases) and set(parent['cases'])==set(cases) and
            parent['configuration']+'-'+parent['math_profile']==profile and parent['runtime_variant_unchanged'] is True and
            parent['observer_sources_unchanged'] is True and parent['actual_original_simulation_data_unchanged'] is True and
            parent['native_admission_qualified'] is False and parent['phase6_complete'] is False and
            all(len(v['runs'])==2 for v in parent['cases'].values()),'Complete actual original 38-scene/two-repeat profile required')


def validate_variant(parent,record,variant):
    expected=dict(protocol=parent['protocol'],protocol_sha256_lf=parent['protocol_sha256_lf'],
                  original_application_and_sdk_source=parent['original_application_and_sdk_source'],producer_commit=ORIGINAL,
                  runtime_variant_manifest_sha256=parent['runtime_variant_manifest_sha256'],frames=960,fixed_step=1/64,
                  capture_tick=800,diagnostic_only=False,cases_requested=parent['cases_requested'])
    require(variant==expected and record['status']=='captured' and record['process_returncode']==0 and
            record['finalized_ticks']==961,'Actual original per-run 960-frame contract or 961 finalized ticks differ')


def initial_signatures(path,declared,families):
    first=[]
    with Path(path).open(newline='') as stream:
        reader=csv.DictReader(stream)
        require({'tick','object','class',*FIELDS}<=set(reader.fieldnames or ()),'Original full SDK initial header incomplete')
        for row in reader:
            if row['tick']!='0':break
            require(None not in row and None not in row.values(),'Incomplete original SDK initial row')
            first.append(row)
    population={row['object']:row['class'] for row in first}
    require(first and len(population)==len(first) and all(population.get(k)==v for k,v in declared.items()),
            'Original complete initial population drops substitutes or duplicates a vessel')
    signatures=set()
    for row in first:
        values=tuple(float(row[k]) for k in FIELDS)
        require(all(math.isfinite(v) for v in values),'Nonfinite original initial SDK capability')
        if row['class'] in families:signatures.add((row['class'],*values))
    return signatures


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    require(os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('RUNNER_OS')=='Linux' and
            Path(os.environ['GITHUB_WORKSPACE']).resolve()==ROOT,'Actual standard hosted reference inspection required; no local full reference scan')
    require(not a.output.exists() and a.output.resolve().is_relative_to(ROOT/'out'),'Fresh original capability inventory required')
    a.output.mkdir(parents=True)
    report=dict(protocol='phase6-full-original-SDK-capability-inventory-v1',status='running',
                source=os.environ['GITHUB_SHA'],original_capture_source=ORIGINAL,fields=list(FIELDS),expected_original_structural_signature_count=16,
                proposed_native_cases=CASES,actual_new_simulator_processes=0,historical_inventory_relabelled=False,
                historical_inventory_available=False,qualification_granted=False,complete_class_eligibility_qualified=False,
                normal_admission_qualified=False,phase6_complete=False,hands_on_ready=False)
    def save():atomic_json(a.output/'inventory.json',report)
    try:
        require(subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()==report['source'],'Actual immutable capability inventory source required')
        report['original_capability_sources_sha256']=sources()
        sys.path.insert(0,str(ROOT/'Tests/Production/CurrentWindows/Hosted'))
        import retry_reference_proof as retry
        import source_complete_retry_provider as provider
        base=ROOT/'out/original-stock-audit';restoration=ROOT/'out/reference-audit-restoration/restoration.json'
        paths=dict(reference_transport=base/'transport/download.json',reference_audit=base/'independent/writer-audit.json',
                   reference_persistence_audit=base/'independent/original-persistence-audit.json',reference_restoration=restoration)
        cfg=dict(roles=dict(runner=dict(commit=report['source'])),reference_retry_inputs=retry.inventory(ROOT/'out'),
                 **{name:dict(path=str(path),sha256=sha(path)) for name,path in paths.items()})
        bound=provider.reference_receipts(cfg)
        require(bound['original_capture_source']==ORIGINAL and bound['original_windows_processes']==608,
                'Exact independently audited original full four-profile cohort required')
        restored=load(restoration);config=load(ROOT/'Tests/Production/RemainingStock/cases.json');cases={c['id']:c for c in config['cases']}
        families=set(requirements()['class-eligibility']['families'])
        require(len(cases)==38 and set(CASES)<=set(cases) and len(CASES)==9 and len(families)==11,'Original complete capability selection required')
        global_signatures=set();selected_signatures=set();reference_files={};profiles={};rows=0
        for profile in PROFILES:
            folder=base/'transport'/profile/'remaining-stock-repaired';parent_path=folder/'capture.json';parent=load(parent_path)
            validate_parent(parent,profile,cases)
            reference_files[str(parent_path)]=sha(parent_path)
            members=restored['original_api_archive_bindings'][profile]['decoded_members_sha256']
            require(reference_files[str(parent_path)]==members['remaining-stock-repaired/capture.json'],'Actual original parent differs from its independently audited API member')
            actual=set();selected=set()
            for name,case in cases.items():
                require(len(parent['cases'][name]['runs'])==2,'Both actual original SDK repetitions required')
                for repeat,record in enumerate(parent['cases'][name]['runs'],1):
                    relative=name+'-'+str(repeat)+'/stock-vessel-state.csv';path=folder/relative;value=sha(path)
                    require(value==record['files_sha256']['stock-vessel-state.csv']==members['remaining-stock-repaired/'+relative],
                            'Actual initial SDK witness differs from the original API/capture record')
                    variant_relative=name+'-'+str(repeat)+'/reference-variant.json';variant_path=folder/variant_relative
                    require(sha(variant_path)==record['files_sha256']['reference-variant.json']==members['remaining-stock-repaired/'+variant_relative],
                            'Original per-run frame descriptor differs from its actual API/capture witness')
                    validate_variant(parent,record,load(variant_path))
                    reference_files[str(variant_path)]=sha(variant_path)
                    reference_files[str(path)]=value;observed=initial_signatures(path,case['declared_vessels'],families)
                    actual.update(observed);rows+=1
                    if name in CASES:selected.update(observed)
            global_signatures.update(actual);selected_signatures.update(selected)
            profiles[profile]=dict(unique_signatures=sorted(actual),selected_case_signatures=sorted(selected),initial_sdk_snapshots=76)
        report.update(original_reference=bound,reference_receipts_sha256={str(p):sha(p) for p in paths.values()},
                      reference_files_sha256=reference_files,profiles=profiles,unique_signatures=sorted(global_signatures),
                      signature_count=len(global_signatures),selected_case_unique_signatures=sorted(selected_signatures),
                      actual_original_initial_sdk_snapshots=rows);save()
        require(rows==304 and len(global_signatures)==16 and selected_signatures==global_signatures,
                'Original sixteen structural combinations must remain exact and be covered by the unchanged nine scenes')
        require({v[0] for v in global_signatures}==families and all({tuple(v) for v in row['selected_case_signatures']}==global_signatures for row in profiles.values()),
                'Every original family and structural combination must be represented in every profile selection')
        require(all(sha(p)==v for p,v in reference_files.items()) and sources()==report['original_capability_sources_sha256'],
                'Original SDK witnesses or conserved owning sources changed during inventory')
        report.update(status='verified-full-original-SDK-initial-capability-inventory-only',
                      all_17_original_capability_fields_retained=True,original_16_signatures_and_nine_cases_preserved=True,
                      native_144_process_observer_off_on_controls_pending=True)
    except BaseException as error:report.update(status='failed-or-incomplete-unqualified',error=str(error));raise
    finally:save()
    print(report['status'])


if __name__=='__main__':main()
