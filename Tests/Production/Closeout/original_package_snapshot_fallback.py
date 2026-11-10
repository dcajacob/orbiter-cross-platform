#!/usr/bin/env python3
"""Retry only failed official-pool transfers at their exact original signed snapshot URI."""
import os
from pathlib import Path
import subprocess
from contracts import ROOT,require,sha,atomic_json

SOURCE='a1c48b762333c084e8c8321668c5fd87a94cc0f6'
ORIGINAL=ROOT/'Tests/Production/Closeout/prepare_original_packages_from_official_pool.sh'
ANCHOR='  run_stage "exact-official-blob-$count" /usr/lib/apt/apt-helper -o Acquire::ForceHash=sha256 download-file "$mirror" "$cache" "SHA256:$expected"'
REPLACEMENT='''  # Preserve the original failed transport log/argv/exit. The fallback URI is
  # the unchanged original signed dated-snapshot URI from the same exact plan.
  if run_stage "exact-official-blob-$count" /usr/lib/apt/apt-helper -o Acquire::ForceHash=sha256 download-file "$mirror" "$cache" "SHA256:$expected"; then
    printf '%s\\t%s\\t%s\\n' "$count" official-pool "$mirror" >> "$output/actual-blob-transports.tsv"
  else
    original_code=$?
    printf '%s\\t%s\\t%s\\n' "$count" "$original_code" "$mirror" >> "$output/preserved-original-pool-failures.tsv"
    run_stage "exact-original-snapshot-blob-$count" /usr/lib/apt/apt-helper -o Acquire::ForceHash=sha256 download-file "$original" "$cache" "SHA256:$expected"
    printf '%s\\t%s\\t%s\\n' "$count" original-signed-snapshot "$original" >> "$output/actual-blob-transports.tsv"
  fi'''


def prepared_body():
    body=ORIGINAL.read_bytes();frozen=subprocess.check_output(['git','-C',str(ROOT),'show',SOURCE+':'+ORIGINAL.relative_to(ROOT).as_posix()])
    require(body==frozen,'Every original signed plan/inventory/TLS/hash/size/cache-only install/source guard must remain exact')
    text=body.decode();require(text.count(ANCHOR)==1,'One exact original official-pool download site required')
    return text.replace(ANCHOR,REPLACEMENT,1)


def main():
    require(os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('RUNNER_OS')=='Linux' and os.environ.get('PROFILE')=='Debug-automatic' and Path(os.environ['GITHUB_WORKSPACE']).resolve()==ROOT,'Only affected actual standard-hosted numerical provisioning required')
    folder=ROOT/'out/numerical-observer-pool-source/Debug-automatic';require(not folder.exists(),'Fresh fallback transport metadata required');folder.mkdir(parents=True)
    body=prepared_body();path=folder/'original-plan-with-explicit-snapshot-fallback.sh';path.write_text(body)
    report=dict(protocol='phase6-exact-original-snapshot-transport-fallback-v1',source=os.environ['GITHUB_SHA'],original_source=SOURCE,original_helper_sha256=sha(ORIGINAL),adapter_sha256=sha(Path(__file__)),generated_body_sha256=sha(path),snapshot='20261109T212432Z',all488_original_versions_unchanged=True,all_original_SHA256_size_TLS_signature_guards_unchanged=True,original_failed_download_logs_preserved=True,qualification_granted=False,phase6_complete=False)
    atomic_json(folder/'source.json',report)
    try:subprocess.run(['bash',str(path)],check=True)
    finally:
        require(sha(ORIGINAL)==report['original_helper_sha256'] and sha(Path(__file__))==report['adapter_sha256'] and sha(path)==report['generated_body_sha256'],'Actual original and explicit adapter source changed during transport')


if __name__=='__main__':main()
