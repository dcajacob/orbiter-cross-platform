"""Install and verify the checksum-pinned Orbiter Phase 8 stock data."""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import sys
import tarfile
import tempfile
import urllib.request
import zipfile

BLOCK = 1024 * 1024
STOCK = "production-stock-data-v1.zip"
PLANETS = "Orbiter2016.zip"
FONT = "Fonts/architext.regular.ttf"
FONT_SETTING = "ImGui_ManuscriptFontFile = Fonts/Cousine-Regular.ttf"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def check(path, record):
    return (path.is_file() and path.stat().st_size == record["bytes"]
            and digest(path) == record["sha256"])


def source_records(stock, planets, storage):
    packages = storage["manifest"]["packages"]
    source = packages["Orbiter-x64.zip"]
    for field in ("sha256", "bytes"):
        require(source[field] == stock[field], "Stock mirror no longer binds the original lock")
        require(packages[PLANETS][field] == planets[field], "Planet archive no longer binds the original lock")
    require(source["excluded"] == [FONT], "Unexpected exclusion in the stock data lock")
    mirror = source["mirrored_archive"]
    require(mirror["name"] == STOCK, "Unexpected stock mirror name")
    url = f"https://github.com/{storage['repository']}/releases/download/{storage['tag']}/{STOCK}"
    return {STOCK: dict(mirror, url=url), PLANETS: planets}


