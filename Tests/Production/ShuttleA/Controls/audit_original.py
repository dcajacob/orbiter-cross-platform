#!/usr/bin/env python3
"""Audit downloaded four-profile original Shuttle-A controls artifacts."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

import capture as controls
from verify_original import compare_state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('artifacts', 'download-manifest', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--producer-commit', required=True)
    args = parser.parse_args()
    controls.require(not args.output.exists(), 'Original controls audit output already exists')
    controls.require(re.fullmatch('[0-9a-f]{40}', args.producer_commit), 'Producer must be an immutable full commit')
    config = controls.settings()
    downloads = json.loads(args.download_manifest.read_text())
    controls.require(downloads['status'] == 'passed' and downloads['source_commit'] == args.producer_commit and
                     len(downloads['artifacts']) == 4, 'Original controls download matrix is incomplete')
    result = dict(status='failed', phase6_complete=False, producer_commit=args.producer_commit,
        application_source=config['application_source'], download_manifest_sha256=controls.digest(args.download_manifest),
        profiles={}, build_comparisons={})
    try:
        profiles = {}
        for configuration in ('Debug', 'Release'):
            for math_profile in ('automatic', 'sse2'):
                profile = configuration+'-'+math_profile
                item = next(i for i in downloads['artifacts'] if i['name'] == 'original-shuttle-a-controls-'+profile)
                archive = controls.ROOT/item['path']
                controls.require(controls.digest(archive) == item['sha256'], 'Downloaded controls archive changed')
                base = args.artifacts/profile
                capture = base/'shuttle-a-controls-original'
                report = json.loads((capture/'controls-report.json').read_text())
                controls.require(report['status'] == 'passed' and not report['failures'] and
                    report['producer'] == 'preserved-original-windows' and report['producer_commit'] == args.producer_commit and
                    report['application_source'] == config['application_source'] and report['configuration'] == configuration and
                    report['math_profile'] == math_profile and report['sources_and_runtime_unchanged'] and
                    set(report['cases']) == {c['id'] for c in config['cases']}, 'Failed, incomplete or mismatched controls capture')
                for name, checksum in report['source_sha256_lf'].items():
                    path = Path(name)
                    controls.require(not path.is_absolute() and '..' not in path.parts, 'Invalid controls source path')
                    original = subprocess.check_output(['git', '-C', str(controls.ROOT), 'show', args.producer_commit+':'+name])
                    # GitHub checks out Windows text with CRLF; source identity is LF normalized.
                    controls.require(hashlib.sha256(original.replace(b'\r\n', b'\n')).hexdigest() == checksum,
                                     'Controls observer source differs from producer commit: '+name)
                runtime = base/'shuttle-a-controls-runtime'
                preserved = json.loads((runtime/'test-runtime.json').read_text())
                client = json.loads((runtime/'control-reference-runtime.json').read_text())
                controls.require(preserved == report['runtime'] and client == report['client'] and
                    preserved['source_commit'] == client['application_source'] == config['application_source'],
                    'Preserved original controls runtime identity differs')
                for name, checksum in {**preserved['files'], **client['client_files_sha256']}.items():
                    if name != 'Modules/Plugin/ProductionCockpitDriver.dll':
                        controls.require(report['binary_sha256'][name] == checksum, 'Preserved original controls binary differs: '+name)
                observer = 'Modules/Plugin/ProductionCockpitDriver.dll'
                controls.require(controls.digest(runtime/observer) == report['binary_sha256'][observer], 'Original controls observer DLL changed')
                for case in config['cases']:
                    controls.require(len(report['cases'][case['id']]['runs']) == 2, 'Original controls repeats incomplete')
                    for repeat in (1, 2):
                        source = (controls.ROOT/'Scenarios'/config['scenario']).read_bytes()
                        initial = {label: (1, 1.) if label == 'DOCKSTATE' else (0, 0.) for label in config['animations']}
                        previous = initial
                        for phase in config['phases']:
                            out = capture/(case['id']+'-'+str(repeat))/phase
                            recorded = report['cases'][case['id']]['runs'][repeat-1][phase]
                            for name, checksum in recorded['files_sha256'].items():
                                controls.require(controls.digest(out/name) == checksum, 'Original controls evidence changed: '+str(out/name))
                            controls.require((out/'flight.scn').read_bytes().replace(b'\r\n', b'\n') == source.replace(b'\r\n', b'\n'),
                                             'Original controls initial/saved scenario chain changed')
                            saved, animations, recomputed = controls.inspect(out, config, case, phase, source)
                            controls.require(recomputed == {k: recorded[k] for k in recomputed}, 'Original controls outcome recomputation differs')
                            for label, index in config['animations'].items():
                                values = [animations[t, index] for t in range(config['phases'][phase]+1)]
                                controls.require(values[0] == previous[label][1], 'Original moving mechanism did not restore')
                                if phase == 'moving':
                                    controls.require(saved[label][0] == (2 if label == 'DOCKSTATE' else 3) and
                                                     0 < saved[label][1] < 1, 'Original key did not start saved motion')
                                elif phase == 'resume':
                                    controls.require(saved[label] == ((0, 0.) if label == 'DOCKSTATE' else (1, 1.)) and
                                        any(0 < v < 1 for v in values), 'Original saved motion failed to resume')
                                else:
                                    controls.require(saved[label] == initial[label], 'Original mechanism did not return to its initial endpoint')
                                    controls.require(any(0 < v < 1 for v in values) if phase == 'retract' else
                                        all(v == initial[label][1] for v in values), 'Original retraction/reload behavior differs')
                                increasing = (label != 'DOCKSTATE') == (phase in ('moving', 'resume'))
                                controls.require(all(a <= b if increasing else a >= b for a, b in zip(values, values[1:])),
                                                 'Original mechanism reversed its commanded motion')
                            previous = saved
                            expected = controls.dispatches(controls.actions(config, case, phase))
                            actual = [(int(r['tick']), int(r['key']), int(r['control'])) for r in controls.rows(out/'shuttle-a-inputs.csv')]
                            controls.require(actual == expected and (out/'shuttle-a-complete.txt').read_text().strip() == str(config['phases'][phase]),
                                             'Original controls input or shutdown differs')
                            controls.require((out/'math-profile.txt').read_text().strip() == recorded['actual_math'] and
                                (math_profile != 'sse2' or recorded['actual_math'] == 'sse2'), 'Actual original controls CRT differs')
                            source = (out/'saved.scn').read_bytes()
                    for phase in config['phases']:
                        paths = [capture/(case['id']+'-'+str(r))/phase for r in (1, 2)]
                        for name in controls.TRACE_FILES:
                            controls.require((paths[0]/name).read_bytes() == (paths[1]/name).read_bytes(), 'Original controls deterministic repeat differs')
                        if phase in ('resume', 'retract'):
                            similarity = controls.image_ssim(*[(p/'scene.rgba').read_bytes() for p in paths], 1280, 720)
                            controls.require(similarity >= config['image_ssim_minimum'] and
                                similarity == report['cases'][case['id']]['repeat_ssim'][phase], 'Original repeated controls image fails')
                gate_path = base/'shuttle-a-controls-gate/verification.json'
                gate = json.loads(gate_path.read_text())
                controls.require(gate['status'] == 'passed' and gate['original_capture_unchanged'] and
                    set(gate['controls']) == {'missing_background_station', 'missing_attachment_port', 'missing_mechanism_tick',
                                             'wrong_cockpit', 'forged_saved_position'} and
                    all(c['rejected'] for c in gate['controls'].values()) and
                    gate['source_sha256_lf'] == controls.source_digest(controls.HERE/'Gate.Test.py'),
                    'Original controls negative tests are incomplete or fail')
                pristine = capture/'shuttle_a_panel-1/moving'
                for name, checksum in gate['capture_sha256'].items():
                    if (pristine/name).exists():
                        controls.require(controls.digest(pristine/name) == checksum, 'Controls gate changed original evidence: '+name)
                result['profiles'][profile] = dict(capture_sha256=controls.digest(capture/'controls-report.json'),
                    observer_sha256=report['binary_sha256'][observer], archive_sha256=item['sha256'],
                    gate_sha256=controls.digest(gate_path))
                profiles[profile] = capture
        for math_profile in ('automatic', 'sse2'):
            compared = {}
            for case in config['cases']:
                phases = {}
                for phase in config['phases']:
                    paths = [profiles[c+'-'+math_profile]/(case['id']+'-1')/phase for c in ('Debug', 'Release')]
                    maxima = compare_state(*paths, config)
                    for name in ('shuttle-a-animations.csv', 'shuttle-a-cockpit.csv', 'stock-vessel-attachments.csv'):
                        controls.require(controls.rows(paths[0]/name) == controls.rows(paths[1]/name), 'Original build-pair controls trajectory differs')
                    phases[phase] = dict(maxima=maxima)
                    if phase in ('resume', 'retract'):
                        similarity = controls.image_ssim(*[(p/'scene.rgba').read_bytes() for p in paths], 1280, 720)
                        controls.require(similarity >= config['image_ssim_minimum'], 'Original build-pair controls image fails')
                        phases[phase]['ssim'] = similarity
                compared[case['id']] = phases
            result['build_comparisons'][math_profile] = compared
        result.update(status='passed', processes=64, scene_presents=3648, native_controls_qualified=False,
                      frozen_references_unchanged=True)
    except BaseException as error:
        result['error'] = str(error)
        raise
    finally:
        args.output.write_text(json.dumps(result, indent=2)+'\n')
    print('Audited all sixty-four original controls sessions and both Debug/Release CRT pairs')


if __name__ == '__main__':
    main()
