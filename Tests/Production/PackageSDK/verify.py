"""Compile the packaged SDK example and load it into the sealed preview."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[3]
STOCK = Path("Scenarios/Delta-glider/DG Mk4 in orbit.scn")
NAME = "Phase8SdkProbe"
MARKERS = ["created", "configured", "read-back-mass", "destroyed"]
VESSEL = """SDK-01:Phase8SdkProbe
  STATUS Orbiting Earth
  ELEMENTS 7200000.0 0.001 30.0 15.0 12.0 3.0 51982.5292925579
END
"""


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def run(command, cwd, log, env=None, check=True, timeout=120):
    print("+", " ".join(map(str, command)), flush=True)
    with log.open("wb") as output:
        return subprocess.run(command, cwd=cwd, env=env, stdout=output, stderr=subprocess.STDOUT,
                              check=check, timeout=timeout)


def install_sdk(args, runtime):
    with ZipFile(args.sdk) as archive:
        archive.extractall(args.work / "SDK")
    sdk = args.work / "SDK"
    report = json.loads((sdk / "sdk.json").read_text(encoding="utf-8"))
    files = {path.relative_to(sdk).as_posix(): digest(path)
             for path in sdk.rglob("*") if path.is_file() and path != sdk / "sdk.json"}
    assert files == report["files"]
    # The SDK links to libraries from the package it actually runs against.
    stock = json.loads((args.install / "stock-data-receipt.json").read_text(encoding="utf-8"))
    assert stock["package_sha256"] == report["package_sha256"]
    assert stock["package_source"] == report["package_source"]
    env = os.environ.copy()
    for name in ("LD_LIBRARY_PATH", "LD_PRELOAD", "DYLD_FRAMEWORK_PATH", "DYLD_LIBRARY_PATH", "CMAKE_PREFIX_PATH"):
        env.pop(name, None)
    for name in ("CFLAGS", "CXXFLAGS", "LDFLAGS"):
        env.pop(name, None)
    build = args.work / "add-on build"
    command = ["cmake", "-S", sdk / "example", "-B", build, "-G", "Ninja", "-DCMAKE_BUILD_TYPE=Release",
               f"-DOrbiterSDK_DIR={sdk / 'cmake'}", f"-DOrbiterRuntime_ROOT={runtime}"]
    if os.name != "nt":
        # Reuse the original rejection fixture, isolated from the delivered example.
        fixture = args.work / "RejectedModule.cpp"
        shutil.copyfile(ROOT / "Tests/Production/RemainingVessels/RejectedModule.cpp", fixture)
        command.append(f"-DORBITER_REJECTION_FIXTURE={fixture}")
    run(command, args.work, args.output / "configure.log", env=env)
    run(["cmake", "--build", build, "--parallel", "2"], args.work, args.output / "build.log", env=env)
    return sdk, report, env, build


def scenario_with_addon(args, sdk, assets):
    source = assets / STOCK
    original = source.read_bytes()
    config = assets / "Config/Vessels" / (NAME + ".cfg")
    assert not config.exists()
    shutil.copy2(sdk / "example" / config.name, config)
    modified = original.replace(b"\r\n", b"\n")
    assert modified.count(b"END_SHIPS") == 1
    modified = modified.replace(b"END_SHIPS", VESSEL.encode() + b"END_SHIPS")
    target = args.output / "SDK add-on smoke.scn"
    target.write_bytes(modified)
    assert source.read_bytes() == original
    return target, digest(source)


def native(args, runtime, sdk, build, env):
    assets = args.install / "assets"
    module = runtime / "NativeModules/Vessel/ShuttlePB.so"
    # The installed stock Module file can be hard-linked from a local fixture.
    # Replace the directory entry in this disposable install.
    module.unlink()
    shutil.copy2(build / module.name, module)
    scenario = assets / STOCK
    original = digest(scenario)
    common = [runtime / "orbiter-production", "--assets", assets,
              "--data", args.install / "data", "--modules", runtime / "NativeModules",
              "--planets", args.install / "planets", "--config", args.install / "user/Orbiter.cfg",
              "--scenario", scenario, "--frames", "12"]
    run([*common, "--evidence", args.output], args.output, args.output / "flight.log", env=env)
    assert (args.output / "sdk-vessel.txt").read_text().splitlines() == MARKERS
    frames = json.loads((args.output / "graphics-lifecycle.json").read_text())
    assert frames == dict(rendered_frames=12, successful_presents=12, context_deleted=True)
    if sys.platform == "darwin":
        run(["otool", "-l", "-L", module], args.output, args.output / "module-linkage.txt", env=env)
    else:
        run(["readelf", "-d", module], args.output, args.output / "module-linkage.txt", env=env)
    assert str(args.work) not in (args.output / "module-linkage.txt").read_text()
    wrong = args.output / "rejection"
    wrong.mkdir()
    try:
        shutil.copy2(build / "SdkMismatch.so", module)
        rejected = run([*common, "--evidence", wrong], wrong, args.output / "rejection.log",
                       env=env, check=False)
        output = (args.output / "rejection.log").read_text(errors="replace")
        assert rejected.returncode != 0 and "Native module SDK build mismatch" in output
        assert "REJECTION_FIXTURE_INITIALIZE_CALLED" not in output
    finally:
        shutil.copy2(build / module.name, module)
    return frames, original


def windows_flight(runtime, scenario, env, log):
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    callback = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows.argtypes = [callback, wintypes.LPARAM]
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    with log.open("wb") as output:
        # --scenariox selects fast process exit, which intentionally skips world
        # destruction. Return to the classic Launchpad to test ovcExit.
        process = subprocess.Popen([runtime / "Orbiter.exe", "--scenario=" + scenario],
                                   cwd=runtime, env=env, stdout=output, stderr=subprocess.STDOUT)
        windows = []

        @callback
        def find_launchpad(window, unused):
            owner = wintypes.DWORD()
            user32.GetWindowThreadProcessId(window, ctypes.byref(owner))
            if owner.value == process.pid and user32.IsWindowVisible(window):
                title = ctypes.create_unicode_buffer(256)
                user32.GetWindowTextW(window, title, len(title))
                if "Orbiter Launchpad" in title.value:
                    windows.append(window)
            return True

        try:
            limit = time.monotonic() + 120
            while process.poll() is None and time.monotonic() < limit:
                if (runtime / "launchpad-flight-end.txt").is_file():
                    user32.EnumWindows(find_launchpad, 0)
                    if windows:
                        assert user32.PostMessageW(windows[0], 0x0010, 0, 0)
                        assert process.wait(timeout=20) == 0
                        return
                time.sleep(0.1)
            raise RuntimeError("Windows flight did not return to the classic Launchpad after normal teardown")
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()


def windows(args, runtime, sdk, build, env):
    sys.path.insert(0, str(ROOT / "Tests/Production/Packages"))
    from windows import mesa_files

    module = runtime / "Modules/Phase8SdkProbe.dll"
    assert not module.exists()
    shutil.copy2(build / module.name, module)
    scenario, original = scenario_with_addon(args, sdk, runtime)
    shutil.copy2(scenario, runtime / "Scenarios" / scenario.name)
    config = runtime / "Orbiter.cfg"
    font = "ImGui_ManuscriptFontFile = Fonts/Cousine-Regular.ttf"
    text = (ROOT / "Tests/Production/Fixtures/Orbiter.cfg").read_text()
    text = text.replace("  ProductionReferenceDriver", "  LaunchpadFlightProbe\n  OGLClient")
    text = text.replace("FixedStep = 1\n", "FixedStep = 0.0625\n")
    assert "ShutdownMode = 0" in text
    installed = config.read_bytes()
    try:
        config.write_text(font + "\n" + text, encoding="ascii")
        shutil.copy2(args.probe, runtime / "Modules/Plugin")
        (runtime / "ogl-evidence.enabled").touch()
        mesa_files(args.mesa, runtime)
        system = Path(os.environ["SYSTEMROOT"])
        env.update(PATH=os.pathsep.join([str(system / "System32"), str(system)]),
                   LIBGL_ALWAYS_SOFTWARE="true", GALLIUM_DRIVER="llvmpipe")
        windows_flight(runtime, scenario.stem, env, args.output / "flight.log")
    finally:
        config.write_bytes(installed)
        for name in ("graphics-lifecycle.json", "launchpad-flight-end.txt", "launchpad-flight.txt",
                     "sdk-vessel.txt", "Orbiter.log"):
            if (runtime / name).is_file():
                shutil.copy2(runtime / name, args.output)
    assert (args.output / "sdk-vessel.txt").read_text().splitlines() == MARKERS
    assert (args.output / "launchpad-flight-end.txt").read_text().strip() == "48"
    assert "vessel=SDK-01:Phase8SdkProbe" in (args.output / "launchpad-flight.txt").read_text()
    frames = json.loads((args.output / "graphics-lifecycle.json").read_text())
    assert frames == dict(rendered_frames=48, successful_presents=48, context_deleted=True)
    return frames, original


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("install", "sdk", "work", "output", "probe", "mesa"):
        parser.add_argument("--" + name, type=lambda value: Path(value).resolve(),
                            required=name in ("install", "sdk", "work", "output"))
    args = parser.parse_args()
    args.work.mkdir(parents=True)
    args.output.mkdir(parents=True)
    assert not args.work.is_relative_to(ROOT) and not args.install.is_relative_to(ROOT)
    runtime = args.install / "runtime"
    sdk, report, env, build = install_sdk(args, runtime)
    test = windows if os.name == "nt" else native
    frames, original = test(args, runtime, sdk, build, env)
    result = dict(status="passed", sdk=args.sdk.name, sdk_sha256=digest(args.sdk),
                  runtime=report["package"], runtime_sha256=report["package_sha256"],
                  source=report["package_source"], architecture=report["architecture"],
                  callbacks=MARKERS, lifecycle=frames, stock_input_sha256=original,
                  vessel_class="Phase8SdkProbe" if os.name == "nt" else "ShuttlePB",
                  wrong_native_sdk_rejected=os.name != "nt", full_runs_invoked=False, windows_hands_on=False)
    (args.output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
