#!/usr/bin/env python3
"""Capture new production Windows candidates; never replace accepted references.

Initial capture requires the frozen pre-extraction production sources. With
--reference, verify current code against immutable evidence without refreshing it.
"""
import argparse
import csv
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Portable'))
from trace_tools import compare, require, LIMITS, norm
from mesa_runtime import digest

ROOT = Path(__file__).resolve().parents[2]
EPOCH = 51982.5
STEPS = 6000


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])


def physics_trace(path):
    with path.open(newline='') as stream:
        reader = csv.DictReader(stream)
        fields = 'step sim_seconds mjd rx ry rz vx vy vz qx qy qz qw wx wy wz'.split()
        require(reader.fieldnames == fields, 'unexpected physics trace columns')
        rows = [(int(row['step']), *(float(row[f]) for f in fields[1:])) for row in reader]
    require(len(rows) == 601, 'production physics trace must contain 601 finalized states')
    for step, row in zip(range(0, STEPS+1, 10), rows):
        require(row[0] == step and row[1] == step, 'production trace step/time mismatch')
        require(all(math.isfinite(x) for x in row), 'nonfinite production physics sample')
        require(abs(row[2] - EPOCH - step/86400) <= LIMITS['mjd_days'], 'production MJD mismatch')
        require(abs(norm(row[9:13])-1) <= 1e-12, 'non-unit production quaternion')
    return rows


def validate(directory, controls):
    physics = physics_trace(directory/'trace.csv')
    with (directory/'production-state.csv').open(newline='') as stream:
        states = list(csv.DictReader(stream))
    require(len(states) == 601*5, 'missing production object samples')
    masses = []
    maximum_spin = 0.0
    for i, row in enumerate(states):
        step = i//5*10
        require(int(row['step']) == step and float(row['seconds']) == step, 'wrong observation time')
        require(row['object'] == ('Sun','Earth','Moon','ISS','PB')[i%5], 'wrong production object order')
        require(abs(float(row['mjd'])-EPOCH-step/86400) <= LIMITS['mjd_days'], 'wrong production epoch')
        require(all(math.isfinite(float(v)) for k,v in row.items() if k != 'object'), 'nonfinite object state')
        matrix = [[float(row[f'm{r}{c}']) for c in range(1,4)] for r in range(1,4)]
        require(all(abs(sum(matrix[r][k]*matrix[c][k] for k in range(3))-(1 if r == c else 0)) <= 1e-12
                    for r in range(3) for c in range(3)), 'invalid production rotation matrix')
        if row['object'] == 'PB':
            masses.append((float(row['mass']), float(row['fuel'])))
            maximum_spin = max(maximum_spin, norm(float(row[k]) for k in ('wx','wy','wz')))
    require(masses[0][1] > 0, 'source-built ShuttlePB propellant missing')
    if controls:
        require(masses[-1][1] < masses[0][1], 'scheduled engines did not consume propellant')
        # Independent bookkeeping from the stock PB thrust/ISP and tick schedule:
        # main: 30000*.5*60/50000; right: 2*200*.25*20/50000;
        # pitch-up: 4*200*.1*5/50000. No propagation is reproduced here.
        expected_fuel = masses[0][1] - 18.048
        require(abs(masses[-1][1]-expected_fuel) <= max(1e-8, abs(expected_fuel)*1e-8),
                'stock ShuttlePB propellant accounting exceeds the declared budget')
        require(maximum_spin > 1e-8, 'scheduled pitch RCS did not rotate the production vessel')
    else:
        require(masses[-1] == masses[0], 'unpowered reference lost propellant or mass')
    events = list(csv.DictReader((directory/'production-events.csv').open(newline='')))
    require(len(events) == 6001*5+1 and events[-1] ==
            dict(step='6001', callback='end', group='', level=''), 'incomplete callback lifecycle')
    for tick in range(6001):
        block = events[tick*5:tick*5+5]
        require([row['callback'] for row in block] == ['pre','control','control','control','post'],
                'unexpected production test-driver callback order')
        require(all(int(row['step']) == tick for row in block), 'callback step mismatch')
        expected = [0.5 if controls and 100 <= tick < 160 else 0,
                    0.25 if controls and 200 <= tick < 220 else 0,
                    0.1 if controls and 300 <= tick < 305 else 0]
        require([row['group'] for row in block[1:4]] == ['main','right','pitchup'] and
                [float(row['level']) for row in block[1:4]] == expected, 'control schedule mismatch')
    log = (directory/'Orbiter.log').read_text(errors='replace')
    require('spice.dll' in log and 'orbiter.bsp - OK' in log and 'ShuttlePB' in log,
            'actual SPICE/ShuttlePB initialization evidence is missing')
    require('Couldn\'t load kernel' not in log and 'outside loaded kernel' not in log,
            'SPICE data/coverage error')
    require((directory/'Scenarios/(Current state).scn').is_file(), 'production save-at-exit missing')
    return dict(samples=601, objects=5, callbacks=len(events), initial_mass_kg=masses[0][0],
                final_mass_kg=masses[-1][0], initial_fuel_kg=masses[0][1], final_fuel_kg=masses[-1][1]), physics


def link_or_copy(source, target):
    target = Path(target)
    if target.exists():
        target.unlink()  # never overwrite the inode of a previously linked asset
    try:
        os.link(source, target)
    except OSError:
        shutil.copy2(source, target)
    return str(target)


