"""Check independent RCS/aerodynamic mode shortcuts in the actual DG window."""
import csv
import json
from pathlib import Path

from keyboard_smoke import require, wait
from systems import digest
from window_keys import input_state

SOURCE_SHA256 = digest(Path(__file__))


def verify(out, window, key):
    out = Path(out)

    def state():
        text = (out/'flight-controls.csv').read_text()
        rows = [r for r in csv.DictReader(text[:text.rfind('\n')+1].splitlines())
                if r.get('rcs_mode') and r['object'] == 'DG' and all(v is not None for v in r.values())]
        return rows[-1] if rows else None

    codes = dict(f=33, Alt_L=56, Control_L=29)

    def deliver(name, down):
        previous = input_state(out)
        key(window, name, down)
        wait(lambda: (now := input_state(out)) and (not previous or now[0] > previous[0]) and
             bool(now[1][codes[name]]) == down,
             'Mode shortcut key did not reach the input snapshot: '+name)

    def tap(modifier=None):
        if modifier:
            deliver(modifier, True)
        deliver('f', True)
        deliver('f', False)
        if modifier:
            deliver(modifier, False)

    initial = wait(state, 'No finalized original DG control state')
    require(int(initial['rcs_mode']) == 1, 'Mode shortcut fixture must start in rotational RCS')
    aerodynamic = int(initial['aerodynamic_mode'])
    samples = []
    # Alt+F is the existing native aerodynamic-control alias. It must not also
    # match the selected profile's RCS mode or enable/disable shortcuts.
    for target in (7 if aerodynamic == 0 else 0, aerodynamic):
        before = int(state()['tick'])
        tap('Alt_L')
        current = wait(lambda: (row := state()) and int(row['tick']) > before and
                       int(row['aerodynamic_mode']) == target and row,
                       'Alt+F did not toggle original aerodynamic controls')
        require(int(current['rcs_mode']) == 1, 'Aerodynamic shortcut also changed the RCS mode')
        samples.append(dict(shortcut='Alt+F', state=current))
    for modifier, targets in ((None, (2, 1)), ('Control_L', (0, 1))):
        for target in targets:
            before = int(state()['tick'])
            tap(modifier)
            current = wait(lambda: (row := state()) and int(row['tick']) > before and
                           int(row['rcs_mode']) == target and row,
                           'RCS keyboard shortcut did not select its original mode')
            require(int(current['aerodynamic_mode']) == aerodynamic,
                    'RCS shortcut also changed aerodynamic controls')
            samples.append(dict(shortcut='Ctrl+F' if modifier else 'F', state=current))
    report = dict(status='passed', source_sha256=SOURCE_SHA256,
                  independent_aerodynamic_and_rcs_modes=True, samples=samples,
                  restored_rcs_mode=1, restored_aerodynamic_mode=aerodynamic)
    (out/'keyboard-modes.json').write_text(json.dumps(report, indent=2)+'\n')
    return report
