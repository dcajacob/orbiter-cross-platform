"""Launch a Phase 8 package from the actual stock installer output."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[3]
STOCK = "Scenarios/Delta-glider/DG Mk4 in orbit.scn"
FONT = "ImGui_ManuscriptFontFile = Fonts/Cousine-Regular.ttf"
PACKAGE_TESTS = ROOT / "Tests/Production/Packages"


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def run(cmd, cwd, env, log, timeout):
    with log.open("wb") as stream:
        subprocess.run(cmd, cwd=cwd, env=env, stdout=stream, stderr=subprocess.STDOUT,
                       check=True, timeout=timeout)


def locked_scene(path):
    locked = json.loads((ROOT / "Tests/Production/production-source.lock.json").read_text())
    expected = next(case["sha256"] for case in locked["scenarios"] if case["path"] == STOCK)
    assert hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest() == expected


def native(args, runtime, env):
    profile_path = args.install / "Launchpad profile.json"
    profile = json.loads(profile_path.read_text())
    path = {key: args.install / value for key, value in profile.items() if key != "mode"}
    assert all(item.exists() for item in path.values())
    assert FONT in path["config"].read_text()
    launcher = runtime / ("orbiter-launchpad.app/Contents/MacOS/orbiter-launchpad"
                          if sys.platform == "darwin" else "bin/orbiter-launchpad")
    if sys.platform == "darwin":
        run(["codesign", "--verify", "--deep", "--strict", runtime / "orbiter-launchpad.app"],
            args.output, env, args.output / "codesign.log", 30)
    if not args.launchpad_driver or not args.launchpad_driver.is_file():
        raise ValueError("A Qt test driver for the installed Launchpad is required")
    scenario = path["assets"] / STOCK
    locked_scene(scenario)
    # Keep the installer's profile and all of Launchpad's arguments. Bound the
    # real child to 12 frames in this disposable install, then restore its name.
    engine = path["executable"]
    original_engine = engine.with_name(engine.name + ".bounded-test-original")
    assert not original_engine.exists()
    arguments = args.output / "launch-arguments.txt"
    events = args.output / "launchpad-events.txt"
    env.update(ORBITER_LAUNCHPAD_TEST_SETTINGS=str(args.output / "settings"),
               ORBITER_LAUNCHPAD_TEST_RECEIPT=str(events), ORBITER_CHECK_STOCK_SCREENSHOT="1",
               ORBITER_FLIGHT_ARGUMENTS=str(arguments), ORBITER_FLIGHT_OUTPUT=str(args.output))
    preload = "DYLD_INSERT_LIBRARIES" if sys.platform == "darwin" else "LD_PRELOAD"
    env[preload] = str(args.launchpad_driver)
    engine.rename(original_engine)
    try:
        engine.write_text("""#!/bin/sh
set -eu
printf '%s\\n' "$@" > "$ORBITER_FLIGHT_ARGUMENTS"
exec "$0.bounded-test-original" "$@" --frames 12 --evidence "$ORBITER_FLIGHT_OUTPUT"
""")
        engine.chmod(0o755)
        run([launcher, "--profile", profile_path], args.output, env, args.output / "qt.log", 100)
    finally:
        original_engine.replace(engine)
    assert events.read_text().splitlines() == [
        "decoded-stock-orbit-jpeg-400x300", "selected-and-launched-stock-scenario",
        "launcher-hidden-during-flight", "launcher-returned-with-selection",
    ]
    argv = arguments.read_text().splitlines()
    assert Path(argv[argv.index("--scenario") + 1]) == scenario
    launch_log = path["saves"].parent / "orbiter-session.log"
    shutil.copy2(launch_log, args.output / "simulator.log")
    assert "Production DeltaGlider flight." in launch_log.read_text(errors="replace")
    return scenario, 12


def windows(args, runtime, env):
    sys.path.insert(0, str(PACKAGE_TESTS))
    from windows import launchpad, mesa_files

    system = Path(os.environ["SYSTEMROOT"])
    env.update(PATH=os.pathsep.join([str(system / "System32"), str(system)]), QT_QPA_PLATFORM="windows")
    config = runtime / "Orbiter.cfg"
    assert FONT in config.read_text()
    with (args.output / "qt.log").open("wb") as log:
        launchpad(runtime / "orbiter-launchpad.exe", args.output, env, log)
    scenario = runtime / STOCK
    locked_scene(scenario)
    original = config.read_bytes()
    assert b"OGLClient" in original.split(b"ACTIVE_MODULES", 1)[1].split(b"END_MODULES", 1)[0].split()
    try:
        shutil.copy2(args.probe, runtime / "Modules/Plugin")
        (runtime / "ogl-evidence.enabled").touch()
        mesa_files(args.mesa, runtime)
        env.update(LIBGL_ALWAYS_SOFTWARE="true", GALLIUM_DRIVER="llvmpipe")
        name = str(Path(STOCK).relative_to("Scenarios").with_suffix(""))
        run([runtime / "Orbiter.exe", "--scenariox=" + name, "--plugin=LaunchpadFlightProbe", "--fixedstep=0.0625"], runtime, env, args.output / "simulator.log", 120)
    finally:
        for name in ("graphics-lifecycle.json", "Orbiter.log", "launchpad-flight.txt", "launchpad-flight-end.txt"):
            if (runtime / name).is_file():
                shutil.copy2(runtime / name, args.output)
    assert (args.output / "launchpad-flight-end.txt").read_text().strip() == "48"
    assert "focus=GL-01\nclass=DeltaGlider\n" in (args.output / "launchpad-flight.txt").read_text()
    return scenario, 48


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("install", "installer", "output", "probe", "mesa", "launchpad-driver"):
        parser.add_argument("--" + name, type=lambda value: Path(value).resolve(),
                            required=name in ("install", "installer", "output"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    assert not args.install.is_relative_to(ROOT)
    runtime = args.install / "runtime"
    receipt = json.loads((args.install / "stock-data-receipt.json").read_text())
    assert not any(path.name.casefold() == "architext.regular.ttf" for path in args.install.rglob("*"))
    verify = [sys.executable, "-B", args.installer, args.install, "--verify-only"]
    subprocess.run(verify, check=True, cwd=args.output)
    env = os.environ.copy()
    for name in ("QT_PLUGIN_PATH", "QT_QPA_PLATFORM_PLUGIN_PATH", "QT_QPA_PLATFORM", "LD_LIBRARY_PATH",
                 "LD_PRELOAD", "DYLD_LIBRARY_PATH", "DYLD_FRAMEWORK_PATH"):
        env.pop(name, None)
    env.update(QT_DEBUG_PLUGINS="1", XDG_CONFIG_HOME=str(args.output / "qt-settings"))
    scenario, frames = windows(args, runtime, env) if os.name == "nt" else native(args, runtime, env)
    lifecycle = json.loads((args.output / "graphics-lifecycle.json").read_text())
    assert lifecycle == dict(rendered_frames=frames, successful_presents=frames, context_deleted=True)
    subprocess.run(verify, check=True, cwd=args.output)
    result = dict(status="passed", installed_path=str(args.install), installer_sha256=digest(args.installer),
                  package=receipt["package"], package_source=receipt["package_source"],
                  package_sha256=receipt["package_sha256"], data_files=len(receipt["managed_files"]),
                  stock_scenario=STOCK, scenario_sha256=digest(scenario), lifecycle=lifecycle,
                  manuscript_font=receipt["manuscript_font"], full_runs_invoked=False,
                  windows_hands_on=False)
    (args.output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