@contextmanager
def cache_lock(path):
    with path.with_suffix(path.suffix + ".lock").open("a+b") as guard:
        try:
            if os.name == "nt":
                import msvcrt
                guard.seek(0)
                msvcrt.locking(guard.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(guard.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            raise ValueError(f"Cannot lock the cache for {path.name}: {error}") from error
        yield


def download(path, record, offline):
    if path.exists():
        require(check(path, record), f"Cached archive checksum mismatch: {path}")
        return path
    require(not offline, f"Offline cache is missing {path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with cache_lock(path):
        if path.exists():
            require(check(path, record), f"Cached archive checksum mismatch: {path}")
        else:
            fetch(path, record)
    return path


def fetch(path, record):
    partial = path.with_suffix(path.suffix + ".partial")
    offset = partial.stat().st_size if partial.exists() else 0
    total = record["bytes"]
    require(offset <= total, f"Partial download is larger than the locked archive: {partial}")
    if offset < total:
        headers = {"Range": f"bytes={offset}-"} if offset else {}
        print(f"Downloading {path.name} from byte {offset:,} of {total:,}", flush=True)
        request = urllib.request.Request(record["url"], headers=headers)
        with urllib.request.urlopen(request, timeout=90) as response:
            if response.status == 206:
                expected = f"bytes {offset}-{total - 1}/{total}"
                require(response.headers.get("Content-Range") == expected,
                        f"Unexpected Content-Range for {path.name}")
            else:
                require(response.status == 200, f"Unexpected HTTP status for {path.name}")
                offset = 0
            with partial.open("ab" if offset else "wb") as output:
                for chunk in iter(lambda: response.read(BLOCK), b""):
                    offset += len(chunk)
                    require(offset <= total, f"Download exceeded locked size: {path.name}")
                    output.write(chunk)
    require(check(partial, record),
            f"Incomplete or invalid download at {partial}; an incomplete transfer can be resumed")
    partial.replace(path)


def relative(name):
    path = PurePosixPath(name)
    require(not path.is_absolute() and path.parts and ".." not in path.parts and
            not any(character in name for character in ("\\", ":", "\x00")),
            f"Unsafe installer path: {name}")
    return Path(*path.parts)


def put(archive, name, destination, record, managed, root):
    require(not destination.is_symlink(), f"Cannot replace symbolic link: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    checksum = hashlib.sha256()
    count = 0
    with archive.open(name) as source, destination.open("wb") as target:
        for chunk in iter(lambda: source.read(BLOCK), b""):
            checksum.update(chunk)
            count += len(chunk)
            target.write(chunk)
    entry = dict(sha256=checksum.hexdigest(), bytes=count)
    require(all(entry[key] == value for key, value in record.items()), f"Archive member differs: {name}")
    managed[destination.relative_to(root).as_posix()] = entry


def extract_runtime(package_path, root, info):
    root.mkdir(parents=True)
    if info["platform"] == "windows":
        with zipfile.ZipFile(package_path) as package:
            package.extractall(root)
    else:
        with tarfile.open(package_path, "r:gz") as package:
            package.extractall(root, filter="data")
    manifest = json.loads((root / "runtime.json").read_text(encoding="utf-8"))
    require(manifest["source"] == info["source"], "Extracted runtime source identity differs from the package lock")


def configure(root, runtime, windows):
    config = runtime / "Orbiter.cfg" if windows else root / "user/Orbiter.cfg"
    config.parent.mkdir(exist_ok=True)
    source = runtime / "Orbiter.cfg"
    current = source.read_bytes() if source.is_file() else b""
    current = re.sub(rb"(?mi)^\s*ImGui_ManuscriptFontFile\s*=.*$", b"", current).rstrip()
    # Older packaged engines default to RK2. Override just the method for a fresh config.
    if not re.search(rb"(?m)^PropStage0[ \t]*=", current):
        current += b"\nPropStage0 = 1"
    if windows:
        # The supported Windows preview can ship without a master configuration.
        # An empty graphics selection starts the simulator in console mode.
        block = re.search(rb"(?ims)^ACTIVE_MODULES[ \t]*\r?\n(.*?)^END_MODULES\b", current)
        if block is None:
            current += b"\nACTIVE_MODULES\n  OGLClient\nEND_MODULES"
        elif not any(line.strip().lower() in (b"oglclient", b"d3d9client") for line in block[1].splitlines()):
            current = current[:block.end(1)] + b"  OGLClient\n" + current[block.end(1):]
    config.write_bytes(current + b"\n" + FONT_SETTING.encode("ascii") + b"\n")
    if windows:
        return
    saves = root / "user/Scenarios"
    saves.mkdir()
    profile = dict(mode="native", executable="runtime/orbiter-production",
                   assets="assets", data="data", planets="planets",
                   modules="runtime/NativeModules", config="user/Orbiter.cfg",
                   keymap="runtime/Keymap.cfg", saves="user/Scenarios")
    (root / "Launchpad profile.json").write_text(json.dumps(profile, indent=2) + "\n", encoding="utf-8")
    mac = (runtime / "orbiter-launchpad.app").is_dir()
    launcher = ("orbiter-launchpad.app/Contents/MacOS/orbiter-launchpad" if mac else "bin/orbiter-launchpad")
    boot = root / ("Launch Orbiter.command" if mac else "Launch Orbiter.sh")
    personal = "" if mac else (
        'if [ ! -w "$base/user" ] || [ ! -w "$base/user/Scenarios" ] || [ ! -w "$base/user/Orbiter.cfg" ]'
        ' || [ "$(stat -c %u "$base/user")" != "$(id -u)" ]; then\n'
        '  exec python3 -I "$base/launch_linux.py" "$@"\nfi\n')
    boot.write_text('#!/bin/sh\nset -eu\nbase=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)\n' + personal +
                    f'exec "$base/runtime/{launcher}" --profile "$base/Launchpad profile.json"\n',
                    encoding="utf-8")
    boot.chmod(0o755)


def install(bundle, package, info, source, stock, planets, destination):
    windows = info["platform"] == "windows"
    runtime = destination / "runtime"
    assets = runtime if windows else destination / "assets"
    planetary_root = runtime if windows else destination / "planets"
    extract_runtime(package, runtime, info)
    managed = {}
    if not windows:
        for name, record in sorted(json.loads(bundle.read("native-assets.json"))["files"].items()):
            put(bundle, f"native-assets/{name}", assets / relative(name), record, managed, destination)
        for shader in (runtime / "shaders").iterdir():
            require(digest(shader) == digest(assets / "Modules/OGLClient" / shader.name),
                    f"Native resources do not match the package renderer: {shader.name}")
    with zipfile.ZipFile(source[STOCK]) as archive:
        for name, record in stock["data_files"].items():
            if name == FONT or name == "LICENSE":
                continue
            path = relative(name)
            target_root = destination / "data" if not windows and path.parts[0] in ("Kernels", "GravityModels") else assets
            put(archive, name, target_root / path, record, managed, destination)
        for name in archive.namelist():
            if name in ("LICENSE", "readme.txt") or name.startswith("Licenses/"):
                put(archive, name, destination / "notices/stock" / relative(name),
                    stock["data_files"].get(name, {}), managed, destination)
    with zipfile.ZipFile(source[PLANETS]) as archive:
        for name, record in planets["data_files"].items():
            put(archive, name, planetary_root / relative(name), record, managed, destination)
        for name in ("readme.txt", "Doc/Orbiter.pdf"):
            put(archive, name, destination / "notices/planets" / relative(name), {}, managed, destination)
    if info["platform"] == "linux":
        (destination / "launch_linux.py").write_bytes(bundle.read("launch_linux.py"))
    configure(destination, runtime, windows)
    receipt = dict(schema=1, package=package.name, package_sha256=info["sha256"],
                   package_source=info["source"], platform=info["platform"],
                   managed_files=managed, manuscript_font="Fonts/Cousine-Regular.ttf")
    (destination / "stock-data-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return len(managed)


def verify(root, bundle, packages, stock, planets, storage):
    receipt = json.loads((root / "stock-data-receipt.json").read_text(encoding="utf-8"))
    info = packages[receipt["package"]]
    require(receipt["package_sha256"] == info["sha256"] and receipt["package_source"] == info["source"]
            and receipt["platform"] == info["platform"], "Installed package identity differs from the supported package lock")
    expected = {}
    windows = info["platform"] == "windows"
    if not windows:
        expected.update((f"assets/{name}", record) for name, record in
                        json.loads(bundle.read("native-assets.json"))["files"].items())
    for name, record in stock["data_files"].items():
        if name == FONT:
            continue
        if name == "LICENSE":
            directory = "notices/stock"
        elif windows:
            directory = "runtime"
        else:
            directory = "data" if name.startswith(("Kernels/", "GravityModels/")) else "assets"
        expected[f"{directory}/{name}"] = record
    expected.update((f"{'runtime' if windows else 'planets'}/{name}", record)
                    for name, record in planets["data_files"].items())
    for package, prefix in (("Orbiter-x64.zip", "stock"), (PLANETS, "planets")):
        for notice in storage["manifest"]["packages"][package]["notices"]:
            expected.setdefault(f"notices/{prefix}/{notice['archive_member']}",
                                {"sha256": notice["sha256"]})
    managed = receipt["managed_files"]
    for name, record in expected.items():
        require(name in managed and all(managed[name].get(key) == value for key, value in record.items()),
                f"Installed receipt differs from the locked profile: {name}")
    for name, record in managed.items():
        path = root / relative(name)
        require(not path.is_symlink() and path.resolve().is_relative_to(root.resolve()) and check(path, record),
                f"Installed file differs: {path}")
    return len(managed)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path, help="A new directory for the installed preview")
    parser.add_argument("--package", type=Path, help="A supported Phase 8 runtime archive")
    parser.add_argument("--cache", type=Path, default=Path.home() / ".cache/orbiter-stock",
                        help="Cache directory for the two pinned data ZIPs")
    parser.add_argument("--offline", action="store_true", help="Use only previously downloaded data ZIPs")
    parser.add_argument("--verify-only", action="store_true", help="Verify all managed files in an existing install")
    args = parser.parse_args()
    destination = args.destination.absolute()
    try:
        with zipfile.ZipFile(Path(sys.argv[0]).resolve()) as bundle:
            packages = json.loads(bundle.read("packages.json"))
            stock = json.loads(bundle.read("stock-data.lock.json"))
            planets = json.loads(bundle.read("standard-planets.lock.json"))
            storage = json.loads(bundle.read("input-storage.lock.json"))
            if args.verify_only:
                count = verify(destination, bundle, packages, stock, planets, storage)
                print(f"Verified {count:,} stock data files in {destination}")
                return 0
            require(not destination.exists() and not destination.is_symlink(),
                    f"Choose a new installation directory: {destination}")
            require(args.package is not None and args.package.name in packages, "Supply a supported Phase 8 package with --package")
            info = packages[args.package.name]
            require(args.package.is_file() and digest(args.package) == info["sha256"], "Runtime archive SHA-256 mismatch")
            records = source_records(stock, planets, storage)
            source = {name: download(args.cache / name, record, args.offline) for name, record in records.items()}
            destination.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(prefix=".orbiter-install-", dir=destination.parent) as work:
                stage = Path(work) / "install"
                count = install(bundle, args.package, info, source, stock, planets, stage)
                require(not destination.exists() and not destination.is_symlink(),
                        f"Install destination appeared during setup: {destination}")
                stage.rename(destination)
            print(f"Installed Orbiter and verified {count:,} stock data files in {destination}")
            print("Open runtime/orbiter-launchpad.exe" if info["platform"] == "windows" else
                  "Open Launch Orbiter.command" if info["platform"] == "macos" else "Run ./Launch Orbiter.sh")
    except (ValueError, KeyError, OSError, zipfile.BadZipFile, tarfile.TarError) as error:
        parser.exit(1, f"orbiter-stock-data: {error}\n")
    return 0
