"""Operate stock DG mechanisms through a caller's owned X11 window only."""
import csv
import json
from pathlib import Path

from keyboard_smoke import require, wait
from systems import ANIMATIONS, states, digest

HELPER_SHA256 = digest(Path(__file__))


def input_state(out):
    text = (Path(out)/'input-state.csv').read_text()
    row = text[:text.rfind('\n')].rsplit('\n', 1)[-1].split(',')
    if len(row) != 7 or not row[0].isdigit():
        return None
    return int(row[0]), bytes.fromhex(row[1])


def operate(out, window, key, title):
    out = Path(out)

    codes = dict(Control_L=29, g=34, k=37, d=32, o=24, u=22, b=48, s=31, t=20, r=19)

    def delivered(name, down):
        prior = input_state(out)
        key(window, name, down)
        def observed():
            current = input_state(out)
            return current and (not prior or current[0] > prior[0]) and bool(current[1][codes[name]]) == down
        # Physics can catch up several steps within one GLFW polling interval.
        # Observe the actual input snapshot before changing a key or modifier.
        wait(observed, 'Real key was not observed by the engine: '+name+(' down' if down else ' up'))

    def tap(name, control=False):
        if control:
            delivered('Control_L', True)
        delivered(name, True)
        delivered(name, False)
        if control:
            delivered('Control_L', False)

    def snapshot():
        # Ignore an unfinished trailing CSV record/group while the app writes.
        text = (out/'flight-animations.csv').read_text()
        rows = [r for r in csv.DictReader(text[:text.rfind('\n')+1].splitlines())
                if r.get('state') and all(v is not None for v in r.values()) and r['object'] == 'DG']
        groups = {}
        selected = set(ANIMATIONS.values())
        for row in rows:
            if int(row['index']) in selected:
                groups.setdefault(int(row['tick']), {})[int(row['index'])] = float(row['state'])
        complete = [(tick, values) for tick, values in groups.items() if set(values) == selected]
        return max(complete) if complete else None

    initial = wait(snapshot, 'No complete original DG animation samples')
    require(all(value == 0 for value in initial[1].values()), 'Mechanisms did not start closed')
    tap('t')
    wait(lambda: ' | x10.000' in title(window), 'Real time-acceleration key did not select 10x')

    def commands(closing):
        for name, control in [('g', False), ('k', False), ('d', False),
                              ('o', False), ('o', True), ('u', False),
                              ('b', closing), ('b', closing)]:
            tap(name, control)

    def endpoint(value, after):
        current = snapshot()
        return current if current and current[0] > after and all(
            state == value for state in current[1].values()) else None

    def save(expected, count):
        current = out/'current.scn'
        before = current.stat().st_mtime_ns if current.exists() else None
        tap('s', True)
        wait(lambda: current.exists() and current.stat().st_mtime_ns != before,
             'Actual Ctrl+S did not update the explicit scenario path')
        saved = states(current)
        require(all(position == expected and speed == 0 for position, speed in saved.values()),
                'Real-key mechanism endpoint did not persist through original writers')
        checkpoint = out/('mechanisms-open.scn' if count == 1 else 'mechanisms-closed.scn')
        require(not checkpoint.exists(), 'Mechanism checkpoint already exists')
        checkpoint.write_bytes(current.read_bytes())
        return dict(file=checkpoint.name, sha256=digest(checkpoint), states=saved)

    commands(False)
    opened = wait(lambda: endpoint(1, initial[0]), 'Real DG keys did not fully deploy all seven mechanisms')
    opened_save = save(1, 1)
    commands(True)
    closed = wait(lambda: endpoint(0, opened[0]), 'Real DG keys did not fully close all seven mechanisms')
    closed_save = save(0, 2)
    tap('r')
    wait(lambda: ' | x1.000' in title(window), 'Real time-deceleration key did not restore 1x')
    report = dict(status='passed', transport='Owned X11 keys through GLFW and original buffered vessel keys',
                  mechanisms=ANIMATIONS, initial_tick=initial[0], opened_tick=opened[0],
                  closed_tick=closed[0], opened_save=opened_save, closed_save=closed_save,
                  actual_warp_key=True, restored_1x=True, actual_quicksave_keys=True, helper_sha256=HELPER_SHA256)
    (out/'window-mechanisms.json').write_text(json.dumps(report, indent=2)+'\n')
    return report


def verify_completed(out, report):
    """Check the finalized input wire trace and complete mechanism trajectories."""
    out = Path(out)
    with (out/'input-events.csv').open() as stream:
        events = list(csv.DictReader(stream))
    expected = [(20, False)]
    for closing in (False, True):
        expected.extend([(34, False), (37, False), (32, False), (24, False),
                         (24, True), (22, False), (48, closing), (48, closing), (31, True)])
    expected.append((19, False))
    selected = {code for code, _ in expected}
    actual = [(int(r['key']), bool(int(r['lctrl']) or int(r['rctrl']))) for r in events
              if r['down'] == '1' and int(r['key']) in selected]
    require(actual == expected, 'Actual mechanism key order or control modifiers differ')
    with (out/'flight-animations.csv').open() as stream:
        animations = list(csv.DictReader(stream))
    for name, index in ANIMATIONS.items():
        selected = [(int(r['tick']), float(r['state'])) for r in animations
                    if r['object'] == 'DG' and int(r['index']) == index]
        for opening in (True, False):
            lo = report['initial_tick'] if opening else report['opened_tick']
            hi = report['opened_tick'] if opening else report['closed_tick']
            values = [value for tick, value in selected if lo <= tick <= hi]
            require(values and values[0] == (0 if opening else 1) and
                    values[-1] == (1 if opening else 0) and any(0 < value < 1 for value in values),
                    'Real-key mechanism trajectory lacks endpoints or intermediate travel: '+name)
            require(all(b >= a if opening else b <= a for a, b in zip(values, values[1:])),
                    'Real-key mechanism reversed unexpectedly: '+name)
    report.update(exact_key_order_and_modifiers=True, monotonic_complete_trajectories=True,
                  input_events_sha256=digest(out/'input-events.csv'),
                  animation_trace_sha256=digest(out/'flight-animations.csv'))
    (out/'window-mechanisms.json').write_text(json.dumps(report, indent=2)+'\n')
