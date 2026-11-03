#!/usr/bin/env python3
"""Reject damaged copies of real intentional-exit evidence without editing the capture."""
import argparse
import csv
import io
import json
from pathlib import Path
import tempfile

from contract import digest, expected_events, inspect, require, rows, settings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', type=lambda p: Path(p).resolve(), required=True)
    parser.add_argument('--host', choices=('native-linux', 'original-windows'), required=True)
    parser.add_argument('--output', type=lambda p: Path(p).resolve(), required=True)
    args = parser.parse_args(); config = settings()
    require(not args.output.exists(), 'Exit gate output exists')
    inspect(args.capture, config, args.host, 0)
    before = {p.name: digest(p) for p in args.capture.iterdir() if p.is_file()}
    rejected = []

    def csv_bytes(data):
        output = io.StringIO(); writer = csv.DictWriter(output, fieldnames=list(data[0]))
        writer.writeheader(); writer.writerows(data); return output.getvalue().encode('ascii')

    def change(view, name, data):
        path = view/name
        if path.is_symlink(): path.unlink()
        path.write_bytes(data)

    mutations = ['missing_background_ship', 'missing_docking_port', 'missing_last_tick', 'nonfinite_state',
                 'duplicate_docking_port', 'missing_assertion', 'forged_completion', 'wrong_scenario', 'wrong_exit_code',
                 'incomplete_teardown', 'wrong_renderer']
    for label in mutations:
        with tempfile.TemporaryDirectory(prefix='orbiter-stock-exit-gate-') as temporary:
            view = Path(temporary)
            for path in args.capture.iterdir():
                if path.is_file(): (view/path.name).symlink_to(path)
            if args.host == 'original-windows':
                (view/'Scenarios').mkdir()
                (view/'Scenarios/Behavior.scn').symlink_to(args.capture/'Scenarios/Behavior.scn')
            code = 0
            state = rows(args.capture/'stock-vessel-state.csv')
            docks = rows(args.capture/'stock-vessel-docks.csv')
            if label == 'missing_background_ship':
                omitted = next(row for row in state if row['tick'] == '3' and row['focus'] == '0')
                state.remove(omitted); change(view, 'stock-vessel-state.csv', csv_bytes(state))
            elif label == 'missing_docking_port':
                docks.pop(); change(view, 'stock-vessel-docks.csv', csv_bytes(docks))
            elif label == 'missing_last_tick':
                last = max(int(row['tick']) for row in state)
                change(view, 'stock-vessel-state.csv', csv_bytes([r for r in state if int(r['tick']) != last]))
            elif label == 'nonfinite_state':
                state[0]['x'] = 'nan'; change(view, 'stock-vessel-state.csv', csv_bytes(state))
            elif label == 'duplicate_docking_port':
                docks.append(dict(docks[0])); change(view, 'stock-vessel-docks.csv', csv_bytes(docks))
            elif label in ('missing_assertion', 'forged_completion'):
                name = 'Orbiter.log' if args.host == 'original-windows' else 'console.txt'
                lines = (args.capture/name).read_text(errors='replace').splitlines(True)
                if label == 'missing_assertion':
                    target = next(event for event in expected_events(config) if event.startswith('Test: '))
                    index = next(i for i, line in enumerate(lines) if line.rstrip().endswith(target))
                    del lines[index]
                else: lines = ['=== All tests passed ===\n']
                change(view, name, ''.join(lines).encode())
            elif label == 'wrong_scenario':
                name = 'Scenarios/Behavior.scn' if args.host == 'original-windows' else 'flight.scn'
                change(view, name, (args.capture/name).read_bytes()+b'\n; changed test scenario\n')
            elif label == 'wrong_exit_code': code = 7
            elif label == 'wrong_renderer':
                name = 'stock-exit-renderer.json' if args.host == 'original-windows' else 'renderer-info.json'
                renderer = json.loads((args.capture/name).read_text()); renderer['renderer'] = 'unverified'
                change(view, name, json.dumps(renderer).encode())
            elif args.host == 'native-linux':
                life = json.loads((args.capture/'graphics-lifecycle.json').read_text()); life['context_deleted'] = False
                change(view, 'graphics-lifecycle.json', json.dumps(life).encode())
            else: (view/'stock-exit-normal-end.txt').write_text('13\n')
            try: inspect(view, config, args.host, code)
            except ValueError as error: rejected.append(dict(control=label, reason=str(error)))
            else: raise ValueError('Damaged exit evidence accepted: '+label)
    require(before == {p.name: digest(p) for p in args.capture.iterdir() if p.is_file()}, 'Original exit capture changed')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(dict(status='passed', controls=rejected, original_capture_unchanged=True), indent=2)+'\n')
    print('Eleven damaged exit captures rejected; original complete capture unchanged')


if __name__ == '__main__': main()
