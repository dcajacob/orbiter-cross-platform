#!/usr/bin/env python3
"""Run the corrected Lua helpers, reject damaged inputs, and preserve original bytes."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
from prepare import ROOT, EARTH, ORIGINAL, corrected, prepare, require


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lua',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();require(not args.output.exists(),'Fresh control receipt required')
    with tempfile.TemporaryDirectory(prefix='phase6-general-api-') as temp:
        root=Path(temp);variant=root/'variant';proof=prepare(variant)
        script=(variant/ORIGINAL).read_text()
        header=script[:script.index('-- "Constants"')]
        # Execute actual generated functions with harmless log sinks. No oapi
        # getters are mocked into a simulator pass; this only tests helpers.
        controls='''
local native_assert = assert
local original_error = error
oapi = {dbg_out=function() end, write_log=function() end}
'''+header+'''
local checks = 0
local function check(value) native_assert(value); checks = checks + 1 end
check(almost_equal(0,0)); check(almost_equal(1,1)); check(almost_equal(-1,-1))
check(almost_equal(5e-10,0)); check(not almost_equal(2e-9,0))
check(almost_equal(1+5e-11,1)); check(almost_equal(1-5e-11,1))
check(not almost_equal(0.5,1)); check(not almost_equal(1.5,1))
check(not almost_equal(-0.5,-1)); check(not almost_equal(-1.5,-1))
check(not almost_equal(0,1)); check(not almost_equal(-1,1))
check(not almost_equal(nil,1)); check(not almost_equal(1,nil))
check(not almost_equal(0/0,1)); check(not almost_equal(math.huge,math.huge))
check(not pcall(assert,false)); check(not pcall(assert,nil))
check(pcall(assert,true)); check(pcall(assert,0)); check(pcall(assert,""))
check(assert(0) == 0)
check(select("#",assert(true,123,nil,"tail")) == 4)
local a,b,c,d = assert("truthy","payload",nil,17)
check(a == "truthy" and b == "payload" and c == nil and d == 17)
local ok,message = pcall(assert,false,"specific assertion failure")
check(not ok and string.find(message,"specific assertion failure",1,true) ~= nil)
print("passed-helper-controls:"..checks)
'''
        path=root/'controls.lua';path.write_text(controls)
        completed=subprocess.run([str(args.lua.resolve()),str(path)],text=True,capture_output=True)
        require(completed.returncode == 0 and completed.stdout.strip() == 'passed-helper-controls:26',
                'Actual Lua helper controls failed: '+completed.stdout+completed.stderr)
        original=(ROOT/ORIGINAL).read_bytes();earth=(ROOT/EARTH).read_bytes()
        rejected=0
        for bad_original,bad_earth in [(original.replace(b'if cond == false then',b'if cond == true then'),earth),
            (original,earth.replace(b'PrecessionObliquity =  0',b'PrecessionObliquity =  1')),
            (original,earth+b'\nObliquity = 0.5\n')]:
            try:corrected(bad_original,bad_earth)
            except ValueError:rejected+=1
            else:raise ValueError('Damaged correction input accepted')
        # Keep the already audited v1 variant reproducible with its owning reader.
        v1,unused=corrected(original,earth,'v1')
        require(b'if not cond then' in v1 and b'local lua_assert = assert' not in v1,
                'Historical correction v1 was silently replaced')
        proof.update(status='passed-correction-helper-controls-only', actual_lua_controls=26,
                     rejected_damaged_inputs=rejected, runtime_windows_and_native_qualified=False,
                     lua_executable=str(args.lua.resolve()),
                     lua_executable_sha256=hashlib.sha256(args.lua.read_bytes()).hexdigest(),
                     control_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                     preparation_source_sha256=hashlib.sha256(Path(__file__).with_name('prepare.py').read_bytes()).hexdigest())
    args.output.write_text(json.dumps(proof,indent=2)+'\n')
    print('26 actual Lua helper controls and 3 damaged-input controls passed')


if __name__=='__main__':main()
