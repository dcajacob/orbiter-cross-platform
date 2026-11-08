#!/usr/bin/env python3
"""Seal only the complete corrected API test matrix, never the stock admission gate."""
import argparse
import json
from pathlib import Path
from prepare import ROOT, require, digest
from startup_contract import settings, EXPECTED_EVENTS

PROFILES={'Debug-automatic','Debug-sse2','Release-automatic','Release-sse2'}


def sha(path): return digest(Path(path).read_bytes())
def load(path): return json.loads(Path(path).read_text())


def inspect(path):
    report=load(path)
    require(report['status']=='qualified-general-api-correction-v2' and report['protocol']=='general-api-startup-exit-v1' and
            set(report['profiles'])==PROFILES and set(report['cohorts'])=={'current-windows','native'} and
            report['normal_stock_admission_qualified'] is False and report['phase6_complete'] is False and
            report['policy']==settings(), 'Complete versioned API qualification required')
    require(report['evidence_sha256'] and all(sha(p)==value for p,value in report['evidence_sha256'].items()),
            'Actual qualified API evidence changed')
    return report


def qualify(native,windows,helpers,controls,output):
    require(not output.exists(), 'Fresh API matrix qualification receipt required')
    evidence={};observed={'native':{},'current-windows':{}}
    def retain(path):
        path=Path(path).resolve();evidence[str(path)]=sha(path);return load(path)
    for path in native:
        report=retain(path);identity=report['runtime_identity'];profile=identity['profile']
        require(report['status']=='passed-native-api-script-diagnostic-only' and profile in PROFILES and
                profile not in observed['native'] and report['startup_exit_policy_audited'] is True and
                identity['sanitizer_linked'] is True and report['normal_admission_qualified'] is False,
                'Native API profile missing, duplicated, unsanitized or startup exit not independently audited')
        for key,value in report['evidence_sha256'].items():
            require(key not in evidence or evidence[key]==value, 'Conflicting API evidence digest');evidence[key]=value
        original=report['observed']['original'];corrected=report['observed']['corrected'];startup=corrected['startup_exit']
        require(original['completed_pass_markers']==10 and corrected['completed_pass_markers']==11 and
                startup['policy']==settings()['protocol'] and startup['assertion_events']==EXPECTED_EVENTS and
                startup['existing_save_preserved'] is True and corrected['returncode']==0,
                'Native original failure/corrected assertions/exit evidence incomplete')
        observed['native'][profile]=dict(identity=identity,original=original,corrected=corrected)
    for path in windows:
        report=retain(path)
        require(report['status']=='passed-current-Windows-api-diagnostic-only' and report['actual_processes']==8 and
                report['normal_admission_qualified'] is False, 'Closed independent current-Windows API audit required')
        for key,value in report['evidence_sha256'].items():
            require(key not in evidence or evidence[key]==value, 'Conflicting API evidence digest');evidence[key]=value
        for profile in report['profiles']:
            require(profile in PROFILES and profile not in observed['current-windows'], 'Windows API profile omitted or duplicated')
            mode=profile.split('-',1)[1];cases={key:report['results'][mode+'-'+key] for key in
                ('original-off','original-on','corrected-off','corrected-on')}
            require(all(cases[key]['script_result']=='failed-inherited-assertion' for key in ('original-off','original-on')) and
                    all(cases[key]['script_result']=='passed-corrected-test' and cases[key]['assertion_events']==EXPECTED_EVENTS
                        for key in ('corrected-off','corrected-on')) and len(cases['corrected-on']['roster'])==1,
                    'Current-Windows corrected test or completed vessel roster incomplete')
            observed['current-windows'][profile]=dict(roles=report['roles'],cases=cases)
    require(all(set(profiles)==PROFILES for profiles in observed.values()), 'Every API cohort/profile required')
    helper=retain(helpers);control=retain(controls)
    require(helper['status']=='passed-correction-helper-controls-only' and helper['actual_lua_controls']==26 and
            helper['rejected_damaged_inputs']==3 and helper['preparation_source_sha256']==sha(Path(__file__).with_name('prepare.py')) and
            helper['control_source_sha256']==sha(Path(__file__).with_name('Controls.Test.py')), 'API helper negative controls missing or stale')
    source=ROOT/'Tests/Production/Closeout/GeneralApi.Test.py'
    selected=[item for item in control['test_inventory'] if item['sha256']==sha(source)]
    require(control['status']=='passed' and control['failures']==control['errors']==control['skipped']==0 and
            len(selected)==1 and selected[0]['discovered_tests']==18, 'Specific API startup-exit rejection controls missing')
    for file in ('prepare.py','startup_contract.py','startup-policy-v1.json'):
        p=Path(__file__).with_name(file);evidence[str(p)]=sha(p)
    require(all(sha(p)==value for p,value in evidence.items()), 'API matrix changed during independent closure')
    result=dict(status='qualified-general-api-correction-v2',protocol=settings()['protocol'],policy=settings(),
        profiles=sorted(PROFILES),cohorts=observed,evidence_sha256=evidence,
        normal_stock_admission_qualified=False,phase6_complete=False,
        scope='Versioned GeneralApiTest correction, actual Windows/native assertions and its specific startup exit only')
    output.write_text(json.dumps(result,indent=2)+'\n');inspect(output)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--native',type=Path,action='append',required=True);p.add_argument('--windows',type=Path,action='append',required=True)
    for name in ('helpers','controls','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();result=qualify(a.native,a.windows,a.helpers,a.controls,a.output)
    print(json.dumps(dict(status=result['status'],profiles=result['profiles'],cohorts=list(result['cohorts']))))
