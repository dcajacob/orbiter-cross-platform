"""Versioned stock-cohort transport for the authorized mixed GitHub campaign.

An overall native failure is retained. Only four successful complete Windows
stock jobs can supply this transport; no native or Phase 6 acceptance is made.
"""
import argparse
import json
from pathlib import Path
import re
import shutil
import stat
import zipfile

import transport as legacy
from observations import require,sha

PROTOCOL='remaining-stock-hosted-campaign-transport-v1'
ROOT=Path(__file__).resolve().parents[3]
JOB_PREFIX='Original Windows complete stock and exact-save reloads / Matched-clock v2 original '
STEPS=(
    'Stage and verify untouched application, SDK, client and data inputs',
    'Build explicit repaired modules and client in a fresh copy while preserving the original',
    'Verify complete unchanged input selection and resource-history reader controls',
    'Observe all 38 complete scenes twice with 960 actual ticks and original default propagators',
    'Reject damaged complete-scene, playback, clock, full-frame and variant evidence',
    'Reject damaged public SDK clock samples and snapshot associations',
    'Reject damaged actual begin/end clocks and finalized-frame evidence',
    'Verify actual startup configuration and reject coherent hash/physics changes',
    'Verify exact saved-input provenance for all complete scenes and repetitions',
    'Reload all 38 exact Windows end saves twice with original physics and matched clocks',
    'Run actions/upload-artifact@v7')


def run_identity(run,jobs=None):
    require(type(run['id']) is int and run['id']>0 and
            run['repository']['full_name']==legacy.REPOSITORY and
            run['head_branch']=='codex/github-qualification' and
            run['path']=='.github/workflows/phase6-qualification.yml' and
            re.fullmatch('[0-9a-f]{40}',run['head_sha']) and
            run['status']=='completed' and run['conclusion'] in ('success','failure'),
            'Completed authorized hosted campaign identity required')
    jobs=run.get('stock_jobs') if jobs is None else jobs
    require(isinstance(jobs,list) and len(jobs)==4,'Four complete original stock jobs required')
    seen=set();ids=set();retained=[]
    for job in jobs:
        require(job['name'].startswith(JOB_PREFIX),'Original stock cohort job required')
        profile=job['name'][len(JOB_PREFIX):].replace(' ','-')
        require(profile in legacy.PROFILES and profile not in seen and
                type(job['id']) is int and job['id']>0 and job['id'] not in ids and
                job['run_id']==run['id'] and job['head_sha']==run['head_sha'] and
                job['head_branch']==run['head_branch'] and
                job['run_url']==f'https://api.github.com/repos/{legacy.REPOSITORY}/actions/runs/{run["id"]}' and
                job['status']=='completed' and job['conclusion']=='success',
                'Complete successful stock job/source/run/profile closure required')
        for name in STEPS:
            matches=[s for s in job['steps'] if s['name']==name]
            require(len(matches)==1 and matches[0]['status']=='completed' and
                    matches[0]['conclusion']=='success','Required stock step missing, skipped or failed: '+name)
        dispatch=[s for s in job['steps'] if s['name']=='Select original SSE2 CRT when required']
        require(len(dispatch)==1 and dispatch[0]['status']=='completed' and
                dispatch[0]['conclusion']==('success' if profile.endswith('-sse2') else 'skipped'),
                'Actual original stock CRT lane selection differs')
        seen.add(profile);ids.add(job['id'])
        retained.append({k:job[k] for k in ('id','run_id','head_sha','head_branch','run_url','name','status','conclusion','steps')}|
                        {'labels':list(job.get('labels',[]))})
    require(seen==legacy.PROFILES,'Complete four-profile original stock cohort required')
    return {k:run[k] for k in ('id','head_sha','head_branch','path','status','conclusion')}|dict(
        repository={'full_name':legacy.REPOSITORY},stock_jobs=retained)


