#!/usr/bin/env bash
set -euo pipefail
orbiter_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../.." && pwd)"
orbiter_preview="$(cd -P -- "${ORBITER_FLIGHT_PREVIEW:-$orbiter_root/out/native-flight-preview/current}" && pwd)"
orbiter_scenario="$orbiter_root/Tests/Production/NativeScene/Sol-ISS-ShuttlePB.scn"
orbiter_keymap="$orbiter_root/Tests/Production/Flight/keymap-laptop.cfg"
orbiter_config="$orbiter_root/Tests/Production/NativeScene/Orbiter.cfg"
orbiter_args=()
while (($#)); do
    case "$1" in
        --scenario|--keymap|--config)
            if (($# < 2)); then echo "Missing value: $1" >&2; exit 1; fi
            if [[ "$1" == --scenario ]]; then orbiter_scenario="$2"; elif [[ "$1" == --config ]]; then orbiter_config="$2"; else orbiter_keymap="$2"; fi
            shift 2 ;;
        *) orbiter_args+=("$1"); shift ;;
    esac
done
export LD_LIBRARY_PATH="$orbiter_preview/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
exec "$orbiter_preview/bin/orbiter-production" \
    --assets "$orbiter_root/out/native-scene-resources" \
    --data "$orbiter_root/out/native-celestial-data" \
    --modules "$orbiter_preview/NativeModules" \
    --planets "$orbiter_root/out/archive-data" \
    --config "$orbiter_config" \
    --scenario "$orbiter_scenario" --keymap "$orbiter_keymap" "${orbiter_args[@]}"
