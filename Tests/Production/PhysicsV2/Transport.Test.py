import subprocess,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import snapshot_transport


class IdenticalSnapshotTransport(unittest.TestCase):
    def fixture(self,status):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);body=snapshot_transport.FUNCTION.replace('/usr/lib/apt/apt-helper','fake_apt').replace('sleep 10',':')
            script='''set -euo pipefail
output="$1"
count=0
fake_apt() {
  [[ "$*" == '-o Acquire::ForceHash=sha256 download-file https://snapshot.ubuntu.com/exact.deb '"$output"'/cache SHA256:unchanged' ]] || return 42
  count=$((count+1))
  printf '%s\\n' partial > "$output/cache"
  if [[ "$count" -lt 3 ]]; then printf '%s\\n' "''' + status + '''";return 100;fi
  return 0
}
run_stage() {
  local label="$1" code
  shift
  printf '%s\\n' "$label" >> "$output/labels"
  "$@" > "$output/$label.log" 2>&1 && return 0 || { code=$?;return "$code"; }
}
'''+body+'''
retry_identical_snapshot original https://snapshot.ubuntu.com/exact.deb "$output/cache" unchanged
'''
            result=subprocess.run(['bash','-c',script,'fixture',str(root)],capture_output=True,text=True)
            return result.returncode,(root/'labels').read_text().splitlines(),sorted(p.name for p in root.glob('*.partial-*.deb'))

    def test_observed503_retries_identical_argv_and_preserves_every_failed_partial(self):
        code,labels,partial=self.fixture('503 Service Unavailable')
        self.assertEqual(code,0);self.assertEqual(labels,['original','original-identical-transport-retry-2','original-identical-transport-retry-3'])
        self.assertEqual(partial,['original-identical-transport-retry-2.partial-1.deb','original.partial-1.deb'])

    def test_hash_mismatch_is_never_retried_or_accepted(self):
        code,labels,partial=self.fixture('Hash Sum mismatch')
        self.assertEqual(code,100);self.assertEqual(labels,['original']);self.assertEqual(partial,['original.partial-1.deb'])

    def test404_is_never_treated_as_observed_transient_snapshot_failure(self):
        code,labels,_=self.fixture('404 Not Found');self.assertEqual(code,100);self.assertEqual(labels,['original'])

    def test_mixed503_and_hash_failure_still_stops_at_the_original_guard(self):
        code,labels,_=self.fixture('503 Service Unavailable; Hash Sum mismatch');self.assertEqual(code,100);self.assertEqual(labels,['original'])

    def test_actual_apt_two_space503_format_retries_the_identical_request(self):
        code,labels,partial=self.fixture('503  Service Unavailable [IP: 185.125.189.37 443]')
        self.assertEqual(code,0);self.assertEqual(len(labels),3);self.assertEqual(len(partial),2)
