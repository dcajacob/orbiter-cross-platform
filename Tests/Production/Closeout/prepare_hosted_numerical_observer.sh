#!/usr/bin/env bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
bash Tests/Production/Closeout/prepare_original_packages_from_official_pool.sh
python3 - <<'PY'
from pathlib import Path
p=Path('/root/.gitconfig')
assert not p.exists()
p.write_text('[safe]\n\tdirectory = '+str(Path.cwd())+'\n')
PY
python3 -B Tests/Production/Closeout/hosted_numerical_observer.py --profile "$PROFILE"
