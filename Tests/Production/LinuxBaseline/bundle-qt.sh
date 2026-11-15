#!/usr/bin/env bash
set -euo pipefail
qt=$1
package=$2
mkdir -p "$package/qt/"{lib,plugins,notices}
for category in platforms xcbglintegrations wayland-decoration-client wayland-graphics-integration-client wayland-shell-integration; do
  if [[ -d "$qt/plugins/$category" ]]; then
    cp -a "$qt/plugins/$category" "$package/qt/plugins/"
  fi
done
test -f "$package/qt/plugins/platforms/libqxcb.so"
# Collect only the dependencies delivered in the Qt prefix. System libraries
# such as glibc, X11 and Mesa remain supplied by the target distribution.
while IFS= read -r dependency; do
  cp -L "$dependency" "$package/qt/lib/"
done < <(
  { LD_LIBRARY_PATH="$qt/lib" ldd "$package/bin/orbiter-launchpad"
    find "$package/qt/plugins" -name '*.so' -exec env LD_LIBRARY_PATH="$qt/lib" ldd {} +
  } | awk -v prefix="$qt/lib/" 'index($3,prefix)==1 {print $3}' | sort -u
)
test -f "$package/qt/lib/libQt6Widgets.so.6"
patchelf --set-rpath '$ORIGIN/../qt/lib' "$package/bin/orbiter-launchpad"
find "$package/qt/lib" -type f -exec patchelf --set-rpath '$ORIGIN' {} \;
find "$package/qt/plugins" -type f -name '*.so' -exec patchelf --set-rpath '$ORIGIN/../../lib' {} \;
printf '[Paths]\nPrefix=../qt\nPlugins=plugins\n' > "$package/bin/qt.conf"
cat > "$package/qt/notices/Qt.txt" <<'NOTICE'
This preview bundles shared libraries and plugins from Qt 6.5.3.
Qt licensing information: https://doc.qt.io/qt-6.5/licensing.html
Qt source: https://download.qt.io/archive/qt/6.5/6.5.3/submodules/
NOTICE
for license in LGPL-3.0-only.txt GPL-3.0-only.txt; do
  curl -fsSL --retry 2 "https://raw.githubusercontent.com/qt/qtbase/v6.5.3/LICENSES/$license" -o "$package/qt/notices/$license"
done
