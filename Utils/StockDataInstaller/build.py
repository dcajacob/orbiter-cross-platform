"""Build the standalone stock installer using the audited original resource stagers."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile

import installer

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TESTS = ROOT / "Tests/Production"
LOCKS = ("stock-data.lock.json", "standard-planets.lock.json", "input-storage.lock.json")


def run(script, *arguments):
    subprocess.run([sys.executable, "-B", TESTS / script, *arguments], cwd=ROOT, check=True)


def add(bundle, path, name, method=zipfile.ZIP_DEFLATED):
    entry = zipfile.ZipInfo(name, (2026, 11, 14, 0, 0, 0))
    entry.compress_type = method
    with path.open("rb") as source, bundle.open(entry, "w") as target:
        shutil.copyfileobj(source, target, installer.BLOCK)


def build(archives, stock, output, package_lock):
    with tempfile.TemporaryDirectory(prefix="asset-build-", dir=output.parent) as directory:
        work = Path(directory)
        data, planets, base, native = (work / item for item in ("data", "planets", "base", "native"))
        run("prepare_native_data.py", "--archive", archives[installer.STOCK], "--destination", data, "--group", "all")
        run("prepare_hosted_data.py", "--lock", TESTS / LOCKS[1], "--archive", archives[installer.PLANETS],
            "--destination", planets)
        run("NativeScene/prepare.py", "--delta-glider", "--shuttle-a", "--data", data,
            "--planets", planets, "--destination", base)
        run("Atlantis/stage_assets.py", "--base-assets", base, "--output", native)
        external = {name.casefold() for name in stock["data_files"]}
        ignored = {"resources.json", "remaining-vessels-resources.json"}
        with zipfile.ZipFile(output.with_suffix(".partial"), "w") as bundle:
            bundle.writestr(zipfile.ZipInfo("__main__.py"), "from installer import main\nraise SystemExit(main())\n")
            add(bundle, HERE / "installer.py", "installer.py")
            add(bundle, HERE / "launch_linux.py", "launch_linux.py")
            add(bundle, package_lock, "packages.json")
            add(bundle, ROOT / "LICENSE", "LICENSE")
            for name in LOCKS:
                add(bundle, TESTS / name, name)
            records = {}
            for path in sorted(native.rglob("*")):
                name = path.relative_to(native).as_posix()
                if path.is_file() and name.casefold() not in external and name not in ignored:
                    records[name] = dict(bytes=path.stat().st_size, sha256=installer.digest(path))
                    add(bundle, path, "native-assets/" + name)
            bundle.writestr(zipfile.ZipInfo("native-assets.json"), json.dumps({"files": records}, sort_keys=True) + "\n")
        output.with_suffix(".partial").replace(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--package-lock", type=Path, default=HERE / "packages.json")
    args = parser.parse_args()
    stock, planets, storage = [json.loads((TESTS / name).read_text()) for name in LOCKS]
    records = installer.source_records(stock, planets, storage)
    archives = {name: installer.download(args.cache.resolve() / name, record, args.offline)
                for name, record in records.items()}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    installer.require(not args.output.exists(), "Choose a new output filename")
    build(archives, stock, args.output, args.package_lock)
    print(f"{installer.digest(args.output)}  {args.output}")


if __name__ == "__main__":
    main()
