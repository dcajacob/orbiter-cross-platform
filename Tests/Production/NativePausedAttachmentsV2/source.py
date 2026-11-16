"""Verify the paused startup scope and replay the previous version's source guards."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PREVIOUS = "c378ab989f3bc08ea6ae4c28a93bf8b725329ec8"
VERSION = "paused-attachments-v2"
APPLICATION = "Src/Orbiter/Production/NativeApplication.cpp"
BUILDER = "Tests/Production/NativePausedAttachments/build_native.py"
INPUTS = tuple(str(path.relative_to(ROOT)) for path in (HERE / "source.py", HERE / "version.json"))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def git(*arguments, root=ROOT):
    return subprocess.check_output(["git", "-C", str(root), *arguments])


def normalized(body):
    return body.replace(b"\r\n", b"\n")


def digest(body):
    return hashlib.sha256(body).hexdigest()


def replace_once(body, old, new):
    require(body.count(old) == 1, "Expected previous version source boundary is missing")
    return body.replace(old, new)


def verify():
    application = normalized(git("show", PREVIOUS + ":" + APPLICATION))
    application = replace_once(
        application,
        b"const std::filesystem::path& evidence,double captureTime) {",
        b"const std::filesystem::path& evidence,double captureTime,bool startRunning) {",
    )
    application = replace_once(
        application,
        b"        for(auto* vessel:system->GetVessels())\n"
        b"            if(!vessel->isAttached())vessel->UpdateAttachments();",
        b"        if(!startRunning) {\n"
        b"            for(auto* vessel:system->GetVessels())\n"
        b"                if(!vessel->isAttached())vessel->UpdateAttachments();\n"
        b"        }",
    )
    application = replace_once(
        application,
        b'application.Initialize(absolute("--config"),scenario,output,capture);',
        b'application.Initialize(absolute("--config"),scenario,output,capture,startRunning);',
    )
    builder = replace_once(
        normalized(git("show", PREVIOUS + ":" + BUILDER)),
        b"from NativePausedAttachments import source as physics_source",
        b"from NativePausedAttachmentsV2 import source as physics_source",
    )
    checker_path = "Tests/Production/NativePausedAttachments/Startup.Test.py"
    checker = replace_once(normalized(git("show", PREVIOUS + ":" + checker_path)),
                           b"'paused-attachments-v1'", b"'paused-attachments-v2'")
    reviewed = {APPLICATION: application, BUILDER: builder, checker_path: checker}
    require(all(normalized((ROOT / name).read_bytes()) == body for name, body in reviewed.items()),
            "Unexpected application or builder change")
    manifest = json.loads((HERE / "version.json").read_text())
    require(manifest == dict(native_bootstrap_version=VERSION, previous_source=PREVIOUS,
                             physics_version="assembly-contact-v3",
                             reviewed_files_sha256_lf={name: digest(body) for name, body in reviewed.items()},
                             qualification_granted=False),
            "Paused startup version manifest differs")
    changes = set(git("diff", "--name-only", PREVIOUS, "--").decode().splitlines())
    changes.update(git("ls-files", "--others", "--exclude-standard").decode().splitlines())
    require(changes == set(reviewed) | set(INPUTS), "Unexpected source or acceptance file change")

    retained = ROOT / "out/native-paused-attachments-baseline-v2"
    retained.mkdir(parents=True, exist_ok=True)
    view = retained / "source"
    if not view.exists():
        from PhysicsV2.source import SCOPES
        subprocess.run(["git", "clone", "--quiet", "--shared", "--no-checkout",
                        str(ROOT), str(view)], check=True)
        subprocess.run(["git", "-C", str(view), "sparse-checkout", "init", "--no-cone"], check=True)
        (view / ".git/info/sparse-checkout").write_text(
            "".join("/" + name + ("/" if "." not in name.rsplit("/", 1)[-1] else "") + "\n"
                    for name in SCOPES))
        subprocess.run(["git", "-C", str(view), "checkout", "--quiet", "--detach", PREVIOUS], check=True)
    require(git("rev-parse", "HEAD", root=view).decode().strip() == PREVIOUS
            and not git("status", "--porcelain", "--untracked-files=no", root=view).strip(),
            "Previous source view changed")
    prior_path = retained / "previous-source-guards.json"
    prior_log = retained / "previous-source-guards.log"
    with prior_log.open("w") as log:
        subprocess.run([sys.executable, "-B", str(view / "Tests/Production/NativePausedAttachments/source.py"),
                        "--output", str(prior_path)], cwd=view, stdout=log,
                       stderr=subprocess.STDOUT, check=True)
    prior = json.loads(prior_path.read_text())
    require(prior["actual_source"] == PREVIOUS and prior["native_bootstrap_version"] == "paused-attachments-v1"
            and prior["original_v3_physics_guards_tests_captures_and_tolerances_unchanged"],
            "Previous version source guards failed")
    return dict(manifest, actual_source=git("rev-parse", "HEAD").decode().strip(),
                original_v3_physics_guards_tests_captures_and_tolerances_unchanged=True,
                previous_source_guard_sha256=digest(prior_path.read_bytes()),
                previous_source_guard_log_sha256=digest(prior_log.read_bytes()))
