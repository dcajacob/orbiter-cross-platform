#!/usr/bin/env python3
"""Restore the existing qualified API reference at its original evidence paths."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
from contracts import ROOT,atomic_json,load,require,sha
from rejection_input_bundle import safe

LOCK=Path(__file__).with_name('phase6-current-candidate.lock.json')
REFERENCE=ROOT/'out/joint-api-qualification/proof/qualification.json'
ARTIFACT=ROOT/'out/frozen-admission-api'
BUNDLE=ROOT/'out/admission-reference-transfer'
EXPECTED_EVIDENCE=1125
EXPECTED_ROOT=Path('/home/runner/work/orbiter-cross-platform/orbiter-cross-platform')


def candidate():
    lock=load(LOCK);candidate_id=lock.pop('id')
    body=json.dumps(lock,sort_keys=True,separators=(',',':')).encode()
    require(lock['protocol']=='phase6-exact-candidate-identity-v1' and candidate_id==hashlib.sha256(body).hexdigest(),
            'Exact frozen candidate identity required')
    for name,value in (lock['identities']['runner']|lock['identities']['reference']['unchanged_locks']).items():
        require(sha(ROOT/name)==value,'Frozen stock runner/reference changed: '+name)
    return lock|dict(id=candidate_id)


def expected_paths(report):
    evidence=report['evidence_sha256']
    require(len(evidence)==EXPECTED_EVIDENCE,'All 1125 original qualification guards required')
    out={}
    for name,h in evidence.items():
        path=Path(name)
        require(path.is_relative_to(EXPECTED_ROOT) and path.is_absolute(),'Qualified reference path outside original runner')
        relative=path.relative_to(EXPECTED_ROOT).as_posix();safe(relative)
        require(str(EXPECTED_ROOT/relative)==name,'Noncanonical original qualification path')
        if relative.startswith('out/joint-api-qualification/'):
            out[relative]=h
        else:
            require(relative in {'Tests/Production/GeneralApiCorrection/'+n for n in ('prepare.py','startup_contract.py','startup-policy-v1.json')},
                    'Unexpected qualification source guard')
            require(sha(ROOT/relative)==h,'Original immutable qualification source changed')
    require(len(out)==1122,'All complete actual scoped evidence paths required')
    return out


def hosted():
    require(os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('RUNNER_OS')=='Linux' and
            Path(os.environ['GITHUB_WORKSPACE']).resolve()==ROOT==EXPECTED_ROOT and
            subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==os.environ['GITHUB_SHA'],
            'Actual immutable standard hosted workspace required')


def restore_reference(lock):
    sys.path.insert(0,str(ROOT/'Tests/Production/GeneralApiCorrection/Hosted'))
    import joint_api_qualification as joint
    pin=lock['identities']['reference']['joint_api'];record=load(ARTIFACT/'api.json');run=record['run'];a=record['artifact']
    jobs=record['jobs']
    require(record['repository']=={'owner':'dcajacob','repo':'orbiter-cross-platform'} and
            (run['id'],run['head_sha'],run['head_branch'],run['path'],run['run_attempt'],run['status'],run['conclusion'])==
            (pin['run_id'],pin['source'],'qualification/joint-general-api-v1','.github/workflows/phase6-joint-general-api.yml',1,'completed','success') and
            len(jobs)==2 and {j['name'] for j in jobs}=={'Joint original API qualification','Independently restore and reproduce joint API qualification'} and
            all(j['run_id']==run['id'] and j['head_sha']==run['head_sha'] and j['status']=='completed' and j['conclusion']=='success' and j['labels']==['ubuntu-24.04'] for j in jobs) and
            (a['id'],a['digest'],a['size_in_bytes'],a['expired'],a['workflow_run']['id'],a['workflow_run']['head_sha'],a['name'])==
            (pin['artifact_id'],'sha256:'+pin['sha256'],pin['bytes'],False,pin['run_id'],pin['source'],'independently-verified-joint-GeneralApi-reference'),
            'Exact completed independent General API source/roster/archive required')
    archive=ARTIFACT/'producer.zip';require(archive.stat().st_size==pin['bytes'] and sha(archive)==pin['sha256'],'Published independent proof bytes differ')
    extracted=ARTIFACT/'published';members=joint.zip_members(archive,extracted,128*1024**2)
    published=extracted/'joint-api-qualification/proof';proof=load(published/'joint-proof.json')
    require(proof['status']=='qualified-complete-native-Windows-GeneralApi-only' and proof['source']==pin['source'] and
            proof['github_run_id']==pin['run_id'] and proof['github_run_attempt']==1 and proof['independently_replayed_published_qualification'] is True and
            proof['qualified_report_sha256']==sha(published/'qualification.json')==pin['qualified_report_sha256'] and
            proof['input_artifacts']==load(joint.LOCK)['inputs'] and proof['inputs_lock_sha256']==sha(joint.LOCK) and
            proof['actual_original_native_processes']==8 and proof['actual_original_Windows_processes']==16 and
            proof['new_simulator_processes_launched']==0 and proof['normal_admission_qualified'] is False,
            'All actual independently qualified API source scopes required')
    atomic_json(ARTIFACT/'published-members.json',members)
    subprocess.run([sys.executable,'-B',joint.__file__,'--replay-published',str(published)],cwd=ROOT,check=True)
    require(sha(REFERENCE)==pin['qualified_report_sha256'],'Original qualified report changed after exact restoration')
    evidence=expected_paths(load(REFERENCE))
    paths=evidence|{REFERENCE.relative_to(ROOT).as_posix():sha(REFERENCE)}
    BUNDLE.mkdir(parents=True,exist_ok=False)
    transport=BUNDLE/'reference.tar.gz'
    with tarfile.open(transport,'x:gz',compresslevel=2) as tar:
        for name,h in sorted(paths.items()):
            path=ROOT/name;require(path.is_file() and not path.is_symlink() and sha(path)==h,'Actual qualified evidence changed: '+name)
            tar.add(path,arcname=name,recursive=False)
    atomic_json(BUNDLE/'reference.json',dict(status='restored-exact-qualified-GeneralApi-reference-only',candidate_id=lock['id'],
        source=os.environ['GITHUB_SHA'],run_id=int(os.environ['GITHUB_RUN_ID']),archive_sha256=sha(transport),
        archive_bytes=transport.stat().st_size,published_reference=pin,actual_qualification_guards=EXPECTED_EVIDENCE,
        retained_files=len(paths),new_simulator_processes=0,normal_admission_qualified=False,phase6_complete=False))


def extract_reference(lock,base):
    record=load(base/'reference.json');archive=base/'reference.tar.gz'
    pin=lock['identities']['reference']['joint_api']
    require(record['status']=='restored-exact-qualified-GeneralApi-reference-only' and record['candidate_id']==lock['id'] and
            record['source']==os.environ['GITHUB_SHA'] and record['run_id']==int(os.environ['GITHUB_RUN_ID']) and
            record['published_reference']==pin and record['retained_files']==1123 and record['actual_qualification_guards']==EXPECTED_EVIDENCE and
            record['new_simulator_processes']==0 and record['normal_admission_qualified'] is False and
            archive.stat().st_size==record['archive_bytes'] and sha(archive)==record['archive_sha256'],
            'Exact current-run qualified reference transport required')
    relative=REFERENCE.relative_to(ROOT).as_posix()
    with tarfile.open(archive,'r:gz') as tar:
        members=tar.getmembers();names={m.name for m in members}
        require(len(members)==len(names)==1123 and sum(m.size for m in members)<2*1024**3 and
                all(m.isfile() and not m.mode&0o7000 and safe(m.name).is_relative_to('out/joint-api-qualification') for m in members),
                'Complete bounded qualified reference transport required')
        body=tar.extractfile(relative).read()
        require(hashlib.sha256(body).hexdigest()==pin['qualified_report_sha256'],'Original qualified report bytes differ')
        expected=expected_paths(json.loads(body))|{relative:pin['qualified_report_sha256']}
        require(names==set(expected),'Original qualified evidence paths cannot be omitted or expanded')
        for m in members:
            p=ROOT/m.name
            require(not p.exists() and p.resolve()==p,'Fresh original evidence path required')
            p.parent.mkdir(parents=True,exist_ok=True)
            with p.open('xb') as output,tar.extractfile(m) as incoming:
                for block in iter(lambda:incoming.read(1024**2),b''):output.write(block)
            require(sha(p)==expected[m.name],'Actual original qualification evidence byte differs')
    sys.path.insert(0,str(ROOT/'Tests/Production/GeneralApiCorrection'))
    import qualification
    require(qualification.inspect(REFERENCE)['evidence_sha256']==json.loads(body)['evidence_sha256'],'Complete unchanged qualification consumer required')


if __name__=='__main__':
    hosted()
    lock=candidate()
    if sys.argv[1:]==['--prepare']:restore_reference(lock)
    elif sys.argv[1:]==['--restore']:extract_reference(lock,ROOT/'out/admission-reference-download')
    else:raise ValueError('Explicit restore or prepare mode required')
