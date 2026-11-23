"""Recover pinned distribution bytes and exercise the SDK outside the checkout."""
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

root = Path.cwd()
out = root / "out"
out.mkdir(exist_ok=True)
manifest = json.loads(Path(__file__).with_name("rc2-inputs.json").read_text())
mode, target = sys.argv[1:]
info = manifest[target]
source = info["package_source"]
runtime = out / info["runtime"]
installer = out / info["installer"]
sdk = out / "distribution" / info["sdk"]

def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()

def run(*cmd):
    subprocess.run(cmd, check=True)

def py(*cmd):
    run(sys.executable, "-B", *cmd)

artifact = info["package_artifact"]
api = f"repos/dcajacob/orbiter-cross-platform/actions/artifacts/{artifact['id']}"
record = json.loads(subprocess.check_output(["gh", "api", api]))
assert record["workflow_run"]["head_sha"] == artifact["source"]
assert record["workflow_run"]["id"] == int(artifact["run"])
assert not record["expired"] and record["digest"] == artifact["sha256"]
archive = out / (target + "-package.zip")
with archive.open("xb") as stream:
    subprocess.run(["gh", "api", api + "/zip"], stdout=stream, check=True)
assert "sha256:" + sha(archive) == record["digest"]
with zipfile.ZipFile(archive) as bundle:
    for path in (runtime, installer):
        bundle.extract(path.name, out)
assert sha(runtime) == info["runtime_sha256"] and sha(installer) == info["installer_sha256"]
if mode == "prepare":
    lock = out / (target + "-lock.json")
    lock.write_text(json.dumps({runtime.name: info["build_lock"]}))
    py("Utils/PackageSDK/build.py", "--package", runtime, "--output", sdk, "--package-lock", lock)
    assert sha(sdk) == info["sdk_sha256"], f"SDK archive differs: {sha(sdk)}"
    sys.exit(0)

assert mode == "fly" and sha(sdk) == info["sdk_sha256"]
win = os.name == "nt"
assert platform.machine().lower() == ("amd64" if win else target.split("-", 1)[1])
assert os.environ["SDL_AUDIODRIVER"] == "dummy"
install = Path(os.environ["RUNNER_TEMP"]) / "Orbiter RC2 installed"
work = install.with_name("Orbiter RC2 SDK consumer")
py(installer, install, "--cache", out / "cache", "--package", runtime)
py(installer, install, "--verify-only")
extras = []
if win:
    run("cmake", "-S", "Tests/Production/Packages", "-B", out / "probe", "-G", "Ninja",
        "-DCMAKE_BUILD_TYPE=Release", f"-DORBITER_TEST_RUNTIME={install/'runtime'}")
    run("cmake", "--build", out / "probe", "--parallel", "2")
    py("Tests/Production/stage_mesa.py", "stage", "--cache", out / "mesa-cache", "--destination", out / "mesa")
    extras = ["--mesa", out / "mesa", "--probe", out / "probe/LaunchpadFlightProbe.dll",
              "--profile-resolver", out / "probe/ResolveSdkFlightProfile.exe"]
py("Tests/Production/PackageSDK/verify.py", "--sdk", sdk, "--install", install,
   "--work", work, "--output", out / "receipt", *extras)
receipt = out / "receipt/result.json"
result = json.loads(receipt.read_text())
assert result["sdk_sha256"] == info["sdk_sha256"] and result["runtime_sha256"] == info["runtime_sha256"]
result.update(candidate="phase8-rc2-f230562b", installer_sha256=sha(installer), runner_arch=platform.machine(),
              workflow_source=os.environ["GITHUB_SHA"], run_id=os.environ["GITHUB_RUN_ID"],
              audio_driver="dummy", xrsound_enabled=False)
receipt.write_text(json.dumps(result, indent=2) + "\n")
print(receipt.read_text())
