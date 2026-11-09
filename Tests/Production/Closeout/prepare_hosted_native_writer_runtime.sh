#!/usr/bin/env bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
# Bootstrap only packages already pinned in the original provider inventory.
mapfile -t bootstrap < <(awk -F= '$1=="python3" || $1=="ca-certificates" || $1=="git" {print}' out/hosted-native-providers/system-packages.txt)
test "${#bootstrap[@]}" -eq 3
apt-get update
apt-get install -y --no-install-recommends "${bootstrap[@]}"
# Git and Python are bootstrapped at their exact original provider versions.
python3 - <<'PY'
from pathlib import Path
p=Path('/root/.gitconfig')
assert not p.exists()
p.write_text('[safe]\n\tdirectory = '+str(Path.cwd())+'\n')
PY
python3 -B Tests/Production/Closeout/capture_hosted_native_writer_runtime.py --profile "$PROFILE"
