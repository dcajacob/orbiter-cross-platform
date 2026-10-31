#!/usr/bin/env python3
"""Integration checks against the frozen original Windows engine traces."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
from trace_tools import load_trace, compare, validate_orbit, validate_convergence

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--binary", type=Path, required=True)
parser.add_argument("--source", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("--suite", choices=("parity","errors"), required=True)
args = parser.parse_args()
BINARY, SOURCE, OUTPUT = args.binary.resolve(), args.source.resolve(), args.output.resolve()


class Runner(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def bundle(self):
        bundle = self.root / "bundle"
        shutil.copytree(SOURCE / "Fixtures", bundle)
        return bundle

    def invoke(self, *options, success=True):
        env = dict(os.environ)
        env.pop("DISPLAY", None)
        env.pop("WAYLAND_DISPLAY", None)
        result = subprocess.run([str(BINARY), *map(str,options)], cwd=self.root,
                                env=env, capture_output=True, text=True, timeout=30)
        if success:
            self.assertEqual(result.returncode, 0, result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout)
            self.assertIn("orbiter-headless:", result.stderr)
        return result

    def run_bundle(self, bundle, trace=None, *extra, success=True):
        return self.invoke("--scenario", bundle / "TwoBody.scn", "--trace",
                           trace or self.root / "trace.csv", *extra, success=success)


class Parity(Runner):
    def test_frozen_reference_and_repeats(self):
        OUTPUT.mkdir(parents=True, exist_ok=True)
        reference = SOURCE / "Reference"
        provenance = json.loads((reference / "provenance.json").read_text())
        self.assertEqual(provenance["status"], "accepted")
        for name, digest in provenance["traces"].items():
            self.assertEqual(hashlib.sha256((reference / name).read_bytes()).hexdigest(), digest)
        report = dict(binary=str(BINARY), reference_commit=provenance["capture_commit"], cases={})
        for name, dt, steps, spin, frozen in (
                ("orbit",1,6000,0,"Orbit.csv"),
                ("orbit-half",.5,12000,0,"Orbit.HalfStep.csv"),
                ("spin",1,6000,1e-4,"Spin.csv")):
            bundle = self.root / name
            shutil.copytree(SOURCE / "Fixtures", bundle)
            if spin:
                path = bundle / "TwoBody.scn"
                path.write_text(path.read_text().replace("VROT 0 0 0", f"VROT 0 0 {math.degrees(spin):.17g}"))
            trace = OUTPUT / (name+".csv")
            self.run_bundle(bundle, trace, "--fixed-step", dt, "--steps", steps)
            rows = load_trace(trace,dt=dt,steps=steps)
            result = dict(analytical=validate_orbit(rows,spin=spin),
                          reference=compare(load_trace(reference/frozen,dt=dt,steps=steps),rows))
            if name != "orbit-half":
                repeat = OUTPUT / (name+"-repeat.csv")
                self.run_bundle(bundle, repeat, "--fixed-step", dt, "--steps", steps)
                self.assertEqual(trace.read_bytes(), repeat.read_bytes(), f"{name} is not repeatable")
            report["cases"][name] = result
        report["convergence"] = validate_convergence(load_trace(OUTPUT/"orbit.csv"),
                                                     load_trace(OUTPUT/"orbit-half.csv",dt=.5,steps=12000))
        (OUTPUT / "parity.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
        print(json.dumps(report,indent=2))


class Errors(Runner):
    def test_help(self):
        self.assertIn("--scenario", self.invoke("--help").stdout)

    def test_invalid_arguments(self):
        for options in ([], ["--unknown", "x"], ["--scenario"],
                        ["--steps", "-1"], ["--steps", "1.5"], ["--trace", ""],
                        ["--scenario", "one", "--scenario", "two"]):
            with self.subTest(options=options): self.invoke(*options, success=False)

    def test_invalid_steps(self):
        bundle = self.bundle()
        for value in ("-1","0","1.5","x","18446744073709551616"):
            with self.subTest(value=value):
                self.run_bundle(bundle,None,"--steps",value,success=False)

    def test_invalid_step_length(self):
        bundle = self.bundle()
        for value in ("0","-1","nan","inf","1junk","1e-320"):
            with self.subTest(value=value):
                self.run_bundle(bundle,None,"--fixed-step",value,success=False)

    def test_missing_assets(self):
        bundle = self.bundle()
        (bundle/"Config/Primary.cfg").unlink()
        self.run_bundle(bundle,success=False)
        self.assertFalse((self.root/"trace.csv").exists())

    def test_unsupported_force_and_propagator(self):
        bundle = self.bundle()
        path = bundle/"Orbiter.cfg"
        original = path.read_text()
        for old,new in (("RadiationPressure = FALSE","RadiationPressure = TRUE"),
                        ("StabiliseOrbits = FALSE","StabiliseOrbits = TRUE"),
                        ("PropStage0 = 1 1 1","PropStage0 = 0 1 1"),
                        ("PropSubsampling = 1","PropSubsampling = 2")):
            path.write_text(original.replace(old,new))
            with self.subTest(feature=new): self.run_bundle(bundle,success=False)

    def test_unsupported_vessel_module_and_thrusters(self):
        bundle = self.bundle()
        config = bundle/"Config/Vessels/PortableProbe.cfg"
        config.write_text(config.read_text()+"\nModule = CustomVessel\n")
        self.run_bundle(bundle,success=False)

    def test_unsupported_scenario_fields(self):
        bundle = self.bundle()
        path = bundle/"TwoBody.scn"
        original = path.read_text()
        for old,new in (("STATUS Orbiting Primary","STATUS Landed Primary"),
                        ("  AROT 0 0 0","  THLEVEL 0:1"),
                        ("END_SHIPS","Another:PortableProbe\nEND\nEND_SHIPS"),
                        ("END_ENVIRONMENT","Script Other\nEND_ENVIRONMENT")):
            path.write_text(original.replace(old,new))
            with self.subTest(field=new): self.run_bundle(bundle,success=False)

    def test_nonfinite_and_malformed_inputs(self):
        bundle = self.bundle()
        path = bundle/"TwoBody.scn"
        original = path.read_text()
        for value in ("nan 0 0","inf 0 0","1e308 0 0","7000000 0","7000000x 0 0"):
            path.write_text(original.replace("7000000 0 0",value))
            with self.subTest(value=value): self.run_bundle(bundle,success=False)

    def test_duplicate_fields(self):
        bundle = self.bundle()
        config = bundle/"Config/Primary.cfg"
        config.write_text(config.read_text()+"\nMass = 1\n")
        self.run_bundle(bundle,success=False)

    def test_input_overwrite_protection(self):
        bundle = self.bundle()
        for path in (bundle/"TwoBody.scn",bundle/"Orbiter.cfg",bundle/"Config/Primary.cfg"):
            original = path.read_bytes()
            self.run_bundle(bundle,path,success=False)
            self.assertEqual(path.read_bytes(),original)

    def test_trace_io_failures(self):
        bundle = self.bundle()
        self.run_bundle(bundle,self.root/"absent/trace.csv",success=False)
        self.run_bundle(bundle,self.root,success=False)
        if sys.platform != "win32" and Path("/dev/full").exists():
            self.run_bundle(bundle,Path("/dev/full"),success=False)

    def test_surface_contact_rejected(self):
        bundle = self.bundle()
        path = bundle/"TwoBody.scn"
        path.write_text(path.read_text().replace("0 0 7544.9801173646956","-1000000 0 0"))
        result = self.run_bundle(bundle,None,"--steps",1,success=False)
        self.assertIn("surface contact",result.stderr)

    def test_final_partial_sampling_interval(self):
        bundle = self.bundle()
        self.run_bundle(bundle,None,"--steps",11)
        rows = load_trace(self.root/"trace.csv",steps=11)
        self.assertEqual([row[0] for row in rows],[0,10,11])

    def test_windows_line_endings(self):
        bundle = self.bundle()
        for path in bundle.rglob("*"):
            if path.is_file():
                path.write_bytes(path.read_bytes().replace(b"\r\n",b"\n").replace(b"\n",b"\r\n"))
        self.run_bundle(bundle,None,"--steps",10)

    def test_case_insensitive_fields_and_comments(self):
        bundle = self.bundle()
        path = bundle/"TwoBody.scn"
        text = path.read_text().replace("BEGIN_","begin_").replace("END_","end_").replace("RPOS","rpos")
        path.write_text("; comment\n\n"+text.replace("7000000 0 0","7000000 0 0 ; initial position"))
        self.run_bundle(bundle,None,"--steps",10)


suite = unittest.defaultTestLoader.loadTestsFromTestCase(Parity if args.suite == "parity" else Errors)
result = unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
