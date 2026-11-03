"""Aim and pick original DG virtual-cockpit controls through real window input."""
import math
import re
import json
from pathlib import Path

from keyboard_smoke import require, wait
from systems import ANIMATIONS, digest, states
from window_keys import input_state
from window_panel import rows

ROOT = Path(__file__).resolve().parents[3]
SOURCE_SHA256 = digest(Path(__file__))
QUAD_SOURCE = ROOT/'Src/Vessel/DeltaGlider/dg_vc_anim.h'
QUADS = dict(GEAR='VC_GEARLEVER', AIRBRAKE='VC_AIRBRAKELEVER', NOSECONE='VC_NCONELEVER',
             RADIATOR='VC_RADIATOR_SWITCH', HATCH='VC_HATCH_SWITCH',
             IAIRLOCK='VC_ILOCK_SWITCH', AIRLOCK='VC_OLOCK_SWITCH')


def control_point(name, closing):
    match = re.search(r'const VECTOR3 '+QUADS[name]+r'_mousearea\[4\]\s*=\s*\{(.*?)\};',
                      QUAD_SOURCE.read_text(), re.S)
    require(match, 'Original VC control quad is missing: '+name)
    values = list(map(float, re.findall(r'-?\d+\.\d+', match.group(1))))
    require(len(values) == 12, 'Original VC quad shape differs: '+name)
    p = [values[i:i+3] for i in range(0, 12, 3)]
    v = (.75 if closing else .25) if name in ('GEAR', 'AIRBRAKE', 'NOSECONE') else (.25 if closing else .75)
    return [p[0][i]+.5*(p[1][i]-p[0][i])+v*(p[2][i]-p[0][i]) for i in range(3)]


