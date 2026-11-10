#!/usr/bin/env python3
"""Recover source-bound original numerical unit evidence without running or rebuilding anything."""
import argparse
import csv
import gzip
import hashlib
import io
import os
from pathlib import Path,PurePosixPath
import stat
import subprocess
import tarfile
import xml.etree.ElementTree as ET
import zipfile
from contracts import ROOT,PROFILES,require,load,sha,atomic_json
import recheck_native_discovery as retained
from hosted_native_general_api import source_identity


def math_scope(value,profile):
    require(profile in PROFILES and value['status']=='passed' and value['maximum_allowed_ulps']==1,'Original successful unchanged one-ULP MPFR budget required')
    expected='sse2' if profile.endswith('sse2') else 'fma3'
    require(value['automatic_profile']=='amd-6121d02-'+expected and value['equatorial_latitude_hex']==('0x1.fdf30f8d54924p-2' if expected=='sse2' else '0x1.fdf30f8d54923p-2'),'Original actual CPU profile and exact latitude result required')
    modes=value['profiles'];require(len(modes)==2 and [v['profile'] for v in modes]==['automatic','fma3' if expected=='sse2' else 'sse2'],'Both original actual CPU dispatch modes required')
    for record in modes:
        require(record['windows_samples_exact']==28800 and record['reload_atan2_samples_exact']==4225 and record['mpfr_samples']==7698 and record['edge_cases']=='passed' and set(record['maximum_ulps'])=={'sin','cos','asin','atan2','exp'} and all(type(v) is int and 0<=v<=1 for v in record['maximum_ulps'].values()),'Every original Windows sample, failing-input neighbour, MPFR input and edge check required')
    oracle=value['oracle'];require(oracle['precision_bits']==[256,512] and oracle['version'] and Path(oracle['path']).is_absolute() and len(oracle['sha256'])==64 and len(value['probe_sha256'])==64,'Actual original MPFR module/version/hash and retained probe identities required')
    return dict(actual_original_Math_unit_processes=1,original_CPU_dispatch_modes=2,original_Windows_samples_per_mode=28800,original_reload_atan2_samples_per_mode=4225,original_MPFR_samples_per_mode=7698,maximum_allowed_ulps=1,all_original_edge_checks_preserved=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('api','archive','output'):parser.add_argument('--'+name,type=lambda v:Path(v).resolve(),required=True)
    parser.add_argument('--profile',choices=PROFILES,required=True);a=parser.parse_args()
    require(os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('RUNNER_OS')=='Linux' and Path(os.environ['GITHUB_WORKSPACE']).resolve()==ROOT,'Actual standard hosted worker required; no local package transfer or execution')
    require(not a.output.exists() and a.output.is_relative_to(ROOT/'out'),'Fresh separate retained numerical evidence audit required');a.output.mkdir(parents=True)
    report=dict(protocol='phase6-source-bound-retained-original-numerical-unit-evidence-v1',status='running',auditor_source=os.environ['GITHUB_SHA'],profile=a.profile,new_simulator_processes=0,new_compiler_processes=0,new_numerical_test_processes=0,original_failed_producer_or_partial_flags_relabelled=False,original_oracle_binary_replayed=False,complete_numerical_reload_gate_qualified=False,complete_class_eligibility_qualified=False,normal_admission_qualified=False,phase6_complete=False,hands_on_ready=False)
    def save():atomic_json(a.output/'proof.json',report)
    try:
        api=load(a.api);job=retained.validate_api(api,a.profile);artifact=api['artifact']
        require(api['run']['status']=='completed' and api['run']['conclusion']=='failure' and a.archive.stat().st_size==artifact['size_in_bytes'] and 'sha256:'+sha(a.archive)==artifact['digest'],'Exact complete original failed package source/API/archive identity required')
        outer=a.output/'original-artifact';outer.mkdir();members={};seen=set()
        with zipfile.ZipFile(a.archive) as incoming:
            require(sum(v.file_size for v in incoming.infolist())<1024**3,'Bounded complete original package ZIP required')
            for item in incoming.infolist():
                name=retained.safe(item.filename);require(name.casefold() not in seen and not stat.S_ISLNK(item.external_attr>>16) and not (item.external_attr>>16)&0o7000,'Exact safe unique original ZIP member required');seen.add(name.casefold())
                if item.is_dir():continue
                path=outer/name;path.parent.mkdir(parents=True,exist_ok=True)
                with incoming.open(item) as source,path.open('xb') as target:
                    for block in iter(lambda:source.read(1024*1024),b''):target.write(block)
                members[name]=dict(bytes=item.file_size,sha256=sha(path))
        sealed_path=outer/a.profile/'hosted-package.json';sealed=load(sealed_path);archive=outer/(a.profile+'.tar.gz')
        require(sealed['status']=='built-only-tests-failed-or-incomplete' and sealed['test_errors']==retained.DISCOVERY_ERROR and sealed['source_commit']==retained.PRODUCER and sealed['configuration']+'-'+sealed['math_profile']==a.profile and sealed['archive_sha256']==sha(archive) and sealed['archive_bytes']==archive.stat().st_size,'Original discovery failure and complete actual sealed package must stay unchanged')
        expected=sealed['archive_members_sha256'];prefix='out/phase6-hosted-native/'+a.profile+'/';metadata={};seen=set();total=0
        selected={'build.json','registered-unit-tests.json','upstream-registered-unit-tests.json','engine-tests.xml','upstream-tests.xml','engine-tests.log','upstream-tests.log','engine/Math/math-verification.json'}
        with tarfile.open(archive) as incoming:
            for item in incoming:
                name=retained.safe(item.name);require(item.isfile() and not item.mode&0o7000 and name in expected and name.casefold() not in seen and name.startswith(prefix),'Exact regular manifested original native package member required');seen.add(name.casefold());total+=item.size;require(total<4*1024**3,'Bounded complete original package required')
                relative=name.removeprefix(prefix);keep=relative in selected;require(not keep or item.size<16*1024**2,'Bounded original numerical metadata required')
                digest=hashlib.sha256();parts=[];stream=incoming.extractfile(item)
                for block in iter(lambda:stream.read(1024*1024),b''):
                    digest.update(block)
                    if keep:parts.append(block)
                require(digest.hexdigest()==expected[name],'Every actual original package member byte must match its immutable manifest')
                if keep:
                    path=a.output/'original-numerical-metadata'/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b''.join(parts));metadata[relative]=dict(bytes=item.size,sha256=sha(path))
        require(seen=={n.casefold() for n in expected} and set(metadata)==selected,'Complete original binary/member closure and all original numerical/unit metadata required')
        folder=a.output/'original-numerical-metadata';build=load(folder/'build.json')
        require(sha(folder/'build.json')==sealed['build_manifest_sha256'] and build['status']=='built' and build['source_base']==retained.PRODUCER and build['instrumentation']=='address,undefined' and build['owning_sources_unchanged'] is True,'Actual immutable sanitized application/probe build identity required')
        sources={**build['source_sha256_lf'],**build['dependency_sha256_lf']}
        for name,digest in sources.items():
            value=(ROOT/name).read_bytes().replace(b'\r\n',b'\n');old=subprocess.check_output(['git','show',retained.PRODUCER+':'+name]).replace(b'\r\n',b'\n');require(hashlib.sha256(value).hexdigest()==digest==hashlib.sha256(old).hexdigest(),'Every exact original compiled source and dependency byte required')
        tests={kind:retained.test_result(folder/inventory,folder/result) for kind,inventory,result in [('engine','registered-unit-tests.json','engine-tests.xml'),('upstream','upstream-registered-unit-tests.json','upstream-tests.xml')]}
        require(tests==sealed['tests'] and tests['engine']['executed_processes']==32 and tests['upstream']['executed_processes']==2,'Every original registered engine/upstream unit must have actually executed without failure or skip')
        for name in ('engine-tests.xml','upstream-tests.xml','engine-tests.log','upstream-tests.log'):retained.clean_sanitizers((folder/name).read_text(errors='replace'))
        inventory=load(folder/'registered-unit-tests.json');entries=[v for v in inventory['tests'] if v['name']=='Production.ReferenceMath'];xml=ET.parse(folder/'engine-tests.xml');executed=[v for v in xml.findall('.//testcase') if v.get('name')=='Production.ReferenceMath']
        require(len(entries)==len(executed)==1 and len(entries[0]['command'])>=6 and 'Tests/Production/Math/verify.py' in entries[0]['command'][2] and executed[0].get('status') in (None,'run'),'The original registered numerical verifier and its actual successful CTest entry required')
        math=load(folder/'engine/Math/math-verification.json');scope=math_scope(math,a.profile);probes=[n for n,v in expected.items() if n.startswith(prefix+'engine/Math/') and n.endswith('.so') and v==math['probe_sha256']]
        require(len(probes)==1 and build['runtime_files_sha256'][probes[0]]==math['probe_sha256'],'Actual original tested numerical probe binary must be present and source-bound')
        fixture=ROOT/'Tests/Production/Math/Reference/ReloadAtan2';provenance=load(fixture/'provenance.json');body=gzip.decompress((fixture/'windows.csv.gz').read_bytes());rows=list(csv.DictReader(io.StringIO(body.decode())))
        require(provenance['automatic_refresh'] is False and provenance['samples']==len(rows)==4225 and provenance['fixture_sha256']==sha(fixture/'windows.csv.gz') and provenance['decoded_sha256']==hashlib.sha256(body).hexdigest() and {v['tag'] for v in rows}=={f'{y}|{x}' for y in range(-32,33) for x in range(-32,33)},'Every original frozen actual Windows neighbour and its complete source/provenance identity required')
        seed=next(v for v in rows if v['tag']=='0|0');require(seed['y']=='c1550c2a4f069879' and seed['x']=='412bcfdda20e1e30' and seed['fma3']=='bff6837bee573509' and seed['sse2']=='bff6837bee57350a','Original first differing primitive input and both exact Windows results required')
        for name in ('verify.py','Probe.cpp','Reference/ReloadAtan2/provenance.json','Reference/ReloadAtan2/windows.csv.gz'):
            relative='Tests/Production/Math/'+name;require((ROOT/relative).read_bytes()==subprocess.check_output(['git','show',retained.PRODUCER+':'+relative]),'Original numerical verifier/probe/frozen reference may not change')
        atomic_json(a.output/'original-package-member-hashes.json',expected);atomic_json(a.output/'original-outer-members.json',members)
        report.update(status='audited-retained-original-numerical-unit-evidence-only',original_source=retained.PRODUCER,original_run_id=retained.RUN,original_job_id=job['id'],original_artifact_id=artifact['id'],original_artifact_SHA256=artifact['digest'],original_source_api_sha256=sha(a.api),original_failed_package_sha256=sha(sealed_path),original_failed_package_status=sealed['status'],original_test_errors=sealed['test_errors'],original_package_members=len(expected),original_package_member_hashes_sha256=sha(a.output/'original-package-member-hashes.json'),original_outer_members_sha256=sha(a.output/'original-outer-members.json'),actual_core_identity=source_identity(),original_unit_results=tests,original_numerical_scope=scope,original_math_verification=math,original_math_probe_member=probes[0],original_metadata_members=metadata,original_verifier_command=entries[0],original_frozen_reload_provenance=provenance,original_first_difference_seed=seed,original_sources_and_all_tests_sanitizers_budgets_unchanged=True,scope='Read-only recovery of actual original source-bound numerical unit records, all28800 Windows primitive samples,4225 first-difference neighbours and7698 MPFR samples in both CPU modes. Original failed package remains failed. Observer equivalence, actual full numerical-reload gate, final class/candidate and software/local acceptance still need separate evidence.')
    except BaseException as error:report.update(status='failed-or-incomplete-unqualified',error=str(error));raise
    finally:save()
    print(report['status'])


if __name__=='__main__':main()
