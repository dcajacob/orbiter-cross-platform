"""Retrieve the previously verified Phase 8 stock installer."""
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
from zipfile import ZipFile

ARGS = ["gh", "api", "repos/dcajacob/orbiter-cross-platform/actions/artifacts/14143683775"]
metadata = json.loads(subprocess.check_output(ARGS))
assert metadata["workflow_run"]["head_sha"] == "91db1aa0cc381c441bfd2ed20a1818e8d65dc868"
archive = subprocess.check_output([*ARGS[:-1], ARGS[-1] + "/zip"])
checksum = hashlib.sha256(archive).hexdigest()
assert metadata["digest"] == "sha256:2cb43d6ae4a8adca9fa115151b02a978a653dea9b16f50bf5f2aa01719074af5"
assert "sha256:" + checksum == metadata["digest"] and len(archive) == metadata["size_in_bytes"]
with ZipFile(io.BytesIO(archive)) as bundle:
    installer = bundle.read("orbiter-stock-data.pyz")
assert hashlib.sha256(installer).hexdigest() == "380062a5372c625208e3e3a8ca08e48f7f97cf65c05349876aeefcd781ec9f7a"
destination = Path(sys.argv[1])
destination.parent.mkdir(parents=True, exist_ok=True)
with destination.open("xb") as stream:
    stream.write(installer)
