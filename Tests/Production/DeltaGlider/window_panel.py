"""Pan and operate original DG 2D controls through an owned X11 window."""
import csv
import json
from pathlib import Path

from keyboard_smoke import require, wait
from systems import ANIMATIONS, digest, states
from window_keys import input_state

SOURCE_SHA256 = digest(Path(__file__))


def rows(path):
    text = path.read_text()
    return [r for r in csv.DictReader(text[:text.rfind('\n')+1].splitlines())
            if all(v is not None for v in r.values())]


def operate(out, window, key, button, title):
    out = Path(out)
    codes = dict(Up=0xc8, Down=0xd0, Left=0xcb, Right=0xcd,
                 Control_L=29, space=57, t=20, r=19, s=31)

    def deliver(name, down):
        previous = input_state(out)
        key(window, name, down)
        wait(lambda: (now := input_state(out)) and (not previous or now[0] > previous[0]) and
             bool(now[1][codes[name]]) == down, 'Panel key did not reach input snapshot: '+name)

    def tap(name, control=False):
        if control:
            deliver('Control_L', True)
        deliver(name, True)
        deliver(name, False)
        if control:
            deliver('Control_L', False)

    def layout():
        path = out/'panel-layout.csv'
        complete = rows(path) if path.exists() else []
        return complete[-1] if complete else None

    def animation():
        groups = {}
        selected = set(ANIMATIONS.values())
        for row in rows(out/'flight-animations.csv'):
            if row.get('object') == 'DG' and int(row['index']) in selected:
                groups.setdefault(int(row['tick']), {})[int(row['index'])] = float(row['state'])
        complete = [(tick, values) for tick, values in groups.items() if set(values) == selected]
        return max(complete) if complete else None

    initial_layout = wait(layout, 'No original panel layout observation')
    require(int(initial_layout['panel_id']) == 0 and float(initial_layout['scale']) == 1 and
            float(initial_layout['x']) == 0 and float(initial_layout['y']) == 338,
            'Stock 1280x720 main panel geometry differs')
    initial = wait(animation, 'No complete original mechanism animation state')
    require(all(v == 0 for v in initial[1].values()), 'Panel mechanisms must start closed')
    deliver('Down', True)
    lowered = wait(lambda: (r := layout()) and float(r['y']) == 148 and r,
                   'Held Down did not expose the stock lower-panel controls')
    deliver('Down', False)
    released = input_state(out)[0]
    wait(lambda: input_state(out)[0] >= released+5, 'No panel key-release samples')
    require(float(layout()['y']) == 148, 'Panel continued moving after key release')

    # Original system controls remain active while simulation time is paused.
    tap('space')
    wait(lambda: ' | PAUSED ' in title(window), 'Panel pause key did not pause simulation')
    paused_seconds = rows(out/'cockpit-state.csv')[-1]['seconds']
    deliver('Up', True)
    paused_up = wait(lambda: (r := layout()) and float(r['y']) >= 300 and r,
                     'Held Up did not pan the panel while paused')
    deliver('Up', False)
    deliver('Down', True)
    wait(lambda: float(layout()['y']) == 148, 'Paused Down did not restore the original clamp')
    deliver('Down', False)
    for name in ('Left', 'Right'):
        deliver(name, True)
        before = input_state(out)[0]
        wait(lambda: input_state(out)[0] >= before+5, 'No held horizontal panel samples')
        deliver(name, False)
        require(float(layout()['x']) == 0, 'A viewport-width panel moved horizontally')
    require(rows(out/'cockpit-state.csv')[-1]['seconds'] == paused_seconds,
            'Panel panning advanced paused simulation time')
    tap('space')
    wait(lambda: ' | RUNNING ' in title(window), 'Panel input did not restore running simulation')
    tap('t')
    wait(lambda: ' | x10.000' in title(window), 'Panel fixture did not select actual 10x')

    points = []
    picks = []

    def click(name, local_x, local_y):
        before = layout()
        px = round(float(before['x'])+local_x*float(before['scale']))
        py = round(float(before['y'])+local_y*float(before['scale']))
        require(0 <= px < 1280 and 0 <= py < 720, 'Mechanism pick lies outside the actual viewport')
        count = len(rows(out/'control-inputs.csv'))
        button(window, px, py, True)
        wait(lambda: len(rows(out/'control-inputs.csv')) > count,
             'Mechanism mouse press did not reach original Pane')
        button(window, px, py, False)
        wait(lambda: len(rows(out/'control-inputs.csv')) >= count+2,
             'Mechanism mouse release did not reach original Pane')
        points.append((px, py))
        picks.append(dict(mechanism=name, panel=before, local=[local_x, local_y], screen=[px, py]))

    def select(overhead):
        tap('Up' if overhead else 'Down', True)
        return wait(lambda: (r := layout()) and int(r['panel_id']) == int(overhead) and r,
                    'Ctrl+arrow did not switch the original DG panel')

    def main_controls(closing):
        if float(layout()['y']) != 148:
            deliver('Down', True)
            wait(lambda: float(layout()['y']) == 148, 'Main panel panning did not expose mechanism levers')
            deliver('Down', False)
        click('GEAR', 109, 453)
        click('NOSECONE', 1240, 407)
        for _ in range(2):
            click('AIRBRAKE', 148, 314 if closing else 344)

    def overhead_controls(closing):
        select(True)
        for name, x in [('HATCH', 447), ('IAIRLOCK', 493), ('AIRLOCK', 539), ('RADIATOR', 859)]:
            click(name, x, 231 if closing else 205)
        select(False)

    def endpoint(value, after):
        current = animation()
        return current if current and current[0] > after and all(v == value for v in current[1].values()) else None

    def save(value, suffix):
        path = out/'current.scn'
        previous = path.stat().st_mtime_ns if path.exists() else None
        tap('s', True)
        wait(lambda: path.exists() and path.stat().st_mtime_ns != previous,
             'Real Ctrl+S did not save the mouse-operated mechanisms')
        saved = states(path)
        require(all(position == value and speed == 0 for position, speed in saved.values()),
                'Mouse-operated mechanism endpoint was not saved by original writers')
        checkpoint = out/('panel-mechanisms-'+suffix+'.scn')
        require(not checkpoint.exists(), 'Panel mechanism checkpoint already exists')
        checkpoint.write_bytes(path.read_bytes())
        return dict(file=checkpoint.name, sha256=digest(checkpoint), states=saved)

    main_controls(False)
    overhead_controls(False)
    opened = wait(lambda: endpoint(1, initial[0]), 'Real panel clicks did not fully deploy all seven mechanisms')
    opened_save = save(1, 'open')
    main_controls(True)
    overhead_controls(True)
    closed = wait(lambda: endpoint(0, opened[0]), 'Real panel clicks did not fully close all seven mechanisms')
    closed_save = save(0, 'closed')
    tap('r')
    wait(lambda: ' | x1.000' in title(window), 'Panel fixture did not restore actual 1x')
    require(float(layout()['y']) == 338 and int(layout()['panel_id']) == 0,
            'Panel switching did not restore the original main panel geometry')
    report = dict(status='passed', source_sha256=SOURCE_SHA256, initial_tick=initial[0],
                  opened_tick=opened[0], closed_tick=closed[0], initial_layout=initial_layout,
                  lower_clamp=lowered, paused_up=paused_up, paused_seconds=paused_seconds,
                  held_arrow_panning=True, release_stops_panning=True, paused_panning=True,
                  horizontal_clamp=True, original_panel_switching=True, picks=picks,
                  opened_save=opened_save, closed_save=closed_save)
    (out/'panel-mechanisms.json').write_text(json.dumps(report, indent=2)+'\n')
    return report, points


