#!/usr/bin/env python3
"""Run the real OpenGL client and verify physics, controls and rendered geometry."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import zlib

sys.dont_write_bytecode = True
from trace_tools import load_trace, compare, validate_orbit, require


def image(path, camera):
    parts = path.read_bytes().split(b"\n", 3)
    require(parts[0] == b"P6" and parts[2] == b"255", "invalid screenshot header")
    width, height = map(int, parts[1].split())
    pixels = parts[3]
    require(width >= 640 and height >= 360 and len(pixels) == width * height * 3,
            "incorrect screenshot dimensions")
    # Exclude the telemetry and controls. Require actual scene geometry, rather
    # than accepting a clear framebuffer with a functioning HUD.
    colors = [pixels[(y*width+x)*3:(y*width+x)*3+3]
              for y in range(175, height-60) for x in range(width)]
    blue = sum(b > 20 and g > 10 and b > r*1.5 and b > g for r,g,b in colors)
    gold = sum(r > 150 and 80 < g < 180 and b < 80 for r,g,b in colors)
    white = sum(min(r,g,b) > 170 for r,g,b in colors)
    require(blue > 10000, "primary geometry is absent")
    if camera == "follow":
        require(gold > 100 and white > 100, "vessel faces/wings are absent")
    def chunk(kind, data):
        return struct.pack(">I",len(data))+kind+data+struct.pack(">I",zlib.crc32(kind+data))
    png = (b"\x89PNG\r\n\x1a\n" +
           chunk(b"IHDR",struct.pack(">IIBBBBB",width,height,8,2,0,0,0)) +
           chunk(b"IDAT",zlib.compress(b"".join(b"\0"+pixels[y*width*3:(y+1)*width*3]
                                               for y in range(height)))) + chunk(b"IEND",b""))
    path.with_suffix(".png").write_bytes(png)
    return dict(width=width,height=height,primary_pixels=blue,vessel_gold_pixels=gold,
                vessel_white_pixels=white,png_sha256=hashlib.sha256(png).hexdigest())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary",type=Path,required=True)
    parser.add_argument("--headless",type=Path,required=True)
    parser.add_argument("--fixture",type=Path,required=True)
    parser.add_argument("--reference",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--backend",choices=("auto","x11","wayland"),default="x11")
    args = parser.parse_args()
    binary, headless = args.binary.resolve(),args.headless.resolve()
    fixture, reference, output = args.fixture.resolve(),args.reference.resolve(),args.output.resolve()
    output.mkdir(parents=True,exist_ok=True)
    reports = {}
    with tempfile.TemporaryDirectory() as temporary:
        cwd = Path(temporary)
        def invoke(command, success=True):
            result = subprocess.run(list(map(str,command)),cwd=cwd,capture_output=True,text=True,timeout=90)
            require((result.returncode == 0) == success, result.stdout+result.stderr)
            if not success:
                require("orbiter-native:" in result.stderr,"failure did not report a client error: "+result.stderr)
            return result
        expected = output/"headless.csv"
        invoke([headless,"--scenario",fixture/"TwoBody.scn","--trace",expected])
        for name, camera, scripted in (("overview","overview",False),
                                       ("overview-repeat","overview",False),
                                       ("controls-follow","overview",True)):
            trace, ppm, report = [output/(name+suffix) for suffix in (".csv",".ppm",".json")]
            command = [binary,"--scenario",fixture/"TwoBody.scn","--smoke-test","--hidden",
                       "--backend",args.backend,"--camera",camera,"--trace",trace,
                       "--screenshot",ppm,"--report",report]
            if scripted:
                script = cwd/"controls.txt"
                script.write_text("0 pause\n1 step\n2 camera\n3 orbit 0.12 -0.08\n"
                                  "4 zoom 1\n5 resize 960 600\n6 reset\n7 resume\n")
                command += ["--input-script",script]
            result = invoke(command)
            data = json.loads(report.read_text())
            require(data["steps"] == 6000 and data["gl_error"] == 0, "incomplete graphics run")
            require(data["script_events"] == (8 if scripted else 0), "input script was not executed")
            candidate = trace
            if scripted:
                require([r[0] for r in load_trace(trace,steps=1)] == [0,1], "reset lost preceding trace segment")
                candidate = trace.with_name(trace.stem+".run-2.csv")
            require(candidate.read_bytes() == expected.read_bytes(), "frontend changed headless numerical trace")
            rows = load_trace(candidate)
            metrics = compare(load_trace(reference/"Orbit.csv"),rows)
            reports[name] = dict(runtime=data,comparison=metrics,analytical=validate_orbit(rows),
                                 image=image(ppm,"follow" if scripted else camera),console=result.stdout)
        require((output/"overview.csv").read_bytes() == (output/"overview-repeat.csv").read_bytes(),
                "graphical run is not repeatable")

        # Finite-spin rendering also verifies that reading/interpolating attitude
        # never modifies the finalized quaternion used for the trace.
        spin = cwd/"spin"
        shutil.copytree(fixture,spin)
        scenario = spin/"TwoBody.scn"
        import math
        scenario.write_text(scenario.read_text().replace("VROT 0 0 0",f"VROT 0 0 {math.degrees(1e-4):.17g}"))
        spin_trace = output/"spin.csv"
        invoke([binary,"--scenario",spin,"--smoke-test"],success=False)  # directory, not scenario file
        invoke([binary,"--scenario",scenario,"--smoke-test","--hidden","--backend",args.backend,
                "--trace",spin_trace,"--camera","follow","--screenshot",output/"spin.ppm"])
        reports["spin"] = dict(comparison=compare(load_trace(reference/"Spin.csv"),load_trace(spin_trace)),
                               analytical=validate_orbit(load_trace(spin_trace),spin=1e-4),
                               image=image(output/"spin.ppm","follow"))

        for extra in (("--fixed-step","0"),("--steps","-1"),("--backend","invalid"),
                      ("--trace",fixture/"TwoBody.scn"),("--unknown","x")):
            invoke([binary,"--scenario",fixture/"TwoBody.scn",*extra],success=False)
        invoke([binary,"--scenario",fixture/"TwoBody.scn","--smoke-test","--hidden",
                "--backend",args.backend,"--steps","1","--screenshot",cwd/"absent/frame.ppm"],success=False)
        bad_script = cwd/"bad.txt"
        bad_script.write_text("0 unsupported\n")
        invoke([binary,"--scenario",fixture/"TwoBody.scn","--smoke-test","--hidden",
                "--backend",args.backend,"--input-script",bad_script],success=False)
    (output/"verification.json").write_text(json.dumps(reports,indent=2,allow_nan=False)+"\n")
    print(json.dumps(reports,indent=2,allow_nan=False))


if __name__ == "__main__":
    try:
        main()
    except (ValueError,OSError,subprocess.SubprocessError) as error:
        raise SystemExit(str(error)) from error
