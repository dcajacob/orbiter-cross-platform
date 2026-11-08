#!/usr/bin/env bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends ca-certificates git build-essential cmake ninja-build meson pkg-config python3 python3-mako python3-yaml \
  bison flex gperf llvm-dev libexpat1-dev libfreetype6-dev libgtk-3-dev libepoxy-dev libx11-xcb-dev \
  libxcb-dri2-0-dev libxcb-dri3-dev libxcb-present-dev libxcb-randr0-dev libxcb-shm0-dev libxshmfence-dev \
  libxxf86vm-dev libdrm-dev libglvnd-dev libwayland-dev wayland-protocols libxkbcommon-dev libzstd-dev \
  zlib1g-dev libxrandr-dev libxinerama-dev libxcursor-dev libxi-dev fonts-dejavu-core xfonts-base

git config --global --add safe.directory "$PWD"
test "$(git rev-parse HEAD)" = "$ORBITER_PROVIDER_SOURCE"
git diff --exit-code HEAD --
P=out/hosted-native-providers
test ! -e "$P"
mkdir -p "$P/cache"
cp /etc/os-release "$P/os-release.txt"
dpkg-query -W -f='${binary:Package}=${Version}\n' > "$P/system-packages.txt"
cc --version > "$P/compiler.txt"
python3 --version > "$P/python.txt"
meson --version > "$P/meson.txt"
python3 -B Tests/Production/NativeScene/dependencies.py --cache "$P/cache/renderer"

python3 -B Tests/Production/FontConfigLifetime/build.py --cache "$P/cache/fontconfig" --output "$P/fontconfig-baseline" --sanitizers --baseline --jobs 2
python3 -B Tests/Production/FontConfigLifetime/build.py --cache "$P/cache/fontconfig" --output "$P/fontconfig-candidate" --sanitizers --jobs 2
python3 -B Tests/Production/FontConfigLifetime/qualify.py --baseline "$P/fontconfig-baseline" --candidate "$P/fontconfig-candidate" --output "$P/fontconfig-controls"

python3 -B Tests/Production/GdkLifetime/build.py --cache "$P/cache/gdk" --output "$P/gdk-baseline" --sanitizers --baseline --jobs 2
python3 -B Tests/Production/GdkLifetime/build.py --cache "$P/cache/gdk" --output "$P/gdk-candidate" --sanitizers --jobs 2
python3 -B Tests/Production/GdkLifetime/qualify.py --baseline "$P/gdk-baseline" --candidate "$P/gdk-candidate" --output "$P/gdk-controls"

python3 -B Tests/Production/WindowDecorationLifetime/build_icon_owner.py --cache "$P/cache/libdecor" --output "$P/libdecor-candidate" --meson /usr/bin/meson --development-prefix /usr --sanitizers
python3 -B Tests/Production/GraphicsDriverLifetime/build_driver.py --cache "$P/cache/mesa" --output "$P/mesa" --wayland --jobs 2
python3 -B Tests/Production/GraphicsDriverLifetime/allocator_test.py --mesa-build "$P/mesa/build" --output "$P/mesa-controls"

# The independent focus client uses an ordinary, unsanitized GLFW tool library.
# Original instrumented simulator and library controls remain instrumented.
mkdir "$P/glfw-source"
cat > "$P/glfw-source/CMakeLists.txt" <<'CMAKE'
cmake_minimum_required(VERSION 3.24)
project(HostedCompositorGlfw LANGUAGES C)
include(FetchContent)
set(GLFW_BUILD_WAYLAND ON CACHE BOOL "" FORCE)
set(GLFW_BUILD_X11 OFF CACHE BOOL "" FORCE)
set(GLFW_BUILD_EXAMPLES OFF CACHE BOOL "" FORCE)
set(GLFW_BUILD_TESTS OFF CACHE BOOL "" FORCE)
set(GLFW_BUILD_DOCS OFF CACHE BOOL "" FORCE)
set(GLFW_INSTALL OFF CACHE BOOL "" FORCE)
set(GLFW_LIBRARY_TYPE STATIC CACHE STRING "" FORCE)
FetchContent_Declare(glfw URL "${ORBITER_GLFW_ARCHIVE}" URL_HASH SHA256=5234f4f29473e9a06bc7847d8371858dd135d38466eeeaa652fdc9f8f9ff0c20 DOWNLOAD_EXTRACT_TIMESTAMP TRUE)
FetchContent_MakeAvailable(glfw)
CMAKE
cmake -S "$P/glfw-source" -B "$P/glfw" -G Ninja -DCMAKE_BUILD_TYPE=Debug -DORBITER_GLFW_ARCHIVE="$PWD/$P/cache/renderer/glfw.tar.gz"
cmake --build "$P/glfw" --target glfw --parallel 2
python3 -B Tests/Production/WaylandInput/prepare.py --output "$P/compositor" --cache "$P/cache/compositor" --glfw-build "$P/glfw"
git diff --exit-code HEAD --
python3 - <<'DONE'
import json,os
from pathlib import Path
Path('out/hosted-native-providers/completed.json').write_text(json.dumps(dict(status='completed-existing-dependency-controls-only',source_commit=os.environ['ORBITER_PROVIDER_SOURCE'],container_digest=os.environ['ORBITER_PROVIDER_CONTAINER_DIGEST'],phase6_complete=False))+'\n')
DONE