def inspect_matrix(manifest,archive_root,decoded,producer):
    require(manifest['status']=='passed' and manifest['protocol']==PROTOCOL and
            manifest['diagnostic_only'] is False and manifest['phase6_complete'] is False and
            manifest['native_admission_qualified'] is False and manifest['source_commit']==producer and
            re.fullmatch('[0-9a-f]{40}',producer) and len(manifest['artifacts'])==4 and
            {v['profile'] for v in manifest['artifacts']}==legacy.PROFILES and set(decoded)==legacy.PROFILES,
            'Complete hosted stock-only transport with explicit incomplete acceptance required')
    run=run_identity(manifest['workflow_run'])
    require(run['head_sha']==producer,'Hosted workflow source differs from captured producer')
    result={}
    for item in manifest['artifacts']:
        profile=item['profile'];recorded=legacy.artifact_identity(item['api_artifact'],run,False)
        require(all(item[k]==v for k,v in recorded.items()),'Hosted API artifact identity differs')
        archive=Path(archive_root)/str(legacy.safe(item['path']))
        members=legacy.inspect_archive(archive,decoded[profile],item['sha256'],item['bytes'])
        job=next(j for j in run['stock_jobs'] if j['name']==JOB_PREFIX+profile.replace('-',' '))
        result[profile]=dict(archive=str(archive),archive_sha256=item['sha256'],archive_bytes=item['bytes'],
            decoded_members_sha256=members,transport_protocol=PROTOCOL,original_stock_job_id=job['id'])
    return result


def retain(records,archives,output):
    output=Path(output).resolve();archives=Path(archives).resolve()
    require(ROOT/'out' in output.parents and not output.exists(),'Fresh hosted transport output below repository out required')
    run=run_identity(records['workflow_run'],records['jobs'])
    identities=[(legacy.artifact_identity(a,run,False),a) for a in records['artifacts']]
    require(len(identities)==4 and {i['profile'] for i,a in identities}==legacy.PROFILES and
            len({i['id'] for i,a in identities})==4,'Exactly four complete distinct hosted stock artifacts required')
    output.mkdir(parents=True)
    manifest=dict(status='validating',protocol=PROTOCOL,source_commit=run['head_sha'],workflow_run=run,
        diagnostic_only=False,phase6_complete=False,native_admission_qualified=False,artifacts=[],
        scope='Original Windows stock cohort only; overall campaign conclusion retained; independent simulation audits required',
        validator_sha256=sha(Path(__file__)),legacy_archive_reader_sha256=sha(Path(legacy.__file__)))
    path=output/'download.json'
    def save():path.write_text(json.dumps(manifest,indent=2)+'\n')
    save()
    try:
        for identity,public in identities:
            archive=archives/(identity['name']+'.zip')
            require(archive.is_file() and not archive.is_symlink() and ROOT in archive.resolve().parents and
                    archive.stat().st_size==identity['bytes'] and sha(archive)==identity['sha256'],
                    'Retained local ZIP differs from actual GitHub artifact digest/length')
            decoded=output/identity['profile'];decoded.mkdir();seen=set()
            with zipfile.ZipFile(archive) as source:
                require(shutil.disk_usage(output).free>=sum(m.file_size for m in source.infolist())+8*1024**3,
                        'Insufficient decoded evidence capacity and reserve')
                for member in source.infolist():
                    name=str(legacy.safe(member.filename));folded=name.casefold()
                    require(folded not in seen and not stat.S_ISLNK(member.external_attr>>16),
                            'Duplicate, case-colliding or symlink hosted archive member')
                    seen.add(folded)
                    if member.is_dir():continue
                    target=decoded/name;target.parent.mkdir(parents=True,exist_ok=True)
                    with source.open(member) as incoming,target.open('xb') as outgoing:shutil.copyfileobj(incoming,outgoing)
            members=legacy.inspect_archive(archive,decoded,identity['sha256'],identity['bytes'])
            public={k:public[k] for k in ('id','name','size_in_bytes','digest','expired','workflow_run')}
            manifest['artifacts'].append(identity|dict(path=archive.relative_to(ROOT).as_posix(),
                decoded=decoded.relative_to(ROOT).as_posix(),api_artifact=public,decoded_members_sha256=members,
                transport_source='retained-local-archive'))
            save();print(identity['profile'],'API digest and',len(members),'decoded members verified',flush=True)
        manifest['status']='passed';save()
        inspect_matrix(manifest,ROOT,{i['profile']:ROOT/i['decoded'] for i in manifest['artifacts']},run['head_sha'])
    except BaseException:
        manifest['status']='failed';save();raise
    return manifest


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('records','archives','output'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();retain(json.loads(args.records.read_text()),args.archives,args.output)
