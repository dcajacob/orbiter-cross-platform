#!/usr/bin/env python3
"""xdg-open BROWSER fixture: render its actual URL in an isolated real browser."""
import json
import os
from pathlib import Path
import subprocess
import sys

out = Path(os.environ['ORBITER_HELP_EVIDENCE'])
out.mkdir(parents=True, exist_ok=True)
url = sys.argv[1]
with (out/('browser-'+str(os.getpid())+'.log')).open('w') as log:
    result = subprocess.run([os.environ.get('ORBITER_HELP_NODE', 'node'),
        str(Path(__file__).with_name('browser.cjs')), '--request', url, str(out/str(os.getpid()))],
        stdout=log, stderr=subprocess.STDOUT, timeout=60)
if result.returncode == 0:
    reports = list((out/str(os.getpid())).glob('*.json'))
    assert len(reports) == 1, 'Browser must record its actual destination'
    report = json.loads(reports[0].read_text())
    with (out/'requests.jsonl').open('a') as stream:
        stream.write(json.dumps({'url': report['url'], 'launch_argument': url, 'pid': os.getpid()})+'\n')
sys.exit(result.returncode)
