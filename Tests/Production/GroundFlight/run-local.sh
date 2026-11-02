#!/usr/bin/env bash
set -euo pipefail
orbiter_ground="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec "$orbiter_ground/../Flight/run-local.sh" \
    --config "$orbiter_ground/Orbiter.cfg" --scenario "$orbiter_ground/Edwards-ShuttlePB.scn" "$@"
