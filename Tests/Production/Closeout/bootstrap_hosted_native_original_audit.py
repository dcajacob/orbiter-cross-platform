#!/usr/bin/env python3
"""Reuse the exact declared native environment setup; audit retained bytes without recapture."""
from pathlib import Path
import capture_hosted_native_writer_runtime as runtime
from contracts import require

ROOT=Path(__file__).resolve().parents[3]
ANCHOR="        build=ROOT/'out/phase6-hosted-native'/a.profile;capture=ROOT/'out/native-stock-writer'/a.profile"


def prepared_body():
    original=runtime.prepared_body()
    require(original.count(ANCHOR)==1 and original.count('    except BaseException as error:')==1,
        'Conserved complete native dependency/bootstrap boundaries changed')
    begin=original.index(ANCHOR);end=original.index('    except BaseException as error:',begin)
    audit="""        require(verify_native_runtime(output/'native-runtime-dependencies.json')==report['native_host_dependencies'],
            'Actual declared native runtime dependencies changed before physical audit')
        from audit_native_original_cli import audit_after_bootstrap
        result=audit_after_bootstrap(a.profile,os.environ['NATIVE_PHASE'],output)
        require(verify_native_runtime(output/'native-runtime-dependencies.json')==report['native_host_dependencies'],
            'Actual declared native runtime dependencies changed during physical audit')
        report.update(status='audited-one-complete-retained-native-original-physical-phase-only',
            actual_native_processes=result['actual_native_processes'],
            actual_direct_original_native_pairs=result['actual_direct_original_native_pairs'],
            physical_report_sha256=sha(ROOT/'out/native-original-physical-audits'/(a.profile+'-'+os.environ['NATIVE_PHASE']+'.json')),
            simulator_executed=False,complete_four_profile_two_phase_matrix_pending=True,current_native_comparisons_pending=True)
"""
    body=original[:begin]+audit+original[end:]
    replacements=[
        ("output=ROOT/'out/hosted-native-writer'/a.profile","output=ROOT/'out/native-original-bootstrap'/(a.profile+'-'+os.environ['NATIVE_PHASE'])"),
        ("protocol='phase6-hosted-native-stock-writer-runtime-v3'","protocol='phase6-hosted-native-original-physical-bootstrap-v1'"),
        ("        require(report['collector_source']==os.environ['GITHUB_SHA'],'Actual immutable collector source differs')",
         "        require(report['collector_source']==os.environ['GITHUB_SHA'],'Actual immutable collector source differs')\n        require(os.environ.get('NATIVE_PHASE') in ('stock-writer','windows-save-reload'),'Exact retained native physical phase required')")]
    for before,after in replacements:
        require(body.count(before)==1,'Conserved native bootstrap anchor changed: '+before);body=body.replace(before,after,1)
    return body


if __name__=='__main__':
    exec(compile(prepared_body(),str(Path(__file__).resolve()),'exec'),{'__name__':'__main__','__file__':str(Path(__file__).resolve())})
