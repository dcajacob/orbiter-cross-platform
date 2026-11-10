#!/usr/bin/env python3
"""Probe three exact original failed package URLs; health alone never grants qualification."""
import datetime
import os
from pathlib import Path
import time
import urllib.error
import urllib.request
from contracts import ROOT,require,atomic_json
URLS=(
 'https://snapshot.ubuntu.com/ubuntu/20261109T212432Z/pool/main/x/xfonts-base/xfonts-base_1.0.5%2bnmu1build1_all.deb',
 'https://snapshot.ubuntu.com/ubuntu/20261109T212432Z/pool/main/m/mako/python3-mako_1.3.10-3ubuntu0.1_all.deb',
 'https://snapshot.ubuntu.com/ubuntu/20261109T212432Z/pool/main/p/pkgconf/pkg-config_2.5.1-4_amd64.deb')


if __name__=='__main__':
    require(os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('RUNNER_OS')=='Linux' and Path(os.environ['GITHUB_WORKSPACE']).resolve()==ROOT,'Only the existing standard hosted Linux workspace may probe package availability')
    output=ROOT/'out/rejection-package-transport-health.json';require(not output.exists(),'Fresh independent package transport observation required')
    report=dict(protocol='phase6-original-package-transport-availability-v1',status='checking-unqualified',snapshot='20261109T212432Z',requests=[],maximum_body_bytes_per_request=1,full_original488_package_install_and_signature_checks_still_required=True,qualification_granted=False,new_simulator_processes=0,phase6_complete=False,hands_on_ready=False)
    def save():atomic_json(output,report)
    save()
    for url in URLS:
        item=dict(url=url,started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),body_bytes_read=0,usable=False);report['requests'].append(item);start=time.monotonic_ns()
        try:
            request=urllib.request.Request(url,headers={'Range':'bytes=0-0','Accept-Encoding':'identity'})
            with urllib.request.urlopen(request,timeout=20) as source:
                item['actual_status']=source.status;item['final_url']=source.url;body=source.read(1);item['body_bytes_read']=len(body);item['first_byte_hex']=body.hex()
                item['usable']=source.status in (200,206) and source.url.startswith('https://snapshot.ubuntu.com/') and body==b'!'
        except urllib.error.HTTPError as error:item.update(actual_status=error.code,error_type=type(error).__name__)
        except Exception as error:item.update(error_type=type(error).__name__,error=str(error))
        finally:item['elapsed_ns']=time.monotonic_ns()-start;save()
    report['status']='available-for-unqualified-original-install-retry' if all(i['usable'] for i in report['requests']) else 'unavailable-unqualified-original-capture-not-started';save();print(__import__('json').dumps(report,indent=2),flush=True)
    require(all(i['usable'] for i in report['requests']),'Exact original package archive still unavailable; preserve results and hold the single-profile capture')
