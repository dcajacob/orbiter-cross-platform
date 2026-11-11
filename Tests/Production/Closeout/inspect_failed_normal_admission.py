#!/usr/bin/env python3
"""Read exact retained failed stock traces on a hosted runner; grant no acceptance."""
import argparse,csv,hashlib,io,json,os
from pathlib import Path
import zipfile,tarfile
from contracts import ROOT,PROFILES,atomic_json,load,require,sha
from rejection_input_bundle import inspect_archive,safe
from frozen_admission_api import hosted,candidate

LOCK=ROOT/'Tests/Production/Closeout/failed-normal-admission-v4.lock.json'
SELECTED={'console.log','flight-state.csv','production-state.csv','thrust-state.csv','ground-math.csv',
          'ground-contact.csv','flight-controls.csv','application-lifecycle.csv','graphics-lifecycle.json',
          'invocation.json','process-receipt.json','Orbiter.cfg','staged-Orbiter.cfg','numerics.json'}


def flight_summary(body):
    rows=list(csv.reader(io.StringIO(body.decode())));require(rows,'Original flight trace header missing')
    header=rows[0];require(len(set(header))==len(header),'Original trace header is ambiguous')
    complete=[];partial=[];by_vessel={}
    for line,row in enumerate(rows[1:],2):
        actual=dict(zip(header,row))
        if len(row)!=len(header):
            partial.append(dict(line=line,values=actual,actual_fields=len(row),expected_fields=len(header),
                                first_unwritten_field=header[len(row)] if len(row)<len(header) else None))
        else:
            complete.append(actual)
            name=actual.get('name',actual.get('vessel','unidentified'))
            by_vessel.setdefault(name,[]).append(actual)
    return dict(header=header,complete_rows=len(complete),partial_rows=partial,
                per_vessel={n:dict(rows=len(v),first=v[:3],last=v[-4:]) for n,v in by_vessel.items()},
                interpretation='Original partial output retained. A missing field identifies where the observer stopped writing, not a diagnosed physics cause.')


def verify_api(pin,api,profile,archive):
    run=api['run'];p=pin['profiles'][profile];a=api['artifact'];repository=run['repository']
    require(repository['full_name']=='dcajacob/orbiter-cross-platform' and repository['private'] is False and
            run['id']==pin['run_id'] and run['run_attempt']==1 and run['head_sha']==pin['source'] and
            run['status']=='completed' and run['conclusion']=='failure' and run['head_branch']==pin['branch'],
            'Exact original failed public run/source/attempt required')
    require(a['id']==p['artifact_id'] and a['name']==p['artifact_name'] and a['expired'] is False and
            a['workflow_run']['id']==run['id'] and a['workflow_run']['head_sha']==pin['source'] and
            a['size_in_bytes']==p['bytes']==archive.stat().st_size and a['digest']=='sha256:'+p['sha256'] and
            sha(archive)==p['sha256'],'Exact original failed raw artifact API/size/digest required')
    jobs=[j for j in api['jobs'] if j['id']==p['job_id']]
    require(len(jobs)==1 and jobs[0]['head_sha']==pin['source'] and jobs[0]['run_id']==pin['run_id'] and
            jobs[0]['run_attempt']==1 and jobs[0]['status']=='completed' and jobs[0]['conclusion']=='failure' and
            jobs[0]['labels']==['ubuntu-24.04'],'Original failed standard hosted profile job required')


