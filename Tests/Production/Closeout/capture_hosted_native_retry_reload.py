#!/usr/bin/env python3
"""Run all unchanged normal-host reloads from exact independently audited Windows end saves."""
from pathlib import Path
import subprocess
import capture_hosted_native_writer_runtime as writer

ROOT=Path(__file__).resolve().parents[3]
SOURCE='fc523104e3d223c1a70dbc3a9519018a0b49d857'


def prepared_body():
    for name in ('capture_hosted_native_writer_runtime.py','hosted_native_runtime_dependencies.py'):
        path=Path(__file__).with_name(name)
        if path.read_bytes()!=subprocess.check_output(['git','-C',str(ROOT),'show',SOURCE+':'+path.relative_to(ROOT).as_posix()]):
            raise ValueError('Original declared-runtime collector changed: '+name)
    body=writer.prepared_body()
    changes=[
        ("protocol='phase6-hosted-native-stock-writer-runtime-v3'","protocol='phase6-hosted-native-exact-save-reload-retry-v2'"),
        ("output=ROOT/'out/hosted-native-writer'/a.profile","output=ROOT/'out/hosted-native-reload'/a.profile"),
        ("windows_comparisons_pending=True,reload_phase_pending=True","windows_comparisons_pending=True,writer_phase_pending=True"),
        ("        require(report['collector_source']==os.environ['GITHUB_SHA'],'Actual immutable collector source differs')",
         "        require(report['collector_source']==os.environ['GITHUB_SHA'],'Actual immutable collector source differs')\n        from hosted_native_retry_reload_reference import bind as bind_reference,verify as verify_reference\n        reference=bind_reference(a.profile);report['original_reference']=reference;save()"),
        ("capture=ROOT/'out/native-stock-writer'/a.profile","capture=ROOT/'out/native-stock-reload'/a.profile"),
        ("'--phase','stock-writer'","'--phase','windows-save-reload'"),
        ("        run('all-38-stock-writers-twice',argv,15000,environment)",
         "        argv+=['--windows-parent-capture',reference['capture'],'--windows-build',reference['build'],'--preserved',reference['preserved']]\n        run('all-38-exact-Windows-save-reloads-twice',argv,15000,environment)"),
        ("reader,a.profile,'stock-writer'","reader,a.profile,'windows-save-reload'"),
        ("'Complete independent native writer-only audit required'","'Complete independent native exact-save reload audit required'"),
        ("'independent-native-writer-audit.json'","'independent-native-reload-audit.json'"),
        ("        report.update(status='captured-and-independently-audited-native-writers-only'",
         "        verify_reference(reference)\n        report.update(status='captured-and-independently-audited-native-exact-save-reloads-only'")]
    for before,after in changes:
        if body.count(before)<1:raise ValueError('Conserved full native reload anchor changed: '+before)
        body=body.replace(before,after)
    return body


if __name__=='__main__':
    exec(compile(prepared_body(),str(writer.mesa_writer.ORIGINAL),'exec'),{'__name__':'__main__','__file__':str(writer.mesa_writer.ORIGINAL)})
