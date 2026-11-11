#!/usr/bin/env python3
"""Diagnose new HST Launch behavior at the original60frame/quartersecond clock."""
import sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE),str(HERE.parent)]
import windows_capture
from PhysicsV2.transforms import replace_once


def main():
    body=windows_capture.prepared_body()
    body=replace_once(body,"ROOT/'Tests/Production/Closeout/failed-normal-admission-v4.lock.json'","ROOT/'Tests/Production/PhysicsV2/hst-cases.json'")
    body=body.replace("ROOT/'out/physics-v2-Windows'","ROOT/'out/physics-v2-HST-Windows'")
    body=replace_once(body,"protocol='phase6-four-original-scenes-fresh-physics-v2-Windows'","protocol='phase6-physics-v2-new-HST-regression-Windows-diagnostic'")
    exec(compile(body,str(HERE/'windows_hst.py'),'exec'),{'__name__':'__main__','__file__':str(HERE/'windows_hst.py')})


if __name__=='__main__':main()
