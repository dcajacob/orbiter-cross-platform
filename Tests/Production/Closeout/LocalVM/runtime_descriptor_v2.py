"""Declared roots and separated runtime roles for local Windows captures (v2)."""
import hashlib
from pathlib import Path, PureWindowsPath
import re
import shutil
import sys

PROTOCOL = 'phase6-local-windows-vm-v2'
ORIGINAL = 'f725194209634f7fd5d1d44d426cfa9b5e303e37'
ROLES = ('application', 'sdk', 'observer', 'runner')
ROOTS = ('share', 'source', 'output', 'build', 'preserved', 'data', 'planets', 'mesa')


def capture_selection(config):
    """Keep explicit diagnostic selections distinct even when all cases are named."""
    scope=config.get('capture_scope', {'kind':'full38'})
    require(scope['kind'] in ('full38','diagnostic'), 'Explicit full38 or diagnostic capture scope required')
    all_cases=['remaining_stock_'+str(i).zfill(3) for i in range(1,39)]
    diagnostic=scope['kind']=='diagnostic'
    require(set(scope)==({'kind','cases'} if diagnostic else {'kind'}),'Capture scope has undeclared selection fields')
    cases=scope['cases'] if diagnostic else all_cases
    require(type(cases) is list and cases and all(type(case) is str for case in cases) and
            cases==sorted(set(cases)) and set(cases)<=set(all_cases),
            'Explicit valid ordered diagnostic scene selection required')
    workers=config.get('scene_workers',2)
    require(type(workers) is int and workers in (1,2),'At most two actual Windows scene workers required')
    return dict(diagnostic_only=diagnostic,cases=cases,scene_workers=workers,expected_processes=4*len(cases),
                expected_presents=4*len(cases)*960,
                arguments=[part for case in cases for part in ('--diagnostic-case',case)] if diagnostic else [])


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def windows_path(value):
    require(isinstance(value, str) and not any(ord(c) < 32 for c in value), 'Invalid Windows path')
    path = PureWindowsPath(value)
    require(path.is_absolute() and re.fullmatch('[A-Za-z]:', path.drive) and '..' not in path.parts and
            not any(':' in part for part in path.parts[1:]), 'Absolute local-volume Windows path required')
    return path


def validate(config):
    require(config['transport_protocol'] == PROTOCOL, 'Unknown local transport protocol')
    require(set(config['roots']) == set(ROOTS), 'Complete explicit Windows roots required')
    roots = {name: windows_path(value) for name, value in config['roots'].items()}
    for field in ROOTS[1:]:
        require(windows_path(config[field]) == roots[field], 'Legacy field differs from declared root: ' + field)
    for name in ('source', 'build', 'preserved', 'data', 'planets', 'mesa'):
        require(not roots['output'].is_relative_to(roots[name]) and
                not roots[name].is_relative_to(roots['output']), 'Output overlaps protected root: ' + name)
    require(roots['output'].drive.lower() != roots['share'].drive.lower(),
            'VM outputs and exported host share must use separate volumes')
    require(set(config['roles']) == set(ROLES), 'Explicit application/SDK/observer/runner roles required')
    for role, identity in config['roles'].items():
        require(re.fullmatch('[0-9a-f]{40}', identity['commit']) and
                re.fullmatch('[0-9a-f]{64}', identity['manifest_sha256']), 'Immutable role identity required: ' + role)
        manifest = windows_path(identity['manifest_path'])
        allowed = roots['preserved'] if role in ('application', 'sdk') else roots['build'] if role == 'observer' else roots['share']
        require(manifest.is_relative_to(allowed), 'Role manifest outside declared owning root: ' + role)
    require(config['cohort'] in ('original-windows', 'current-windows'), 'Explicit Windows cohort required')
    require(config['roles']['observer']['commit'] == config['source_commit'], 'Observer source role differs')
    if config['cohort'] == 'original-windows':
        require(config['roles']['application']['commit'] == config['roles']['sdk']['commit'] == ORIGINAL and
                config['reference_variant'] == 'remaining-stock-repaired-sources-v4',
                'Original application/SDK and declared repaired-module v4 required')
    else:
        require(config['roles']['application']['commit'] == config['roles']['sdk']['commit'],
                'Current Windows application and SDK must match')
    for role in ('worker', 'bootstrap'):
        require(windows_path(config[role + '_script']).is_relative_to(roots['share']) and
                re.fullmatch('[0-9a-f]{64}', config[role + '_sha256']), 'Runner script is outside declared share')
    require(windows_path(config['export']).is_relative_to(roots['share']), 'Export outside declared host share')
    selection=capture_selection(config)
    # A diagnostic selection containing all 38 scenes still needs the same
    # storage as a full capture, while retaining diagnostic-only evidence scope.
    minimum=max(1024**3,(8*1024**3*len(selection['cases'])+37)//38)
    require(type(config['minimum_free_bytes']) is int and config['minimum_free_bytes'] >= minimum,
            'Insufficient declared full38/diagnostic capacity reserve')
    return roots


def preflight(config):
    require(sys.platform == 'win32', 'Actual Windows root validation required')
    roots = validate(config)
    for name, pure in roots.items():
        path = Path(pure)
        if name == 'output':
            require(not path.exists() and path.parent.is_dir(), 'Fresh local output root required')
        else:
            require(path.is_dir() and path.resolve() == path, 'Missing or redirected declared root: ' + name)
    for role, identity in config['roles'].items():
        require(sha(identity['manifest_path']) == identity['manifest_sha256'], 'Actual role manifest bytes differ: ' + role)
    space = shutil.disk_usage(Path(roots['output']).parent)
    require(space.free >= config['minimum_free_bytes'], 'Insufficient VM capacity; archive duplicates before running')
    witness = Path(roots['share']) / config['share_witness']['path']
    relative = PureWindowsPath(config['share_witness']['path'])
    require(not relative.is_absolute() and '..' not in relative.parts and ':' not in str(relative),
            'Unsafe share witness path')
    require(sha(witness) == config['share_witness']['sha256'], 'Actual host-share witness bytes differ')
    return dict(status='passed-actual-Windows-root-and-capacity-preflight', protocol=PROTOCOL,
                roots={name: str(path) for name, path in roots.items()}, free_bytes=space.free,
                minimum_free_bytes=config['minimum_free_bytes'], share_witness_sha256=sha(witness))