def run(executable, data, directory, controls):
    directory.mkdir()
    for path in executable.parent.iterdir():
        if path.is_file() and path.suffix.lower() in ('.exe','.dll'):
            shutil.copy2(path, directory/path.name)
    # Configuration and modules must come from this source build, never release
    # DLLs or a different Orbiter installation. Data is shared read-only by link.
    for name in ('Config','Modules','Meshes','Images','Script','Textures','Textures2'):
        source = executable.parent/name
        if source.is_dir():
            shutil.copytree(source, directory/name, copy_function=link_or_copy)
    for name in ('Kernels','Textures','Textures2','GravityModels','Fonts'):
        require((data/name).is_dir(), 'required production data directory missing: '+name)
        shutil.copytree(data/name, directory/name, dirs_exist_ok=True, copy_function=link_or_copy)
    (directory/'Scenarios').mkdir()
    fixtures = Path(__file__).with_name('Fixtures')
    shutil.copy2(fixtures/'Sol-ISS-ShuttlePB.scn', directory/'Scenarios/Reference.scn')
    shutil.copy2(fixtures/'Orbiter.cfg', directory/'Orbiter.cfg')
    if controls:
        (directory/'production-controls.enabled').write_text('tick-indexed SDK controls\n')
    argv = [str(directory/executable.name), '--scenariox=Reference', '--fixedstep=1',
            '--maxframes=6001', '--physics-trace=trace.csv', '--trace-vessel=PB', '--trace-primary=Earth']
    (directory/'invocation.json').write_text(json.dumps(dict(argv=argv, observed_steps=6000,
        application_frames=6001, sampling='PreStep S0 before control; existing finalized PhysicsTrace',
        input_sha256={p.relative_to(directory).as_posix():digest(p) for parent in ('Config','Meshes','Scenarios')
                      for p in (directory/parent).rglob('*') if p.is_file()}), indent=2)+'\n')
    with (directory/'console.txt').open('w') as console:
        subprocess.run(argv, cwd=directory, stdout=console, stderr=subprocess.STDOUT, check=True, timeout=240)
    return validate(directory, controls)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--orbiter', type=Path, required=True)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--configuration', choices=['Debug','Release'], required=True)
    parser.add_argument('--reference', type=Path,
                        help='verify a current application against accepted evidence; never create a new baseline')
    args = parser.parse_args()
    require(sys.platform == 'win32', 'production reference capture requires native Windows')
    require(not git('status','--porcelain','--untracked-files=no').strip(), 'capture requires committed sources')
    lock = json.loads(Path(__file__).with_name('production-source.lock.json').read_text())
    if args.reference:
        from frozen_reference import load_reference
        load_reference(args.reference)
    else:
        require(not git('diff','--name-only',lock['source_commit'],'--','Src','Orbitersdk','Extern','CMakeLists.txt',
                        'Config','Meshes','Textures','Textures2','GravityModels','Kernels','Scenarios','Script').strip(),
                'production implementation/dependencies changed before reference capture')
        for path in lock['source_sha256']:
            original = git('show', lock['source_commit']+':'+path).replace(b'\r\n',b'\n')
            require((ROOT/path).read_bytes().replace(b'\r\n',b'\n') == original,
                    'production source changed before reference capture: '+path)
    executable, data, output = args.orbiter.resolve(), args.data.resolve(), args.output.resolve()
    data_lock = json.loads(Path(__file__).with_name('stock-data.lock.json').read_text())
    for name, expected in data_lock['data_files'].items():
        require((data/name).is_file() and digest(data/name) == expected['sha256'],
                'missing or incompatible production data: '+name)
    require(executable.is_file() and (executable.parent/'Modules/Plugin/ProductionReferenceDriver.dll').is_file(),
            'production application or test driver is missing')
    for path in ('Modules/ShuttlePB.dll','Modules/Celbody/spice.dll'):
        require((executable.parent/path).is_file(), 'required source-built module missing: '+path)
    output.mkdir(parents=True, exist_ok=False)
    report = dict(status='candidate', source_commit=git('rev-parse','HEAD').decode().strip(),
                  production_source_commit=lock['source_commit'], configuration=args.configuration,
                  executable_sha256=digest(executable), data_lock_sha256=digest(Path(__file__).with_name('stock-data.lock.json')),
                  vessel_only_fields=dict(objects=['ISS','PB'], fields=['wx','wy','wz','fuel','ground']),
                  module_sha256={p.relative_to(executable.parent).as_posix():digest(p) for p in
                                 (executable.parent/'Modules').rglob('*.dll')}, cases={})
    try:
        for name, controls in [('orbit',False),('controls',True)]:
            first, rows = run(executable, data, output/name, controls)
            repeat, repeated = run(executable, data, output/(name+'-repeat'), controls)
            report['cases'][name] = dict(first=first, repeat=repeat, numerical_comparison=compare(rows,repeated))
            for trace in ('trace.csv','production-state.csv','production-events.csv','production-objects.txt'):
                require((output/name/trace).read_bytes() == (output/(name+'-repeat')/trace).read_bytes(),
                        'production repeat is not byte-identical: '+name+'/'+trace)
        report['status'] = 'repeatable-candidate; cross-configuration acceptance pending'
        if args.reference:
            from frozen_reference import compare_capture
            report['frozen_reference'] = compare_capture(args.reference,output)
            report['status'] = 'repeatable-candidate; frozen-reference verification passed'
    except Exception as error:
        report.update(status='failed', error=str(error))
        raise
    finally:
        (output/'production-reference.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        raise SystemExit(str(error)) from error
