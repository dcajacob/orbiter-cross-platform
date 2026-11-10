#!/usr/bin/env python3
"""Allow slow signed package transfer without changing any original inventory or runtime test."""
import hashlib
import os
from pathlib import Path
import subprocess
from contracts import ROOT,require,atomic_json

ORIGINAL_SOURCE='4174959a80c5966d93feeccb7337564933903fba'
ORIGINAL=ROOT/'Tests/Production/Closeout/hosted_class_userspace.py'
ORIGINAL_TIMEOUT=1200
PROVISIONING_TIMEOUT=3600


def prepared_body():
    body=ORIGINAL.read_bytes();require(body==subprocess.check_output(['git','-C',str(ROOT),'show',ORIGINAL_SOURCE+':'+ORIGINAL.relative_to(ROOT).as_posix()]),
        'Every original package inventory/version/TLS/signature preflight guard must remain unchanged')
    text=body.decode();before='def run(label,argv,timeout=1200):';after='def run(label,argv,timeout=3600):'
    require(text.count(before)==1,'One exact original provisioning deadline required')
    return text.replace(before,after,1)


def main():
    require(os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('RUNNER_OS')=='Linux' and
            Path(os.environ['GITHUB_WORKSPACE']).resolve()==ROOT,'Actual standard hosted Linux package preflight required; no local install')
    output=ROOT/'out/class-rejection-provisioning-deadline.json';require(not output.exists(),'Fresh provisioning-only deadline receipt required')
    body=prepared_body();atomic_json(output,dict(protocol='phase6-rejection-provisioning-deadline-only-v1',
        original_preflight_source=ORIGINAL_SOURCE,original_preflight_sha256=hashlib.sha256(ORIGINAL.read_bytes()).hexdigest(),
        original_setup_timeout_seconds=ORIGINAL_TIMEOUT,actual_setup_timeout_seconds=PROVISIONING_TIMEOUT,
        exact_original_packages_versions_snapshot_TLS_and_signatures_preserved=True,runtime_test_or_sanitizer_deadlines_changed=False,
        qualification_granted=False,phase6_complete=False))
    exec(compile(body,str(ORIGINAL),'exec'),{'__name__':'__main__','__file__':str(ORIGINAL)})


if __name__=='__main__':main()
