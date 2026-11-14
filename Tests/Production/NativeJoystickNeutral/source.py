"""Bind the steering repair to the previously verified Linux source."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = "ef3beaa53d838c33aeb16a50e33fb0dfe0e18cfa"
BUILDER = "Tests/Production/NativePausedAttachments/build_native.py"
INPUTS = (
    "Docs/Production/NativeFlight.md",
    "OVP/OGLClient/Native/LinuxAdapter.cpp",
    "Src/Orbiter/Production/NativeJoystick.h",
    "Tests/Production/Boundary/NativeJoystick.Test.cpp",
    "Tests/Production/Flight/keymap-laptop.cfg",
    "Tests/Production/NativeJoystickNeutral/source.py",
)


def git(*args, root=ROOT):
    return subprocess.check_output(["git", "-C", str(root), *args])


def require(condition, message):
    if not condition:
        raise ValueError(message)


def verify():
    changes = set(git("diff", "--name-only", BASE, "--").decode().splitlines())
    changes.update(git("ls-files", "--others", "--exclude-standard").decode().splitlines())
    require(changes == set(INPUTS) | {BUILDER}, "Unexpected steering-repair or acceptance files")
    original = git("show", BASE + ":" + BUILDER)
    old_import = b"from NativeThrottleDirection import source as physics_source"
    require(original.count(old_import) == 1 and (ROOT / BUILDER).read_bytes() ==
            original.replace(old_import, b"from NativeJoystickNeutral import source as physics_source"),
            "Unexpected package builder change")

    retained = ROOT / "out/native-joystick-neutral-baseline"
    retained.mkdir(parents=True, exist_ok=True)
    view = retained / "source"
    if not view.exists():
        from PhysicsV2.source import SCOPES
        subprocess.run(["git", "clone", "--quiet", "--shared", "--no-checkout", str(ROOT), str(view)], check=True)
        git("sparse-checkout", "init", "--no-cone", root=view)
        (view / ".git/info/sparse-checkout").write_text(
            "".join("/" + name + ("/" if "." not in name.rsplit("/", 1)[-1] else "") + "\n"
                    for name in SCOPES))
        git("checkout", "--quiet", "--detach", BASE, root=view)
    require(git("rev-parse", "HEAD", root=view).decode().strip() == BASE and
            not git("status", "--porcelain", "--untracked-files=no", root=view).strip(),
            "Throttle baseline source differs")
    with (retained / "source-guards.log").open("w") as log:
        proof_text = subprocess.check_output(
            [sys.executable, "-B", "-c",
             "import json; from NativeThrottleDirection.source import verify; print(json.dumps(verify()))"],
            cwd=view, env={"PATH": "/usr/bin:/bin", "PYTHONPATH": str(view / "Tests/Production")},
            stderr=log, text=True)
    proof = json.loads(proof_text)
    require(proof["actual_source"] == BASE and proof["native_bootstrap_version"] == "paused-attachments-v2" and
            proof["original_v3_physics_guards_tests_captures_and_tolerances_unchanged"],
            "Original source guards failed")
    (retained / "source-guards.json").write_text(proof_text)
    return dict(proof, actual_source=git("rev-parse", "HEAD").decode().strip(),
                steering_baseline=BASE, steering_baseline_guard_sha256=hashlib.sha256(proof_text.encode()).hexdigest())
