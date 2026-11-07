"""Independently inspect scoped class evidence; partial facets never admit a class."""
import argparse
import csv
import math
from pathlib import Path

from contracts import atomic_json, load, require, sha

OBJECTS = {'ISS': 'ProjectAlpha_ISS', 'STS-101': 'Atlantis', 'Leonardo': 'Leonardo_mplm'}
STRINGS = {'object', 'class', 'dock', 'focus', 'attached'}
BAD = ('ERROR: AddressSanitizer', 'ERROR: LeakSanitizer', 'runtime error:',
       'AddressSanitizer:DEADLYSIGNAL', 'Production teardown:',
       'LeakSanitizer has encountered', 'Suppressions used:')


def rows(path):
    with Path(path).open(newline='') as stream:
        return list(csv.DictReader(stream))


def inspect_paused(path):
    path = Path(path).resolve()
    report = load(path)
    require(report['status'] == 'passed-actual-paused-attached-docked-world-lifetimes' and
            report['requested_worlds'] == report['worlds_observed_ready'] == report['clean_contexts'] == 20 and
            report['actual_exitcode'] == 0 and report['actual_pid'] > 0 and
            report['no_preload_observer'] is True and report['sanitizer_suppressions'] is False and
            report['all_guarded_inputs_unchanged'] is True and
            report['native_admission_qualified'] is False and report['phase6_complete'] is False and
            report['original_objects'] == OBJECTS, 'Incomplete paused attachment control')
    require(all(sha(p) == value for p, value in report['guarded_files_sha256'].items()),
            'Paused control owning source, binary, resource or runner changed')
    require(report['guarded_files_sha256'].get(report['actual_executable']) ==
            report['actual_executable_sha256'] == sha(report['actual_executable']),
            'Actual paused executable binding missing')
    require(not any(v in (path.parent / 'console.log').read_text(errors='replace') for v in BAD),
            'Paused control runtime/sanitizer diagnostic')
    keys = report['physical_keys']
    require([(k['code'], k['down']) for k in keys] == [(63, True), (63, False)] * 19 + [(1, True)] and
            all(a['monotonic_ns'] < b['monotonic_ns'] for a, b in zip(keys, keys[1:])),
            'Physical nineteen-F5/normal-Escape schedule differs')
    worlds = []
    for index in range(1, 21):
        folder = path.parent if index == 1 else path.parent / ('session-' + str(index))
        life = load(folder / 'graphics-lifecycle.json')
        require(life == report['lifecycles'][index - 1] and life['context_deleted'] is True and
                life['rendered_frames'] == life['successful_presents'] >= 60,
                'Paused graphics lifetime differs')
        require((folder / 'scene.rgba').stat().st_size == 1280 * 720 * 4,
                'Paused full frame incomplete')
        actual = rows(folder / 'flight-state.csv')
        require(len(actual) == 3 and {r['object']: r['class'] for r in actual} == OBJECTS and
                all(r['tick'] == r['seconds'] == '0' and
                    all(math.isfinite(float(v)) for k, v in r.items() if k not in STRINGS)
                    for r in actual), 'Original finite paused world differs')
        by_name = {r['object']: r for r in actual}
        require(by_name['STS-101']['dock'] == 'ISS' and
                by_name['STS-101']['attached'] == 'Leonardo;' and
                by_name['Leonardo']['attached'] == 'STS-101;', 'Reciprocal paused graph differs')
        events = rows(folder / 'input-events.csv')
        # Escape closes through graphics Poll before the flight event logger;
        # F5 is consumed by the original buffered-flight dispatch in each world.
        require([(int(r['key']), int(r['down'])) for r in events] ==
                ([(63, 1), (63, 0)] if index < 20 else []),
                'Actual dispatch did not consume the nineteen recorded F5 pairs')
        worlds.append(dict(lifecycle=life, files_sha256={p.name: sha(p) for p in folder.iterdir()
                            if p.is_file() and p.name != 'verification.json' and
                            not p.name.startswith('independent-audit')}))
    require(report['successful_presents'] == sum(w['lifecycle']['successful_presents'] for w in worlds) and
            report['finite_original_vessel_rows'] == 60, 'Paused aggregate differs')
    return dict(status='audited-paused-attachment-lifetime-facet-only',
                capture_sha256=sha(path), runtime_identity=report['runtime_identity'],
                actual_simulator_pid=report['actual_pid'], actual_exitcode=report['actual_exitcode'],
                worlds=worlds, real_F5_reloads=19, original_vessels=OBJECTS,
                owning_bytes_unchanged=True, no_preload_observer=True, sanitizer_suppressions=False,
                scope='Twenty paused original ISS/Atlantis/Leonardo worlds. Original bytes seed F5; '
                      'does not establish actual-save persistence, unpaused lifetime, interactions, '
                      'normal admission or a complete class-eligibility gate.',
                native_admission_qualified=False, phase6_complete=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--paused-capture', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), 'Fresh independent class-evidence audit required')
    atomic_json(args.output, inspect_paused(args.paused_capture))
