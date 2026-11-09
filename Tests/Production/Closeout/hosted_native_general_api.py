#!/usr/bin/env python3
"""Fresh General API diagnostics on the exact retained sanitized native packages."""
import hashlib
import json
from pathlib import Path
import subprocess
import capture_hosted_native_writer_runtime as runtime_writer
from hosted_native_package import ROOT, require, sha, load

RUNTIME='ccc02c8a34bd1f227624d8778a141e8736ae8111'
WINDOWS='c08f93151827949ee3ad498f8021f35c11753fde'
BASE='315ae66e31ec13c4b43743e4c91316b4041d481b'
API='Tests/Production/GeneralApiCorrection/'
CONSERVED=('capture_native.py','audit_native.py','prepare.py','startup_contract.py','startup-policy-v1.json','inputs-v2.json')


def source_identity():
    producer=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
    lock=ROOT/'Tests/Production/phase3-extraction.lock.json'
    frozen=subprocess.check_output(['git','-C',str(ROOT),'show',BASE+':'+lock.relative_to(ROOT).as_posix()])
    require(lock.read_bytes()==frozen,'Original complete extraction source lock changed')
    paths=sorted(json.loads(frozen)['files'])
    require(len(paths)==623 and len(set(paths))==623,'Complete locked extraction source set required')
    for role,source in (('native',RUNTIME),('current-Windows',WINDOWS)):
        changed=set(subprocess.check_output(['git','-C',str(ROOT),'diff','--name-only',source,producer],text=True).splitlines())
        require(not changed.intersection(paths),'Actual compiled '+role+' owning core differs from this collector')
    conserved={}
    for name in CONSERVED:
        relative=API+name;path=ROOT/relative
        original=subprocess.check_output(['git','-C',str(ROOT),'show',BASE+':'+relative])
        require(path.read_bytes()==original,'Original API collector/audit/startup contract changed: '+name)
        conserved[relative]=sha(path)
    return dict(collector_source=producer,compiled_runtime_source=RUNTIME,current_windows_core_source=WINDOWS,
                complete_locked_source_count=len(paths),locked_source_paths_sha256=hashlib.sha256(json.dumps(paths).encode()).hexdigest(),
                actual_core_sources_identical=True,original_api_sources_sha256=conserved,
                retained_runtime_relabelled=False,phase6_complete=False)


def inspect_audit(capture,output,profile):
    diagnostic=load(capture/'diagnostic.json');audit=load(output)
    require(diagnostic['status']=='captured-original-and-corrected-native-diagnostic-only' and
            audit['status']=='passed-native-api-script-diagnostic-only' and
            audit['runtime_identity']==diagnostic['runtime_identity'] and
            audit['runtime_identity']['runtime_source_commit']==RUNTIME and
            audit['runtime_identity']['profile']==profile and audit['runtime_identity']['sanitizer_linked'] is True and
            audit['startup_exit_policy_audited'] is True and audit['normal_admission_qualified'] is False and
            audit['phase6_complete'] is False,'Complete independent actual sanitized API audit required')
    require(set(audit['observed'])==set(diagnostic['cases'])=={'original','corrected'},'Both real original and corrected API processes required')
    pids=[]
    for variant,markers in (('original',10),('corrected',11)):
        observed=audit['observed'][variant];process=diagnostic['cases'][variant]['process']
        require(observed['completed_pass_markers']==markers and observed['returncode']==0 and
                observed['actual_pid']==process['actual_collector_pid']>0 and process['terminal'] is True and
                process['actual_returncode']==0 and process['cancelled'] is False,'Actual inherited-failure/corrected pass markers and process identity required')
        pids.append(observed['actual_pid'])
    require(len(set(pids))==2,'Two distinct real simulator processes required')
    require(audit['evidence_sha256'] and all(Path(p).is_file() and sha(p)==h for p,h in audit['evidence_sha256'].items()),
            'Every independent actual API evidence byte must remain available and unchanged')
    return dict(actual_processes=2,profile=profile,original_inherited_assertion_preserved=True,
                corrected_pass_markers=11,capture_sha256=sha(capture/'diagnostic.json'),independent_audit_sha256=sha(output),
                windows_comparison_pending=True,complete_general_api_qualification=False,normal_admission_qualified=False,phase6_complete=False)


def prepared_body():
    body=runtime_writer.prepared_body()
    changes=[("protocol='phase6-hosted-native-stock-writer-runtime-v3'","protocol='phase6-hosted-native-general-api-v1'"),
             ("ROOT/'out/hosted-native-writer'","ROOT/'out/hosted-native-api'"),
             ("ROOT/'out/native-writer-container.json'","ROOT/'out/native-api-container.json'")]
    for before,after in changes:
        expected=2 if 'container.json' in before else 1
        require(body.count(before)==expected,'Conserved provider setup path/protocol anchor changed: '+before)
        body=body.replace(before,after)
    start=body.index("        build=ROOT/'out/phase6-hosted-native'/a.profile;capture=")
    end=body.index("        require(sha(ROOT/'out/mesa-topology-restoration/restoration.json')",start)
    replacement=r"""
        from hosted_native_general_api import source_identity,inspect_audit
        report['source_identity']=source_identity();save()
        build=ROOT/'out/phase6-hosted-native'/a.profile;capture=ROOT/'out/native-general-api-capture'/a.profile
        capture.parent.mkdir(parents=True,exist_ok=True)
        environment=dict(os.environ,__EGL_VENDOR_LIBRARY_FILENAMES=str(mesa/'install/share/glvnd/egl_vendor.d/50_mesa.json'))
        argv=py+['Tests/Production/GeneralApiCorrection/capture_native.py','--owner',str(ROOT),'--package',str(build),
            '--assets','out/native-stock-assets','--data','out/native-stock-data','--planets','out/native-stock-planets',
            '--compositor-tools',str(providers/'compositor'),'--gtk-plugin',str(providers/'libdecor-candidate/build/src/plugins/gtk/libdecor-gtk.so'),
            '--output',str(capture)]
        for folder in ('fontconfig-candidate','gdk-candidate'):argv+=['--library',str(providers/folder/'install/lib/x86_64-linux-gnu')]
        argv+=['--library',str(mesa/'install/lib/x86_64-linux-gnu')]
        run('original-and-corrected-GeneralApi',argv,900,environment)
        audit=output/'independent-native-api-audit.json'
        run('independent-GeneralApi-audit',py+['Tests/Production/GeneralApiCorrection/audit_native.py',
            '--capture',str(capture),'--owner',str(ROOT),'--variant-version','v2','--output',str(audit)],300,environment)
        report['actual_api_results']=inspect_audit(capture,audit,a.profile);save()
        require(source_identity()==report['source_identity'],'Actual API and core sources changed during capture')
""".lstrip('\n')
    body=body[:start]+replacement+body[end:]
    before="        report.update(status='captured-and-independently-audited-native-writers-only',actual_processes=76,\n            capture_sha256=sha(capture/'capture.json'),independent_audit_sha256=sha(output/'independent-native-writer-audit.json'))"
    require(body.count(before)==1,'Original final writer summary anchor changed')
    body=body.replace(before,"        report.update(status='captured-and-independently-audited-native-GeneralApi-diagnostics-only',actual_processes=2,\n            complete_general_api_qualification=False,normal_admission_qualified=False,phase6_complete=False)",1)
    return body


if __name__=='__main__':
    exec(compile(prepared_body(),str(Path(__file__)),'exec'),{'__name__':'__main__','__file__':str(Path(__file__))})
