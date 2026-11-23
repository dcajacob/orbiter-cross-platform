"""Make a packaging-only successor to the frozen Windows RC2 using Info-ZIP 3.0."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile


ORIGINAL = "Orbiter-windows-x64-user-profile-f6c66ea7.zip"
CANDIDATE = "Orbiter-windows-x64-f6c66ea7-no-vc71.zip"
INSTALLER = "orbiter-stock-data.pyz"
RUNTIME_HASH = "dfb60f8258cde5e6734f0fa8c49fecb8fdfdec32eb29a7c834950acb3bd65154"
INSTALLER_HASH = "f5557f112f3cc3111799bb9ffd03b2b91941aa17b4724b3e5623d280d5b4ea2a"
OMIT = {"msvcp71.dll", "msvcr71.dll"}


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def rewrite(source, output, metadata, record, removed, zip_tool):
    # Info-ZIP copies the retained compressed members without recompressing them.
    shutil.copyfile(source, output)
    subprocess.run([zip_tool, "-qd", output.name, metadata, *sorted(removed)],
                   cwd=output.parent, check=True)
    with zipfile.ZipFile(output, "a") as archive:
        entry = zipfile.ZipInfo(metadata, (2026, 11, 23, 0, 0, 0))
        entry.create_system = 3
        entry.external_attr = 0o100644 << 16
        archive.writestr(entry, json.dumps(record, indent=2).encode("utf-8") + b"\n")


def prepare(original, destination, zip_tool):
    runtime = original / ORIGINAL
    installer = original / INSTALLER
    if digest(runtime) != RUNTIME_HASH or digest(installer) != INSTALLER_HASH:
        raise ValueError("Inputs differ from frozen Windows RC2")
    with zipfile.ZipFile(runtime) as archive:
        manifest = json.loads(archive.read("runtime.json"))
    for name in OMIT:
        del manifest["files"][name]
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise FileExistsError(destination)
    with tempfile.TemporaryDirectory(dir=destination.parent) as temporary:
        stage = Path(temporary) / "candidate"
        stage.mkdir()
        candidate = stage / CANDIDATE
        rewrite(runtime, candidate, "runtime.json", manifest, OMIT, zip_tool)
        with zipfile.ZipFile(candidate) as archive:
            names = [item.filename for item in archive.infolist() if not item.is_dir()]
            if len(names) != len(set(names)) or set(names) != set(manifest["files"]) | {"runtime.json"}:
                raise ValueError("Unexpected members in candidate")
            for name, expected in manifest["files"].items():
                with archive.open(name) as stream:
                    if hashlib.file_digest(stream, "sha256").hexdigest() != expected:
                        raise ValueError(f"Runtime member changed: {name}")
        with zipfile.ZipFile(installer) as archive:
            lock = json.loads(archive.read("packages.json"))
        info = lock.pop(ORIGINAL)
        if lock or info["sha256"] != RUNTIME_HASH or info["source"] != manifest["source"]:
            raise ValueError("Unexpected frozen installer lock")
        info["sha256"] = digest(candidate)
        rewrite(installer, stage / INSTALLER, "packages.json", {CANDIDATE: info}, (), zip_tool)
        for name in (CANDIDATE, INSTALLER):
            print(f"{digest(stage / name)}  {name}", flush=True)
        stage.rename(destination)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--zip-tool", default="zip")
    args = parser.parse_args()
    prepare(args.original.resolve(), args.destination.resolve(), args.zip_tool)
