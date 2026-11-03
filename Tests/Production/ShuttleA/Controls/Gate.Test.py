#!/usr/bin/env python3
"""Prove that incomplete or forged controls observations fail without editing captures."""
import argparse
import csv
import json
from pathlib import Path
import shutil

import capture as controls


def rewrite(path, mutate):
    with path.open(newline='') as stream:
        reader = csv.DictReader(stream)
        fields, data = reader.fieldnames, list(reader)
    data = mutate(data)
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    config = controls.settings()
    case = next(c for c in config['cases'] if c['cockpit'] == 2)
    source = (args.capture/'flight.scn').read_bytes()
    before = {p.name: controls.digest(p) for p in args.capture.iterdir() if p.is_file()}
    controls.inspect(args.capture, config, case, 'moving', source)
    args.output.mkdir(parents=True, exist_ok=False)
    result = dict(status='failed', controls={}, capture_sha256=before, original_capture_unchanged=False,
                  source_sha256_lf=controls.source_digest(Path(__file__)))
    def reject(name, expected, action):
        directory = args.output/name
        directory.mkdir()
        for path in args.capture.iterdir():
            if path.name in (*controls.TRACE_FILES, 'flight.scn', 'saved.scn', 'graphics-lifecycle.json',
                             'renderer-info.json', 'graphics-errors.txt', 'console.log', 'Orbiter.log'):
                shutil.copyfile(path, directory/path.name)
        action(directory)
        try:
            controls.inspect(directory, config, case, 'moving', source)
        except (ValueError, KeyError) as error:
            controls.require(expected in str(error), 'Negative controls failed for another reason: '+str(error))
            result['controls'][name] = dict(rejected=True, error=str(error))
            return
        raise ValueError('Invalid controls evidence was accepted: '+name)
    try:
        reject('missing_background_station', 'Background vessel missing', lambda p: rewrite(p/'stock-vessel-state.csv',
            lambda rows: [r for r in rows if r['object'] != 'Mir']))
        reject('missing_attachment_port', 'Incomplete or duplicate controls ports', lambda p: rewrite(p/'stock-vessel-attachments.csv', lambda rows: rows[1:]))
        reject('missing_mechanism_tick', 'Incomplete mechanism trajectories', lambda p: rewrite(p/'shuttle-a-animations.csv', lambda rows: rows[1:]))
        def wrong_mode(path):
            def mutate(rows):
                rows[-1]['cockpit'] = '3'
                return rows
            rewrite(path/'shuttle-a-cockpit.csv', mutate)
        reject('wrong_cockpit', 'Ordinary cockpit selection failed', wrong_mode)
        def wrong_save(path):
            text = (path/'saved.scn').read_text()
            lines = text.splitlines()
            inside = False
            for i, line in enumerate(lines):
                if line.strip().startswith(config['focus']+':'):
                    inside = True
                elif line.strip() == 'END':
                    inside = False
                elif inside and line.strip().startswith('DOCKSTATE '):
                    lines[i] = '  DOCKSTATE 2 0.1234'
            (path/'saved.scn').write_text('\n'.join(lines)+'\n')
        reject('forged_saved_position', 'Saved position differs', wrong_save)
        result['original_capture_unchanged'] = before == {p.name: controls.digest(p) for p in args.capture.iterdir() if p.is_file()}
        controls.require(result['original_capture_unchanged'], 'Negative controls changed the original capture')
        result['status'] = 'passed'
    finally:
        (args.output/'verification.json').write_text(json.dumps(result, indent=2)+'\n')
    print('Rejected five damaged controls captures; original evidence unchanged')


if __name__ == '__main__':
    main()
