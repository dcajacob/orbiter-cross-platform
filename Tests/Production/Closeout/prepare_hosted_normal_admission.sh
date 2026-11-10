#!/usr/bin/env bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
test "${GITHUB_ACTIONS:-}" = true
test "${RUNNER_OS:-}" = Linux
case "${PROFILE:-}" in Debug-automatic|Debug-sse2|Release-automatic|Release-sse2) ;; *) exit 2;; esac
source_dir="out/admission-package-source/$PROFILE"
sha256sum --check "$source_dir/before.sha256"
bash "$source_dir/original-plan-with-explicit-snapshot-fallback.sh"
sha256sum --check "$source_dir/before.sha256"
python3 - <<'PY'
from pathlib import Path
p=Path('/root/.gitconfig')
assert not p.exists()
p.write_text('[safe]\n\tdirectory = '+str(Path.cwd())+'\n')
PY
python3 -B Tests/Production/Closeout/hosted_normal_admission.py --profile "$PROFILE"
