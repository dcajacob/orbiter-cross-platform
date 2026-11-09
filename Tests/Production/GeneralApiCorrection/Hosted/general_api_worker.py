#!/usr/bin/env python3
"""Conserve the original Windows API matrix in its actual inherited GitHub session."""
import hashlib
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[4]
LEGACY=ROOT/'Tests/Production/GeneralApiCorrection/capture_windows.py'
LEGACY_SHA256_LF='aae7e5d70f73c0cc91328f058fccb950d9ae32a1a262fe5bf96cf55c6b79ab93'


def replace_once(body,before,after):
    if body.count(before)!=1:raise ValueError('Conserved actual Windows API anchor changed: '+before[:100])
    return body.replace(before,after,1)


def prepared_body():
    body=LEGACY.read_bytes().replace(b'\r\n',b'\n')
    if hashlib.sha256(body).hexdigest()!=LEGACY_SHA256_LF:raise ValueError('Original Windows API collector body changed')
    body=body.decode()
    changes=(
      ('from windows_session_v1 import context\nfrom runtime_descriptor_v3 import preflight,require,sha',
       'from general_api_provider import context,preflight,require,sha'),
      ('cloud_builds_used=False','cloud_builds_used=True'),
      ("        require(report['context']==dict(session=cfg['active_session'],window_station='WinSta0',desktop=cfg['desktop']),\n                'Actual declared rendering context differs')\n",''),
      ("        built=load(cfg['application_build_manifest']);item=",
       "        built=load(cfg['application_build_manifest']);require(built['protocol']=='phase6-github-current-application-v1','Actual original hosted SDK protocol required');item="),
      ("        guards[observer['binary']]=observer['sha256']",
       "        guards[observer['binary']]=observer['sha256']\n        from general_api_shaders import guarded as shader_guarded,stage as stage_shader_inputs,inspect_staged as inspect_shader_inputs\n        guards.update(shader_guarded(cfg))\n        from inactive_stager_fixture import guarded as fixture_guarded,stage as stage_inactive_fixture,verify_staged as inspect_inactive_fixture\n        guards.update(fixture_guarded(cfg))"),
      ('                    def configure(directory):','                    def configure(directory):\n                        guards.update(stage_shader_inputs(directory,cfg))\n                        guards.update(stage_inactive_fixture(directory,cfg))'),
      ("                        dict(fixed_step=0.015625,frames=60,delivery_repairs=[]),case,configure,process_timeout=900)",
       "                        dict(fixed_step=0.015625,frames=60,delivery_repairs=[]),case,configure,process_timeout=900)\n                    inspect_shader_inputs(folder,cfg)\n                    inspect_inactive_fixture(folder,cfg)"),
      ("                        (directory/'ogl-evidence.enabled').touch();mesa_files(Path(cfg['mesa']),directory)",
       "                        (directory/'ogl-evidence.enabled').touch();mesa_files(Path(cfg['mesa']),directory)\n                        inspect_inactive_fixture(directory,cfg)"),
      ("            paths += [folder/script,folder/scenario]",
       "            paths += [folder/script,folder/scenario]\n            paths += [p for p in (folder/'Modules/OGLClient').rglob('*') if p.is_file()]\n            paths += [folder/'Modules/Plugin/ProductionCockpitDriver.dll']")
    )
    for before,after in changes:body=replace_once(body,before,after)
    return body


def main():
    sys.path[:0]=[str(Path(__file__).resolve().parent),str(ROOT/'Tests/Production/CurrentWindows/Hosted'),
        str(ROOT/'Tests/Production/RemainingStockPersistence/LocalVM')]
    exec(compile(prepared_body(),str(Path(__file__).resolve()),'exec'),{'__name__':'__main__','__file__':str(Path(__file__).resolve())})


if __name__=='__main__':main()
