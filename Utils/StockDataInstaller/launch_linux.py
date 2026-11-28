"""Start an installed Linux Launchpad with a profile in the user's data directory."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile


def seed_file(source, destination):
    if not destination.exists():
        # A second launcher must see either the full seed or the user's later edits.
        with source.open("rb") as original, tempfile.NamedTemporaryFile(dir=destination.parent) as seed:
            shutil.copyfileobj(original, seed)
            seed.flush()
            try:
                os.link(seed.name, destination)
            except FileExistsError:
                pass


def personal_profile(install):
    data = Path(os.environ.get("XDG_DATA_HOME", ""))
    if not data.is_absolute():
        data = Path.home() / ".local/share"
    install_id = hashlib.sha256(os.fsencode(install)).hexdigest()
    state = data / "orbiter/installations" / install_id
    state.mkdir(mode=0o700, parents=True, exist_ok=True)
    profile = json.loads((install / "Launchpad profile.json").read_text(encoding="utf-8"))
    for field in ("executable", "assets", "data", "planets", "modules", "keymap", "help", "xrsoundAssets"):
        if profile.get(field):
            profile[field] = str(install / profile[field])

    default = Path(os.path.abspath(install / profile["config"]))
    config = state / "Orbiter.cfg"
    seed_file(default, config)
    profile["config"] = str(config)
    saves = state / "Scenarios"
    saves.mkdir(exist_ok=True)
    if "scenarioConfigs" in profile:
        # Launchpad normally resolves both sides relative to the installed profile.
        if not isinstance(profile["scenarioConfigs"], dict):
            raise ValueError("scenarioConfigs must map scenario paths to configuration paths")
        shared_saves = Path(os.path.abspath(install / profile["saves"])) if profile.get("saves") else None
        overrides = {}
        for scenario, setting in profile["scenarioConfigs"].items():
            if not scenario or not isinstance(setting, str) or not setting:
                raise ValueError("Each scenarioConfigs entry needs a scenario and configuration path")
            source = Path(os.path.abspath(install / setting))
            personal = config
            if source != default:
                identity = hashlib.sha256(os.fsencode(source)).hexdigest()
                personal = state / "configs" / identity / source.name
                personal.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                if source.is_file():
                    seed_file(source, personal)
            scene = Path(os.path.abspath(install / scenario))
            if shared_saves and scene.is_relative_to(shared_saves):
                # Named saves are discovered under the new personal save directory.
                personal_scene = saves / scene.relative_to(shared_saves)
                if scene.is_file():
                    personal_scene.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                    seed_file(scene, personal_scene)
                scene = personal_scene
            overrides[str(scene)] = str(personal)
        profile["scenarioConfigs"] = overrides
    profile["saves"] = str(saves)
    destination = state / "Launchpad profile.json"
    with tempfile.NamedTemporaryFile(dir=state, mode="w", encoding="utf-8", delete=False) as output:
        json.dump(profile, output, indent=2)
    os.replace(output.name, destination)
    return destination


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--prepare-profile":
        print(personal_profile(Path(sys.argv[2]).resolve(strict=True)))
        sys.exit(0)
    root = Path(__file__).resolve().parent
    launcher = root / "runtime/bin/orbiter-launchpad"
    os.execv(launcher, [str(launcher), "--profile", str(personal_profile(root)), *sys.argv[1:]])
