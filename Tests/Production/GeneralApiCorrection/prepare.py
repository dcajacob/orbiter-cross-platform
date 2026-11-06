#!/usr/bin/env python3
"""Create a narrow versioned GeneralApiTest variant; never overwrite original inputs."""
import argparse
import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ORIGINAL = 'Script/Tests/GeneralApiTest.lua'
EARTH = 'Src/Celbody/SPICE/Config/Earth.cfg'


def require(value, message):
    if not value:
        raise ValueError(message)


def digest(body):
    return hashlib.sha256(body).hexdigest()


def corrected(original, earth):
    fields = {}
    for line in earth.decode('ascii').splitlines():
        line = line.split(';', 1)[0].strip()
        key, separator, value = line.partition('=')
        if separator:
            require(key.strip().lower() not in fields, 'Ambiguous Earth configuration key')
            fields[key.strip().lower()] = value.strip()
    # With no precession obliquity the axis tilt equals the declared fixed
    # Obliquity. Do not silently apply this oracle to a different axis model.
    require(fields['module'] == 'spice' and fields['body'] == 'EARTH' and
            float(fields['precessionobliquity']) == 0, 'Oracle requires locked SPICE fixed-tilt model')
    period = float(fields['sidrotperiod']); tilt = float(fields['obliquity'])
    equatorial_speed = 2 * math.pi * float(fields['size']) / period
    require(86000 < period < 87000 and 0 < tilt < 1, 'Invalid Earth oracle')
    source = original.decode('utf-8')
    old_comparator = '''function almost_equal(a,b)
\tif a==0 and b==0 then
\t\treturn true
\tend
\tif b==0 then
\t\treturn math.abs(a) < 0.000000001
\tend
\treturn math.abs(a/b) < 1.0000000001\x20
end'''
    new_comparator = '''function almost_equal(a,b)
\tif type(a) ~= "number" or type(b) ~= "number" then return false end
\tif a ~= a or b ~= b or math.abs(a) == math.huge or math.abs(b) == math.huge then return false end
\tif b == 0 then return math.abs(a) < 0.000000001 end
\treturn math.abs(a-b) < math.abs(b)*0.0000000001
end'''
    old_planet = '''assert(almost_equal(oapi.get_planetperiod(earth), 86164.10132))
assert(almost_equal(oapi.get_planetobliquity(earth)/math.pi*180,23.43929100097))'''
    new_planet = ('-- Oracle: locked SPICE Earth.cfg; zero PrecessionObliquity fixes the axis tilt.\n'
                  'assert(almost_equal(oapi.get_planetperiod(earth), ' + repr(period) + '))\n'
                  'assert(almost_equal(oapi.get_planetobliquity(earth), ' + repr(tilt) + '))')
    replacements = [('if cond == false then', 'if not cond then'),
                    (old_comparator, new_comparator), (old_planet, new_planet),
                    ('assert(almost_equal(gv.z, 464.58137217991))',
                     'assert(almost_equal(gv.z, ' + repr(equatorial_speed) + '))')]
    for old, new in replacements:
        require(source.count(old) == 1, 'Narrow original test repair no longer applies')
        source = source.replace(old, new)
    return source.encode(), dict(sidereal_period_seconds=period, fixed_obliquity_radians=tilt,
                                precession_obliquity_radians=0, equatorial_speed_m_s=equatorial_speed, replaced_regions=4)


def prepare(output):
    output = Path(output)
    require(not output.exists(), 'Fresh test-variant output required')
    lock = json.loads((HERE/'inputs-v1.json').read_text())
    inputs = {name:(ROOT/name).read_bytes() for name in (ORIGINAL, EARTH)}
    for name, body in inputs.items():
        require(digest(body.replace(b'\r\n',b'\n')) == lock['inputs_sha256_lf'][name], 'Locked correction input differs: ' + name)
    body, oracle = corrected(inputs[ORIGINAL].replace(b'\r\n',b'\n'), inputs[EARTH])
    output.mkdir(parents=True)
    original = output/'original/GeneralApiTest.lua'; original.parent.mkdir(); original.write_bytes(inputs[ORIGINAL])
    target = output/ORIGINAL;target.parent.mkdir(parents=True);target.write_bytes(body)
    manifest = dict(protocol=lock['protocol'], status='prepared-test-variant-not-runtime-qualified', oracle=oracle,
        original_script_sha256=digest(inputs[ORIGINAL]), corrected_script_sha256=digest(body),
        locked_inputs_sha256_lf=lock['inputs_sha256_lf'], scenario_entry_points_unchanged=True,
        planetary_data_and_simulation_tolerances_unchanged=True, phase6_complete=False)
    (output/'variant.json').write_text(json.dumps(manifest,indent=2)+'\n')
    require(all((ROOT/name).read_bytes() == body for name,body in inputs.items()), 'Original correction inputs changed')
    return manifest


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    prepare(parser.parse_args().output)
