"""Start an installed Linux Launchpad with a profile in the user's data directory."""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile


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

    config = state / "Orbiter.cfg"
    if not config.exists():
        # Publish the complete seed once, including when two launchers start together.
        with tempfile.NamedTemporaryFile(dir=state) as seed:
            seed.write((install / profile["config"]).read_bytes())
            seed.flush()
            try:
                os.link(seed.name, config)
            except FileExistsError:
                pass
    profile["config"] = str(config)
    saves = state / "Scenarios"
    saves.mkdir(exist_ok=True)
    profile["saves"] = str(saves)
    destination = state / "Launchpad profile.json"
    with tempfile.NamedTemporaryFile(dir=state, mode="w", encoding="utf-8", delete=False) as output:
        json.dump(profile, output, indent=2)
    os.replace(output.name, destination)
    return destination


if __name__ == "__main__":
    root = Path(__file__).resolve().parent
    launcher = root / "runtime/bin/orbiter-launchpad"
    os.execv(launcher, [str(launcher), "--profile", str(personal_profile(root)), *sys.argv[1:]])
