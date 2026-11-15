"""Extract and verify the Windows package using the original 48-frame stock probe."""
import argparse
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile

from native import ROOT, STOCK, digest, manifest

sys.path[:0] = [str(ROOT / "Tests/Production" / folder) for folder in ("RemainingStock", "Client", "")]
from run_client import mesa_files


def launchpad(executable, cwd, env, log):
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    process = subprocess.Popen([executable], cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT)
    windows = []

    @callback_type
    def visible_window(window, unused):
        owner = wintypes.DWORD()
        title = ctypes.create_unicode_buffer(256)
        user32.GetWindowThreadProcessId(window, ctypes.byref(owner))
        if owner.value == process.pid and user32.IsWindowVisible(window):
            user32.GetWindowTextW(window, title, len(title))
            if "Orbiter Launchpad" in title.value:
                windows.append(window)
        return True

    try:
        deadline = time.monotonic() + 45
        while process.poll() is None and time.monotonic() < deadline:
            user32.EnumWindows(visible_window, 0)
            if windows:
                if not user32.PostMessageW(windows[0], 0x0010, 0, 0) or process.wait(timeout=15):
                    raise RuntimeError("Installed Qt Launchpad did not close normally")
                return
            time.sleep(0.15)
        raise RuntimeError("Installed Qt Launchpad window did not appear")
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("archive", "data", "planets", "mesa", "probe", "output"):
        parser.add_argument("--" + name, type=lambda value: Path(value).resolve(), required=True)
    parser.add_argument("--source", required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="Orbiter clean install ") as directory:
        clean = Path(directory)
        root = clean / "Install"
        with zipfile.ZipFile(args.archive) as package:
            package.extractall(root)
        packaged = json.loads((root / "runtime.json").read_text(encoding="utf-8"))
        actual = manifest(root)
        del actual["runtime.json"]
        if packaged != {"source": args.source, "files": actual}:
            raise RuntimeError("Installed runtime contents differ from the manifest")
        env = os.environ.copy()
        for name in ("QT_PLUGIN_PATH", "QT_QPA_PLATFORM_PLUGIN_PATH"):
            env.pop(name, None)
        # Use system search locations and the deployed runtime's own directory.
        system_root = Path(os.environ["SYSTEMROOT"])
        env.update(PATH=os.pathsep.join([str(system_root / "System32"), str(system_root)]),
                   QT_QPA_PLATFORM="windows", QT_DEBUG_PLUGINS="1")
        with (args.output / "qt.log").open("wb") as log:
            launchpad(root / "orbiter-launchpad.exe", clean, env, log)
        stock = root / STOCK
        if digest(stock) != digest(ROOT / STOCK):
            raise RuntimeError("Installed stock scenario differs from the checkout")
        for name in ("Kernels", "Textures", "Textures2", "GravityModels", "Fonts"):
            shutil.copytree(args.data / name, root / name, dirs_exist_ok=True)
        for name in json.loads((ROOT / "Tests/Production/standard-planets.lock.json").read_text())["data_files"]:
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            try:
                os.link(args.planets / name, target)
            except OSError:
                shutil.copyfile(args.planets / name, target)
        test_config = (ROOT / "Tests/Production/Fixtures/Orbiter.cfg").read_text()
        test_config = test_config.replace("  ProductionReferenceDriver", "  LaunchpadFlightProbe\n  OGLClient")
        test_config = test_config.replace("FixedStep = 1\n", "FixedStep = 0.0625\n")
        (root / "Orbiter.cfg").write_text(test_config, encoding="ascii")
        shutil.copy2(args.probe, root / "Modules/Plugin")
        (root / "ogl-evidence.enabled").touch()
        mesa_files(args.mesa, root)
        env.update(LIBGL_ALWAYS_SOFTWARE="true", GALLIUM_DRIVER="llvmpipe")
        with (args.output / "flight.log").open("wb") as log:
            scenario = str(Path(STOCK).relative_to("Scenarios").with_suffix(""))
            subprocess.run([root / "Orbiter.exe", "--scenariox=" + scenario], cwd=root, env=env,
                           check=True, stdout=log, stderr=subprocess.STDOUT, timeout=120)
        files = ("graphics-lifecycle.json", "launchpad-flight.txt", "launchpad-flight-end.txt", "Orbiter.log")
        for name in files:
            shutil.copyfile(root / name, args.output / name)
        lifecycle = json.loads((root / "graphics-lifecycle.json").read_text())
        flight = (root / "launchpad-flight.txt").read_text()
        if (lifecycle != dict(rendered_frames=48, successful_presents=48, context_deleted=True)
                or "focus=GL-01\nclass=DeltaGlider\n" not in flight or "close-requested=1" not in flight
                or (root / "launchpad-flight-end.txt").read_text().strip() != "48"):
            raise RuntimeError("Packaged stock flight did not render or close as expected")
        report = dict(source=args.source, archive=args.archive.name, archive_sha256=digest(args.archive),
                      installed_path=str(root), scenario=STOCK, scenario_sha256=digest(stock),
                      qt_started=True, lifecycle=lifecycle, full_runs_invoked=False)
        (args.output / "clean-install.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
