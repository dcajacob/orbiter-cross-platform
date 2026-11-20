# Licensed under the MIT License
"""Compile the legacy aerodynamic method from Vessel.cpp with prescribed inputs."""
import argparse
import re
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("source", type=Path)
parser.add_argument("output", type=Path)
args = parser.parse_args()

source = args.source.read_text(encoding="cp1252")
method = re.search(
    r"^void Vessel::UpdateAerodynamicForces_OLD\s*\(\s*\)\s*\{.*?^\}",
    source, re.MULTILINE | re.DOTALL,
)
if method is None:
    raise ValueError(f"Cannot locate the legacy aerodynamic method in {args.source}")
line = source.count("\n", 0, method.start()) + 1
body = method[0].replace("Vessel::", "LegacyForceProbe::", 1)
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(f'#include "Probe.h"\n#line {line} "{args.source.resolve().as_posix()}"\n{body}\n')
