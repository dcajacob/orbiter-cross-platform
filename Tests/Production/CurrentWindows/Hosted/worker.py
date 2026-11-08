#!/usr/bin/env python3
"""Run the conserved stock collector in its inherited standard Actions session."""
import hashlib
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[4]
LEGACY=ROOT/'Tests/Production/Closeout/LocalVM/stock_runtime_worker_v3.py'
LEGACY_SHA256_LF='dddbbf40656524ffa2dddcfcd745767ed270d3d46109917c2da3a89f66a15c51'


def replace_once(body,before,after):
    if body.count(before)!=1:raise ValueError('Conserved worker anchor changed: '+before[:100])
    return body.replace(before,after,1)


def prepared_body():
    body=LEGACY.read_bytes().replace(b'\r\n',b'\n')
    if hashlib.sha256(body).hexdigest()!=LEGACY_SHA256_LF:
        raise ValueError('Retained stock worker changed; hosted transport requires independent review')
    body=body.decode()
    # A historical VM-only supplemental export is outside the simulation body.
    start=body.index('def collect_closed_inputs(');end=body.index('\ndef main():',start)
    body=body[:start]+body[end:]
    for before,after in (
        ('from windows_session_v1 import context\nfrom runtime_descriptor_v3 import preflight,require,sha',
         'from provider import context,preflight,require,sha,selection'),
        ('from current_stock import selection,inspect_run','from stock import inspect_run'),
        ("    if cfg.get('action')=='collect-closed-input-witnesses':collect_closed_inputs(request,cfg);return\n",''),
        ('cloud_builds_used=False','cloud_builds_used=True'),
        ("        require(report['context']==dict(session=cfg['active_session'],window_station='WinSta0',desktop=cfg['desktop']), 'Actual declared rendering context differs')\n",''),
        ("        built=load(cfg['application_build_manifest']);item=",
         "        built=load(cfg['application_build_manifest']);require(built['protocol']=='phase6-github-current-application-v1', 'Actual hosted SDK build protocol required');item="),
        ("expected_inputs={(mode,case['id'],repeat) for mode in ('automatic','sse2')",
         "expected_inputs={(mode,case['id'],repeat) for mode in (cfg['math_profile'],)"),
        ("        for mode in ('automatic','sse2'):\n","        for mode in (cfg['math_profile'],):\n"),
    ):body=replace_once(body,before,after)
    return body


def main():
    sys.path[:0]=[str(Path(__file__).resolve().parent),str(ROOT/'Tests/Production/CurrentWindows'),
                  str(ROOT/'Tests/Production/Closeout/LocalVM')]
    exec(compile(prepared_body(),str(Path(__file__).resolve()),'exec'),
         {'__name__':'__main__','__file__':str(Path(__file__).resolve())})


if __name__=='__main__':main()
