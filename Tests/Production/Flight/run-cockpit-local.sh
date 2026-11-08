#!/usr/bin/env bash
# Start the separately staged Phase 6 keyboard/mouse development candidate.
set -euo pipefail
orbiter_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../.." && pwd)"
orbiter_walkthrough="$orbiter_root/out/phase6-keyboard-mouse-walkthrough-v2/run.py"
if [[ ! -f "$orbiter_walkthrough" ]]; then
    echo "The keyboard/mouse walkthrough has not been staged in this checkout." >&2
    exit 1
fi
exec python3 -B "$orbiter_walkthrough" "$@"
