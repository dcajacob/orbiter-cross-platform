#!/usr/bin/env python3
"""Reject undeclared Lua inputs/edits and preserve original sources exactly."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[3]


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--output',type=Path)
    a=p.parse_args();source=a.source.resolve()
    if a.output and a.output.exists():raise ValueError('Lua source-control output exists')
    declaration=json.loads(Path(__file__).with_name('upvalue-source.lock.json').read_text())
    expected=declaration['original_files_sha256']
    before={name:digest(source/name) for name in expected}
    if before!=expected:raise ValueError('Original Lua source identities differ')
    with tempfile.TemporaryDirectory(prefix='orbiter-lua-upvalues-') as temporary:
        folder=Path(temporary);script=folder/'generate.cmake'
        script.write_text('include("${ORBITER_SOURCE_ROOT}/Src/Module/LuaScript/Native/UpvalueGuards.cmake")\n'
                          'orbiter_native_lua_upvalues("${LUA_SOURCE_DIR}" "${LUA_OUTPUT_DIR}" effective)\n')
        def generate(inputs,out):
            return subprocess.run(['cmake','-DORBITER_SOURCE_ROOT='+str(ROOT),'-DLUA_SOURCE_DIR='+str(inputs),
                '-DLUA_OUTPUT_DIR='+str(out),'-P',str(script)],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        out=folder/'positive';result=generate(source,out)
        if result.returncode:raise ValueError(result.stdout)
        generated=out/'defined-upvalues/lfunc.c'
        if digest(generated)!=declaration['effective_lfunc_sha256']:raise ValueError('Wrong effective Lua source')
        timestamp=generated.stat().st_mtime_ns
        result=generate(source,out)
        if result.returncode or generated.stat().st_mtime_ns!=timestamp:raise ValueError('Lua source generation is not idempotent')
        changed=folder/'changed';changed.mkdir()
        for name in expected:shutil.copy2(source/name,changed/name)
        with (changed/'lfunc.c').open('a') as stream:stream.write('\n/* unrecorded edit */\n')
        result=generate(changed,folder/'bad-source')
        if result.returncode==0 or 'Original Lua source differs: lfunc.c' not in result.stdout:
            raise ValueError('Unrecorded original Lua edit was accepted')
        shutil.copy2(source/'lfunc.c',changed/'lfunc.c')
        (changed/'unrecorded.c').write_text('int unrecorded;\n')
        result=generate(changed,folder/'extra-source')
        if result.returncode==0 or 'Original Lua source input set differs' not in result.stdout:
            raise ValueError('Additional original Lua source was accepted')
        with generated.open('a') as stream:stream.write('\n/* unrecorded generated edit */\n')
        result=generate(source,out)
        if result.returncode==0 or 'Generated Lua upvalue source differs' not in result.stdout:
            raise ValueError('Unrecorded generated Lua edit was accepted')
    if before!={name:digest(source/name) for name in expected}:raise ValueError('Original Lua source tree changed')
    result=dict(status='passed',source_sha256=digest(Path(__file__)),locked_original_inputs=len(before),
        input_edits_rejected=True,extra_source_rejected=True,generated_edits_rejected=True,
        generated_source_idempotent=True,original_source_tree_unchanged=True)
    if a.output:a.output.write_text(json.dumps(result,indent=2)+'\n')
    print('Lua source drift rejected; two-guard generation is idempotent and original inputs unchanged')


if __name__=='__main__':main()
