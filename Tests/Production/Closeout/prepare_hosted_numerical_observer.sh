#!/usr/bin/env bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
sha256sum --check out/numerical-observer-pool-source/Debug-automatic/before.sha256
bash out/numerical-observer-pool-source/Debug-automatic/original-plan-with-explicit-snapshot-fallback.sh
sha256sum --check out/numerical-observer-pool-source/Debug-automatic/before.sha256
python3 - <<'PY'
from pathlib import Path
p=Path('/root/.gitconfig')
assert not p.exists()
p.write_text('[safe]\n\tdirectory = '+str(Path.cwd())+'\n')
PY
python3 -B Tests/Production/Closeout/hosted_numerical_observer.py --profile "$PROFILE"
