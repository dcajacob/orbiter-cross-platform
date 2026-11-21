"""Verify the reviewed OpenGL source changes and the historical source audit separately."""
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile

from PhysicsV2.transforms import BASELINE

ROOT = Path(__file__).resolve().parents[2]

# The extraction ledger predates OpenGL atmospheric scattering, the assembly
# and airfoil corrections, DelThruster and the legacy backward-drag fix.
REVIEWED_SHA256 = {
    'OVP/OGLClient/Native/CMakeLists.txt': 'dd72aa4aabb7720656bfa6a0288d17929fda28d072f962d9f9f16c69ce439c56',
    'Src/Orbiter/SuperVessel.cpp': 'ff62c190556d8779b64ec190ad3cc482a62a466fe6a242d91b852cf0b69374eb',
    'Src/Orbiter/SuperVessel.h': '240cedd7c7f4820b7cca79f0a0893e2d63720de1a1e2b77540bc4a7a07f11059',
    'Src/Orbiter/Vessel.cpp': 'd170211e2d28cbbeb85815276def18e1bb4e414e43d94410a34f51a5d8b8bb6e',
    'Src/Orbiter/Vessel.h': '60d1a4fc8547d67eabbb073a4d1232a873cc62573baea5de7cd51f4bbb62b468',
}


def verify():
    for path, expected in REVIEWED_SHA256.items():
        source = (ROOT / path).read_bytes().replace(b'\r\n', b'\n')
        if hashlib.sha256(source).hexdigest() != expected:
            raise ValueError('Unreviewed OpenGL source: ' + path)

    # The caller requires a clean candidate checkout. Preserve every other
    # committed input in the audit copy, including the source guards themselves.
    # Only the candidate executable is used for the subsequent flight captures.
    revision = subprocess.check_output(['git', '-C', ROOT, 'rev-parse', 'HEAD'], text=True).strip()
    with tempfile.TemporaryDirectory(prefix='orbiter-source-audit-') as temporary:
        view = Path(temporary) / 'source'
        subprocess.run(['git', 'clone', '--quiet', '--shared', '--no-checkout', ROOT, view], check=True)
        subprocess.run(['git', '-C', view, 'checkout', '--quiet', '--detach', revision], check=True)
        subprocess.run(['git', '-C', view, 'restore', '--source', BASELINE, '--', *REVIEWED_SHA256], check=True)
        subprocess.run([sys.executable, '-B', view / 'Tests/Production/observation_source.py'], cwd=view, check=True)
    print('Verified the reviewed OpenGL source changes and the original extraction audit')


if __name__ == '__main__':
    verify()
