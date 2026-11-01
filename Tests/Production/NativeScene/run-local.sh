#!/usr/bin/env bash
set -euo pipefail
orbiter_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../.." && pwd)"
orbiter_preview="$orbiter_root/out/native-production-preview"
export LD_LIBRARY_PATH="$orbiter_preview/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
exec "$orbiter_preview/bin/orbiter-production" \
    --assets "$orbiter_root/out/native-scene-resources" \
    --data "$orbiter_root/out/native-celestial-data" \
    --modules "$orbiter_preview/NativeModules" \
    --planets "$orbiter_root/out/archive-data" \
    --config "$orbiter_root/Tests/Production/NativeScene/Orbiter.cfg" \
    --scenario "$orbiter_root/Tests/Production/NativeScene/Sol-ISS-ShuttlePB.scn" \
    --evidence "$orbiter_root/out/native-production-live" "$@"
