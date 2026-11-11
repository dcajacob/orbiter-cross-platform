"""Retry only observed502/503/504 for identical original signed snapshot package bytes."""
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT/'Tests/Production/Closeout'))
import original_package_snapshot_fallback as original
from contracts import require

FUNCTION=r'''
retry_identical_snapshot() {
  local label="$1" original="$2" cache="$3" expected="$4" attempt code partial_number
  for attempt in 1 2 3 4; do
    local actual_label="$label"
    if [[ "$attempt" -gt 1 ]]; then actual_label="$label-identical-transport-retry-$attempt"; fi
    if run_stage "$actual_label" /usr/lib/apt/apt-helper -o Acquire::ForceHash=sha256 download-file "$original" "$cache" "SHA256:$expected"; then
      return 0
    else
      code=$?
      partial_number=0
      for partial in "$cache" "$cache.partial"; do
        partial_number=$((partial_number+1))
        if [[ -f "$partial" ]]; then
          cp -a "$partial" "$output/$actual_label.partial-$partial_number.deb"
          sha256sum "$output/$actual_label.partial-$partial_number.deb" >> "$output/preserved-partial-downloads.sha256"
        fi
      done
      if [[ "$attempt" -eq 4 ]] || ! grep -Eq '50[234] (Bad Gateway|Service Unavailable|Gateway Time-out|Gateway Timeout)' "$output/$actual_label.log"; then return "$code"; fi
      sleep 10
    fi
  done
}
'''


def prepared_body():
    body=original.prepared_body();anchor='export DEBIAN_FRONTEND=noninteractive\n'
    require(body.count(anchor)==1,'Exact original package setup anchor required');body=body.replace(anchor,anchor+FUNCTION+'\n',1)
    invocation='    run_stage "exact-original-snapshot-blob-$count" /usr/lib/apt/apt-helper -o Acquire::ForceHash=sha256 download-file "$original" "$cache" "SHA256:$expected"'
    require(body.count(invocation)==1,'Exact original failed signed snapshot download required')
    return body.replace(invocation,'    retry_identical_snapshot "exact-original-snapshot-blob-$count" "$original" "$cache" "$expected"',1)
