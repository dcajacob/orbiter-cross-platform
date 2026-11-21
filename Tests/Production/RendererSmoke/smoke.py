"""Run the 48-frame Win32/WGL smoke and exercise a missing shader in this isolated installation."""
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

parser = argparse.ArgumentParser()
for name in ("run", "output", "data", "planets", "mesa", "source-root"):
    parser.add_argument("--" + name, required=True, type=lambda path: Path(path).resolve())
args = parser.parse_args()
if sys.platform != "win32":
    parser.error("Windows is required")
run = args.run
output = args.output
output.mkdir(parents=True, exist_ok=True)
if any(output.iterdir()):
    parser.error("Choose an empty evidence directory")
prod = args.source_root / "Tests/Production"
sys.path[:0] = [str(prod / "Client"), str(prod)]
from run_client import mesa_files


def sha(path):
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def put_json(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def provision(source, lock, skip=()):
    records = json.loads((prod / lock).read_text())["data_files"]
    for name, record in records.items():
        if name in skip:
            continue
        item = source / name
        require(item.stat().st_size == record["bytes"] and sha(item) == record["sha256"],
                f"Locked stock file differs: {name}")
        dest = run / name
        if dest.is_file() and sha(dest) == record["sha256"]:
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        # This is the disposable extracted app. Break any prior hardlink before adding the locked file.
        dest.unlink(missing_ok=True)
        try:
            os.link(item, dest)
        except OSError:
            shutil.copyfile(item, dest)


def fly(case, env):
    folder = output / case
    folder.mkdir()
    always = ("Orbiter.log", "renderer-info.json", "graphics-lifecycle.json", "visual-events.csv",
              "graphics-errors.txt", "graphics-failure.txt", "launchpad-flight.txt", "launchpad-flight-end.txt")
    for name in always:
        (run / name).unlink(missing_ok=True)
    exe = run / "Orbiter.exe"
    with (folder / "console.log").open("wb") as log:
        result = subprocess.run([str(exe), r"--scenariox=Delta-glider\DG Mk4 in orbit"],
                                cwd=run, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=120)
    for name in always:
        if (run / name).is_file():
            shutil.copyfile(run / name, folder / name)
    life = json.loads((folder / "graphics-lifecycle.json").read_text())
    info = json.loads((folder / "renderer-info.json").read_text())
    require("llvmpipe" in info["renderer"].casefold(), f"Unexpected renderer: {info}")
    expected = 48 if case == "positive" else 0
    require(life == dict(rendered_frames=expected, successful_presents=expected, context_deleted=True),
            f"Wrong {case} renderer lifecycle: {life}")
    logtext = (folder / "Orbiter.log").read_text(errors="replace")
    require("xrsound.dll" not in logtext.casefold(), "XRSound was active")
    if case == "positive":
        require(result.returncode == 0, f"Stock flight exited {result.returncode}")
        flight = (folder/"launchpad-flight.txt").read_text()
        require("focus=GL-01\nclass=DeltaGlider\n" in flight and "close-requested=1" in flight
                and (folder/"launchpad-flight-end.txt").read_text().strip() == "48",
                "Stock flight failed to reach the automatic 48-frame exit")
        errors = folder / "graphics-errors.txt"
        require(not errors.exists() or not errors.read_text(errors="replace").strip(), "OpenGL errors")
    else:
        diagnostics = (logtext + (folder/"console.log").read_text(errors="replace")).casefold()
        require("overlay.vs" in diagnostics and any(word in diagnostics for word in ("missing","could not","unable","cannot","failed","not found")),
                "Expected missing shader diagnostic is absent")
        require("launchpad-flight-end.txt" not in [p.name for p in folder.iterdir()],
                "Faulted renderer unexpectedly ran the flight")
        require(result.returncode in (0, 1), f"Process aborted or crashed: {result.returncode:#x}")
    return dict(exit_code=result.returncode, lifecycle=life, renderer=info)


scenario = Path("Scenarios/Delta-glider/DG Mk4 in orbit.scn")
# These are the exact Git-blob LF and attested Windows-package CRLF files.
stock_hashes = {"fc76ff6089ef242c2f92c680192748e95175483f8eb33832e50b83cf0dda6155",
                "0b3db48473487602eb14e19b60da98fd5b22dd744f1c53db13f666334edbbb43"}
require(sha(run / scenario) in stock_hashes and sha(args.source_root / scenario) in stock_hashes,
        "Wrong stock Delta-glider scenario")
exe = run / "Orbiter.exe"
dll = run / "Modules/Plugin/OGLClient.dll"
probe = run / "Modules/Plugin/LaunchpadFlightProbe.dll"
# Upstream data provisioner excludes its restricted font; the smoke can use an already-installed font
# or the production test font staged into the ephemeral stock data directory.
skips = ["LICENSE"]
if not (args.data / "Fonts/architext.regular.ttf").is_file():
    skips.append("Fonts/architext.regular.ttf")
provision(args.data, "stock-data.lock.json", skips)
provision(args.planets, "standard-planets.lock.json")
mesa_files(args.mesa, run)
config = (prod / "Fixtures/Orbiter.cfg").read_text()
require(config.count("  ProductionReferenceDriver") == config.count("FixedStep = 1\n") == 1, "Fixture changed")
config = config.replace("  ProductionReferenceDriver", "  LaunchpadFlightProbe\n  OGLClient")
config = config.replace("FixedStep = 1\n", "FixedStep = 0.0625\n")
config = config.replace("ACTIVE_MODULES", "SurfMarkers = 33\nACTIVE_MODULES", 1)
(run / "Orbiter.cfg").unlink(missing_ok=True)
(run / "Orbiter.cfg").write_text(config, encoding="ascii")
(run / "ogl-evidence.enabled").touch()
env = os.environ.copy()
env.update(LIBGL_ALWAYS_SOFTWARE="true", GALLIUM_DRIVER="llvmpipe", LP_NUM_THREADS="2", SDL_AUDIODRIVER="dummy")
ctypes.windll.kernel32.SetErrorMode(0x8003)  # suppress the OS crash/error popups in unattended tests
report = dict(exe_sha256=sha(exe), renderer_sha256=sha(dll), probe_sha256=sha(probe),
              scenario_sha256=sha(run / scenario), active_modules=["LaunchpadFlightProbe","OGLClient"],
              full_runs=False, physical_input=False)
put_json(output/"results.json", report)
failures = []
shader = run / "Modules/OGLClient/Overlay.vs"
backup = shader.with_name("Overlay.vs.smoke-hidden")
for case in ("positive", "missing-overlay"):
    try:
        if case == "missing-overlay":
            require(not backup.exists(), "Shader backup already exists")
            shader.rename(backup)
        report[case] = {**fly(case, env), "status":"passed"}
    except Exception as error:
        failures.append(case)
        report[case] = {"status":"failed", "detail":str(error)}
        # Preserve final host diagnostics when an exception occurred before normal collection.
        for name in ("Orbiter.log","renderer-info.json","graphics-lifecycle.json","graphics-errors.txt"):
            if (output / case).is_dir() and (run / name).is_file():
                shutil.copyfile(run / name, output / case / name)
    finally:
        if case == "missing-overlay" and backup.exists() and not shader.exists():
            backup.rename(shader)
        put_json(output/"results.json", report)
print(json.dumps(report, indent=2))
sys.exit(bool(failures))

