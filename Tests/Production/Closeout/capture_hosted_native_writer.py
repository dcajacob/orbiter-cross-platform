#!/usr/bin/env python3
"""Run and independently inspect all normal-host stock writers on a standard runner."""
import argparse
import datetime
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from hosted_native_package import ROOT,require,sha,load


def package_inventory(body):
    lines=body.splitlines()
    require(lines and len(lines)<3000 and all(re.fullmatch(r'[a-z0-9][a-z0-9+.-]*(?::[a-z0-9-]+)?=[A-Za-z0-9.+:~_-]+',line) for line in lines),
            'Complete bounded original binary package/version inventory required')
    result=dict(line.split('=',1) for line in lines)
    require(len(result)==len(lines),'Duplicate original system package')
    return result


def stage_configuration(source,assets):
    source=Path(source);target=Path(assets)/'Orbiter.cfg'
    require(source.is_file() and not target.exists() and not target.is_symlink(),
            'Original configuration fixture and a fresh private asset destination required')
    checksum=sha(source);shutil.copy2(source,target)
    require(sha(source)==sha(target)==checksum and source.stat().st_ino!=target.stat().st_ino,
            'Original native configuration must retain its bytes in a separate asset file')
    return dict(source=str(source),target=str(target),sha256=checksum,canonical_source_unchanged=True)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--profile',required=True)
    a=p.parse_args();require(a.profile in {c+'-'+m for c in ('Debug','Release') for m in ('automatic','sse2')},'Explicit native profile required')
    require(os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('RUNNER_OS')=='Linux' and
            Path(os.environ['GITHUB_WORKSPACE']).resolve()==ROOT,'GitHub-hosted Linux workspace required; no local capture')
    output=ROOT/'out/hosted-native-writer'/a.profile;require(not output.exists(),'Fresh hosted writer output required');output.mkdir(parents=True)
    report=dict(protocol='phase6-hosted-native-stock-writer-v1',status='running',profile=a.profile,
        collector_source=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(),
        compiled_runtime_source='ccc02c8a34bd1f227624d8778a141e8736ae8111',
        compiled_provider_source='60ba46377f236c2d4705f444c0174e0f5af8252f',commands=[],
        phase6_complete=False,native_admission_qualified=False,windows_comparisons_pending=True,reload_phase_pending=True)
    def save():(output/'collection.json').write_text(json.dumps(report,indent=2)+'\n')
    def run(label,argv,timeout=600,environment=None):
        item=dict(label=label,argv=list(map(str,argv)),cwd=str(ROOT),started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
        report['commands'].append(item);started=time.monotonic_ns();log=output/(label+'.log')
        print('Starting '+label,flush=True)
        with log.open('w') as stream:
            child=subprocess.Popen(item['argv'],cwd=ROOT,env=environment,stdout=stream,stderr=subprocess.STDOUT);item['actual_pid']=child.pid;save()
            try:item['actual_returncode']=child.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                child.kill();item['actual_returncode']=child.wait();item['timed_out']=True;raise
            finally:item.update(elapsed_ns=time.monotonic_ns()-started,log_sha256=sha(log));save()
        if item['actual_returncode']:print(log.read_text(errors='replace')[-16000:],flush=True)
        require(item['actual_returncode']==0,'Actual hosted writer stage failed: '+label)
    try:
        require(report['collector_source']==os.environ['GITHUB_SHA'],'Actual immutable collector source differs')
        lock=load(ROOT/'Tests/Production/Closeout/native-provider-container.lock.json')
        image=load(ROOT/'out/native-writer-container.json')
        require(len(image)==1 and any(d.endswith('@'+lock['image_digest']) for d in image[0]['RepoDigests']),
                'Actual capture userspace image differs from the pinned provider image')
        report['actual_container_receipt_sha256']=sha(ROOT/'out/native-writer-container.json')
        providers=ROOT/'out/hosted-native-providers';restoration=load(ROOT/'out/native-provider-restoration/restoration.json')
        require(restoration['status']=='restored-verified-dependency-bytes-only' and restoration['compiled_provider_source']==report['compiled_provider_source'] and
                restoration['collector_source']==report['collector_source'] and restoration['actual_original_package_inventory_sha256']==sha(providers/'system-packages.txt'),
                'Exact dependency-only provider restoration required')
        inventory=package_inventory((providers/'system-packages.txt').read_text())
        run('apt-update',['apt-get','update'])
        run('restore-original-system-packages',['apt-get','install','-y','--no-install-recommends',*[name+'='+version for name,version in inventory.items()]],1200)
        actual=subprocess.check_output(['dpkg-query','-W','-f=${binary:Package}=${Version}\n'],text=True)
        (output/'actual-system-packages.txt').write_text(actual)
        require(package_inventory(actual)==inventory,'Actual complete provider userspace package versions differ')
        report['actual_system_packages_sha256']=sha(output/'actual-system-packages.txt');save()
        py=[sys.executable,'-B']
        run('stock-data',py+['Tests/Production/prepare_native_data.py','--archive','out/data-cache/production-stock-data-v1.zip','--destination','out/native-stock-data','--group','all'],1200)
        run('planet-data',py+['Tests/Production/prepare_hosted_data.py','--lock','Tests/Production/standard-planets.lock.json','--archive','out/planet-cache/Orbiter2016.zip','--destination','out/native-stock-planets'],1200)
        run('base-assets',py+['Tests/Production/NativeScene/prepare.py','--delta-glider','--shuttle-a','--data','out/native-stock-data','--planets','out/native-stock-planets','--destination','out/native-stock-base-assets'])
        run('test-font',py+['Tests/Production/CockpitUI/prepare_fonts.py','--assets','out/native-stock-base-assets'])
        report['staged_configuration_fixture']=stage_configuration(ROOT/'Tests/Production/NativeScene/Orbiter.cfg',ROOT/'out/native-stock-base-assets');save()
        run('complete-stock-assets',py+['Tests/Production/Atlantis/stage_assets.py','--base-assets','out/native-stock-base-assets','--output','out/native-stock-assets'])
        build=ROOT/'out/phase6-hosted-native'/a.profile;capture=ROOT/'out/native-stock-writer'/a.profile
        environment=dict(os.environ,__EGL_VENDOR_LIBRARY_FILENAMES=str(providers/'mesa/install/share/glvnd/egl_vendor.d/50_mesa.json'))
        argv=py+['Tests/Production/RemainingStockPersistence/capture_native.py','--build',str(build/'engine'),'--build-record',str(build/'build.json'),
            '--assets','out/native-stock-assets','--data','out/native-stock-data','--planets','out/native-stock-planets',
            '--compositor-tools',str(providers/'compositor'),'--gtk-plugin',str(providers/'libdecor-candidate/build/src/plugins/gtk/libdecor-gtk.so'),
            '--gtk-build-record',str(providers/'libdecor-candidate/build.json'),
            '--phase','stock-writer','--runtime-role','normal','--runtime-owner',str(ROOT),'--asset-staging','private-cache-links',
            '--jobs','2','--output',str(capture)]
        for folder in ('fontconfig-candidate','gdk-candidate','mesa'):argv+=['--library',str(providers/folder/'install/lib/x86_64-linux-gnu')]
        run('all-38-stock-writers-twice',argv,15000,environment)
        sys.path.insert(0,str(ROOT/'Tests/Production/RemainingStockPersistence'))
        import observations
        reader=observations.bind_owner(ROOT,report['collector_source'])
        audit=observations.inspect_native(capture,ROOT,reader,a.profile,'stock-writer')
        require(audit['actual_processes']==76 and audit['actual_presentations']==72960 and audit['runtime_role']=='normal' and
                audit['observer_delay_ms']==120 and audit['runtime_source']==report['compiled_runtime_source'] and
                audit['native_admission_qualified'] is False and audit['phase6_complete'] is False,
                'Complete independent native writer-only audit required')
        (output/'independent-native-writer-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
        report.update(status='captured-and-independently-audited-native-writers-only',actual_processes=76,
            capture_sha256=sha(capture/'capture.json'),independent_audit_sha256=sha(output/'independent-native-writer-audit.json'))
    except BaseException as error:report.update(status='failed-or-incomplete-unqualified',error=str(error));raise
    finally:save()
    print(report['status'])


if __name__=='__main__':main()
