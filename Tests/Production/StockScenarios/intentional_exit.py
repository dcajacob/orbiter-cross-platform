"""One audited stock-script exit; ordinary scenarios retain sixty frames."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from inventory import ROOT,digest,require,ships

FIXTURE=ROOT/'Tests/Production/NativeLua/StockExit'
sys.path[:0]=[str(FIXTURE),str(ROOT/'Tests/Production/StockVessels')]
from contract import inspect as inspect_stock_exit,settings,sha_lf
from verify_original import compare_state


def policy(name,case,assets=None):
    pins=json.loads((FIXTURE/'observations.lock.json').read_text())
    termination=pins['termination']
    if name!=termination['scenario']:return None
    config=settings()
    require(pins['status']=='audited-original-observations' and pins['automatic_refresh'] is False and
            pins['application_source']==config['application_source'] and
            sha_lf(FIXTURE/'case.json')==pins['case_sha256_lf'], 'Stock exit reference is not pinned')
    require(case['sha256_lf']==termination['scenario_sha256_lf']==config['scenario_sha256_lf'] and
            case['ships']==ships((ROOT/'Scenarios'/name).read_text()), 'Stock exit scenario identity differs')
    require(termination['script']==config['script'] and
            termination['script_sha256_lf']==config['script_sha256_lf'] and
            termination['fixed_step']==config['fixed_step'] and termination['frame_limit']==config['frames'] and
            termination['exit_code']==config['expected_exit_code'], 'Pinned stock exit protocol differs')
    if assets is not None:
        require(sha_lf(assets/config['script'])==config['script_sha256_lf'], 'Staged stock exit script changed')
    return dict(config=config,pins=pins)


def audit_reference(reference,output):
    require(reference is not None,'The pinned stock exit requires independently audited original observations')
    pins=json.loads((FIXTURE/'observations.lock.json').read_text())
    subprocess.run([sys.executable,'-B',str(FIXTURE/'audit_original.py'),
        '--artifacts',str(reference),'--download-manifest',str(reference/'downloads.json'),
        '--producer-commit',pins['producer_commit'],'--metadata-lock',str(FIXTURE/'observations.lock.json'),
        '--output',str(output)],check=True,stdout=subprocess.DEVNULL)
    audit=json.loads(output.read_text())
    require(audit['status']=='passed' and audit['processes']==8 and len(audit['profiles'])==4 and
            audit['verifier_sha256']==pins['audit_verifier_sha256'], 'Original stock exit audit incomplete')
    for profile,item in pins['profiles'].items():
        require(audit['profiles'][profile]['capture_sha256']==item['capture_sha256'],
                'Original stock exit profile differs from the frozen capture')
    return dict(path=str(reference),audit_sha256=digest(output),audit_path=str(output),
                producer_commit=pins['producer_commit'])


def build_identity(executable,modules,record_path,source_commit,owner=None):
    owner=Path(owner).resolve() if owner is not None else ROOT
    require(re.fullmatch('[0-9a-f]{40}',source_commit),'Runtime source must be an immutable full commit')
    record=json.loads(record_path.read_text())
    require(record['status']=='built','Stock runtime build is incomplete')
    owning=record.get('source_sha256_lf',record.get('source_sha256'))
    ledger=json.loads((owner/'Tests/Production/phase3-extraction.lock.json').read_text())['files']
    require(owning and set(owning)==set(ledger),'Stock runtime owning-source ledger incomplete')
    for name,expected in owning.items():
        body=subprocess.check_output(['git','-C',str(owner),'show',source_commit+':'+name])
        require(hashlib.sha256(body.replace(b'\r\n',b'\n')).hexdigest()==expected,
                'Built stock input differs from immutable source: '+name)
        require(sha_lf(owner/name)==expected,'Current owning source differs from the selected stock runtime: '+name)
    for name,expected in record['runtime_files_sha256'].items():
        require(digest(owner/name)==expected,'Retained stock runtime file changed: '+name)
    require(record['runtime_files_sha256'][executable.relative_to(owner).as_posix()]==digest(executable) and
            record['runtime_files_sha256'][(modules/'Graphics/OGLClient.so').relative_to(owner).as_posix()]==
            digest(modules/'Graphics/OGLClient.so'),'Selected stock application or renderer differs from its build')
    cache_path=executable.parent/'CMakeCache.txt'
    require(record['runtime_files_sha256'][cache_path.relative_to(owner).as_posix()]==digest(cache_path),
            'Stock runtime cache identity differs')
    cache=dict(line.split('=',1) for line in cache_path.read_text().splitlines()
               if '=' in line and not line.startswith(('#','//')))
    configuration=cache['CMAKE_BUILD_TYPE:STRING']
    require(configuration in ('Debug','Release'),'Unsupported actual stock runtime configuration')
    math_profile='sse2' if cache['ORBITER_MATH_FORCE_SSE2:BOOL']=='ON' else 'automatic'
    flags=[cache['CMAKE_'+language+'_FLAGS:STRING'] for language in ('C','CXX')]
    sanitized=all('-fsanitize=address,undefined' in flag for flag in flags)
    require(sanitized or not any('-fsanitize=' in flag for flag in flags),'Partially instrumented stock runtime')
    linked=subprocess.check_output(['readelf','-d',str(executable)],text=True)
    require(('libasan.so' in linked)==sanitized and ('libubsan.so' in linked)==sanitized,
            'Actual stock runtime sanitizer linkage differs')
    return dict(configuration=configuration,math_profile=math_profile,profile=configuration+'-'+math_profile,
                sanitizer_linked=sanitized,compiler=cache['CMAKE_CXX_COMPILER:FILEPATH'],
                cache_sha256=digest(cache_path),build_record_sha256=digest(record_path),
                runtime_source_commit=source_commit)


def compile_probe(output,executable,identity):
    probe=output/'stock-exit-probe.so'
    argv=[identity['compiler'],'-std=c++17','-fPIC','-shared','-Wl,--no-undefined']
    if identity['sanitizer_linked']:argv+=['-fsanitize=address,undefined','-fno-omit-frame-pointer']
    build=executable.parent
    argv+=['-I'+str(ROOT/'Orbitersdk/include'),'-I'+str(ROOT/'Src/Orbiter'),str(FIXTURE/'NativeProbe.cpp'),
        '-L'+str(build),'-Wl,-rpath,'+str(build),'-lorbiter_production_vessels',
        '-lorbiter_production_boundary','-ldl','-o',str(probe)]
    (output/'probe-command.json').write_text(json.dumps(argv,indent=2)+'\n')
    with (output/'probe-build.log').open('w') as log:
        subprocess.run(argv,stdout=log,stderr=subprocess.STDOUT,check=True)
    return probe


def environment(probe,identity):
    result=dict(os.environ)
    require('LD_PRELOAD' not in result,'Stock exit probe requires an explicit, unmixed preload')
    result['LD_PRELOAD']=str(probe)
    if identity['sanitizer_linked']:
        asan=subprocess.check_output([identity['compiler'],'-print-file-name=libasan.so'],text=True).strip()
        result['LD_PRELOAD']=asan+':'+str(probe)
    return result


def inspect(out,selected,returncode,reference,profile):
    require(reference is not None and profile in selected['pins']['profiles'],
            'Audited original profile required for stock exit acceptance')
    require((out/'console.txt').read_bytes()==(out/'console.log').read_bytes(),'Stock exit console alias differs')
    actual=inspect_stock_exit(out,selected['config'],'native-linux',returncode)
    pins=selected['pins'];expected=pins['termination']
    for field in ('completed_frames','finalized_ticks','all_vessel_rows','docking_rows'):
        require(actual[field]==expected[field],'Stock exit boundary or complete trace differs: '+field)
    require(actual['declared_vessels']==expected['vessels'] and actual['assertion_events']==expected['assertion_events'] and
            actual['assertion_passes']==expected['assertion_passes'],'Stock exit assertions or scene incomplete')
    original=reference/profile/'stock-exit-original'
    require(digest(original/'capture.json')==pins['profiles'][profile]['capture_sha256'],
            'Pinned stock exit original profile changed')
    report=json.loads((original/'capture.json').read_text())
    left=original/'run-1'
    for name,expected_sha in report['runs'][0]['files_sha256'].items():
        require(digest(left/name.replace('\\','/'))==expected_sha,'Audited original stock exit artifact changed')
    math=json.loads((out/'numerics.json').read_text())['math']
    require(math=='amd-6121d02-'+pins['profiles'][profile]['actual_math'],'Stock exit original/native CRT differs')
    errors=compare_state(left,out,json.loads((ROOT/'Tests/Production/Cockpit/cases.json').read_text()))
    require((left/'stock-exit-phases.csv').read_bytes().replace(b'\r\n',b'\n')==
            (out/'stock-exit-phases.csv').read_bytes().replace(b'\r\n',b'\n'),'Stock exit completion sequence differs')
    return dict(policy='pinned-original-stock-script-exit',original_profile=profile,
                original_capture_sha256=digest(original/'capture.json'),maxima=errors,
                completed_frames=actual['completed_frames'],assertion_events=actual['assertion_events'],
                assertion_passes=actual['assertion_passes'],docking_rows=actual['docking_rows'],actual_math=math)
