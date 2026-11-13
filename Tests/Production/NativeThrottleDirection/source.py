"""Verify the input-only change against the original paused-start source guards."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = "3e37cc114c467f50ab8a4cbdc07c9c58791ac4a7"
THROTTLE = "7cc76ca34fc401c45c1bc28bee1c9f17eaaf0fdf"
BUILDER = "Tests/Production/NativePausedAttachments/build_native.py"
INPUTS = (HERE.relative_to(ROOT).joinpath("source.py").as_posix(),)


def git(*args, root=ROOT):
    return subprocess.check_output(["git", "-C", str(root), *args])


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify():
    edits = git("diff", "--name-only", BASE, THROTTLE).decode().splitlines()
    require(git("rev-parse", THROTTLE + "^").decode().strip() == BASE,
            "Unexpected parent of reviewed joystick change")
    allowed = set(edits) | set(INPUTS) | {BUILDER}
    changes = set(git("diff", "--name-only", BASE, "--").decode().splitlines())
    changes.update(git("ls-files", "--others", "--exclude-standard").decode().splitlines())
    require(changes == allowed, "Unexpected input or acceptance source changes")
    for name in edits:
        require((ROOT / name).read_bytes() == git("show", THROTTLE + ":" + name),
                "Reviewed joystick source differs: " + name)
    before = b"from NativePausedAttachmentsV2 import source as physics_source"
    after = b"from NativeThrottleDirection import source as physics_source"
    original_builder = git("show", BASE + ":" + BUILDER)
    require(original_builder.count(before) == 1 and
            (ROOT / BUILDER).read_bytes() == original_builder.replace(before, after),
            "Unexpected package builder change")

    retained = ROOT / "out/native-throttle-direction-baseline"
    retained.mkdir(parents=True, exist_ok=True)
    view = retained / "source"
    if not view.exists():
        from PhysicsV2.source import SCOPES
        subprocess.run(["git", "clone", "--quiet", "--shared", "--no-checkout", str(ROOT), str(view)],
                       check=True)
        subprocess.run(["git", "-C", str(view), "sparse-checkout", "init", "--no-cone"], check=True)
        (view / ".git/info/sparse-checkout").write_text(
            "".join("/" + name + ("/" if "." not in name.rsplit("/", 1)[-1] else "") + "\n"
                    for name in SCOPES))
        subprocess.run(["git", "-C", str(view), "checkout", "--quiet", "--detach", BASE], check=True)
    require(git("rev-parse", "HEAD", root=view).decode().strip() == BASE and
            not git("status", "--porcelain", "--untracked-files=no", root=view).strip(),
            "Paused-start source view differs")
    log = retained / "paused-start-source-guards.log"
    with log.open("w") as output:
        proof_text = subprocess.check_output(
            [sys.executable, "-B", "-c",
             "import json; from NativePausedAttachmentsV2.source import verify; print(json.dumps(verify()))"],
            cwd=view, env={"PATH": "/usr/bin:/bin", "PYTHONPATH": str(view / "Tests/Production")},
            stderr=output, text=True)
    proof = json.loads(proof_text)
    require(proof["actual_source"] == BASE and proof["native_bootstrap_version"] == "paused-attachments-v2" and
            proof["original_v3_physics_guards_tests_captures_and_tolerances_unchanged"],
            "Original paused-start source guards failed")
    receipt = retained / "paused-start-source-guards.json"
    receipt.write_text(proof_text)
    return dict(proof, actual_source=git("rev-parse", "HEAD").decode().strip(),
                joystick_change=THROTTLE, previous_bootstrap_source=BASE,
                previous_bootstrap_guard_sha256=sha(receipt),
                reviewed_joystick_files_sha256={name: sha(ROOT / name) for name in edits})
