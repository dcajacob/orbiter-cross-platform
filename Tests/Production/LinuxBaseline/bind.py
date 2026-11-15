"""Bind the 24.04 SDK and installer to the sealed package and record ELF requirements."""
import argparse
from hashlib import file_digest
import json
from pathlib import Path
import re
import subprocess


def sha(path):
    with path.open("rb") as stream:
        return file_digest(stream, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("runtime", "archive", "generated-header", "source-lock", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    runtime = args.runtime
    manifest = json.loads((runtime / "runtime.json").read_text())
    for name, checksum in manifest["files"].items():
        assert sha(runtime / name) == checksum, name
    abi_re = rb"(?:gcc|clang)-[^\0\n]{1,110}:libstdc\+\+-[0-9]+-abi-[01]-(?:normal|debug)-gxx-[0-9]+:[0-9]+L(?=\0)"
    identities = set()
    for name in ("liborbiter_production_boundary.so", "NativeModules/Vessel/DeltaGlider.so",
                 "NativeModules/Graphics/OGLClient.so", "NativeModules/Celbody/spice.so"):
        matches = set(re.findall(abi_re, (runtime / name).read_bytes()))
        assert len(matches) == 1, (name, matches)
        identities.update(matches)
    assert len(identities) == 1
    header = args.generated_header.read_text()
    build = re.search(r'#define ORBITER_NATIVE_BUILD_BASE "([0-9a-f]{64})"', header)[1]
    assert "#define ORBITER_BUILD_NATIVE_COCKPIT 1" in header
    locks = json.loads(args.source_lock.read_text())
    assert args.archive.name not in locks
    locks[args.archive.name] = dict(sha256=sha(args.archive), platform="linux", source=manifest["source"],
                                   arch="x86_64", native_build=build, abi=identities.pop().decode())
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "packages.json").write_text(json.dumps(locks, indent=2) + "\n")
    versions = {}
    for name in sorted(manifest["files"]):
        path = runtime / name
        with path.open("rb") as stream:
            if stream.read(4) != b"\x7fELF":
                continue
        report = subprocess.check_output(["readelf", "--version-info", "-d", path], text=True)
        for search_path in re.findall(r"(?:RPATH|RUNPATH).*?\[([^\]]+)\]", report):
            assert all(part.startswith("$ORIGIN") for part in search_path.split(":")), (name, search_path)
        required = {}
        for family in ("GLIBC", "GLIBCXX", "CXXABI"):
            matches = re.findall(rf"\b{family}_([0-9]+(?:\.[0-9]+)+)\b", report)
            if matches:
                required[family] = max(matches, key=lambda v: tuple(map(int, v.split("."))))
        assert "GLIBC_PRIVATE" not in report
        assert tuple(map(int, required.get("GLIBC", "0").split("."))) <= (2, 39), (name, required)
        versions[name] = required
    assert {"orbiter-production", "bin/orbiter-launchpad", "NativeModules/Graphics/OGLClient.so"} <= versions.keys()
    (args.output / "elf-requirements.json").write_text(json.dumps(versions, indent=2) + "\n")
    print("Verified ELF imports and relative search paths for", len(versions), "packaged binaries")
    print("SDK:", locks[args.archive.name]["abi"])


if __name__ == "__main__":
    main()
