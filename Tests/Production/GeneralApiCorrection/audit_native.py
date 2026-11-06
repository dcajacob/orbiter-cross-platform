#!/usr/bin/env python3
"""Re-read focused API script diagnostics without granting normal-host exit acceptance."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from prepare import ROOT, ORIGINAL, EARTH, corrected, digest, require


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture',type=Path,required=True)
    parser.add_argument('--owner',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--variant-version',choices=('v1','v2'),default='v2')
    args=parser.parse_args();require(not args.output.exists(),'Fresh focused audit output required')
    report_path=args.capture/'diagnostic.json';body=report_path.read_bytes();report=json.loads(body)
    require(report['status']=='captured-original-and-corrected-native-diagnostic-only' and
            set(report['cases'])=={'original','corrected'} and report['normal_admission_qualified'] is False,
            'Complete focused original/corrected diagnostic required')
    expected,oracle=corrected((ROOT/ORIGINAL).read_bytes(),(ROOT/EARTH).read_bytes(),args.variant_version)
    sys.path.insert(0,str(args.owner/'Tests/Production/StockScenarios'))
    import intentional_exit
    observed={};protected={str(report_path):digest(body),**report['guarded_files_sha256']}
    require(all(digest(Path(p).read_bytes())==h for p,h in protected.items()), 'Retained diagnostic inputs differ')
    for variant in ('original','corrected'):
        folder=args.capture/variant;record=report['cases'][variant]
        invocation=json.loads((folder/'diagnostic-invocation.json').read_text())
        engine=Path(invocation['argv'][0]).parent;build=engine.parent/'build.json'
        identity=intentional_exit.build_identity(engine/'orbiter-production',engine/'NativeModules',build,
                                                report['runtime_identity']['runtime_source_commit'])
        require(identity==report['runtime_identity'] and identity['sanitizer_linked'] and
                hashlib.sha256(build.read_bytes()).hexdigest()==report['build_sha256'], 'Actual native package identity differs')
        script=(folder/ORIGINAL).read_bytes();console=(folder/'console.log').read_bytes();text=console.decode(errors='replace')
        require(script==((ROOT/ORIGINAL).read_bytes() if variant=='original' else expected) and
                digest(script)==record['script_sha256']==invocation['script_sha256'] and digest(console)==record['console_sha256'],
                'Actual script or console bytes differ')
        require(invocation['sanitizer_environment']==dict(ASAN_OPTIONS='detect_leaks=1:fast_unwind_on_malloc=0',
                LSAN_OPTIONS='',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1'), 'Sanitizers must remain unsuppressed')
        require(record['process']['terminal'] is True and record['process']['actual_returncode']==0 and
                record['process']['cancelled'] is False and record['process']['actual_collector_pid']>0,
                'Actual completed simulator receipt required')
        life=json.loads((folder/'graphics-lifecycle.json').read_text())
        require(life==record['graphics'] and life['context_deleted'] is True, 'Actual graphics closure differs')
        math=json.loads((folder/'numerics.json').read_text())['math']
        require(math=='amd-6121d02-'+('sse2' if identity['math_profile']=='sse2' else 'fma3'),
                'Actual original/corrected math profile differs')
        require(not any(s in text for s in ('ERROR: AddressSanitizer','ERROR: LeakSanitizer','runtime error:')),
                'Native sanitizer finding in focused diagnostic')
        if variant=='original':
            require('Assertion failed' in text and 'Test: planet status' in text and
                    '=== All tests passed ===' not in text, 'Original inherited failure was lost')
        else:
            require(text.count('=== All tests passed ===')==1 and text.count(' - passed')==11 and
                    'LuaCall (' not in text and ' - FAILED!' not in text,
                    'Corrected actual API script did not pass')
        for path in (folder/ORIGINAL,folder/'console.log',folder/'diagnostic-invocation.json',folder/'graphics-lifecycle.json',
                     folder/'numerics.json',folder/'flight-state.csv',folder/'Scenarios/Tests/GeneralApiTest.scn'):
            protected[str(path)]=digest(path.read_bytes())
        observed[variant]=dict(actual_pid=record['process']['actual_collector_pid'],returncode=0,
            completed_pass_markers=text.count(' - passed'),graphics=life,script_sha256=digest(script))
    require(all(digest(Path(p).read_bytes())==h for p,h in protected.items()), 'Diagnostic changed during independent read')
    result=dict(status='passed-native-api-script-diagnostic-only',runtime_identity=report['runtime_identity'],oracle=oracle,
        observed=observed,evidence_sha256=protected,normal_admission_qualified=False,phase6_complete=False,
        windows_match_and_explicit_startup_exit_policy_pending=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(status=result['status'],observed=observed)))


if __name__=='__main__':main()
