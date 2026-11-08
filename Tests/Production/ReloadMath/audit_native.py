#!/usr/bin/env python3
"""Re-read completed observer-toggle runs; keep any collector-only failure preserved."""
import argparse
import csv
import hashlib
import json
from pathlib import Path


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def require(value,message):
    if not value:raise ValueError(message)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--capture',type=Path,required=True);p.add_argument('--baseline',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    require(not a.output.exists(),'Fresh independent observation audit required')
    recorded=json.loads((a.capture/'capture.json').read_text())
    additional=recorded.get('observer_kind')=='additional-passive-module'
    known=recorded['status']=='failed' and recorded.get('error')=='Actual enabled/disabled observation coverage differs'
    require(known or recorded['status']=='passed-native-observer-equivalence-diagnostic-only','Only completed observation captures or the preserved initial-row count failure can be audited')
    protected={str(a.capture/'capture.json'):sha(a.capture/'capture.json')};modes={}
    for mode in ('off','on'):
        folder=a.capture/('observer-'+mode);receipt=json.loads((folder/'process-result.json').read_text())
        require(receipt['actual_returncode']==0 and receipt['terminal'] and not receipt['cancelled'],'Actual successful simulator receipt required')
        invoke=json.loads((folder/'diagnostic-invocation.json').read_text())
        require(invoke['mode']==mode and invoke['sanitizer_environment']==dict(ASAN_OPTIONS='detect_leaks=1:fast_unwind_on_malloc=0',LSAN_OPTIONS='',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1'), 'Actual unsuppressed observer mode differs')
        require(json.loads((folder/'graphics-lifecycle.json').read_text())==dict(rendered_frames=960,successful_presents=960,context_deleted=True),'Complete real graphics closure required')
        require((folder/'stock-vessel-complete.txt').read_text().strip()=='960','Complete actual SDK boundary required')
        text=(folder/'console.log').read_text(errors='replace')
        require(not any(s in text for s in ('ERROR: AddressSanitizer','ERROR: LeakSanitizer','runtime error:','LuaCall (')),'Diagnostic finding in completed native run')
        for name,expected in recorded['baseline_sha256'].items():
            require(sha(a.baseline/name)==expected==sha(folder/name),'Actual simulation/frame/save differs from retained baseline')
            protected[str(folder/name)]=expected
        with (folder/'stock-vessel-state.csv').open() as stream:rows=list(csv.DictReader(stream))
        require({int(r['tick']) for r in rows}==set(range(961)),'Complete finalized all-vessel snapshots required')
        math_rows=(folder/'ground-math.csv').read_text().splitlines();baseline_rows=(a.baseline/'ground-math.csv').read_text().splitlines()
        require(len(math_rows)==(len(baseline_rows) if mode=='on' or additional else 1),'Actual observation coverage differs')
        if mode=='on' or additional:require(sha(folder/'ground-math.csv')==sha(a.baseline/'ground-math.csv'),'Enabled math observation differs')
        if additional:
            observer=recorded['extra_observer'];require(sha(Path(observer['path']))==observer['sha256'],'Actual extra observer binary changed')
            require((folder/'internal-state.csv').is_file()==(mode=='on'),'Actual extra observer toggle differs')
            mapped=folder/'observer-loaded-maps.txt'
            require((observer['path'] in mapped.read_text())==(mode=='on'),'Actual extra observer mapping differs')
            protected[str(mapped)]=sha(mapped);protected[observer['path']]=observer['sha256']
            if mode=='on':protected[str(folder/'internal-state.csv')]=sha(folder/'internal-state.csv')
        for name in ('process-result.json','diagnostic-invocation.json','graphics-lifecycle.json','console.log','ground-math.csv'):
            protected[str(folder/name)]=sha(folder/name)
        modes[mode]=dict(actual_pid=receipt['actual_collector_pid'],returncode=0,math_rows=len(math_rows)-1,baseline_bytes_identical=True)
    require(all(sha(Path(n))==v for n,v in protected.items()),'Capture changed during independent audit')
    result=dict(status='audited-native-observer-equivalence-diagnostic-only',modes=modes,evidence_sha256=protected,
                collector_initial_row_count_failure_preserved=known,physics_formulas_unchanged=True,
                software_gate_closed=False,phase6_complete=False)
    a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(status=result['status'],modes=modes)))


if __name__=='__main__':main()
