#!/usr/bin/env python3
"""Discover closeout control tests and retain their actual totals and source hashes."""
import argparse
import ast
import importlib.util
import io
from pathlib import Path
import time
import unittest
import sys
import subprocess
import hashlib
from contracts import ROOT,atomic_json,require,sha

HERE=Path(__file__).resolve().parent


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--test-directory',type=lambda p:Path(p).resolve(),default=HERE,
                        help='One explicitly selected helper-test directory; CLI/runtime fixtures are inventoried separately')
    args=parser.parse_args();require(not args.output.exists(),'Fresh controls output required')
    require(args.test_directory.is_dir(),'Existing helper-test directory required')
    sys.path.insert(0,str(args.test_directory))
    suite=unittest.TestSuite();inventory=[];other=[]
    paths=set(args.test_directory.glob('*.Test.py')) | set(args.test_directory.glob('test_*.py'))
    for path in sorted(paths):
        tree=ast.parse(path.read_bytes(),filename=str(path))
        if any(isinstance(node,(ast.Assign,ast.Expr)) and any(isinstance(call,ast.Call) and
                isinstance(call.func,ast.Attribute) and call.func.attr=='parse_args'
                for call in ast.walk(node.value)) for node in tree.body):
            other.append(dict(path=str(path),sha256=sha(path),scope='Explicit CLI/runtime arguments required; not executed by helper discovery'))
            continue
        if not any(isinstance(node,ast.ClassDef) and any(
                isinstance(base,ast.Attribute) and base.attr=='TestCase' or
                isinstance(base,ast.Name) and base.id=='TestCase' for base in node.bases)
                for node in tree.body):
            other.append(dict(path=str(path),sha256=sha(path),scope='Separate CLI/runtime fixture; not a unittest suite'))
            continue
        spec=importlib.util.spec_from_file_location('closeout_control_'+path.name.split('.')[0],path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        tests=unittest.defaultTestLoader.loadTestsFromModule(module)
        inventory.append(dict(path=str(path),sha256=sha(path),discovered_tests=tests.countTestCases()))
        suite.addTests(tests)
    require(suite.countTestCases()>0,'No unittest tests discovered; empty selection cannot pass')
    stream=io.StringIO();started=time.monotonic_ns()
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    sources={str(p):sha(p) for directory in {HERE,args.test_directory} for p in directory.rglob('*.py')}
    producer=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
    exact=True
    for filename,checksum in sources.items():
        path=Path(filename)
        if not path.is_relative_to(ROOT):
            exact=False;continue
        original=subprocess.run(['git','-C',str(ROOT),'show',producer+':'+path.relative_to(ROOT).as_posix()],
                                stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
        exact=exact and original.returncode==0 and hashlib.sha256(original.stdout).hexdigest()==checksum
    report=dict(status='passed' if result.wasSuccessful() else 'failed',
        tests_run=result.testsRun,skipped=len(result.skipped),failures=len(result.failures),errors=len(result.errors),
        elapsed_ns=time.monotonic_ns()-started,test_inventory=inventory,output=stream.getvalue(),
        discovery_directory=str(args.test_directory),separate_cli_runtime_fixtures=other,
        discovery_patterns=['*.Test.py','test_*.py'],
        producer_commit=producer,sources_match_producer=exact,sources_sha256=sources,
        scope='Control fixtures and disposable processes only; no runtime acceptance credit',phase6_complete=False)
    atomic_json(args.output,report)
    print(stream.getvalue(),end='')
    return int(not result.wasSuccessful())


if __name__=='__main__':raise SystemExit(main())
