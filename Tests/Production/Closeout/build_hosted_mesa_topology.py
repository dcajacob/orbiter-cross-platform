#!/usr/bin/env python3
"""Rebuild only the affected Mesa provider and exercise its unsuppressed owner controls."""
import datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from hosted_native_package import ROOT,require,sha,load
from capture_hosted_native_writer import package_inventory


def main():
    require(os.environ.get('GITHUB_ACTIONS')=='true' and Path(os.environ['GITHUB_WORKSPACE']).resolve()==ROOT,'Hosted matching-userspace provider build only')
    base=ROOT/'out/hosted-mesa-topology';require(not base.exists(),'Fresh separate Mesa candidate required');base.mkdir(parents=True)
    source=os.environ['GITHUB_SHA'];report=dict(status='running',source_commit=source,original_provider_source='60ba46377f236c2d4705f444c0174e0f5af8252f',
        commands=[],controls={},application_rebuilt=False,original_capture_relabelled=False,phase6_complete=False,native_admission_qualified=False)
    def save():(base/'build.json').write_text(json.dumps(report,indent=2)+'\n')
    def run(label,argv,timeout=600,environment=None,required=True):
        record=dict(label=label,argv=list(map(str,argv)),started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat());report['commands'].append(record)
        print('Starting '+label,flush=True);started=time.monotonic_ns();log=base/(label+'.log')
        with log.open('w') as stream:
            child=subprocess.Popen(record['argv'],cwd=ROOT,env=environment,stdout=stream,stderr=subprocess.STDOUT);record['actual_pid']=child.pid;save()
            try:record['actual_returncode']=child.wait(timeout=timeout)
            except subprocess.TimeoutExpired:child.kill();record['actual_returncode']=child.wait();record['timed_out']=True;raise
            finally:record.update(elapsed_ns=time.monotonic_ns()-started,log_sha256=sha(log));save()
        if record['actual_returncode']:
            print(log.read_text(errors='replace')[-18000:],flush=True)
            require(not required,'Actual Mesa topology stage failed: '+label)
        return record['actual_returncode']
    try:
        require(subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()==source,'Actual immutable provider-repair source differs')
        providers=ROOT/'out/hosted-native-providers';restored=load(ROOT/'out/native-provider-restoration/restoration.json')
        require(restored['status']=='restored-verified-dependency-bytes-only' and restored['compiled_provider_source']==report['original_provider_source'] and
            restored['collector_source']==source and restored['actual_original_package_inventory_sha256']==sha(providers/'system-packages.txt'),
            'Exact original passed provider restoration required')
        guard={str(ROOT/name):item['sha256'] for name,item in restored['members'].items()}
        require(all(sha(name)==value for name,value in guard.items()),'Original retained dependency closure changed before repair')
        lock=load(ROOT/'Tests/Production/Closeout/native-provider-container.lock.json');image=load(ROOT/'out/mesa-topology-container.json')
        require(len(image)==1 and any(d.endswith('@'+lock['image_digest']) for d in image[0]['RepoDigests']),'Exact original pinned provider userspace required')
        report['container_receipt_sha256']=sha(ROOT/'out/mesa-topology-container.json');save()
        inventory=package_inventory((providers/'system-packages.txt').read_text())
        run('apt-update',['apt-get','update'])
        run('original-package-versions',['apt-get','install','-y','--no-install-recommends',*[name+'='+value for name,value in inventory.items()]],1200)
        actual=subprocess.check_output(['dpkg-query','-W','-f=${binary:Package}=${Version}\n'],text=True)
        require(package_inventory(actual)==inventory,'Every original provider OS package version must remain exact')
        (base/'actual-system-packages.txt').write_text(actual)
        py=[sys.executable,'-B'];mesa=base/'mesa'
        run('mesa-topology-build',py+['Tests/Production/GraphicsDriverLifetime/build_topology_driver.py','--cache',str(providers/'cache/mesa'),'--output',str(mesa),'--wayland','--jobs','2'],4200)
        run('original-executable-heap-controls',py+['Tests/Production/GraphicsDriverLifetime/allocator_test.py','--mesa-build',str(mesa/'build'),'--output',str(base/'allocator-controls')])
        run('cpu-cache-owner-controls',py+['Tests/Production/GraphicsDriverLifetime/topology_test.py','--mesa-build',str(mesa/'build'),'--output',str(base/'cpu-controls')])
        egl=base/'egl-controls'
        run('egl-configure',['cmake','-S','Tests/Production/GraphicsDriverLifetime','-B',str(egl),'-G','Ninja','-DCMAKE_BUILD_TYPE=Debug'])
        run('egl-build',['cmake','--build',str(egl),'--parallel','2'])
        selected=json.loads(subprocess.check_output(['ctest','--test-dir',str(egl),'--show-only=json-v1'],text=True))
        require({t['name'] for t in selected['tests']}=={'driver-mipmap','driver-no-mipmap'} and len(selected['tests'])==2,'Both original graphics unload tests required')
        (egl/'registered-tests.json').write_text(json.dumps(selected,indent=2)+'\n')
        sanitizers=dict(ASAN_OPTIONS='detect_leaks=1:fast_unwind_on_malloc=0',LSAN_OPTIONS='',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
        baseline=load(providers/'mesa/driver-build.json')['runtime_environment']
        baseline_code=run('original-driver-unload-observation',['ctest','--test-dir',str(egl),'--output-on-failure','--output-junit',str(egl/'baseline.xml')],environment=dict(os.environ,**baseline,**sanitizers),required=False)
        report['original_driver_observation']=dict(actual_returncode=baseline_code,scope='Actual old-driver observation on this runner; deterministic original-owner failure is independently required by cpu-controls')
        candidate=load(mesa/'driver-build.json')['runtime_environment']
        run('candidate-original-driver-unload-tests',['ctest','--test-dir',str(egl),'--output-on-failure','--output-junit',str(egl/'candidate.xml')],environment=dict(os.environ,**candidate,**sanitizers))
        cases=list(ET.parse(egl/'candidate.xml').getroot().iter('testcase'))
        require(len(cases)==2 and {c.attrib['name'] for c in cases}=={'driver-mipmap','driver-no-mipmap'} and
            not any(c.find(tag) is not None for c in cases for tag in ('failure','error','skipped')),'Both actual unsuppressed original driver tests must execute and pass')
        for name,path in [('allocator',base/'allocator-controls/report.json'),('cpu-owner',base/'cpu-controls/report.json')]:
            require(load(path)['status']=='passed','Original/new Mesa owner control failed');report['controls'][name]=dict(path=str(path),sha256=sha(path),status='passed')
        report['controls']['egl']=dict(path=str(egl/'candidate.xml'),sha256=sha(egl/'candidate.xml'),status='passed',executed_tests=2)
        require(all(sha(name)==value for name,value in guard.items()),'Original retained dependency bytes changed during separate repair')
        report.update(status='built-Mesa-topology-cleanup-and-passed-dependency-controls-only',original_provider_bytes_unchanged=True,
            variant=load(mesa/'topology-source-variant.json'),full_native_capture_and_comparisons_pending=True)
    except BaseException as error:report.update(status='failed-or-incomplete-unqualified',error=str(error));raise
    finally:save()
    print(report['status'])


if __name__=='__main__':main()
