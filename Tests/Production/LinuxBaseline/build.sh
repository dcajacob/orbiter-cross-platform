#!/usr/bin/env bash
set -euo pipefail
source_revision=f2fead9d259e93fd9fbfd3c432eda982030f2ec5
root=$PWD
out="$root/out"
baseline=${ORBITER_UBUNTU_BASELINE:-24.04}
runtime_name=Orbiter-linux-x86_64-ubuntu$baseline.tar.gz
qt_flags=()
if [[ -n ${ORBITER_BUNDLE_QT:-} ]]; then qt_flags+=("-DCMAKE_PREFIX_PATH=$ORBITER_BUNDLE_QT"); fi
src="$RUNNER_TEMP/orbiter-source"
mkdir -p "$out"/{receipt,distribution}
test "$(lsb_release -rs)" = "$baseline"
{
  cat /etc/os-release
  getconf GNU_LIBC_VERSION
  c++ --version
  dpkg-query -W libstdc++6
} > "$out/receipt/build-platform.txt"
git worktree add --detach "$src" "$source_revision"
test "$(git -C "$src" rev-parse HEAD)" = "$source_revision"
(cd "$src" && python3 -B Tests/Production/frozen_reference.py && python3 -B Tests/Production/frozen_behavior.py)
python3 -B "$src/Tests/Production/NativeScene/dependencies.py" --cache "$out/ogl-dependencies"
cmake -S "$src/Src/Orbiter/Production" -B "$out/engine" -G Ninja -DCMAKE_BUILD_TYPE=Release \
  -DORBITER_MATH_FORCE_SSE2=ON -DORBITER_BUILD_NATIVE_VESSELS=ON -DORBITER_BUILD_NATIVE_COCKPIT=ON \
  -DORBITER_BUILD_NATIVE_CELESTIAL_MODULES=ON -DBUILD_TESTING=OFF \
  -DCMAKE_BUILD_WITH_INSTALL_RPATH=ON -DCMAKE_BUILD_RPATH_USE_ORIGIN=ON \
  '-DCMAKE_INSTALL_RPATH=$ORIGIN;$ORIGIN/..;$ORIGIN/../..;$ORIGIN/../../..;$ORIGIN/../../../..' \
  "-DORBITER_NATIVE_UI_ARCHIVE=$out/ogl-dependencies/imgui.zip" 2>&1 | tee "$out/receipt/engine-configure.log"
cmake --build "$out/engine" --parallel 4 --target orbiter-production native_xrsound native_deltaglider \
  native_shuttle_a native_shuttle_a_payload native_atlantis native_atlantis_tank native_atlantis_srb \
  native_hst native_solar_sail native_quadcopter native_dragonfly native_lua_inline native_lua_mfd \
  orbiter_native_spice orbiter_native_EarthAtmJ71G orbiter_native_EarthAtm2006 orbiter_native_MarsAtm2006 \
  2>&1 | tee "$out/receipt/engine-build.log"
cmake -S "$src/OVP/OGLClient/Native" -B "$out/renderer" -G Ninja -DCMAKE_BUILD_TYPE=Release \
  "-DORBITER_ENGINE_BUILD=$out/engine" "-DORBITER_RENDERER_DEPENDENCIES=$out/ogl-dependencies" \
  -DCMAKE_BUILD_WITH_INSTALL_RPATH=ON '-DCMAKE_INSTALL_RPATH=$ORIGIN/../..' 2>&1 | tee "$out/receipt/renderer-configure.log"
cmake --build "$out/renderer" --parallel 4 --target orbiter_ogl_native 2>&1 | tee "$out/receipt/renderer-build.log"
cmake -S "$src/Utils/Launchpad" -B "$out/qt" -G Ninja -DCMAKE_BUILD_TYPE=Release \
  "${qt_flags[@]}" "-DORBITER_GLFW_ARCHIVE=$out/ogl-dependencies/glfw.tar.gz" 2>&1 | tee "$out/receipt/qt-configure.log"
cmake --build "$out/qt" --parallel 4 2>&1 | tee "$out/receipt/qt-build.log"
tools="$root/Tests/Production/Packages/native.py"
python3 -B "$tools" stage --engine "$out/engine" --destination "$out/package"
cp "$out/engine/native-lua/liblua.so" "$out/package/"
cp "$src/Tests/Production/Licenses/lua-lua.h" "$out/package/Lua-LICENSE.h"
cp -a "$src/OVP/OGLClient/shaders" "$out/package/"
cmake --install "$out/qt" --prefix "$out/package"
if [[ -n ${ORBITER_BUNDLE_QT:-} ]]; then
  bash Tests/Production/LinuxBaseline/bundle-qt.sh "$ORBITER_BUNDLE_QT" "$out/package"
fi
python3 -B "$tools" manifest --destination "$out/package" --source "$source_revision"
tar -C "$out/package" -czf "$out/distribution/$runtime_name" .
python3 -B Tests/Production/LinuxBaseline/bind.py --runtime "$out/package" \
  --archive "$out/distribution/$runtime_name" --generated-header "$out/engine/native-sdk/OrbiterNativeBuild.h" \
  --glibc-max "${ORBITER_GLIBC_MAX:-2.39}" --source-lock Utils/PackageSDK/packages.json --output "$out/receipt"
python3 -B Utils/PackageSDK/build.py --package "$out/distribution/$runtime_name" \
  --package-lock "$out/receipt/packages.json" --output "$out/distribution/Orbiter-SDK-linux-x86_64-ubuntu$baseline.zip"
