#!/usr/bin/env python3
"""Reproduce omitted SDK restoration using only exact retained bytes; no module execution."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tarfile
import zipfile
from contracts import ROOT,require,load,sha,atomic_json
from recheck_native_discovery import safe
import inspect_rejection_sdk_witnesses as inspection
import restore_rejection_sdk_header as sdk


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('api','archive','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();require(__import__('os').environ.get('GITHUB_ACTIONS')=='true' and __import__('os').environ.get('RUNNER_OS')=='Linux' and not a.output.exists(),'Fresh read-only hosted SDK restoration inspection required')
    a.output.mkdir(parents=True);original=inspection.inspect(load(a.api),a.archive,a.output/'original-witnesses')
    packed=a.output/'original-package.tar.gz';profile='Debug-sse2';prefix='out/phase6-hosted-native/'+profile+'/'
    with zipfile.ZipFile(a.archive) as z:
        sealed=json.loads(z.read(profile+'/hosted-package.json'))
        with z.open(profile+'.tar.gz') as source,packed.open('xb') as target:shutil.copyfileobj(source,target,1024*1024)
    with tarfile.open(packed,'r:gz') as sizing:actual_bytes=sum(v.size for v in sizing.getmembers())
    require(actual_bytes<4*1024**3 and packed.stat().st_size==sealed['archive_bytes'] and sha(packed)==sealed['archive_sha256'] and not (ROOT/prefix).exists() and shutil.disk_usage(ROOT).free>8*1024**3+actual_bytes,'Fresh original retained package and unchanged eight-GiB reserve required')
    expected=sealed['archive_members_sha256'];seen=set()
    with tarfile.open(packed,'r:gz') as tar:
        for item in tar:
            name=safe(item.name);require(item.isfile() and not item.mode&0o7000 and name.startswith(prefix) and name in expected and name not in seen,'Exact safe original package member required');seen.add(name)
            target=ROOT/name;require(not target.exists() and not target.is_symlink(),'Never overwrite an existing original input');target.parent.mkdir(parents=True,exist_ok=True)
            with tar.extractfile(item) as source,target.open('xb') as stream:shutil.copyfileobj(source,stream,1024*1024)
            target.chmod(item.mode&0o777);require(sha(target)==expected[name],'Actual original restored member differs')
    require(seen==set(expected),'Every original retained member required');packed.unlink()
    restored=sdk.restore(profile,ROOT/prefix/'build.json',a.output/'header-restoration.json')
    require(restored['header_was_present'] is False and restored['header_was_in_original_retained_archive'] is False and restored['compiled_runtime_rebuilt'] is False and restored['original_fixture_or_rejection_auditor_changed'] is False and restored['phase6_complete'] is False,'Reconstructed header must never be relabelled retained or grant runtime qualification')
    report=dict(protocol='phase6-read-only-original-SDK-header-restoration-proof-v1',status='verified-original-SDK-header-restoration-only-not-qualified',collector_source=original['collector_source'],compiled_source=sdk.COMPILED,actual_original_members_verified=len(seen),original_inspection_sha256=sha(a.output/'original-witnesses/inspection.json'),header_restoration_sha256=sha(a.output/'header-restoration.json'),header_sha256=restored['header_sha256'],actual_SDK_owner_tokens=restored['binary_SDK_build_bases'],original_module_roles=restored['native_module_SDK_roles'],new_simulator_processes=0,ELF_modules_executed=False,qualification_granted=False,phase6_complete=False,hands_on_ready=False)
    atomic_json(a.output/'inspection.json',report);print(json.dumps(report,indent=2))
