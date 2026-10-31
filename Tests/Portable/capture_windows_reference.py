#!/usr/bin/env python3
"""Capture candidate references from the ORIGINAL Windows application only.

Never installs or replaces a frozen reference. All outputs need review before
they can be used to unlock the portability refactor.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True
from trace_tools import compare, load_trace, require, validate_convergence, validate_orbit

UPSTREAM = "8e6ae437901417eef56f08b8f969ff92df83db5e"
PHYSICS_SOURCES = (
    "Src/Orbiter/Body.cpp", "Src/Orbiter/BodyIntegrator.cpp",
    "Src/Orbiter/Rigidbody.cpp", "Src/Orbiter/Element.cpp", "Src/Orbiter/Astro.h",
    "Src/Orbiter/Psys.cpp", "Src/Orbiter/Celbody.cpp", "Src/Orbiter/Star.cpp",
    "Src/Orbiter/Vessel.cpp", "Src/Orbiter/Vesselbase.cpp",
    "Src/Orbiter/Vesselstatus.cpp", "Src/Orbiter/TimeData.cpp", "Src/Orbiter/Vecmat.cpp",
)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def git(source, *args):
    return subprocess.check_output(["git", "-C", str(source), *args])


def source_manifest(source):
    require(not git(source, "status", "--porcelain", "--untracked-files=no").strip(),
            "capture requires a clean, committed source checkout")
    # The workflow downloads DXSDK into an untracked tool directory. Require
    # source additions to be committed without mistaking that tool for source.
    require(not git(source, "ls-files", "--others", "--exclude-standard", "--",
                    "Src", "Orbitersdk", "Tests", ".github").strip(),
            "capture requires all application, test and workflow sources to be committed")
    hashes = {}
    for name in PHYSICS_SOURCES:
        # Git's Windows checkout can legitimately use CRLF. Compare source
        # content after newline normalization, while recording actual file hashes.
        original = git(source, "show", f"{UPSTREAM}:{name}").replace(b"\r\n", b"\n")
        actual = (source / name).read_bytes().replace(b"\r\n", b"\n")
        require(actual == original, f"original physics changed before reference capture: {name}")
        hashes[name] = digest(source / name)
    return dict(commit=git(source, "rev-parse", "HEAD").decode().strip(),
                upstream_physics_commit=UPSTREAM, physics_sha256=hashes)


def stage_run(executable, fixture, directory, spin):
    directory.mkdir()
    # Copy only runtime binaries; never mutate an installed Orbiter or its config.
    for path in executable.parent.iterdir():
        if path.is_file() and path.suffix.lower() in (".exe", ".dll"):
            shutil.copy2(path, directory / path.name)
    for name in ("Scenarios", "Textures", "Textures2", "Meshes", "Modules/Startup",
                 "Modules/Plugin", "Images", "Config/PortableTwoBody/Marker"):
        (directory / name).mkdir(parents=True, exist_ok=True)
    shutil.copytree(fixture / "Config", directory / "Config", dirs_exist_ok=True)
    provider = executable.parent / "Modules/Celbody/PortableFixedPrimary.dll"
    require(provider.is_file(), "build with ORBITER_PORTABLE_REFERENCE_CAPTURE=ON first")
    (directory / "Modules/Celbody").mkdir(parents=True, exist_ok=True)
    shutil.copy2(provider, directory / "Modules/Celbody/PortableFixedPrimary.dll")
    with (directory / "Config/Primary.cfg").open("a", encoding="ascii") as primary:
        primary.write("\nModule = PortableFixedPrimary\n")
    shutil.copy2(fixture / "Orbiter.cfg", directory / "Orbiter.cfg")
    scenario = (fixture / "TwoBody.scn").read_text(encoding="ascii")
    if spin:
        # Scenario VROT uses degrees/second; trace uses radians/second.
        scenario = scenario.replace("VROT 0 0 0", f"VROT 0 0 {math.degrees(spin):.17g}")
    (directory / "Scenarios/TwoBody.scn").write_text(scenario, encoding="ascii")
    return directory / executable.name


def run_capture(executable, fixture, output, name, dt=1.0, steps=6000, spin=0.0):
    directory = output / name
    binary = stage_run(executable, fixture, directory, spin)
    inputs = {str(path.relative_to(directory)).replace("\\", "/"): digest(path)
              for path in directory.rglob("*") if path.is_file() and path.suffix in (".cfg", ".scn")}
    args = [str(binary), "--scenariox=TwoBody", f"--fixedstep={dt:.17g}",
            f"--maxframes={steps}", "--physics-trace=trace.csv",
            "--trace-vessel=Probe", "--trace-primary=Primary"]
    (directory / "invocation.json").write_text(
        json.dumps(dict(argv=args, input_sha256=inputs), indent=2), encoding="utf-8")
    with (directory / "console.txt").open("w", encoding="utf-8") as console:
        subprocess.run(args, cwd=directory, stdout=console, stderr=subprocess.STDOUT,
                       check=True, timeout=180)
    rows = load_trace(directory / "trace.csv", dt=dt, steps=steps)
    result = validate_orbit(rows, spin=spin)
    return rows, result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--orbiter", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--configuration", choices=("Debug", "Release"), required=True)
    args = parser.parse_args()
    require(sys.platform == "win32", "reference capture must execute the original app on Windows")
    source, executable, output = args.source.resolve(), args.orbiter.resolve(), args.output.resolve()
    require(executable.is_file(), "Windows Orbiter executable is missing")
    require(executable.name.lower() == "orbiter.exe", "capture requires the original Orbiter.exe")
    cache = executable.parent / "CMakeCache.txt"
    require(cache.is_file(), "capture requires the original application's CMakeCache.txt")
    require(f"CMAKE_BUILD_TYPE:STRING={args.configuration}" in cache.read_text(encoding="utf-8"),
            "requested configuration does not match the application's CMake build")
    require((executable.parent / "compiler.txt").is_file(),
            "record the MSVC compiler version in compiler.txt before capturing")
    metadata = source_manifest(source)
    metadata.update(configuration=args.configuration, platform=sys.platform,
                    executable_sha256=digest(executable), python=sys.version,
                    fixed_primary_provider_sha256=digest(executable.parent / "Modules/Celbody/PortableFixedPrimary.dll"),
                    github_run_id=os.environ.get("GITHUB_RUN_ID"),
                    github_repository=os.environ.get("GITHUB_REPOSITORY"),
                    status="capture_pending")
    output.mkdir(parents=True, exist_ok=False)
    fixture = source / "Tests/Portable/Fixtures"
    shutil.copytree(fixture, output / "inputs")
    for name in ("CMakeCache.txt", "build.log", "configure.log", "ctest.log"):
        if (executable.parent / name).is_file():
            shutil.copy2(executable.parent / name, output / name)
    # The caller supplies cl's actual version banner and environment flags.
    for name in ("compiler.txt", "build-metadata.txt"):
        if (executable.parent / name).is_file():
            shutil.copy2(executable.parent / name, output / name)
    metadata["fixture_sha256"] = {path.relative_to(fixture).as_posix(): digest(path)
                                  for path in fixture.rglob("*") if path.is_file()}
    report = output / "capture.json"
    report.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    try:
        first, first_result = run_capture(executable, fixture, output, "orbit")
        repeat, repeat_result = run_capture(executable, fixture, output, "orbit-repeat")
        require((output / "orbit/trace.csv").read_bytes() == (output / "orbit-repeat/trace.csv").read_bytes(),
                "original Windows orbit is not repeatable")
        fine, fine_result = run_capture(executable, fixture, output, "orbit-half", dt=.5, steps=12000)
        convergence = validate_convergence(first, fine)
        spin, spin_result = run_capture(executable, fixture, output, "spin", spin=1e-4)
        spin_repeat, _ = run_capture(executable, fixture, output, "spin-repeat", spin=1e-4)
        require((output / "spin/trace.csv").read_bytes() == (output / "spin-repeat/trace.csv").read_bytes(),
                "original Windows free-spin run is not repeatable")
        metadata.update(status="candidate_passed_requires_review",
                        results=dict(orbit=first_result, repeat=repeat_result, half_step=fine_result,
                                     convergence=convergence, spin=spin_result,
                                     repeat_comparison=compare(first, repeat),
                                     spin_repeat_comparison=compare(spin, spin_repeat)))
        print("Candidate Windows reference passed. Review and freeze it before physics extraction.")
    except Exception as error:
        metadata.update(status="failed", error=str(error))
        raise
    finally:
        report.write_text(json.dumps(metadata, indent=2, allow_nan=False), encoding="utf-8")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        raise SystemExit(str(error)) from error
