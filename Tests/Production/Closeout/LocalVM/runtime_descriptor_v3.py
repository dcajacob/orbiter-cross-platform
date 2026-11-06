"""Local Windows transport with an explicit owner for the declared source tree.

The original v1/v2 capture readers remain available at their existing versions.
This descriptor validates execution identities; each gate still audits its scope.
"""
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import shutil
import sys
try:
    from .runtime_descriptor_v2 import ROOTS, ROLES, require, sha, windows_path
except ImportError:
    from runtime_descriptor_v2 import ROOTS, ROLES, require, sha, windows_path

PROTOCOL='phase6-local-windows-vm-v3'


def validate(config):
    require(config['transport_protocol']==PROTOCOL,'Unknown local transport protocol')
    require(set(config['roots'])==set(ROOTS),'Complete explicit Windows roots required')
    roots={name:windows_path(value) for name,value in config['roots'].items()}
    for name in ROOTS[1:]:
        require(windows_path(config[name])==roots[name],'Declared root differs: '+name)
    for name in ('source','build','preserved','data','planets','mesa'):
        require(not roots['output'].is_relative_to(roots[name]) and not roots[name].is_relative_to(roots['output']),
                'Output overlaps protected root: '+name)
    require(roots['output'].drive.lower()!=roots['share'].drive.lower(),'VM output must remain separate from the host share')
    require(set(config['roles'])==set(ROLES),'Complete independent runtime roles required')
    for role,identity in config['roles'].items():
        require(re.fullmatch('[0-9a-f]{40}',identity['commit']) and re.fullmatch('[0-9a-f]{64}',identity['manifest_sha256']),
                'Immutable runtime role required: '+role)
        allowed=roots['preserved'] if role in ('application','sdk') else roots['build'] if role=='observer' else roots['share']
        require(windows_path(identity['manifest_path']).is_relative_to(allowed),'Role manifest outside its owning root')
    require(config['cohort']=='current-windows' and config['roles']['application']['commit']==config['roles']['sdk']['commit'],
            'Current application and SDK must match')
    require(config['source_role'] in ROLES and config['source_commit']==config['roles'][config['source_role']]['commit'],
            'Actual source-tree owner differs from its declared role')
    scope=config['capture_scope']
    require(scope['kind'] in ('diagnostic','complete') and re.fullmatch('[a-z0-9-]+',scope['gate']),
            'Explicit gate scope required')
    cases=scope['cases'];require(type(cases) is list and cases and cases==sorted(set(cases)),
                                'Unique ordered entry points required')
    for name in cases:
        path=PurePosixPath(name)
        require(str(path)==name and not path.is_absolute() and '..' not in path.parts and '\\' not in name and ':' not in name,
                'Safe repository-relative entry point required')
    for role in ('worker','bootstrap'):
        require(windows_path(config[role+'_script']).is_relative_to(roots['share']) and
                re.fullmatch('[0-9a-f]{64}',config[role+'_sha256']),'Pinned local runner required')
    require(windows_path(config['export']).is_relative_to(roots['share']),'Export outside declared share')
    require(type(config['minimum_free_bytes']) is int and config['minimum_free_bytes']>=1024**3,
            'At least one GiB of explicitly reserved local capacity required')
    return roots


def preflight(config):
    require(sys.platform=='win32','Actual Windows preflight required')
    roots=validate(config)
    for name,pure in roots.items():
        path=Path(pure)
        if name=='output':require(not path.exists() and path.parent.is_dir(),'Fresh output root required')
        else:require(path.is_dir() and path.resolve()==path,'Missing or redirected root: '+name)
    for role,identity in config['roles'].items():
        require(sha(identity['manifest_path'])==identity['manifest_sha256'],'Actual role manifest differs: '+role)
    witness=PureWindowsPath(config['share_witness']['path'])
    require(not witness.is_absolute() and '..' not in witness.parts and ':' not in str(witness),'Unsafe share witness')
    require(sha(Path(roots['share'])/witness)==config['share_witness']['sha256'],'Actual host-share witness differs')
    space=shutil.disk_usage(Path(roots['output']).parent)
    require(space.free>=config['minimum_free_bytes'],'Insufficient local Windows capacity')
    return dict(status='passed-actual-Windows-root-and-capacity-preflight',protocol=PROTOCOL,
        roots={name:str(path) for name,path in roots.items()},free_bytes=space.free,
        minimum_free_bytes=config['minimum_free_bytes'],share_witness_sha256=config['share_witness']['sha256'])