def operate(out, window, key, button, title, capture=None):
    out = Path(out)
    (out/'vc-driver.py').write_bytes(Path(__file__).read_bytes())
    codes = dict(Up=0xc8, Down=0xd0, Left=0xcb, Right=0xcd, Alt_L=56,
                 Control_L=29, Home=0xc7, space=57, t=20, r=19, s=31)
    aims, points, picks = [], [], []
    screenshots = {}

    def camera():
        path = out/'cockpit-camera.csv'
        complete = rows(path) if path.exists() else []
        return complete[-1] if complete else None

    def deliver(name, down):
        previous = input_state(out)
        key(window, name, down)
        return wait(lambda: (now := input_state(out)) and (not previous or now[0] > previous[0]) and
                    bool(now[1][codes[name]]) == down and now,
                    'VC key did not reach the actual input snapshot: '+name)

    def advance(ticks):
        start = input_state(out)[0]
        wait(lambda: input_state(out)[0] >= start+ticks, 'No real VC input ticks')

    def tap(name, control=False):
        if control:
            deliver('Control_L', True)
        deliver(name, True)
        deliver(name, False)
        if control:
            deliver('Control_L', False)

    def pulse(name, ticks):
        before = camera()
        deliver('Alt_L', True)
        prior = input_state(out)[0]
        deliver(name, True)
        # One GLFW poll may be followed by several catch-up physics steps.
        # Measure from the first actual held sample, rather than extending a
        # pulse by however many steps elapsed before Python observed it.
        start = next(int(r['tick']) for r in rows(out/'input-state.csv')
                     if int(r['tick']) > prior and bytes.fromhex(r['keys'])[codes[name]])
        wait(lambda: input_state(out)[0] >= start+ticks, 'VC camera key did not remain held')
        deliver(name, False)
        deliver('Alt_L', False)
        advance(65)  # Allow the original acceleration/deceleration to settle.
        after = camera()
        aims.append(dict(key='Alt+'+name, held_ticks=ticks, before=before, after=after))
        (out/'vc-camera-aims.json').write_text(json.dumps(aims, indent=2)+'\n')
        return after

    initial_camera = wait(camera, 'No read-only original VC camera observation')
    require(int(initial_camera['mode']) == 3 and float(initial_camera['phi']) == 0 and
            float(initial_camera['theta']) == 0, 'VC must start in the default original view')
    tap('space')
    wait(lambda: ' | PAUSED ' in title(window), 'VC camera fixture did not pause')
    paused_seconds = rows(out/'cockpit-state.csv')[-1]['seconds']
    moved = pulse('Down', 30)
    require(float(moved['theta']) < -.2, 'Alt+Down did not reach the original cockpit camera handler')
    require(rows(out/'cockpit-state.csv')[-1]['seconds'] == paused_seconds,
            'Cockpit camera movement advanced paused simulation time')
    tap('Home')
    wait(lambda: abs(float(camera()['theta'])) < 1e-10, 'Original Home did not recenter while paused')
    tap('space')
    wait(lambda: ' | RUNNING ' in title(window), 'VC camera fixture did not resume')

    def projected(point, pose):
        delta = [point[i]-float(pose[k]) for i, k in enumerate(('x', 'y', 'z'))]
        view = [sum(float(pose['m'+str(j+1)+str(i+1)])*delta[j] for j in range(3)) for i in range(3)]
        if view[2] <= 0:
            return None
        scale = 360/math.tan(float(pose['aperture']))
        return [639.5+view[0]*scale/view[2], 359.5-view[1]*scale/view[2]]

    def aim(point):
        for _ in range(16):
            pose = camera()
            pixel = projected(point, pose)
            if pixel and 80 < pixel[0] < 1200 and 80 < pixel[1] < 640:
                return pose, tuple(math.floor(v+.5) for v in pixel)
            delta = [point[i]-float(pose[k]) for i, k in enumerate(('x', 'y', 'z'))]
            phi = -math.atan2(delta[0], delta[2])
            theta = math.atan2(delta[1], math.hypot(delta[0], delta[2]))
            errors = [phi-float(pose['phi']), theta-float(pose['theta'])]
            errors[0] = (errors[0]+math.pi) % (2*math.pi)-math.pi
            axis = max(range(2), key=lambda i: abs(errors[i]))
            error = errors[axis]
            name = ('Left' if error > 0 else 'Right') if axis == 0 else ('Up' if error > 0 else 'Down')
            pulse(name, max(1, min(12, round(math.sqrt(abs(error)*1500)))))
        raise RuntimeError('Real camera keys could not expose the requested original VC control')

    def animation():
        groups = {}
        selected = set(ANIMATIONS.values())
        for row in rows(out/'flight-animations.csv'):
            if row.get('object') == 'DG' and int(row['index']) in selected:
                groups.setdefault(int(row['tick']), {})[int(row['index'])] = float(row['state'])
        complete = [(tick, values) for tick, values in groups.items() if set(values) == selected]
        return max(complete) if complete else None

    initial = wait(animation, 'No complete original VC mechanism samples')
    require(all(v == 0 for v in initial[1].values()), 'VC mechanisms must start closed')
    tap('t')
    wait(lambda: ' | x10.000' in title(window), 'VC fixture did not select actual 10x')

    def click(name, closing):
        point = control_point(name, closing)
        pose, pixel = aim(point)
        count = len(rows(out/'control-inputs.csv'))
        button(window, *pixel, True)
        wait(lambda: len(rows(out/'control-inputs.csv')) > count, 'VC press did not reach original Pane')
        button(window, *pixel, False)
        wait(lambda: len(rows(out/'control-inputs.csv')) >= count+2, 'VC release did not reach original Pane')
        points.append(pixel)
        picks.append(dict(mechanism=name, closing=closing, local=point, camera=pose, screen=pixel))
        if capture and not closing and name not in screenshots:
            image = 'vc-'+name+'.png'
            capture(image)
            screenshots[name] = dict(file=image, sha256=digest(out/image))
        (out/'vc-picks.json').write_text(json.dumps(picks, indent=2)+'\n')

    def commands(closing):
        for name in ('GEAR', 'AIRBRAKE', 'AIRBRAKE', 'NOSECONE', 'RADIATOR', 'HATCH', 'IAIRLOCK', 'AIRLOCK'):
            click(name, closing)

    def endpoint(value, after):
        current = animation()
        return current if current and current[0] > after and all(v == value for v in current[1].values()) else None

    def save(value, suffix):
        path = out/'current.scn'
        before = path.stat().st_mtime_ns if path.exists() else None
        tap('s', True)
        wait(lambda: path.exists() and path.stat().st_mtime_ns != before, 'VC Ctrl+S did not save')
        saved = states(path)
        require(all(position == value and speed == 0 for position, speed in saved.values()),
                'Original writer did not persist the mouse-operated VC mechanism stops')
        checkpoint = out/('vc-mechanisms-'+suffix+'.scn')
        require(not checkpoint.exists(), 'VC checkpoint already exists')
        checkpoint.write_bytes(path.read_bytes())
        return dict(file=checkpoint.name, sha256=digest(checkpoint), states=saved)

    commands(False)
    opened = wait(lambda: endpoint(1, initial[0]), 'Real VC mouse picks did not open all seven mechanisms')
    opened_save = save(1, 'open')
    commands(True)
    closed = wait(lambda: endpoint(0, opened[0]), 'Real VC mouse picks did not close all seven mechanisms')
    closed_save = save(0, 'closed')
    tap('r')
    wait(lambda: ' | x1.000' in title(window), 'VC fixture did not restore actual 1x')
    tap('Home')
    wait(lambda: (pose := camera()) and abs(float(pose['phi'])) < 1e-10 and
         abs(float(pose['theta'])) < 1e-10, 'Original Home did not recenter the VC camera')
    report = dict(status='passed', source_sha256=SOURCE_SHA256, quad_source=QUAD_SOURCE.relative_to(ROOT).as_posix(),
                  quad_source_sha256=digest(QUAD_SOURCE), initial_tick=initial[0], opened_tick=opened[0],
                  closed_tick=closed[0], original_camera_key_movement=True, original_home_recenter=True,
                  paused_camera_movement=True, paused_seconds=paused_seconds,
                  original_projection_and_pane_picking=True, picks=picks, aims=aims,
                  screenshots=screenshots,
                  opened_save=opened_save, closed_save=closed_save)
    (out/'vc-mechanisms.json').write_text(json.dumps(report, indent=2)+'\n')
    return report, points


