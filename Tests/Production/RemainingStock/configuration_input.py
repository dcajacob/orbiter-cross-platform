"""Preserve the actual startup file separately from Orbiter's normal config rewrite."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

PROTOCOL='stock-staged-configuration-v1'
SNAPSHOT='staged-Orbiter.cfg'


def require(value,message):
    if not value:raise ValueError(message)


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def stage(directory):
    body=(directory/'Orbiter.cfg').read_bytes()
    with (directory/SNAPSHOT).open('xb') as target:target.write(body)
    return dict(protocol=PROTOCOL,runtime_path='Orbiter.cfg',snapshot_path=SNAPSHOT,sha256=sha(directory/SNAPSHOT))


def inspect(directory,expected):
    invocation=json.loads((directory/'invocation.json').read_text())
    record=invocation['configuration_input']
    require(set(record)=={'protocol','runtime_path','snapshot_path','sha256'} and
            record['protocol']==PROTOCOL and record['runtime_path']=='Orbiter.cfg' and record['snapshot_path']==SNAPSHOT,
            'Actual startup configuration descriptor differs')
    body=(directory/SNAPSHOT).read_bytes()
    require(hashlib.sha256(body).hexdigest()==record['sha256'],'Actual startup configuration snapshot/hash differs')
    expected=expected.encode('ascii')
    require(b'\r' not in expected and body in (expected,expected.replace(b'\n',b'\r\n')),
            'Actual startup configuration differs from the complete frozen fixture')
    return dict(protocol=PROTOCOL,runtime_path='Orbiter.cfg',snapshot_path=SNAPSHOT,sha256=record['sha256'],
                sha256_lf=hashlib.sha256(body.replace(b'\r\n',b'\n')).hexdigest(),bytes=len(body))


def expected(root,producer,kind):
    require(re.fullmatch('[0-9a-f]{40}',producer) and kind in ('repaired-windows','native'),'Immutable configuration source and known fixture kind required')
    path='Tests/Production/'+('Fixtures/Orbiter.cfg' if kind=='repaired-windows' else 'NativeScene/Orbiter.cfg')
    text=subprocess.check_output(['git','-C',str(root),'show',producer+':'+path]).decode('ascii').replace('\r\n','\n')
    if kind=='repaired-windows':
        text=text.replace('ProductionReferenceDriver','ProductionBehaviorDriver')
        text+='\nVesselCollision = FALSE\nBaseCollision = TRUE\nUnlimitedFuel = FALSE\n'
    for line in ('PropStages = 1\n','PropStage0 = 1 1 1\n','PropSubsampling = 1\n'):
        require(text.count(line)==1,'Original fixture propagator override differs');text=text.replace(line,'')
    if kind=='repaired-windows':text=text.replace('  ProductionBehaviorDriver','  ProductionCockpitDriver\n  OGLClient')
    text+='\nFPS = 0\nMenubarMode = 1\nInfobarMode = 1\nInstrumentUpdateInterval = 0.25\n'
    if kind=='native':text+='VesselCollision = FALSE\nBaseCollision = TRUE\nUnlimitedFuel = FALSE\n'
    return text
