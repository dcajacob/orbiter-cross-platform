#!/usr/bin/env python3
"""Compare complete Shuttle-A controls captures with audited original Windows runs."""
import argparse
import json
import math
from pathlib import Path

import capture as controls
from verify_original import compare_state
from behavior_suite import quaternion, quaternion_angle


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('original', 'native', 'reference-audit', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    config = controls.settings()
    controls.require(not args.output.exists(), 'Controls comparison output already exists')
    reports = [json.loads((p/'controls-report.json').read_text()) for p in (args.original, args.native)]
    audit = json.loads(args.reference_audit.read_text())
    controls.require(all(r['status'] == 'passed' and not r['failures'] and r['sources_and_runtime_unchanged'] for r in reports) and
        reports[0]['producer'] == 'preserved-original-windows' and reports[1]['producer'] == 'native' and
        reports[0]['application_source'] == reports[1]['application_source'] == config['application_source'],
        'Controls comparison requires complete original/native captures')
    controls.require(all(set(r['cases']) == {c['id'] for c in config['cases']} for r in reports) and
        all(reports[0][k] == reports[1][k] for k in ('configuration', 'math_profile', 'source_sha256_lf')),
        'Controls matrix, profiles or observer protocol differ')
    profile = reports[0]['configuration']+'-'+reports[0]['math_profile']
    controls.require(audit['status'] == 'passed' and
        audit['profiles'][profile]['capture_sha256'] == controls.digest(args.original/'controls-report.json'),
        'Original controls capture has not passed the four-profile source/artifact audit')
    for name, checksum in reports[1]['source_sha256_lf'].items():
        controls.require(controls.source_digest(controls.ROOT/name) == checksum, 'Controls comparison source changed: '+name)
    result = dict(status='failed', phase6_complete=False, profile=profile, cases={},
                  original_report_sha256=controls.digest(args.original/'controls-report.json'),
                  native_report_sha256=controls.digest(args.native/'controls-report.json'),
                  reference_audit_sha256=controls.digest(args.reference_audit))
    try:
        for case in config['cases']:
            compared = []
            for repeat in (1, 2):
                phases = {}
                for phase in config['phases']:
                    paths = [p/(case['id']+'-'+str(repeat))/phase for p in (args.original, args.native)]
                    for path, report in zip(paths, reports):
                        recorded = report['cases'][case['id']]['runs'][repeat-1][phase]
                        for name, checksum in recorded['files_sha256'].items():
                            controls.require(controls.digest(path/name) == checksum, 'Controls evidence changed: '+str(path/name))
                        controls.inspect(path, config, case, phase, (path/'flight.scn').read_bytes())
                    controls.require(controls.saved_state(paths[0]/'saved.scn', config) ==
                                     controls.saved_state(paths[1]/'saved.scn', config), 'Original saved mechanisms differ')
                    for name in ('shuttle-a-animations.csv', 'shuttle-a-cockpit.csv', 'stock-vessel-attachments.csv'):
                        left, right = (controls.rows(p/name) for p in paths)
                        controls.require(left == right, 'Original mechanism/cockpit/attachment trajectory differs: '+name)
                    maxima = compare_state(*paths, config)
                    phases[phase] = dict(maxima=maxima, exact_mechanism_trajectories=True,
                                         exact_saved_mechanisms=True, exact_attachment_ports=True)
                    if phase in ('resume', 'retract'):
                        similarity = controls.image_ssim(*[(p/'scene.rgba').read_bytes() for p in paths], 1280, 720)
                        controls.require(similarity >= config['image_ssim_minimum'], 'Controls framebuffer exceeds unchanged SSIM budget')
                        cameras = [controls.rows(p/'camera.csv') for p in paths]
                        controls.require(all(len(c) == 1 for c in cameras), 'Incomplete controls camera')
                        a, b = (c[0] for c in cameras)
                        position = math.dist([float(a[k]) for k in ('px','py','pz')], [float(b[k]) for k in ('px','py','pz')])
                        rotation = quaternion_angle(quaternion(a), quaternion(b))
                        controls.require(position <= config['budgets']['position_m'] and rotation <= config['budgets']['rotation_rad'] and
                                         float(a['aperture']) == float(b['aperture']), 'Original controls camera exceeds unchanged budgets')
                        phases[phase].update(full_frame_ssim=similarity, camera_position_m=position, camera_rotation_rad=rotation)
                compared.append(phases)
            result['cases'][case['id']] = compared
        result.update(status='passed', compared_processes=16, compared_presents=912,
                      complete_stock_vessel_graph=True, references_and_budgets_unchanged=True)
    except BaseException as error:
        result['error'] = str(error)
        raise
    finally:
        args.output.write_text(json.dumps(result, indent=2)+'\n')
    print('Compared sixteen complete-scene controls sessions against audited original Windows observations')


if __name__ == '__main__':
    main()