def verify_focus(out, window, destination, key, transfer, focused):
    out = Path(out)

    def camera():
        return rows(out/'cockpit-camera.csv')[-1]

    def advance(ticks):
        before = input_state(out)[0]
        wait(lambda: input_state(out)[0] >= before+ticks, 'No camera focus-release samples')

    require(focused() == window, 'VC lost focus before explicit camera transfer')
    key(window, 'Alt_L', True)
    key(window, 'Up', True)
    held = wait(lambda: (state := input_state(out)) and state[1][56] and state[1][0xc8] and
                float(camera()['theta']) > .1 and state, 'VC focus setup did not hold a moving camera key')
    transfer(destination)
    wait(lambda: focused() == destination, 'VC camera focus destination did not receive focus')
    cleared = wait(lambda: (state := input_state(out)) and state[0] > held[0] and
                   not state[1][56] and not state[1][0xc8] and state,
                   'Focus loss did not clear the actual cockpit camera keys')
    advance(65)
    stopped = camera()
    advance(5)
    require(all(camera()[field] == stopped[field] for field in ('phi', 'theta')),
            'Cockpit camera did not stop after its original deceleration')
    key(window, 'Up', False)
    key(window, 'Alt_L', False)
    transfer(window)
    wait(lambda: focused() == window, 'VC camera did not regain focus')
    advance(5)
    require(all(camera()[field] == stopped[field] for field in ('phi', 'theta')),
            'Cockpit camera motion restarted on focus regain')
    report = dict(status='passed', destination=destination, held_input_tick=held[0],
                  released_input_tick=cleared[0], stopped_camera=stopped,
                  actual_keys_cleared=True, original_deceleration_completed=True,
                  no_motion_on_focus_regain=True)
    (out/'vc-camera-focus.json').write_text(json.dumps(report, indent=2)+'\n')
    return report


