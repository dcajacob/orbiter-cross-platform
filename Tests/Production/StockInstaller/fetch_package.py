"""Get a retained Phase 8 preview and verify the artifact and inner archive."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[3]
REPO = "dcajacob/orbiter-cross-platform"


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package")
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    packages = json.loads((ROOT / "Utils/StockDataInstaller/packages.json").read_text())
    locked = packages[args.package]
    endpoint = f"repos/{REPO}/actions/artifacts/{locked['artifact']}"
    metadata = json.loads(subprocess.check_output(["gh", "api", endpoint]))
    assert metadata["workflow_run"]["head_sha"] == locked["source"] and not metadata["expired"]
    assert metadata["digest"] == "sha256:" + locked["artifact_sha256"]
    args.destination.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=args.destination) as work:
        path = Path(work) / "artifact.zip"
        with path.open("wb") as stream:
            subprocess.run(["gh", "api", endpoint + "/zip"], stdout=stream, check=True)
        assert path.stat().st_size == metadata["size_in_bytes"] and digest(path) == locked["artifact_sha256"]
        package = args.destination / args.package
        with zipfile.ZipFile(path) as zip_file, zip_file.open(args.package) as source, package.open("wb") as target:
            shutil.copyfileobj(source, target)
    assert digest(package) == locked["sha256"]


if __name__ == "__main__":
    main()
