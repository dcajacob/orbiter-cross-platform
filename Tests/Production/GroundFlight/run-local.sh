#!/usr/bin/env bash
set -euo pipefail
orbiter_ground="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
export ORBITER_FLIGHT_PREVIEW="$orbiter_ground/../../../out/native-ground-preview/current"
echo 'Experimental Phase 5 ground preview: impact attitude and controlled-flight fuel parity remain open.' >&2
exec "$orbiter_ground/../Flight/run-local.sh" \
    --config "$orbiter_ground/Orbiter.cfg" --scenario "$orbiter_ground/Edwards-ShuttlePB.scn" "$@"