def verify_completed(out, report):
    out = Path(out)
    events = rows(out/'input-events.csv')
    require(not any(r['down'] == '1' and int(r['key']) in (34, 37, 32, 24, 22, 48) for r in events),
            'Mechanism shortcut keys were used during the mouse-only operation')
    animations = rows(out/'flight-animations.csv')
    for name, index in ANIMATIONS.items():
        selected = [(int(r['tick']), float(r['state'])) for r in animations
                    if r['object'] == 'DG' and int(r['index']) == index]
        for opening in (True, False):
            lo = report['initial_tick'] if opening else report['opened_tick']
            hi = report['opened_tick'] if opening else report['closed_tick']
            values = [value for tick, value in selected if lo <= tick <= hi]
            require(values and values[0] == (0 if opening else 1) and
                    values[-1] == (1 if opening else 0) and any(0 < value < 1 for value in values),
                    'Mouse mechanism trajectory lacks complete travel: '+name)
            require(all(b >= a if opening else b <= a for a, b in zip(values, values[1:])),
                    'Mouse mechanism reversed unexpectedly: '+name)
    report.update(no_mechanism_shortcut_keys=True, monotonic_complete_trajectories=True,
                  input_events_sha256=digest(out/'input-events.csv'),
                  animation_trace_sha256=digest(out/'flight-animations.csv'),
                  panel_layout_sha256=digest(out/'panel-layout.csv'))
    (out/'panel-mechanisms.json').write_text(json.dumps(report, indent=2)+'\n')
