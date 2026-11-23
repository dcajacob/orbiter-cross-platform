"""One muted stock Delta-glider flight from a fresh, pinned Windows installation."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

from prune_rc2_windows import CANDIDATE, INSTALLER, OMIT, ORIGINAL, digest, prepare
from windows import ROOT, STOCK, launchpad, mesa_files


def py(*args):
    subprocess.run([sys.executable, "-B", *args], check=True)


def main():
    out = ROOT / "out"
    receipt_dir = out / "receipt"
    receipt_dir.mkdir(parents=True)
    original = out / "original"
    original.mkdir()
    api = "repos/dcajacob/orbiter-cross-platform/actions/artifacts/14764140535"
    artifact = json.loads(subprocess.check_output(["gh", "api", api]))
    assert not artifact["expired"] and artifact["workflow_run"]["id"] == 45045995374
    assert artifact["workflow_run"]["head_sha"] == "33b6c221aeb6bd2044c86681afeb30fc4c83a031"
    outer = out / "original.zip"
    with outer.open("xb") as f:
        subprocess.run(["gh", "api", api + "/zip"], check=True, stdout=f)
    assert "sha256:" + digest(outer) == artifact["digest"] == "sha256:962c358d8783a3c9b90af215d2181a94a591f29877650b1266387de772c1b5b9"
    with zipfile.ZipFile(outer) as z:
        for name in (ORIGINAL, INSTALLER):
            z.extract(name, original)
    dist = out / "candidate"
    prepare(original, dist, os.environ["INFOZIP"])
    package = dist / CANDIDATE
    installer = dist / INSTALLER
    assert digest(package) == "b220225da9c17ac00ea50456ce44cc4496abf0dd93e98a62f60e4e6b4ad61930"
    assert digest(installer) == "651ceaae5c3db1b56b19cad0ba9ed9cc020a9dae0c6933fd1a3bbdfd1532de23"
    install = Path(os.environ["RUNNER_TEMP"]) / "Orbiter clean x64"
    assert not install.exists() and not install.is_relative_to(ROOT)
    py(installer, install, "--package", package, "--cache", out / "cache")
    py(installer, install, "--verify-only")
    runtime = install / "runtime"
    assert not any(p.name.casefold() in OMIT for p in install.rglob("*"))
    stock_hash = digest(runtime / STOCK)
    assert stock_hash == "0b3db48473487602eb14e19b60da98fd5b22dd744f1c53db13f666334edbbb43"
    probe = out / "probe"
    subprocess.run(["cmake", "-S", ROOT / "Tests/Production/Packages", "-B", probe, "-G", "Ninja",
                    "-DCMAKE_BUILD_TYPE=Release", f"-DORBITER_TEST_RUNTIME={runtime}"], check=True)
    subprocess.run(["cmake", "--build", probe, "--parallel", "2"], check=True)
    py(ROOT / "Tests/Production/stage_mesa.py", "stage", "--cache", out / "mesa-cache", "--destination", out / "mesa")
    mesa_files(out / "mesa", runtime)
    env = os.environ.copy()
    assert env["SDL_AUDIODRIVER"] == "dummy"
    for name in ("GH_TOKEN", "QT_PLUGIN_PATH", "QT_QPA_PLATFORM_PLUGIN_PATH"):
        env.pop(name, None)
    system = Path(os.environ["SYSTEMROOT"])
    env.update(PATH=os.pathsep.join([str(system / "System32"), str(system)]),
               QT_QPA_PLATFORM="windows", LIBGL_ALWAYS_SOFTWARE="true", GALLIUM_DRIVER="llvmpipe")
    config = (ROOT / "Tests/Production/Fixtures/Orbiter.cfg").read_text().replace(
        "  ProductionReferenceDriver", "  LaunchpadFlightProbe\n  OGLClient").replace("FixedStep = 1\n", "FixedStep = 0.0625\n")
    assert "SaveExitScreen = FALSE" in config and "XRSound" not in config
    (runtime / "Orbiter.cfg").write_text("ImGui_ManuscriptFontFile = Fonts/Cousine-Regular.ttf\n" + config, encoding="ascii")
    state_file = out / "state-path.txt"
    subprocess.run([probe / "ResolveSdkFlightProfile.exe", runtime / "Orbiter.exe", state_file], check=True)
    state = Path(state_file.read_text(encoding="utf-8"))
    assert state.is_relative_to(Path(os.environ["LOCALAPPDATA"]) / "Orbiter/Installations")
    assert (state / "Orbiter.cfg").read_bytes() == (runtime / "Orbiter.cfg").read_bytes()
    assert not (state / "launchpad-flight.txt").exists()
    shutil.copy2(probe / "LaunchpadFlightProbe.dll", runtime / "Modules/Plugin")
    (state / "ogl-evidence.enabled").touch()
    with (receipt_dir / "qt.log").open("wb") as log:
        launchpad(runtime / "orbiter-launchpad.exe", install, env, log)
    scenario = str(Path(STOCK).relative_to("Scenarios").with_suffix(""))
    try:
        with (receipt_dir / "flight.log").open("wb") as log:
            subprocess.run([runtime / "Orbiter.exe", "--scenariox=" + scenario], cwd=runtime, env=env,
                           check=True, timeout=120, stdout=log, stderr=subprocess.STDOUT)
    finally:
        for name in ("Orbiter.log", "graphics-lifecycle.json", "launchpad-flight.txt", "launchpad-flight-end.txt"):
            if (state / name).is_file():
                shutil.copy2(state / name, receipt_dir)
    lifecycle = json.loads((receipt_dir / "graphics-lifecycle.json").read_text())
    assert lifecycle == dict(rendered_frames=48, successful_presents=48, context_deleted=True), lifecycle
    events = (receipt_dir / "launchpad-flight.txt").read_text()
    assert "focus=GL-01\nclass=DeltaGlider\n" in events and "close-requested=1" in events
    assert (receipt_dir / "launchpad-flight-end.txt").read_text().strip() == "48"
    assert "XRSound.dll" not in (receipt_dir / "Orbiter.log").read_text(errors="replace")
    py(installer, install, "--verify-only")
    receipt = json.loads((install / "stock-data-receipt.json").read_text())
    assert receipt["package"] == CANDIDATE and receipt["package_sha256"] == digest(package)
    result = dict(status="passed", package=CANDIDATE, runtime_sha256=digest(package), installer_sha256=digest(installer),
                  scenario=STOCK, scenario_sha256=stock_hash, qt_launchpad_opened_and_closed=True, lifecycle=lifecycle,
                  omitted=sorted(OMIT), managed_files=len(receipt["managed_files"]), install=str(install),
                  xrsound_enabled=False, audio_driver="dummy", full_runs_invoked=False, windows_hands_on=False,
                  workflow_source=os.environ["GITHUB_SHA"], run_id=os.environ["GITHUB_RUN_ID"])
    (receipt_dir / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
