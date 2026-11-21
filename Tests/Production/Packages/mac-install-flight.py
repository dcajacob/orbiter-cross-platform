"""Install the packaged Mac runtime and verify its installed files and muted flight."""
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

prod = Path("Tests/Production")
dist = Path("out/dist")
receipt = Path("out/receipt/clean-install")
receipt.mkdir()
arch = os.environ["ORBITER_ARCH"]
source = os.environ["GITHUB_SHA"]
package = dist / f"Orbiter-macos-{arch}-8e576b84.tar.gz"
installer = dist / f"orbiter-stock-data-{arch}.pyz"
target = Path(os.environ["RUNNER_TEMP"]) / "Orbiter Clean Install"
cache = Path("out/stock-cache")
cache.mkdir()


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def tool(*args):
    subprocess.run([sys.executable, "-B", *args], check=True)


require(not target.exists() and not target.resolve().is_relative_to(Path.cwd()), "Expected a new external install")
for archive in [Path("out/data-cache/production-stock-data-v1.zip"), Path("out/planet-cache/Orbiter2016.zip")]:
    if archive.is_file():
        os.link(archive, cache / archive.name)
lock = {package.name: dict(source=source, platform="macos", sha256=sha(package))}
lock_path = Path("out/package-lock.json")
lock_path.write_text(json.dumps(lock))
tool("Utils/StockDataInstaller/build.py", "--cache", cache, "--output", installer, "--package-lock", lock_path)
tool(installer, target, "--cache", cache, "--offline", "--package", package)
runtime = target / "runtime"
manifest = json.loads((runtime / "runtime.json").read_bytes())
require(manifest["source"] == source, "Installed source mismatch")
files = {p.relative_to(runtime).as_posix(): sha(p) for p in runtime.rglob("*") if p.is_file() and not p.is_symlink() and p != runtime/"runtime.json"}
require(files == manifest["files"], "Installed runtime inventory or hash differs")
for name in ("orbiter-production", "NativeModules/Graphics/OGLClient.so", "orbiter-launchpad.app/Contents/MacOS/orbiter-launchpad"):
    actual = subprocess.check_output(["lipo", "-archs", runtime / name], text=True).strip()
    require(actual == arch == platform.machine(), f"Wrong architecture {actual} in {name}")
for p in (runtime/"shaders").iterdir():
    require(sha(p) == sha(target/"assets/Modules/OGLClient"/p.name), f"Installed shader mismatch: {p.name}")
cfg = target / "user/Orbiter.cfg"
original = cfg.read_bytes()
try:
    text = cfg.read_text()
    require(text.count("FixedStep = 1\n") == 1, "Unexpected fixed-step default")
    cfg.write_text(text.replace("FixedStep = 1\n","FixedStep = 0.0625\n")+"\nSurfMarkers = 33\n")
    tool(prod / "StockInstaller/mac-installed-smoke.py", "--install", target, "--installer", installer, "--output", receipt.resolve())
finally:
    cfg.write_bytes(original)
errors = receipt/"graphics-errors.txt"
require(not errors.is_file() or not errors.read_text().strip(), "OpenGL errors during flight")
result = json.loads((receipt/"result.json").read_bytes())
require(result["package_sha256"] == lock[package.name]["sha256"], "Flight install/package mismatch")
result.update(arch=arch, source=source, renderer_tree="d7754fb7682a1a2f69f34ebfec93f65de5ae500b",
              renderer_sha256=files["NativeModules/Graphics/OGLClient.so"], files_verified=len(files),
              renderer=json.loads((receipt/"renderer-info.json").read_bytes()), sound_enabled=False)
(receipt/"verified.json").write_text(json.dumps(result, indent=2)+"\n")
(dist/"SHA256SUMS").write_text("".join(f"{sha(p)}  {p.name}\n" for p in (package,installer)))
print(json.dumps(result, indent=2))
