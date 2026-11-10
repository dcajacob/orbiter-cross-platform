#!/usr/bin/env bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
python3 -B Tests/Production/Closeout/original_package_snapshot_fallback.py
python3 - <<'PY'
from pathlib import Path
p=Path('/root/.gitconfig')
assert not p.exists()
p.write_text('[safe]\n\tdirectory = '+str(Path.cwd())+'\n')
PY
python3 -B Tests/Production/Closeout/hosted_numerical_observer.py --profile "$PROFILE"
