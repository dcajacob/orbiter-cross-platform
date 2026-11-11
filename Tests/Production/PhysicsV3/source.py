#!/usr/bin/env python3
"""Bind the assembly state-buffer repair to v2 and replay unchanged v2 guards on v2."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASELINE = '0d7d0d2427a900e76766fe16884880834eaa42ef'
VERSION = 'assembly-contact-v3'
TARGET = 'Src/Orbiter/SuperVessel.cpp'
OLD_BUILDER = 'Tests/Production/RemainingVessels/build_native.py'
BUILDER = 'Tests/Production/PhysicsV3/build_native.py'
INPUTS = tuple('Tests/Production/PhysicsV3/' + name for name in
               ('source.py', 'version.json', 'correction.patch', 'build_native.py', 'Version.Test.py', 'README.md'))

def require(value, message):
    if not value:
        raise ValueError(message)

def git(*args, root=ROOT):
    return subprocess.check_output(['git', '-C', str(root), *args])

def normalized(body):
    return body.replace(b'\r\n', b'\n')

def digest(body):
    return hashlib.sha256(body).hexdigest()

def corrected_physics(body):
    anchor = '\t\tRigidBody::Update (force);'
    require(body.count(anchor) == 1, 'Exact original dynamic assembly integration boundary required')
    return body.replace(anchor,
        '\t\t// Assemblies are outside the general body update list. Preserve the\n'
        '\t\t// initial state separately so a collision retry can restart the step.\n'
        '\t\tBeginStateUpdate();\n' + anchor + '\n\t\tEndStateUpdate();')

def versioned_builder(body):
    anchor = "p.add_argument('--physics-version',choices=('original','assembly-contact-v2'),default='original')"
    require(body.count(anchor) == 1 and body.count('from PhysicsV2 import source as physics_source') == 1,
            'Exact unchanged original v2 builder required')
    return body.replace(anchor, "p.add_argument('--physics-version',choices=('assembly-contact-v3',),default='assembly-contact-v3')").replace(
        'from PhysicsV2 import source as physics_source', 'from PhysicsV3 import source as physics_source')

def expected_sources():
    return {
        TARGET: corrected_physics(normalized(git('show', BASELINE + ':' + TARGET)).decode()).encode(),
        BUILDER: versioned_builder(normalized(git('show', BASELINE + ':' + OLD_BUILDER)).decode()).encode(),
    }

def validate_current(root=ROOT):
    root = Path(root).resolve()
    manifest = json.loads((root / 'Tests/Production/PhysicsV3/version.json').read_text())
    require(manifest['physics_version'] == VERSION and manifest['baseline_source'] == BASELINE and
            manifest['previous_physics_version'] == 'assembly-contact-v2', 'Exact separately versioned baseline required')
    expected = expected_sources()
    checks = {}
    for name, body in expected.items():
        actual = normalized((root / name).read_bytes())
        require(actual == body, 'Unreviewed physics or builder change: ' + name)
        checks[name] = digest(actual)
    require(checks[TARGET] == manifest['corrected_source_sha256_lf'] and
            digest(normalized(git('show', BASELINE + ':' + TARGET))) == manifest['original_source_sha256_lf'],
            'Exact state-buffer correction source required')
    require(digest((root / 'Tests/Production/PhysicsV3/correction.patch').read_bytes()) == manifest['patch_sha256'],
            'Exact incremental physics patch required')
    for name, key in [('Tests/Production/PhysicsV2/version.json', 'previous_version_manifest_sha256'),
                      (OLD_BUILDER, 'original_builder_sha256')]:
        actual = normalized((root / name).read_bytes())
        require(actual == normalized(git('show', BASELINE + ':' + name)) and digest(actual) == manifest[key],
                'Original v2 version/builder must remain unchanged: ' + name)
    for name, pin in manifest['original_guard_files_sha256_lf'].items():
        require(digest(normalized((root / name).read_bytes())) == pin, 'Original guard or acceptance bytes changed: ' + name)
    changes = set(git('diff', '--name-only', BASELINE, '--', root=root).decode().splitlines())
    changes.update(git('ls-files', '--others', '--exclude-standard', root=root).decode().splitlines())
    allowed = lambda name: name == TARGET or name.startswith('Tests/Production/PhysicsV3/')
    require(all(allowed(name) for name in changes),
            'Original control, capture, tolerance or unrelated source changed: ' + str(sorted(n for n in changes if not allowed(n))))
    return dict(physics_version=VERSION, baseline_source=BASELINE, actual_reviewed_sources_sha256_lf=checks,
                production_files_changed=[TARGET], original_v1_and_v2_guards_captures_tolerances_unchanged=True,
                normal_admission_qualified=False, phase6_complete=False)

def baseline_clone(destination):
    require(not destination.exists(), 'Fresh preserved v2 source view required')
    subprocess.run(['git', 'clone', '--quiet', '--shared', '--no-checkout', str(ROOT), str(destination)], check=True)
    subprocess.run(['git', '-C', str(destination), 'sparse-checkout', 'init', '--no-cone'], check=True)
    sys.path.insert(0, str(HERE.parent))
    from PhysicsV2.source import SCOPES
    (destination / '.git/info/sparse-checkout').write_text(''.join('/' + n + ('/' if '.' not in n.rsplit('/', 1)[-1] else '') + '\n' for n in SCOPES))
    subprocess.run(['git', '-C', str(destination), 'checkout', '--quiet', '--detach', BASELINE], check=True)

def verify(output=None):
    proof = validate_current()
    base = ROOT / 'out/physics-v3-baseline'
    base.mkdir(parents=True, exist_ok=True)
    view = base / 'source'
    if not view.exists():
        baseline_clone(view)
    require(git('rev-parse', 'HEAD', root=view).decode().strip() == BASELINE and
            not git('status', '--porcelain', '--untracked-files=no', root=view).strip(), 'Preserved v2 source view changed')
    log = base / 'original-v2-source-guards.log'
    old_proof = base / 'original-v2-source-guards.json'
    with log.open('w') as stream:
        result = subprocess.run([sys.executable, '-B', str(view / 'Tests/Production/PhysicsV2/source.py'),
                                 '--output', str(old_proof)], cwd=view, stdout=stream, stderr=subprocess.STDOUT)
    require(result.returncode == 0, 'Original v2 source guards must pass their exact retained v2 source; see ' + str(log))
    original = json.loads(old_proof.read_text())
    require(original['actual_source'] == BASELINE and original['physics_version'] == 'assembly-contact-v2' and
            original['all_original_guards_captures_and_tolerances_unchanged'], 'Exact v2-to-original guard chain required')
    require(validate_current() == proof, 'Versioned repair inputs changed during original guard replay')
    proof.update(actual_source=git('rev-parse', 'HEAD').decode().strip(), baseline_view=str(view),
                 previous_version_source_guards=dict(actual_returncode=result.returncode, proof_sha256=digest(old_proof.read_bytes()),
                                                     log_sha256=digest(log.read_bytes())),
                 scope='New assembly state-buffer version; all original v1/v2 captures and failures retain their original identities')
    text = json.dumps(proof, indent=2) + '\n'
    (base / 'verification.json').write_text(text)
    if output:
        Path(output).write_text(text)
    return proof

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    verify(args.output)
    print('Explicit v3 state-buffer correction verified; unchanged v2 and original source guards passed their retained sources')
