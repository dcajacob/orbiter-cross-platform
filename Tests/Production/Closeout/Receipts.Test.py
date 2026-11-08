#!/usr/bin/env python3
"""Synthetic v2 receipt controls; these fixtures qualify no actual Windows run."""
import base64
import copy
import json
from pathlib import Path
import tempfile
import unittest
from contracts import atomic_json,sha
from receipts import inspect_launch,inspect_selected_processes,inspect_full38_processes


def fixture(root):
    scripts=root/'scripts';scripts.mkdir()
    pins={}
    for name in ('worker.py','private_desktop_bootstrap_v1.py','system_user_launcher_v1.py'):
        (scripts/name).write_text('# fixture '+name+'\n');pins[name]=sha(scripts/name)
    roots={name:'C:/Phase6/'+name for name in ('source','output','build','preserved','data','planets','mesa')}
    roots['share']='Z:/Phase6'
    roles={name:dict(commit=('f725194209634f7fd5d1d44d426cfa9b5e303e37' if name in ('application','sdk') else 'a'*40),
        manifest_sha256='f'*64,manifest_path=('C:/Phase6/preserved/test-runtime.json' if name in ('application','sdk') else
                                          'C:/Phase6/build/build.json' if name=='observer' else 'Z:/Phase6/runners.json'))
        for name in ('application','sdk','observer','runner')}
    config=dict(transport_protocol='phase6-local-windows-vm-v2',roots=roots,roles=roles,
        **{k:v for k,v in roots.items() if k!='share'}, source_commit='a'*40,cohort='original-windows',
        reference_variant='remaining-stock-repaired-sources-v4',worker_script='Z:/Phase6/scripts/worker.py',
        worker_sha256=pins['worker.py'],bootstrap_script='Z:/Phase6/scripts/private_desktop_bootstrap_v1.py',
        bootstrap_sha256=pins['private_desktop_bootstrap_v1.py'],export='Z:/Phase6/export',minimum_free_bytes=8*1024**3,
        request_path='Z:/Phase6/request.json',active_session=2,name='test',desktop='PrivateTest',
        configuration='Debug',math_profile='automatic',share_witness=dict(path='witness',sha256='b'*64))
    atomic_json(root/'request.json',config);binding=sha(root/'request.json')
    context=dict(session=2,window_station='WinSta0',desktop='Default')
    system=dict(status='launched-normal-user-bootstrap',active_session=2,actual_bootstrap_pid=101,
                no_desktop_switch=True,request_sha256=binding,launcher_sha256=pins['system_user_launcher_v1.py'])
    started=dict(status='actual-private-worker-started',actual_worker_pid=102,context=context,
                 desktop=config['desktop'],bootstrap_sha256=config['bootstrap_sha256'],
                 no_desktop_switch=True,request_sha256=binding)
    finished=dict(started,status='actual-private-worker-finished',actual_worker_exitcode=0,private_desktop_closed=True)
    worker=dict(context=dict(context,desktop=config['desktop']),source=config['source_commit'],roles=roles,
        transport_protocol=config['transport_protocol'],script_sha256=pins['worker.py'],configuration='Debug',math_profile='automatic',
        cloud_builds_used=False,native_admission_qualified=False,phase6_complete=False,request_sha256=binding,
        root_preflight=dict(status='passed-actual-Windows-root-and-capacity-preflight',protocol=config['transport_protocol'],
            roots={n:str(__import__('pathlib').PureWindowsPath(v)) for n,v in roots.items()},free_bytes=9*1024**3,
            minimum_free_bytes=8*1024**3,share_witness_sha256='b'*64))
    records={'system-launch':system,'bootstrap-started':started,'bootstrap-result':finished,'worker-result':worker,
        'guest-job':dict(pid=100,guest_script='Z:/Phase6/scripts/system_user_launcher_v1.py',
            script_sha256=pins['system_user_launcher_v1.py'],domain='win11',
            domain_uuid='3b599191-901c-4578-9706-ba2763d030b7',
            argv=['-B','Z:\\Phase6\\scripts\\system_user_launcher_v1.py','Z:\\Phase6\\request.json']),
        'guest-result':dict(exited=True,exitcode=0,**{'out-data':base64.b64encode(json.dumps(system).encode()).decode()}),
        'vm':dict(hypervisor='libvirt/kvm',domain_name='win11',guest_os_id='mswindows',guest_arch='x86_64',
                  domain_uuid='3b599191-901c-4578-9706-ba2763d030b7')}
    for name,value in records.items():atomic_json(root/(name+'.json'),value)
    return pins,records


