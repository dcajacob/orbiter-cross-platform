#!/usr/bin/env python3
"""Synthetic inputs test the validator; they are never engine references."""
import csv
import math
from pathlib import Path
import sys
import tempfile
import unittest
import subprocess

sys.dont_write_bytecode = True
import trace_tools as trace
import capture_windows_reference as capture


def analytical_rows(dt=1.0, steps=6000, spin=0.0):
    rows = []
    n = math.sqrt(trace.MU / trace.RADIUS**3)
    for step in range(0, steps + 1, 10):
        t = step * dt
        rows.append((step, t, trace.EPOCH+t/86400,
                     trace.RADIUS*math.cos(n*t), 0, trace.RADIUS*math.sin(n*t),
                     -trace.SPEED*math.sin(n*t), 0, trace.SPEED*math.cos(n*t),
                     0, 0, math.sin(spin*t/2), math.cos(spin*t/2), 0, 0, spin))
    return rows


class TraceValidation(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "synthetic.csv"
        self.rows = analytical_rows()

    def write(self, rows=None, fields=trace.FIELDS):
        with self.path.open("w", newline="", encoding="ascii") as stream:
            writer = csv.writer(stream)
            writer.writerow(fields)
            writer.writerows(self.rows if rows is None else rows)
        return self.path

    def bad_cell(self, column, value):
        rows = list(self.rows)
        row = list(rows[10])
        row[column] = value
        rows[10] = row
        return rows

    def test_complete_analytical_trace(self):
        rows = trace.load_trace(self.write())
        self.assertEqual(len(rows), 601)
        trace.validate_orbit(rows)
        trace.compare(rows, rows)

    def test_sample_count(self):
        for rows in (self.rows[:-1], self.rows[1:], self.rows + [self.rows[-1]]):
            with self.subTest(rows=len(rows)), self.assertRaises(ValueError):
                trace.load_trace(self.write(rows))

    def test_wrong_header(self):
        with self.assertRaises(ValueError):
            trace.load_trace(self.write(fields=list(reversed(trace.FIELDS))))

    def test_bad_sampling_and_time(self):
        for column, value in ((0, 99), (1, 100.001), (2, trace.EPOCH)):
            with self.subTest(column=column), self.assertRaises(ValueError):
                trace.load_trace(self.write(self.bad_cell(column, value)))

    def test_missing_and_extra_fields(self):
        for row in (self.rows[10][:-1], (*self.rows[10], 9)):
            rows = list(self.rows)
            rows[10] = row
            with self.assertRaises(ValueError):
                trace.load_trace(self.write(rows))

    def test_nonfinite_every_numeric_field(self):
        for column in range(1, 16):
            for value in (math.nan, math.inf, -math.inf):
                with self.subTest(column=column, value=value), self.assertRaises(ValueError):
                    trace.load_trace(self.write(self.bad_cell(column, value)))

    def test_bad_quaternions(self):
        for value in (0.0, 2.0):
            with self.assertRaises(ValueError):
                trace.load_trace(self.write(self.bad_cell(12, value)))

    def test_sign_independent_quaternion_comparison(self):
        negated = [(*r[:9], *[-q for q in r[9:13]], *r[13:]) for r in self.rows]
        trace.compare(self.rows, negated)

    def test_tiny_rotation_error_detected(self):
        # acos(dot) rounds this angle to zero on ordinary double precision.
        angle = 2e-8
        row = self.rows[10]
        rotated = (*row[:9], math.sin(angle/2), 0, 0, math.cos(angle/2), *row[13:])
        candidate = list(self.rows)
        candidate[10] = rotated
        with self.assertRaises(ValueError):
            trace.compare(self.rows, candidate)

    def test_each_comparison_budget(self):
        for column, delta in ((3, .02), (6, 2e-5), (13, 2e-10), (2, 2e-10)):
            with self.subTest(column=column), self.assertRaises(ValueError):
                trace.compare(self.rows, self.bad_cell(column, self.rows[10][column]+delta))

    def test_combined_vector_error(self):
        candidate = list(self.rows)
        row = list(candidate[10])
        for index in (3, 4, 5):
            row[index] += .008
        candidate[10] = row
        with self.assertRaises(ValueError):
            trace.compare(self.rows, candidate)

    def test_analytical_position_failure(self):
        with self.assertRaises(ValueError):
            trace.validate_orbit(self.bad_cell(3, self.rows[10][3]+1))

    def test_free_spin_and_half_step(self):
        trace.validate_orbit(analytical_rows(spin=1e-4), spin=1e-4)
        fine = analytical_rows(dt=.5, steps=12000)
        trace.validate_convergence(self.rows, fine)
        with self.assertRaises(ValueError):
            trace.validate_convergence(self.rows, analytical_rows(dt=.5))

    def test_invalid_run_parameters(self):
        for dt in (0, -1, math.inf, math.nan):
            with self.assertRaises(ValueError):
                trace.load_trace(self.write(), dt=dt)
        with self.assertRaises(ValueError):
            trace.load_trace(self.write(), steps=6001)

    def test_fixture_initial_conditions(self):
        fixture = Path(__file__).parent / "Fixtures"
        text = (fixture / "TwoBody.scn").read_text()
        self.assertIn("Date MJD 51544.5", text)
        self.assertIn("RPOS 7000000 0 0", text)
        speed = float(next(line.split()[-1] for line in text.splitlines() if "RVEL" in line))
        self.assertEqual(speed, trace.SPEED)
        primary = (fixture / "Config/Primary.cfg").read_text()
        mass = float(next(line.split("=")[1] for line in primary.splitlines() if line.startswith("Mass")))
        self.assertEqual(mass, trace.MASS)
        astro = (fixture.parents[2] / "Src/Orbiter/AstroMath.h").read_text()
        self.assertIn("Ggrav = 6.67259e-11", astro)

    def test_reference_staging_preserves_installation(self):
        installed = Path(self.tmp.name) / "installation"
        installed.mkdir()
        executable = installed / "Orbiter.exe"
        executable.write_bytes(b"synthetic test placeholder, not an engine")
        provider = installed / "Modules/Celbody/PortableFixedPrimary.dll"
        provider.parent.mkdir(parents=True)
        provider.write_bytes(b"synthetic provider placeholder")
        startup = installed / "Modules/Startup/unwanted.dll"
        startup.parent.mkdir()
        startup.write_bytes(b"must not preload installed startup plugins")
        (installed / "Orbiter.cfg").write_text("existing user settings")
        fixture = Path(__file__).parent / "Fixtures"
        original = (fixture / "TwoBody.scn").read_bytes()
        staged = Path(self.tmp.name) / "staged"
        capture.stage_run(executable, fixture, staged, spin=1e-4)
        self.assertEqual((installed / "Orbiter.cfg").read_text(), "existing user settings")
        self.assertEqual((fixture / "TwoBody.scn").read_bytes(), original)
        self.assertFalse((staged / "Modules/Startup/unwanted.dll").exists())
        self.assertEqual((staged / "Modules/Celbody/PortableFixedPrimary.dll").read_bytes(),
                         provider.read_bytes())
        self.assertIn("Module = PortableFixedPrimary", (staged / "Config/Primary.cfg").read_text())
        self.assertIn(f"VROT 0 0 {math.degrees(1e-4):.17g}",
                      (staged / "Scenarios/TwoBody.scn").read_text())
        with self.assertRaises(FileExistsError):
            capture.stage_run(executable, fixture, staged, spin=0)

    @unittest.skipIf(sys.platform == "win32", "non-Windows guard")
    def test_linux_cannot_create_windows_reference(self):
        script = Path(__file__).parent / "capture_windows_reference.py"
        output = Path(self.tmp.name) / "must-not-exist"
        result = subprocess.run([sys.executable, "-B", str(script), "--source", ".",
                                 "--orbiter", "Orbiter.exe", "--output", str(output),
                                 "--configuration", "Release"], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must execute the original app on Windows", result.stderr)
        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
