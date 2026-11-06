#!/usr/bin/env python3
"""Discover closeout control tests and retain their actual totals and source hashes."""
import argparse
import importlib.util
import io
from pathlib import Path
import time
import unittest
from contracts import atomic_json,require,sha

HERE=Path(__file__).resolve().parent


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();require(not args.output.exists(),'Fresh controls output required')
    suite=unittest.TestSuite();inventory=[]
    for path in sorted(HERE.glob('*.Test.py')):
        spec=importlib.util.spec_from_file_location('closeout_control_'+path.name.split('.')[0],path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        tests=unittest.defaultTestLoader.loadTestsFromModule(module)
        inventory.append(dict(path=str(path),sha256=sha(path),discovered_tests=tests.countTestCases()))
        suite.addTests(tests)
    stream=io.StringIO();started=time.monotonic_ns()
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    report=dict(status='passed' if result.wasSuccessful() else 'failed',
        tests_run=result.testsRun,skipped=len(result.skipped),failures=len(result.failures),errors=len(result.errors),
        elapsed_ns=time.monotonic_ns()-started,test_inventory=inventory,output=stream.getvalue(),
        sources_sha256={str(p.relative_to(HERE)):sha(p) for p in HERE.rglob('*.py')},
        scope='Control fixtures and disposable processes only; no runtime acceptance credit',phase6_complete=False)
    atomic_json(args.output,report)
    print(stream.getvalue(),end='')
    return int(not result.wasSuccessful())


if __name__=='__main__':raise SystemExit(main())