def inspect(profile,source,output):
    pin=load(LOCK);api=load(source/'api.json');archive=source/'producer.zip';verify_api(pin,api,profile,archive)
    require(pin['candidate_id']==candidate()['id'],'Exact unchanged frozen candidate required')
    require(not output.exists(),'Fresh separately labelled failed diagnostic output required');output.mkdir(parents=True)
    package=source/'selected-raw';package.mkdir()
    with zipfile.ZipFile(archive) as z:
        entries=z.infolist();names=[safe(e.filename).as_posix() for e in entries]
        require(len(set(n.casefold() for n in names))==len(entries),'Unsafe or colliding original raw ZIP member')
        for ending in ('/capture-raw.tar.gz','/capture-raw-index.json','/capture/stock-scenarios.json','/collection.json'):
            matches=[e for e in entries if e.filename.endswith(ending)]
            require(len(matches)==1 and matches[0].file_size<1024**3,'One bounded exact original raw member required')
            e=matches[0];target=package/ending.rsplit('/',1)[1]
            with z.open(e) as incoming,target.open('xb') as out:
                import shutil
                shutil.copyfileobj(incoming,out,1024**2)
    index=load(package/'capture-raw-index.json');raw=package/'capture-raw.tar.gz'
    require(index['archive_bytes']==raw.stat().st_size and index['archive_sha256']==sha(raw) and
            index['original_files_rewritten'] is False and not index['missing_guarded_paths'],
            'Exact complete original raw archive bytes and preservation record required')
    closure=inspect_archive(raw,index['files'])
    require(closure==index['closure'],'Complete original raw logical member closure differs')
    prefix='out/hosted-normal-admission/'+profile+'/'
    for relative,filename in [('capture/stock-scenarios.json','stock-scenarios.json'),('collection.json','collection.json')]:
        require(index['files'][prefix+relative]['sha256']==sha(package/filename),
                'Published outer capture/collection differs from actual complete raw closure')
    capture=load(package/'stock-scenarios.json');collection=load(package/'collection.json')
    require(collection['profile']==profile and collection['collector_source']==pin['source'] and
            collection['candidate_id']==pin['candidate_id'] and collection['native_admission_qualified'] is False and
            capture['status']=='incomplete' and capture['summary']==pin['summary'] and
            capture['runtime_identity']['profile']==profile and capture['sources_and_binaries_unchanged'] is True,
            'Original incomplete capture/source/sanitizer profile scope changed')
    failed={n:c for n,c in capture['cases'].items() if c['status']!='passed'}
    require({n:c['output'] for n,c in failed.items()}==pin['failed_cases'],'Exact same original four failed scenes required')
    prefix='out/hosted-normal-admission/'+profile+'/capture/'
    wanted={prefix+c['output']+'/'+f for c in failed.values() for f in SELECTED if prefix+c['output']+'/'+f in index['files']}
    retained={};total=0
    with tarfile.open(raw,'r:gz') as tar:
        for entry in tar:
            if entry.name not in wanted:continue
            require(entry.isfile() and entry.size<=2*1024**2,'Bounded actual diagnostic text file required')
            body=tar.extractfile(entry).read();total+=len(body)
            require(total<=12*1024**2 and len(body)==index['files'][entry.name]['bytes'] and
                    hashlib.sha256(body).hexdigest()==index['files'][entry.name]['sha256'],'Original diagnostic bytes changed')
            n=entry.name.removeprefix(prefix);p=output/'original-partials'/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(body)
            retained[n]=dict(bytes=len(body),sha256=sha(p))
    require(set(retained)=={n.removeprefix(prefix) for n in wanted},'Missing selected original diagnostic member')
    cases={}
    for name,c in failed.items():
        root=output/'original-partials'/c['output']
        require((root/'flight-state.csv').is_file() and (root/'console.log').is_file(),'Original failed flight trace and console required')
        cases[name]=dict(original_case=c,flight=flight_summary((root/'flight-state.csv').read_bytes()),
                         original_console_tail=(root/'console.log').read_text(errors='replace')[-16000:])
    for file in ('api.json','download-transport-attempts.json'):
        atomic_json(output/file,load(source/file))
    atomic_json(output/'inspection.json',dict(protocol='phase6-original-failed-normal-trace-inspection-v1',
        status='inspected-original-failed-traces-only',profile=profile,source_run_id=pin['run_id'],original_source=pin['source'],
        inspector_source=os.environ['GITHUB_SHA'],candidate_id=pin['candidate_id'],original_conclusion='failure',
        original_summary=capture['summary'],original_archive=pin['profiles'][profile],full_raw_closure=closure,
        original_index_sha256=sha(package/'capture-raw-index.json'),original_capture_sha256=sha(package/'stock-scenarios.json'),
        selected_unchanged_files=retained,cases=cases,new_simulator_processes=0,normal_admission_qualified=False,
        phase6_complete=False,hands_on_ready=False,bulk_local_transfers=False))
    print(json.dumps(dict(profile=profile,original_failures=len(cases),selected_original_bytes=total,qualification_granted=False)))


if __name__=='__main__':
    hosted();cli=argparse.ArgumentParser(description=__doc__);cli.add_argument('--profile',choices=PROFILES,required=True)
    a=cli.parse_args();inspect(a.profile,ROOT/'out/failed-normal-source'/a.profile,ROOT/'out/failed-normal-diagnostics'/a.profile)