class ReceiptTests(unittest.TestCase):
    def test_selected_receipts_require_every_phase_repeat_and_never_qualify_full38(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);fixture(root)
            config=json.loads((root/'request.json').read_text())
            config['capture_scope']=dict(kind='diagnostic',cases=['remaining_stock_003'])
            worker=dict(status='completed-local-Windows-selected-stock-and-exact-save-reload-diagnostic-only',
                diagnostic_only=True,cases_requested=['remaining_stock_003'],actual_processes=4,successful_presents=3840,
                actual_process_receipts=[])
            for phase,folder in [('stock','remaining-stock-repaired'),('reload','remaining-stock-persistence')]:
                for repeat in [1,2]:
                    path=root/folder/('remaining_stock_003-'+str(repeat));path.mkdir(parents=True)
                    timing=dict(actual_pid=200+len(worker['actual_process_receipts']),actual_returncode=0,
                        timed_out=False,timeout_seconds=900,elapsed_wall_ns=1000)
                    atomic_json(path/'process-timing.json',timing)
                    atomic_json(path/'graphics-lifecycle.json',dict(rendered_frames=960,successful_presents=960,context_deleted=True))
                    worker['actual_process_receipts'].append(dict(phase=phase,case='remaining_stock_003',repeat=repeat,
                        folder=config['output']+'/'+folder+'/'+path.name,timing=timing))
            self.assertEqual(inspect_selected_processes(root,config,worker)['actual_processes'],4)
            with self.assertRaises(ValueError):inspect_full38_processes(root,config,worker)
            for items in (worker['actual_process_receipts'][:-1],worker['actual_process_receipts']+[worker['actual_process_receipts'][0]]):
                changed=dict(worker,actual_process_receipts=items)
                with self.assertRaises(ValueError):inspect_selected_processes(root,config,changed)

    def test_launch_chain_and_each_missing_terminal_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);pins,records=fixture(root)
            inspect_launch(root,pins)
            mutations=[('bootstrap-result',lambda r:r.update(actual_worker_exitcode=1)),
                ('bootstrap-result',lambda r:r.update(private_desktop_closed=False)),
                ('bootstrap-started',lambda r:r.update(actual_worker_pid=True)),
                ('bootstrap-started',lambda r:r.update(no_desktop_switch=False)),
                ('worker-result',lambda r:r.update(phase6_complete=True)),
                ('worker-result',lambda r:r['roles']['application'].update(commit='c'*40)),
                ('worker-result',lambda r:r['root_preflight'].update(free_bytes=1)),
                ('worker-result',lambda r:r['context'].update(session=0)),
                ('guest-job',lambda r:r.update(guest_script='O:/old/launcher.py')),
                ('guest-job',lambda r:r.update(argv=['-B','Z:/Phase6/scripts/system_user_launcher_v1.py','Z:/Other/request.json'])),
                ('guest-job',lambda r:r.update(domain_uuid='4b599191-901c-4578-9706-ba2763d030b7')),
                ('guest-result',lambda r:r.update(exited=False)),
                ('guest-result',lambda r:r.update(exitcode=1)),
                ('vm',lambda r:r.update(guest_os_id='linux'))]
            for name,mutate in mutations:
                changed=copy.deepcopy(records[name]);mutate(changed);atomic_json(root/(name+'.json'),changed)
                with self.subTest(name=name,changed=changed),self.assertRaises(ValueError):inspect_launch(root,pins)
                atomic_json(root/(name+'.json'),records[name])
            slash_job=copy.deepcopy(records['guest-job'])
            slash_job['argv']=[value.replace('\\','/') for value in slash_job['argv']]
            atomic_json(root/'guest-job.json',slash_job)
            inspect_launch(root,pins)
            (root/'scripts/worker.py').write_text('# changed\n')
            with self.assertRaisesRegex(ValueError,'runner bytes'):inspect_launch(root,pins)


if __name__=='__main__':unittest.main()
