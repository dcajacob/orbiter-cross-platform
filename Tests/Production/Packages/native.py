"""Stage and smoke-test a relocatable native Orbiter package."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[3]
STOCK = "Scenarios/Delta-glider/DG Mk4 in orbit.scn"
FRAMES = 12


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def manifest(root):
    return {path.relative_to(root).as_posix(): digest(path)
            for path in sorted(root.rglob("*")) if path.is_file() and not path.is_symlink()}


def stage(args):
    root = args.destination
    root.mkdir()
    shutil.copy2(args.engine / "orbiter-production", root)
    libraries = sorted(args.engine.glob("liborbiter*.dylib" if sys.platform == "darwin" else "liborbiter*.so"))
    if len(libraries) != 3:
        raise RuntimeError(f"Expected three production libraries, got {libraries}")
    for library in libraries:
        shutil.copy2(library, root)
    shutil.copytree(args.engine / "NativeModules", root / "NativeModules", symlinks=True)
    shutil.copy2(ROOT / "LICENSE", root / "LICENSE")
    shutil.copy2(ROOT / "Sound/XRSound/LICENSE", root / "XRSound-LICENSE")
    shutil.copy2(ROOT / "Tests/Production/NativeScene/Orbiter.cfg", root / "Orbiter.cfg")
    shutil.copy2(ROOT / "Tests/Production/Flight/keymap-laptop.cfg", root / "Keymap.cfg")
    shutil.copy2(ROOT / "Tests/Production/Packages/README.md", root / "README.md")


def smoke(args):
    package = args.archive.resolve()
    args.output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="Orbiter clean install ") as directory:
        temp = Path(directory)
        work = temp / "Flight"
        work.mkdir()
        root = temp / "Install"
        root.mkdir()
        if sys.platform == "darwin":
            subprocess.run(["/usr/bin/tar", "-xzf", package, "-C", root], check=True)
        else:
            with tarfile.open(package) as archive:
                archive.extractall(root, filter="data")
        report = json.loads((root / "runtime.json").read_text())
        actual = manifest(root)
        del actual["runtime.json"]
        if report != {"source": args.source, "files": actual}:
            raise RuntimeError("Installed runtime contents differ from the manifest")
        for name in ("LD_LIBRARY_PATH", "LD_PRELOAD", "DYLD_LIBRARY_PATH", "DYLD_FRAMEWORK_PATH",
                     "QT_PLUGIN_PATH", "QT_QPA_PLATFORM_PLUGIN_PATH", "QT_QPA_PLATFORM"):
            os.environ.pop(name, None)
        launcher = root / ("orbiter-launchpad.app/Contents/MacOS/orbiter-launchpad"
                           if sys.platform == "darwin" else "bin/orbiter-launchpad")
        env = dict(os.environ, QT_DEBUG_PLUGINS="1", XDG_CONFIG_HOME=str(temp / "config"),
                   XDG_DATA_HOME=str(temp / "data"))
        with (args.output / "qt.log").open("wb") as log:
            subprocess.run([launcher, "--help"], cwd=work, env=env, check=True,
                           stdout=log, stderr=subprocess.STDOUT, timeout=30)
        scenario = args.assets / STOCK
        if digest(scenario) != digest(ROOT / STOCK):
            raise RuntimeError("Unchanged stock scenario required")
        config = work / "Orbiter.cfg"
        shutil.copy2(root / config.name, config)
        with (args.output / "flight.log").open("wb") as log:
            subprocess.run([root / "orbiter-production",
                            "--assets", args.assets, "--data", args.data,
                            "--modules", root / "NativeModules", "--planets", args.planets,
                            "--config", config, "--scenario", scenario,
                            "--evidence", args.output, "--frames", str(FRAMES)],
                           cwd=work, env=env, check=True, stdout=log,
                           stderr=subprocess.STDOUT, timeout=180)
        lifecycle = json.loads((args.output / "graphics-lifecycle.json").read_text())
        if lifecycle != dict(rendered_frames=FRAMES, successful_presents=FRAMES, context_deleted=True):
            raise RuntimeError(f"Incomplete packaged flight: {lifecycle}")
        log = (args.output / "flight.log").read_text(errors="replace")
        if "Production DeltaGlider flight." not in log:
            raise RuntimeError("Stock Delta-glider did not load")
        receipt = dict(source=args.source, archive=package.name, archive_sha256=digest(package),
                       installed_path=str(root), working_directory=str(work), scenario=STOCK,
                       scenario_sha256=digest(scenario), qt_started=True, lifecycle=lifecycle,
                       full_runs_invoked=False)
        (args.output / "clean-install.json").write_text(json.dumps(receipt, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("step", choices=("stage", "manifest", "verify"))
    for name in ("engine", "destination", "archive", "assets", "data", "planets", "output"):
        parser.add_argument("--" + name, type=lambda value: Path(value).resolve())
    parser.add_argument("--source")
    args = parser.parse_args()
    if args.step == "stage":
        stage(args)
    elif args.step == "manifest":
        files = manifest(args.destination)
        if "runtime.json" in files:
            raise RuntimeError("Generate the manifest on a fresh staging tree")
        (args.destination / "runtime.json").write_text(
            json.dumps(dict(source=args.source, files=files), indent=2) + "\n")
    else:
        smoke(args)


if __name__ == "__main__":
    main()
