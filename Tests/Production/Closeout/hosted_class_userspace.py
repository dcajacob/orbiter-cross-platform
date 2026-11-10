#!/usr/bin/env python3
"""Preflight exact original packages in the pinned image before any class simulator."""
import datetime
import json
import os
from pathlib import Path
import subprocess
import time
from capture_hosted_native_writer import package_inventory
from hosted_native_package import ROOT,require,sha,load

SNAPSHOT='20261109T212432Z'


def verify_inventory(original,actual):
    expected=package_inventory(original)
    require(package_inventory(actual)==expected,'Actual complete original userspace inventory differs')
    for package in ('libheif1','libheif-plugin-aomdec'):
        versions=[v for k,v in expected.items() if k.split(':')[0]==package]
        require(versions==['1.21.2-3ubuntu0.6'],'Original failed libheif package versions must be retained')
    return len(expected)


def main():
    require(os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('RUNNER_OS')=='Linux' and
            Path(os.environ['GITHUB_WORKSPACE']).resolve()==ROOT,'Actual hosted Linux workspace required; no local package install')
    output=ROOT/'out/class-userspace-preflight'
    require(not output.exists(),'Fresh original package preflight evidence required')
    output.mkdir(parents=True)
    report=dict(protocol='phase6-original-class-userspace-preflight-v1',status='running',snapshot=SNAPSHOT,
                collector_source=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
                commands=[],actual_simulator_processes=0,qualification_granted=False,phase6_complete=False)
    def save():(output/'preflight.json').write_text(json.dumps(report,indent=2)+'\n')
    def run(label,argv,timeout=1200):
        item=dict(label=label,argv=argv,started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
        report['commands'].append(item);started=time.monotonic_ns();log=output/(label+'.log')
        print('Starting '+label,flush=True)
        with log.open('w') as stream:
            process=subprocess.Popen(argv,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT)
            item['actual_pid']=process.pid;save()
            try:item['actual_returncode']=process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                process.kill();item['actual_returncode']=process.wait();item['timed_out']=True;raise
            finally:item.update(elapsed_ns=time.monotonic_ns()-started,log_sha256=sha(log));save()
        if item['actual_returncode']:print(log.read_text(errors='replace')[-16000:],flush=True)
        require(item['actual_returncode']==0,'Original package preflight failed: '+label)
    try:
        require(report['collector_source']==os.environ['GITHUB_SHA'],'Actual preflight collector source differs')
        lock=load(ROOT/'Tests/Production/Closeout/native-provider-container.lock.json')
        image=load(ROOT/'out/class-userspace-container.json')
        require(len(image)==1 and any(d.endswith('@'+lock['image_digest']) for d in image[0]['RepoDigests']),
                'Exact original provider userspace image required')
        report['actual_container_sha256']=sha(ROOT/'out/class-userspace-container.json')
        providers=ROOT/'out/hosted-native-providers';inventory_path=providers/'system-packages.txt'
        restoration=load(ROOT/'out/native-provider-restoration/restoration.json')
        require(restoration['status']=='restored-verified-dependency-bytes-only' and
                restoration['compiled_provider_source']=='60ba46377f236c2d4705f444c0174e0f5af8252f' and
                restoration['collector_source']==report['collector_source'] and
                restoration['actual_original_package_inventory_sha256']==sha(inventory_path),
                'Exact unchanged source-bound original provider inventory required')
        config=Path('/etc/apt/apt.conf.d/99-orbiter-class-snapshot')
        require(config.read_text()=='APT::Snapshot "'+SNAPSHOT+'";\n','Exact official dated archive selection required')
        report['archive_snapshot_config_sha256']=sha(config)
        expected_body=inventory_path.read_text();expected=package_inventory(expected_body)
        report['original_inventory_sha256']=sha(inventory_path)
        run('signed-snapshot-update',['apt-get','update'])
        run('restore-complete-original-package-versions',['apt-get','install','-y','--no-install-recommends',
                                                        *[name+'='+version for name,version in expected.items()]])
        actual=subprocess.check_output(['dpkg-query','-W','-f=${binary:Package}=${Version}\n'],text=True)
        (output/'actual-system-packages.txt').write_text(actual)
        report['actual_package_count']=verify_inventory(expected_body,actual)
        report['actual_inventory_sha256']=sha(output/'actual-system-packages.txt')
        report.update(status='verified-complete-original-package-inventory-only',all_original_versions_preserved=True,
                      archive_signatures_and_tls_required=True)
    except BaseException as error:report.update(status='failed-or-incomplete-unqualified',error=str(error));raise
    finally:save()
    print(report['status'])


if __name__=='__main__':main()
