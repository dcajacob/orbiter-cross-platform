#!/usr/bin/env python3
"""Freeze/verify the production input inventory without rewriting any reference.

--create is an explicit first-capture action and refuses an existing manifest.
Normal CI only verifies the recorded source tree and unchanged stock scenarios.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

SOURCE = '38b7c627878ea893390675616897071f8bb8e90f'
DONOR = 'ad96494482e6101afebf1c635e4e1f542623b51d'
ROOT = Path(__file__).resolve().parents[2]
MANIFEST = Path(__file__).with_name('production-source.lock.json')


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])


def sha(data):
    return hashlib.sha256(data).hexdigest()


def create():
    if MANIFEST.exists():
        raise ValueError('frozen production inventory already exists; do not overwrite it')
    files = git('ls-tree', '-r', '--name-only', SOURCE).decode().splitlines()
    selected = [p for p in files if p.startswith(('Src/Orbiter/', 'Orbitersdk/include/', 'Kernels/'))
                or p.startswith('Scenarios/') and p.endswith('.scn')]
    hashes = {p: sha(git('show', SOURCE + ':' + p)) for p in selected}
    scenarios = []
    for path in selected:
        if not path.endswith('.scn'):
            continue
        text = git('show', SOURCE + ':' + path).decode('cp1252')
        ships = re.search(r'^BEGIN_SHIPS\s*\n(.*?)^END_SHIPS', text, re.M | re.S)
        objects = []
        if ships:
            for line in ships[1].splitlines():
                if line and not line[0].isspace() and line != 'END' and not line.startswith(';'):
                    name, _, vessel = line.partition(':')
                    objects.append(dict(name=name, vessel_class=vessel or name))
        system = re.search(r'^\s*System\s+(\S+)', text, re.M)
        scenarios.append(dict(path=path, sha256=hashes[path],
                              system=system[1] if system else None, objects=objects))
    cmake = [p for p in files if p.endswith('/CMakeLists.txt') and
             p.startswith(('Src/Vessel/', 'Src/Celbody/', 'Src/Module/', 'Src/Plugin/', 'Sound/'))]
    modules = []
    for path in cmake:
        text = git('show', SOURCE + ':' + path).decode('utf-8', errors='replace')
        modules.append(dict(build_file=path, sha256=sha(text.encode()),
                            targets=re.findall(r'add_library\s*\(\s*([^\s)]+)', text, re.I),
                            native_status='not-ported'))
    header = git('show', SOURCE + ':Orbitersdk/include/GraphicsAPI.h').decode('cp1252')
    callbacks = sorted(set(re.findall(r'\b(clbk\w+)\s*\(', header)))
    assets = [p for p in files if any('/' + part + '/' in '/' + p for part in
              ('Meshes', 'Textures', 'Textures2', 'GravityModels', 'Kernels'))]
    result = dict(schema=1, source_commit=SOURCE, source_tree=git('rev-parse', SOURCE+'^{tree}').decode().strip(),
                  donor_commit=DONOR, scenario_count=len(scenarios), scenarios=scenarios,
                  source_sha256=hashes, module_build_files=modules, graphics_callbacks=callbacks,
                  tracked_asset_git_blobs={p: git('rev-parse', SOURCE+':'+p).decode().strip() for p in assets},
                  missing_external_data=['SPICE orbiter.bsp and coverage', 'production planetary tile packages'],
                  status='source-frozen; production runtime references not captured')
    if len(scenarios) != 157:
        raise ValueError('pinned stock corpus must contain 157 scenarios')
    MANIFEST.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    print(f"Frozen {len(hashes)} source/config/scenario hashes, {len(modules)} module build files, "
          f"{len(callbacks)} graphics callbacks and {len(assets)} tracked assets")


def verify():
    lock = json.loads(MANIFEST.read_text())
    if lock['source_commit'] != SOURCE or lock['donor_commit'] != DONOR:
        raise ValueError('unexpected baseline or donor revision')
    if git('rev-parse', SOURCE+'^{tree}').decode().strip() != lock['source_tree']:
        raise ValueError('production source tree identity changed')
    for path, expected in lock['source_sha256'].items():
        if sha(git('show', SOURCE+':'+path)) != expected:
            raise ValueError('frozen source digest mismatch: '+path)
    current = sorted(p.relative_to(ROOT).as_posix() for p in (ROOT/'Scenarios').rglob('*.scn'))
    if current != sorted(row['path'] for row in lock['scenarios']):
        raise ValueError('stock scenario corpus changed')
    for row in lock['scenarios']:
        if sha((ROOT/row['path']).read_bytes()) != row['sha256']:
            raise ValueError('stock scenario contents changed: '+row['path'])
    print(f"Verified frozen source {SOURCE}, all 157 original scenarios and the graphics/module inventory")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--create', action='store_true')
    group.add_argument('--verify', action='store_true')
    options = parser.parse_args()
    create() if options.create else verify()