def verify_camera_keys(out, window, key, title):
    """Check continuous FOV and external camera keys in a disposable window."""
    out = Path(out)
    codes = dict(x=45, z=44, F1=59, Control_L=29, Right=0xcd,
                 Prior=0xc9, Next=0xd1, Home=0xc7, space=57)

    def camera():
        return rows(out/'cockpit-camera.csv')[-1]

    def deliver(name, down):
        before = input_state(out)[0]
        key(window, name, down)
        wait(lambda: (now := input_state(out)) and now[0] > before and
             bool(now[1][codes[name]]) == down, 'Camera key did not reach input: '+name)

    def tap(name):
        deliver(name, True)
        deliver(name, False)

    def advance(ticks):
        before = input_state(out)[0]
        wait(lambda: input_state(out)[0] >= before+ticks, 'No camera release samples')

    for name in ('Home', 'Prior', 'Next'):
        deliver(name, True)
        advance(5)
        deliver(name, False)
        current = rows(out/'thrust-state.csv')[-1]
        require(all(float(current[field]) == 0 for field in ('main', 'hover', 'rcs', 'exhaust')),
                'A bare camera key also fired an engine: '+name)
    tap('space')
    wait(lambda: ' | PAUSED ' in title(window), 'Camera key test did not pause')
    paused_seconds = rows(out/'cockpit-state.csv')[-1]['seconds']
    samples = []
    for name, field, increasing in (('x', 'aperture', True), ('z', 'aperture', False)):
        before = camera()
        deliver(name, True)
        current = wait(lambda: (r := camera()) and
                       (float(r[field])-float(before[field]))*(1 if increasing else -1) > .001 and r,
                       'Original FOV key did not change camera aperture')
        deliver(name, False)
        advance(5)
        stopped = camera()
        advance(5)
        require(camera()[field] == stopped[field], 'Camera FOV continued changing after key release')
        samples.append(dict(key=name, before=before, changed=current, released=stopped))
    tap('F1')
    wait(lambda: camera()['internal'] == '0', 'Original F1 did not select the external camera')
    before = camera()
    deliver('Control_L', True)
    deliver('Right', True)
    wait(lambda: float(camera()['phi']) != float(before['phi']), 'Ctrl+Right did not rotate the external camera')
    deliver('Right', False)
    deliver('Control_L', False)
    advance(65)
    samples.append(dict(key='Ctrl+Right', before=before, released=camera()))
    for name, increasing in (('Prior', True), ('Next', False)):
        before = camera()
        deliver(name, True)
        changed = wait(lambda: (r := camera()) and
                       (float(r['distance'])-float(before['distance']))*(1 if increasing else -1) > .001 and r,
                       'Original PageUp/PageDown did not move the external camera')
        deliver(name, False)
        samples.append(dict(key=name, before=before, changed=changed, released=camera()))
    tap('F1')
    wait(lambda: camera()['internal'] == '1', 'F1 did not return to the cockpit')
    tap('Home')
    wait(lambda: abs(float(camera()['phi'])) < 1e-10 and abs(float(camera()['theta'])) < 1e-10,
         'Home did not recenter after external camera controls')
    require(rows(out/'cockpit-state.csv')[-1]['seconds'] == paused_seconds,
            'System camera keys advanced paused simulation time')
    tap('space')
    wait(lambda: ' | RUNNING ' in title(window), 'Camera key test did not resume')
    report = dict(status='passed', source_sha256=SOURCE_SHA256, continuous_fov_increase_decrease=True,
                  fov_release_stops=True, external_rotation=True, external_advance_retreat=True,
                  internal_external_toggle=True, paused_camera_controls=True,
                  bare_camera_keys_do_not_fire_engines=True, samples=samples)
    (out/'camera-keys.json').write_text(json.dumps(report, indent=2)+'\n')
    return report


def verify_completed(out, report):
    out = Path(out)
    events = rows(out/'input-events.csv')
    require(not any(r['down'] == '1' and int(r['key']) in (34, 37, 32, 24, 22, 48) for r in events),
            'Mechanism shortcut keys were used during VC mouse picking')
    animations = rows(out/'flight-animations.csv')
    for name, index in ANIMATIONS.items():
        selected = [(int(r['tick']), float(r['state'])) for r in animations
                    if r['object'] == 'DG' and int(r['index']) == index]
        for opening in (True, False):
            lo = report['initial_tick'] if opening else report['opened_tick']
            hi = report['opened_tick'] if opening else report['closed_tick']
            values = [value for tick, value in selected if lo <= tick <= hi]
            require(values and values[0] == (0 if opening else 1) and values[-1] == (1 if opening else 0) and
                    any(0 < v < 1 for v in values), 'VC mouse trajectory lacks complete travel: '+name)
            require(all(b >= a if opening else b <= a for a, b in zip(values, values[1:])),
                    'VC mouse trajectory reversed unexpectedly: '+name)
    report.update(no_mechanism_shortcut_keys=True, monotonic_complete_trajectories=True,
                  camera_trace_sha256=digest(out/'cockpit-camera.csv'),
                  input_events_sha256=digest(out/'input-events.csv'),
                  animation_trace_sha256=digest(out/'flight-animations.csv'))
    (out/'vc-mechanisms.json').write_text(json.dumps(report, indent=2)+'\n')
