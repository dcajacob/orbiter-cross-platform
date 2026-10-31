#!/usr/bin/env python3
"""Verify the current Windows application against the immutable original traces.

This does not create, refresh, or replace a baseline.
"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True
from capture_windows_reference import digest, git, run_capture
from trace_tools import compare, load_trace, require, validate_convergence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--orbiter", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--configuration", choices=("Debug","Release"), required=True)
    args = parser.parse_args()
    require(sys.platform == "win32", "application verification requires native Windows")
    source, executable, output = args.source.resolve(), args.orbiter.resolve(), args.output.resolve()
    require(executable.is_file() and executable.name.lower() == "orbiter.exe", "Orbiter.exe is missing")
    require(not git(source,"status","--porcelain","--untracked-files=no").strip(),
            "application verification requires a clean committed checkout")
    reference = source / "Tests/Portable/Reference"
    provenance = json.loads((reference/"provenance.json").read_text())
    require(provenance["status"] == "accepted", "frozen original reference is missing")
    for name, expected in provenance["traces"].items():
        require(digest(reference/name) == expected, "frozen reference digest changed: " + name)
    output.mkdir(parents=True, exist_ok=False)
    for name in ("CMakeCache.txt","compiler.txt","build-metadata.txt","configure.log","build.log","ctest.log"):
        path = executable.parent/name
        require(path.is_file(), "build evidence is missing: " + name)
        shutil.copy2(path,output/name)
    report = dict(status="pending",commit=git(source,"rev-parse","HEAD").decode().strip(),
                  configuration=args.configuration,binary_sha256=digest(executable),
                  reference_commit=provenance["capture_commit"],cases={})
    try:
        results = {}
        for name,dt,steps,spin,frozen in (("orbit",1,6000,0,"Orbit.csv"),
                ("orbit-half",.5,12000,0,"Orbit.HalfStep.csv"),("spin",1,6000,1e-4,"Spin.csv")):
            rows,analytical = run_capture(executable,source/"Tests/Portable/Fixtures",output,name,dt,steps,spin)
            report["cases"][name] = dict(analytical=analytical,
                reference=compare(load_trace(reference/frozen,dt=dt,steps=steps),rows))
            results[name] = rows
            if name != "orbit-half":
                run_capture(executable,source/"Tests/Portable/Fixtures",output,name+"-repeat",dt,steps,spin)
                require((output/name/"trace.csv").read_bytes() == (output/(name+"-repeat")/"trace.csv").read_bytes(),
                        "current Windows application is not repeatable: " + name)
        report["convergence"] = validate_convergence(results["orbit"],results["orbit-half"])
        report["status"] = "passed"
        print(json.dumps(report,indent=2,allow_nan=False))
    except Exception as error:
        report.update(status="failed",error=str(error))
        raise
    finally:
        (output/"application-verification.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")


if __name__ == "__main__":
    try:
        main()
    except (ValueError,OSError,subprocess.SubprocessError) as error:
        raise SystemExit(str(error)) from error
