"""The versioned API test's startup exit, separate from ordinary scene lifetimes."""
import csv
import hashlib
import json
import math
from pathlib import Path

from prepare import ROOT, ORIGINAL, EARTH, corrected, digest, require

HERE = Path(__file__).resolve().parent
SAVE_SENTINEL = b'Existing save preserved across corrected GeneralApiTest startup exit.\n'
TESTS = (
    'oapi.get_orbiter_version()', 'oapi.rand()', 'oapi.deflate()', 'oapi.inflate()',
    'oapi.formatvalue(value,prec)', 'oapi.openfile(fname,FILE_OUT,root)',
    'oapi.writeline(f,line)', 'oapi.writeitem_xxx(f,item,value)',
    'oapi.readitem_xxx(f,item)', 'oapi.openfile(fname,FILE_IN,...)', 'planet status')
EXPECTED_EVENTS = [part for name in TESTS for part in ('Test: '+name, ' - passed')] + ['=== All tests passed ===']
ERRORS = ('Assertion failed', ' - FAILED!', 'LuaCall (', 'Lua error:',
          'ERROR: AddressSanitizer', 'ERROR: LeakSanitizer', 'runtime error:',
          'WARNING: ThreadSanitizer:', 'Orbiter native production:')


def settings():
    cfg = json.loads((HERE/'startup-policy-v1.json').read_text())
    body, unused = corrected((ROOT/ORIGINAL).read_bytes(), (ROOT/EARTH).read_bytes(), 'v2')
    require(cfg['protocol']=='general-api-startup-exit-v1' and
            cfg['test_variant']=='general-api-spice-test-correction-v2' and
            cfg['script']==ORIGINAL and digest(body)==cfg['script_sha256'] and
            cfg['automatic_reference_refresh'] is False, 'Pinned API startup policy differs')
    require(digest((ROOT/'Scenarios'/cfg['scenario']).read_bytes().replace(b'\r\n',b'\n'))==cfg['scenario_sha256_lf'],
            'Pinned API scenario differs')
    return cfg


def events(text):
    result = []
    for line in text.splitlines():
        if 'Test: ' in line: result.append(line[line.index('Test: '):].rstrip())
        elif line.rstrip().endswith(' - passed'): result.append(' - passed')
        elif '=== All tests passed ===' in line: result.append('=== All tests passed ===')
    return result


def corrected_log(text):
    require(events(text)==EXPECTED_EVENTS and not any(error in text for error in ERRORS),
            'Corrected API assertions incomplete or failed')


def rows(path):
    with path.open(newline='') as stream: return list(csv.DictReader(stream))


def inspect_native(out, profile, returncode, script, scenario, save):
    """No frame waiver is available to another script, scene, or CPU profile."""
    cfg=settings();out=Path(out)
    require(profile in ('Debug-automatic','Debug-sse2','Release-automatic','Release-sse2'), 'Unknown API runtime profile')
    require(type(returncode) is int and returncode==cfg['expected_exit_code'], 'API process did not exit successfully')
    require(digest(Path(script).read_bytes())==cfg['script_sha256'] and
            digest(Path(scenario).read_bytes().replace(b'\r\n',b'\n'))==cfg['scenario_sha256_lf'],
            'API startup script/scenario was substituted')
    corrected_log((out/'console.log').read_text(errors='replace'))
    life=json.loads((out/'graphics-lifecycle.json').read_text())
    require(life==dict(rendered_frames=0,successful_presents=0,context_deleted=True),
            'Corrected native API startup must close its context without presenting')
    actual_math=json.loads((out/'numerics.json').read_text())['math']
    require(actual_math=='amd-6121d02-'+('sse2' if profile.endswith('-sse2') else 'fma3'), 'API actual math profile differs')
    states=rows(out/'flight-state.csv')
    require(len(states)==1 and {row['object']:row['class'] for row in states}==cfg['vessels'],
            'Complete unchanged API vessel roster required')
    row=states[0]
    require(row['tick']=='0' and row['frame']=='0' and float(row['seconds'])==0 and
            float(row['mjd'])==51982.5292925579, 'API startup finalized boundary differs')
    for key in ('rx','ry','rz','vx','vy','vz','wx','wy','wz','mass','fuel'):
        require(math.isfinite(float(row[key])), 'Nonfinite API initial vessel quantity')
    require(float(row['mass'])>0 and float(row['fuel'])>=0 and row['focus']=='GL-01', 'API initial vessel state incomplete')
    require(Path(save).read_bytes()==SAVE_SENTINEL, 'Startup API exit overwrote the existing save')
    return dict(policy=cfg['protocol'],variant=cfg['test_variant'],completed_frames=0,
                finalized_ticks=1,declared_vessels=cfg['vessels'],assertion_passes=11,
                assertion_events=EXPECTED_EVENTS,actual_math=actual_math,existing_save_preserved=True)


def inspect_windows_roster(out, enabled):
    """Read the roster after insertion; load.after itself still has count zero."""
    observed=rows(Path(out)/'api-startup-objects.csv')
    if not enabled:
        require(not observed and not rows(Path(out)/'api-startup-events.csv'), 'Disabled observer still observed startup')
        return []
    require(len(observed)==1 and {r['name']:r['class'] for r in observed}==settings()['vessels'],
            'Actual completed Windows API vessel roster missing or substituted')
    r=observed[0]
    require(r['phase']=='vessel.postcreation.after' and r['index']=='0' and float(r['seconds'])==0 and
            float(r['mjd'])==51982.5292925579 and int(r['version'])==3 and
            all(math.isfinite(float(r[k])) and float(r[k])>0 for k in ('size','empty_mass','mass')) and
            int(r['meshes'])>0 and int(r['docks'])>0, 'Windows API startup capability observation incomplete')
    return observed
