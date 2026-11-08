#!/usr/bin/env python3
"""Correct case discovery on retained CCC builds without rewriting their failed receipts."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import tarfile
import time
import xml.etree.ElementTree as ET
import zipfile

from hosted_native_package import ROOT, require, sha, load, test_result

PRODUCER = 'ccc02c8a34bd1f227624d8778a141e8736ae8111'
RUN = 42519601899
PROFILES = {c+'-'+m for c in ('Debug','Release') for m in ('automatic','sse2')}
DISCOVERY_ERROR = {'upstream-lua-discovery':'Actual nonempty upstream Catch case discovery missing'}


def safe(name):
    value = PurePosixPath(name)
    require(name and str(value)==name.rstrip('/') and not value.is_absolute() and '..' not in value.parts and ':' not in name and '\\' not in name,
            'Unsafe retained evidence member')
    return name


def validate_api(record, profile):
    run = record['run']; artifact = record['artifact']
    require(profile in PROFILES and record['repository'] == {'owner':'dcajacob','repo':'orbiter-cross-platform'},
            'Exact authorized repository/profile required')
    require(run['id'] == RUN and run['head_sha'] == PRODUCER and run['head_branch'] == 'qualification/native-package-retry'
            and run['path'] == '.github/workflows/phase6-hosted-closeout.yml' and run['run_attempt'] == 1,
            'Immutable compiled producer run differs')
    require(artifact['name'] == 'phase6-full-native-'+profile and artifact['expired'] is False and
            artifact['workflow_run']['id'] == RUN and artifact['workflow_run']['head_sha'] == PRODUCER and
            re.fullmatch('sha256:[0-9a-f]{64}', artifact['digest']), 'Exact original API artifact identity required')
    jobs = [j for j in record['jobs'] if j['name'] == 'Complete sanitized native package '+profile.replace('-',' ',1)]
    require(len(jobs) == 1, 'Unique actual compiled-profile job required'); job = jobs[0]
    require(job['run_id'] == RUN and job['status'] == 'completed' and job['conclusion'] == 'failure' and
            'ubuntu-24.04' in job['labels'], 'Actual closed failed source job on the standard runner required')
    steps = {s['name']:s for s in job['steps']}
    for name, outcome in (
        ('Build all stock families, normal host and unchanged upstream unit bodies with sanitizers','success'),
        ('Run every registered engine and upstream unit with ASan loaded before the Python math probe','failure'),
        ('Seal exact runtime, generated sources and actual test results without acceptance credit','failure'),
        ('Run actions/upload-artifact@v7','success')):
        require(name in steps and steps[name]['conclusion'] == outcome, 'Actual producer build/unit/retention step differs: '+name)
    return job


def expected_cases(body):
    pattern = r'TEST_CASE\s*\(\s*("(?:[^"\\]|\\.)*")\s*,\s*("(?:[^"\\]|\\.)*")'
    matches = list(re.finditer(pattern, body))
    require(matches and len(matches) == len(re.findall(r'\bTEST_CASE\s*\(', body)), 'Complete literal upstream case declarations required')
    cases={json.loads(m[1]):dict(tags=sorted(re.findall(r'\[[^]]+\]',json.loads(m[2]))),
                                line=body.count('\n',0,m.start())+1) for m in matches}
    require(len(cases)==len(matches),'Duplicate immutable upstream case name')
    return cases


def clean_sanitizers(text):
    require(not re.search(r'ERROR: (?:Address|Leak)Sanitizer|AddressSanitizer:DEADLYSIGNAL|UndefinedBehaviorSanitizer:|\.(?:cpp|cc|c|h):\d+:\d+: runtime error:',text),
            'Unsuppressed native sanitizer diagnostic in otherwise successful unit execution')


def inspect_discovery(path, expected, source):
    xml = ET.parse(path).getroot(); require(xml.tag == 'MatchingTests', 'Actual Catch discovery XML required')
    cases = xml.findall('TestCase'); names = [c.findtext('Name') for c in cases]
    require(len(names) == len(set(names)) == len(expected) and set(names) == set(expected), 'Missing, duplicate or substituted upstream Catch case')
    for case in cases:
        target = expected[case.findtext('Name')]
        require(sorted(re.findall(r'\[[^]]+\]',case.findtext('Tags',''))) == target['tags'] and
                Path(case.findtext('SourceInfo/File')).resolve() == source.resolve() and
                int(case.findtext('SourceInfo/Line')) == target['line'], 'Actual upstream case tags/source/line differs')
    return dict(cases=names, source=str(source), xml_sha256=sha(path))


def inspect_execution(path, expected, source):
    xml = ET.parse(path).getroot(); require(xml.tag == 'Catch', 'Actual complete Catch execution XML required')
    cases = xml.findall('.//TestCase'); names = [c.attrib['name'] for c in cases]
    require(len(names) == len(set(names)) == len(expected) and set(names) == set(expected),
            'Every original upstream case must execute exactly once')
    for case in cases:
        target=expected[case.attrib['name']]; outcome=case.findall('OverallResult')
        require(sorted(re.findall(r'\[[^]]+\]',case.get('tags',''))) == target['tags'] and
                Path(case.attrib['filename']).resolve() == source.resolve() and int(case.attrib['line']) == target['line'] and
                len(outcome)==1 and outcome[0].get('success')=='true', 'Executed upstream case identity/outcome differs')
    assertions=xml.findall('OverallResults'); totals=xml.findall('OverallResultsCases')
    require(len(assertions)==len(totals)==1 and int(assertions[0].get('successes','0'))>0 and
            int(totals[0].get('successes','0'))==len(expected), 'Complete nonempty assertion and case totals required')
    require(all(n.get('failures')=='0' and n.get('expectedFailures')=='0' for n in
                [*xml.iter('OverallResults'),*xml.iter('OverallResultsCases')]) and
            not any(xml.findall('.//'+tag) for tag in ('Exception','FatalErrorCondition','Failure','Skip')) and
            all(n.get('success')=='true' for n in xml.iter('Expression')),
            'Failed, skipped or incomplete upstream assertion execution')
    return dict(cases=names, assertions=int(assertions[0].get('successes')), catch_xml_sha256=sha(path))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('api','archive','output'):p.add_argument('--'+name,type=lambda v:Path(v).resolve(),required=True)
    p.add_argument('--profile',choices=sorted(PROFILES),required=True); a=p.parse_args()
    require(not a.output.exists(), 'Fresh correction output required'); a.output.mkdir(parents=True)
    report = dict(protocol='phase6-retained-native-unit-discovery-correction-v1',status='running',
        compiled_source=PRODUCER,collector_source=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(),
        profile=a.profile,commands=[],phase6_complete=False,native_admission_qualified=False,
        original_failed_job_relabelled=False,compiled_runtime_rebuilt=False)
    original = a.output/'original-artifact'; original.mkdir(); guarded={}
    def save():(a.output/'correction.json').write_text(json.dumps(report,indent=2)+'\n')
    def run(label, argv, directory, environment):
        started=time.monotonic_ns(); record=dict(label=label,argv=list(map(str,argv)),cwd=str(directory),
            started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat());report['commands'].append(record)
        with (a.output/(label+'.log')).open('w') as log:
            child=subprocess.Popen(record['argv'],cwd=directory,env=environment,stdout=log,stderr=subprocess.STDOUT)
            record['actual_pid']=child.pid;save()
            try:record['actual_returncode']=child.wait(timeout=30)
            except subprocess.TimeoutExpired:
                child.kill();record['actual_returncode']=child.wait();record['timed_out']=True;raise
        record.update(elapsed_ns=time.monotonic_ns()-started,log_sha256=sha(a.output/(label+'.log')));save()
        require(record['actual_returncode']==0,'Actual retained upstream process failed: '+label)
        clean_sanitizers((a.output/(label+'.log')).read_text(errors='replace'))
    try:
        api=load(a.api);job=validate_api(api,a.profile); artifact=api['artifact']
        require(a.archive.stat().st_size==artifact['size_in_bytes'] and 'sha256:'+sha(a.archive)==artifact['digest'],
                'Actual downloaded source artifact differs')
        guarded[str(a.archive)]=sha(a.archive);guarded[str(a.api)]=sha(a.api)
        with zipfile.ZipFile(a.archive) as z:
            require(sum(i.file_size for i in z.infolist())<1024**3,'Retained ZIP exceeds bounded restoration')
            seen=set()
            for info in z.infolist():
                name=safe(info.filename);require(name.casefold() not in seen and not stat.S_ISLNK(info.external_attr>>16),'Duplicate/symlink ZIP member');seen.add(name.casefold())
                if info.is_dir():continue
                target=original/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(z.read(info));guarded[str(target)]=sha(target)
        sealed=load(original/a.profile/'hosted-package.json');archive=original/(a.profile+'.tar.gz')
        require(sealed['status']=='built-only-tests-failed-or-incomplete' and sealed['test_errors']==DISCOVERY_ERROR and
                sealed['source_commit']==PRODUCER and sealed['configuration']+'-'+sealed['math_profile']==a.profile and
                sealed['archive_sha256']==sha(archive) and sealed['archive_bytes']==archive.stat().st_size,
                'Only the closed discovery-argument failure can use this correction')
        package=ROOT/'out/phase6-hosted-native'/a.profile;require(not package.exists(),'Fresh retained runtime destination required')
        expected=sealed['archive_members_sha256'];seen=set()
        with tarfile.open(archive,'r:gz') as tar:
            require(sum(m.size for m in tar.getmembers())<4*1024**3,'Retained package size exceeds bounded restoration')
            for info in tar.getmembers():
                name=safe(info.name);require(info.isfile() and not info.mode&0o7000 and name.casefold() not in seen and
                    PurePosixPath(name).is_relative_to('out/phase6-hosted-native/'+a.profile) and name in expected,
                    'Unsafe, duplicate or unmanifested runtime member');seen.add(name.casefold())
                path=ROOT/name;path.parent.mkdir(parents=True,exist_ok=True);require(not path.exists(),'Retained runtime would overwrite another input')
                path.write_bytes(tar.extractfile(info).read());path.chmod(info.mode&0o777)
                require(sha(path)==expected[name],'Retained raw runtime member differs');guarded[str(path)]=expected[name]
        require({str(ROOT/name) for name in expected}<=set(guarded) and len(seen)==len(expected),'Complete original binary/raw evidence closure required')
        build=load(package/'build.json');require(sha(package/'build.json')==sealed['build_manifest_sha256'] and
            build['status']=='built' and build['source_base']==PRODUCER and build['instrumentation']=='address,undefined' and
            build['owning_sources_unchanged'] is True,'Original current-source sanitized build identity differs')
        for name,value in {**build['source_sha256_lf'],**build['dependency_sha256_lf']}.items():
            body=(ROOT/name).read_bytes().replace(b'\r\n',b'\n');frozen=subprocess.check_output(['git','-C',str(ROOT),'show',PRODUCER+':'+name]).replace(b'\r\n',b'\n')
            require(hashlib.sha256(body).hexdigest()==value==hashlib.sha256(frozen).hexdigest(),'Actual compiled input differs: '+name)
            guarded[str(ROOT/name)]=sha(ROOT/name)
        tests={kind:test_result(package/inventory,package/result) for kind,inventory,result in (
            ('engine','registered-unit-tests.json','engine-tests.xml'),('upstream','upstream-registered-unit-tests.json','upstream-tests.xml'))}
        require(tests==sealed['tests'] and tests['engine']['executed_processes']==32 and tests['upstream']['executed_processes']==2,
                'Original complete passed unit execution differs')
        for name in ('engine-tests.xml','upstream-tests.xml','engine-tests.log','upstream-tests.log'):
            clean_sanitizers((package/name).read_text(errors='replace'))
        units={t['name']:t for t in load(package/'upstream-registered-unit-tests.json')['tests']}
        environment=dict(os.environ,LD_PRELOAD=subprocess.check_output(['c++','-print-file-name=libasan.so'],text=True).strip(),PYTHONMALLOC='malloc')
        require('detect_leaks=0' not in environment.get('ASAN_OPTIONS','') and
                not any('suppressions=' in environment.get(key,'') for key in ('ASAN_OPTIONS','LSAN_OPTIONS','UBSAN_OPTIONS')),
                'Sanitizer suppression or disabled leak checks cannot qualify retained units')
        results={}
        for name,binary,source_name in (('Lua.Interpreter','existing_lua_unit','Tests/Lua.Interpreter.cpp'),
                                       ('Collision.CollisionCore','existing_collision_unit','Tests/Collision.CollisionCore.cpp')):
            command=units[name]['command'];executable=package/'upstream-units'/binary
            require(command==[str(executable),*([str(package/'upstream-units/assets')] if binary=='existing_lua_unit' else [])],
                    'Original upstream executable/resource context differs')
            source=ROOT/source_name;body=subprocess.check_output(['git','-C',str(ROOT),'show',PRODUCER+':'+source_name]).decode().replace('\r\n','\n');cases=expected_cases(body)
            catalog=a.output/(binary+'-discovery.xml');execution=a.output/(binary+'-execution.xml')
            run(binary+'-discovery',command+['--list-tests','--reporter','xml','--out',str(catalog)],package/'upstream-units',environment)
            discovery=inspect_discovery(catalog,cases,source)
            run(binary+'-execution',command+['--reporter','xml','--out',str(execution)],package/'upstream-units',environment)
            results[name]=dict(discovery=discovery,execution=inspect_execution(execution,cases,source),binary_sha256=sha(executable))
        require(all(sha(path)==value for path,value in guarded.items()),'Original source, binary or evidence changed during correction')
        shutil.copy2(a.api,a.output/'producer-api.json')
        report.update(status='passed-retained-native-units-and-corrected-case-discovery',original_job_id=job['id'],
            original_run_id=RUN,original_artifact_id=artifact['id'],original_artifact_sha256=sha(a.archive),
            retained_archive_sha256=sha(archive),original_failed_manifest_sha256=sha(original/a.profile/'hosted-package.json'),
            reused_actual_unit_results=tests,fresh_upstream_results=results,compiled_inputs_and_raw_evidence_unchanged=True,
            asan_runtime=dict(path=environment['LD_PRELOAD'],sha256=sha(environment['LD_PRELOAD'])),
            verified_binary_and_evidence_sha256=guarded,runtime_and_full_stock_qualification_pending=True)
    except BaseException as error:report.update(status='failed',error=str(error));raise
    finally:save()
    print(report['status'])


if __name__=='__main__':main()
