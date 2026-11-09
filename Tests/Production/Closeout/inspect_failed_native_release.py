#!/usr/bin/env python3
"""Inspect exact retained failed Release process bytes using the unchanged original diagnostic."""
import importlib.util
from pathlib import Path
import subprocess
from contracts import ROOT,require

ORIGINAL_READER_SOURCE='59e599c598dffeda7e5fbf055a4d5ecc520da11c'
PINS={
    'Release-sse2':(128890766422,13643838359,353743219,'33137732fe1c1627850d205fc78b768bb6a7abff46197ea3507e7a021332b6a8'),
    'Release-automatic':(128890766404,13644054477,353965745,'bea7052e4edf63f5f2e7dbe6375d1af3ac66cad27c9f6062466304594b7b5727')}


def main():
    path=ROOT/'Tests/Production/Closeout/inspect_failed_native_writers.py'
    original=subprocess.check_output(['git','-C',str(ROOT),'show',ORIGINAL_READER_SOURCE+':'+path.relative_to(ROOT).as_posix()])
    require(path.read_bytes()==original,'Original retained failure diagnostic body must remain unchanged')
    spec=importlib.util.spec_from_file_location('actual_retained_release_failure_reader',path)
    reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader)
    require(reader.SOURCE=='d23d371a510dd464cde95a301dbc685514391f9c' and reader.RUN==42532847296,
            'Exact old native collector identity required; no capture relabeling')
    reader.PINS=PINS
    reader.main()


if __name__=='__main__':main()
