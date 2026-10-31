#!/usr/bin/env python3
"""Inspect real engine traces. This module does not propagate simulation state."""
import argparse
import csv
import json
import math
from pathlib import Path

FIELDS = "step sim_seconds mjd rx ry rz vx vy vz qx qy qz qw wx wy wz".split()
# Same historical constant as Astro.h; do not substitute a newer physical value.
G = 6.67259e-11
MASS = 5.972e24
MU = G * MASS
RADIUS = 7_000_000.0
EPOCH = 51544.5
SPEED = math.sqrt(MU / RADIUS)
LIMITS = dict(position_m=0.01, velocity_m_s=1e-5, orientation_rad=1e-8,
              angular_velocity_rad_s=1e-10, mjd_days=1e-10)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def norm(values):
    return math.sqrt(sum(x * x for x in values))


def distance(a, b):
    return norm([x - y for x, y in zip(a, b)])


def cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def quaternion_angle(a, b):
    # Chord lengths stay accurate near zero, unlike acos(dot). q and -q are
    # the same rotation. Normalize only after load_trace verifies unit length.
    a = [x / norm(a) for x in a]
    b = [x / norm(b) for x in b]
    minus = distance(a, b)
    plus = norm([x + y for x, y in zip(a, b)])
    return 4 * math.atan2(min(minus, plus), max(minus, plus))


def load_trace(path, *, dt=1.0, steps=6000):
    require(math.isfinite(dt) and dt > 0, "dt must be finite and positive")
    require(steps > 0, "steps must be positive")
    expected_steps = list(range(0, steps + 1, 10))
    if expected_steps[-1] != steps:
        expected_steps.append(steps)
    with Path(path).open(newline="", encoding="ascii") as stream:
        reader = csv.DictReader(stream)
        require(reader.fieldnames == FIELDS, "unexpected trace header")
        rows = []
        for index, row in enumerate(reader):
            require(set(row) == set(FIELDS) and None not in row.values(), "malformed CSV row")
            step = int(row["step"])
            values = [float(row[key]) for key in FIELDS[1:]]
            require(all(math.isfinite(x) for x in values), f"nonfinite row {index}")
            require(index < len(expected_steps) and step == expected_steps[index],
                    f"missing, duplicate or reordered step at row {index}")
            require(values[0] == step * dt, f"incorrect elapsed time at step {step}")
            require(abs(values[1] - (EPOCH + step * dt / 86400)) <= LIMITS["mjd_days"],
                    f"incorrect MJD at step {step}")
            require(abs(norm(values[8:12]) - 1) <= 1e-12,
                    f"non-unit quaternion at step {step}")
            rows.append((step, *values))
        require(len(rows) == len(expected_steps), "incorrect trace sample count")
    return rows


def compare(reference, candidate):
    require(len(reference) == len(candidate), "trace lengths differ")
    maxima = dict.fromkeys(LIMITS, 0.0)
    for ref, got in zip(reference, candidate):
        require(ref[:2] == got[:2], "step or simulation time differs")
        errors = dict(position_m=distance(ref[3:6], got[3:6]),
                      velocity_m_s=distance(ref[6:9], got[6:9]),
                      orientation_rad=quaternion_angle(ref[9:13], got[9:13]),
                      angular_velocity_rad_s=distance(ref[13:16], got[13:16]),
                      mjd_days=abs(ref[2]-got[2]))
        for key, error in errors.items():
            require(math.isfinite(error) and error <= LIMITS[key],
                    f"step {ref[0]}: {key} error {error} exceeds {LIMITS[key]}")
            maxima[key] = max(maxima[key], error)
    return maxima


def validate_orbit(rows, *, spin=0.0):
    require(math.isfinite(spin), "spin must be finite")
    expected_w = (0, 0, spin)
    n = math.sqrt(MU / RADIUS**3)
    energy0 = -MU / (2*RADIUS)
    momentum0 = RADIUS * SPEED
    maxima = dict(position_m=0.0, velocity_m_s=0.0, orientation_rad=0.0,
                  angular_velocity_rad_s=0.0, energy_relative=0.0, momentum_relative=0.0)
    for row in rows:
        t = row[1]
        r, v, q, w = row[3:6], row[6:9], row[9:13], row[13:16]
        expected_r = (RADIUS*math.cos(n*t), 0, RADIUS*math.sin(n*t))
        expected_v = (-SPEED*math.sin(n*t), 0, SPEED*math.cos(n*t))
        expected_q = (0, 0, math.sin(spin*t/2), math.cos(spin*t/2))
        require(norm(r) > 0, "zero orbital radius")
        errors = dict(position_m=distance(r, expected_r), velocity_m_s=distance(v, expected_v),
                      orientation_rad=quaternion_angle(q, expected_q),
                      angular_velocity_rad_s=distance(w, expected_w),
                      energy_relative=abs((norm(v)**2/2 - MU/norm(r))/energy0 - 1),
                      momentum_relative=abs(norm(cross(r, v))/momentum0 - 1))
        for key, error in errors.items():
            limit = LIMITS.get(key, 1e-8)
            require(math.isfinite(error) and error <= limit,
                    f"step {row[0]}: analytical {key} error {error} exceeds {limit}")
            maxima[key] = max(maxima[key], error)
    return maxima


def validate_convergence(coarse, fine):
    require(coarse[-1][1] == fine[-1][1], "convergence runs must end at the same time")
    coarse_errors = validate_orbit(coarse)
    fine_errors = validate_orbit(fine)
    for field, noise in (("position_m", 2e-7), ("velocity_m_s", 2e-10)):
        require(fine_errors[field] <= coarse_errors[field] * 0.5 + noise,
                f"half-step run did not converge for {field}")
    return dict(coarse=coarse_errors, half_step=fine_errors)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace", type=Path)
    parser.add_argument("--reference", type=Path)
    parser.add_argument("--dt", type=float, default=1.0)
    parser.add_argument("--steps", type=int, default=6000)
    parser.add_argument("--spin", type=float, default=0.0, help="body z spin in radians/second")
    args = parser.parse_args()
    rows = load_trace(args.trace, dt=args.dt, steps=args.steps)
    result = dict(analytical=validate_orbit(rows, spin=args.spin))
    if args.reference:
        result["comparison"] = compare(load_trace(args.reference, dt=args.dt, steps=args.steps), rows)
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, OverflowError) as error:
        raise SystemExit(str(error)) from error
