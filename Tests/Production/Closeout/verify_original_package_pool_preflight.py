#!/usr/bin/env python3
"""Audit only exact original package provisioning; no simulator acceptance follows."""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
from contracts import ROOT,require,load,sha,atomic_json
import hosted_class_userspace as original


def inspect(profile):
    require(profile in ('Debug-automatic','Debug-sse2','Release-automatic','Release-sse2'),'Exact original profile required')
    folder=ROOT/'out/original-package-official-pool'/profile;inventory=(folder/'original-system-packages.txt').read_text();actual=(folder/'actual-system-packages.txt').read_text()
    require(sha(folder/'original-system-packages.txt')==sha(folder/'actual-system-packages.txt')=='0ae6765d460a0d744c48afdb242257d02a29da4845cf7e8b7fda42004e164900' and original.verify_inventory(inventory,actual)==488,'Every exact original package and prior failed libheif version required')
    require((folder/'terminal-exit-code.txt').read_text()=='0\n' and (folder/'status.txt').read_text()=='prepared-exact-original-package-inventory-only-not-qualified\n','Closed original inventory installation required')
    plan=[line.split('\t') for line in (folder/'exact-original-plan.tsv').read_text().splitlines()];done=[line.split('\t') for line in (folder/'independently-verified-original-blobs.tsv').read_text().splitlines()]
    require(plan and len(plan)==len(done) and len({v[2] for v in plan})==len(plan) and all(len(v)==5 for v in plan) and all(len(v)==6 for v in done),'Complete unique exact original blob-plan scope required')
    for before,after in zip(plan,done):
        uri,mirror,name,size,digest=before
        require(after==before+[digest] and uri.startswith('https://snapshot.ubuntu.com/ubuntu/20261109T212432Z/pool/') and mirror==uri.replace('https://snapshot.ubuntu.com/ubuntu/20261109T212432Z/','https://archive.ubuntu.com/ubuntu/',1) and len(digest)==64 and all(c in '0123456789abcdef' for c in digest) and int(size)>0,'Every official mirror body must equal the original signed snapshot SHA256 and size')
    uri_plan=[]
    for line in (folder/'original-pinned-URI-plan.log').read_text().splitlines():
        if not line.startswith("'"):continue
        values=shlex.split(line);require(len(values)==4 and values[3].startswith('SHA256:'),'Original APT printed SHA256 URI record required');uri,name,size,digest=values
        uri_plan.append([uri,uri.replace('https://snapshot.ubuntu.com/ubuntu/20261109T212432Z/','https://archive.ubuntu.com/ubuntu/',1),name,size,digest.split(':',1)[1]])
    require(uri_plan==plan,'Independent original APT URI-plan reproduction differs')
    pins=inventory.splitlines();expected={'original-signed-snapshot-update':['apt-get','update'],'original-pinned-URI-plan':['apt-get','-o','Acquire::ForceHash=sha256','--print-uris','--yes','--download-only','--no-install-recommends','install',*pins],'install-only-exact-verified-cache':['apt-get','--no-download','install','-y','--no-install-recommends',*pins]}
    for label,argv in expected.items():require(shlex.split((folder/(label+'.argv.txt')).read_text())==argv,'Original pinned package installer or signed metadata command differs')
    commands=[v.split('\t') for v in (folder/'commands.tsv').read_text().splitlines()];require([v[0] for v in commands]==['original-signed-snapshot-update','original-pinned-URI-plan',*['exact-official-blob-'+str(i) for i in range(1,len(plan)+1)],'install-only-exact-verified-cache'] and all(v[1]=='0' for v in commands),'Every exact metadata, SHA-bound blob and cache-only install command must pass')
    for index,row in enumerate(plan,1):require(shlex.split((folder/('exact-official-blob-'+str(index)+'.argv.txt')).read_text())==['/usr/lib/apt/apt-helper','-o','Acquire::ForceHash=sha256','download-file',row[1],'/var/cache/apt/archives/'+row[2],'SHA256:'+row[4]],'Actual APT hash-bound download command differs')
    configs={}
    for line in (folder/'original-archive-config-before.sha256').read_text().splitlines():
        digest,name=line.split('  ',1);captured=folder/'archive-config'/name.lstrip('/').replace('/','__');require(sha(captured)==digest,'Original source/signature/TLS configuration copy differs');configs[name]=digest
    require((folder/'archive-config/etc__apt__apt.conf.d__99-orbiter-class-snapshot').read_text()=='APT::Snapshot "20261109T212432Z";\n','Original immutable dated snapshot configuration must remain unchanged')
    require((folder/'original-archive-config-after-verification.txt').read_text().splitlines()==[n+': OK' for n in configs],'Original APT sources, snapshot and TLS trust must remain unchanged')
    metadata={str(p.relative_to(folder)):dict(bytes=p.stat().st_size,sha256=sha(p)) for p in (folder/'signed-metadata').iterdir() if p.is_file()}
    require(any(n.endswith('_InRelease') for n in metadata) and any('_Packages' in n for n in metadata) and 'signed-metadata/ubuntu-archive-keyring.gpg' in metadata,'Original signed index bytes and original public archive keyring must remain retained')
    preflight=load(ROOT/'out/class-userspace-preflight/preflight.json')
    require(preflight['status']=='verified-complete-original-package-inventory-only' and preflight['actual_package_count']==488 and preflight['all_original_versions_preserved'] is True and preflight['archive_signatures_and_tls_required'] is True and preflight['actual_inventory_sha256']==preflight['original_inventory_sha256']=='0ae6765d460a0d744c48afdb242257d02a29da4845cf7e8b7fda42004e164900' and all(v['actual_returncode']==0 for v in preflight['commands']),'Unchanged original complete package preflight must independently pass after provisioning')
    return dict(protocol='phase6-exact-original-package-official-pool-preflight-v1',status='verified-original488-packages-and-identical-official-pool-blobs-only',source=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(),profile=profile,original_archive_snapshot='20261109T212432Z',original_inventory_sha256=preflight['original_inventory_sha256'],actual_original_package_count=488,actual_downloaded_blob_count=len(plan),all_original_blob_SHA256_and_sizes_verified_independently=True,original_APT_sources_snapshot_TLS_and_signatures_unchanged=True,original_package_preflight_reproduced=True,actual_original_blob_plan=plan,original_signed_metadata_members=metadata,original_archive_config_sha256=configs,provisioning_files_sha256={str(p.relative_to(ROOT)):sha(p) for p in folder.rglob('*') if p.is_file()},original_preflight_sha256=sha(ROOT/'out/class-userspace-preflight/preflight.json'),original_failed_snapshot_attempts_not_relabelled=True,new_simulator_processes=0,complete_class_eligibility_qualified=False,normal_admission_qualified=False,phase6_complete=False,hands_on_ready=False)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--profile',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();require(not a.output.exists(),'Fresh provisioning-only proof required');atomic_json(a.output,inspect(a.profile))
