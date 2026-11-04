#!/usr/bin/env python3
"""Check real application/companion mappings and reject mismatched plugin inputs."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]


def require(value,message):
    if not value:raise ValueError(message)


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('capture','output'):p.add_argument('--'+name,type=lambda v:Path(v).resolve(),required=True)
    a=p.parse_args();require(not a.output.exists(),'Fresh decoration selection controls required')
    result=json.loads((a.capture/'wayland-input.json').read_text());decoration=result['application_decoration']
    plugin=Path(decoration['plugin']);record=Path(decoration['build_record'])
    paths=(plugin,record,a.capture/'wayland-input.json',a.capture/'loaded-maps.txt',a.capture/'focus-sink-loaded-maps.txt',HERE/'run.py')
    protected={str(path):sha(path) for path in paths}
    require(result['status']=='passed' and decoration['plugin_sha256']==sha(plugin) and decoration['build_record_sha256']==sha(record) and
            result['focus_sink_mappings_sha256']==sha(a.capture/'focus-sink-loaded-maps.txt'),
            'Actual successful decoration/mapping evidence differs')
    app=(a.capture/'loaded-maps.txt').read_text();sink=(a.capture/'focus-sink-loaded-maps.txt').read_text()
    require(str(plugin) in app and str(plugin) not in sink and 'libasan.so' not in sink,
            'Actual application/normal companion plugin isolation differs')
    require(all(sha(ROOT/name)==value for name,value in result['source_sha256'].items()),'Actual input source changed')
    controls=[]
    with tempfile.TemporaryDirectory(prefix='phase6-decoration-selection-controls-') as temporary:
        root=Path(temporary)
        for name,missing in (('changed_plugin_hash',False),('missing_build_record',True)):
            target=root/name
            command=[sys.executable,'-B',str(HERE/'run.py')]
            # These paths must never be opened: selection rejects before the
            # compositor, focus client, or simulator can launch.
            for option in ('dependencies','executable','assets','data','modules','planets','frozen'):
                command+=['--'+option,str(root/'must-not-be-opened')]
            command+=['--output',str(target),'--decoration-plugin',str(plugin)]
            if missing:reason='must be supplied together'
            else:
                damaged=copy.deepcopy(json.loads(record.read_text()));damaged['plugin_sha256']='0'*64
                fixture=root/'changed-build.json';fixture.write_text(json.dumps(damaged)+'\n')
                command+=['--decoration-build-record',str(fixture)];reason='ownership build differs'
            process=subprocess.run(command,capture_output=True,text=True)
            require(process.returncode!=0 and reason in process.stderr and not target.exists(),
                    'Invalid decoration selection was not rejected before runtime initialization: '+name)
            controls.append(dict(control=name,reason=reason,returncode=process.returncode,rejected_before_runtime=True))
    require(all(sha(Path(name))==value for name,value in protected.items()),'Owning actual capture/plugin/source bytes changed')
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(dict(status='passed-actual-decoration-selection-controls',
        actual_application_and_companion_mappings_checked=True,controls=controls,protected_files_sha256=protected,
        test_sha256=sha(Path(__file__)),owning_bytes_unchanged=True,phase6_complete=False),indent=2)+'\n')
    print('Actual application/companion mappings verified; two invalid selections rejected before runtime initialization')


if __name__=='__main__':main()
