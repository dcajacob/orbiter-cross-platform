import copy,csv,hashlib,json,tempfile
from pathlib import Path
from unittest import TestCase
import audit_contact_component_trial as audit
from contracts import atomic_json
import hosted_contact_component_trial as producer


class ContactIndependent(TestCase):
    def table(self,path):
        rows=[]
        for tick in range(61):
            row={n:'0' for n in audit.HEADER};row.update(tick=str(tick),frame=str(tick),seconds=str(tick*.25),mjd='57462.5',object='Ship',**{'class':'ShuttlePB'},dock='',focus='Ship',attached='');rows.append(row)
        self.write(path,rows);return rows

    def write(self,path,rows):
        with path.open('w') as f:
            writer=csv.DictWriter(f,fieldnames=audit.HEADER);writer.writeheader();writer.writerows(rows)

    def test_complete_reader_rejects_nonfinite_partial_duplicate_rosters_and_changed_clock(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'flight-state.csv';rows=self.table(path);self.assertEqual(audit.flight(path,{'Ship':'ShuttlePB'})['ticks'],61)
            for field,value in [('rx','nan'),('seconds','0.2'),('object','Substituted')]:
                changed=copy.deepcopy(rows);changed[1][field]=value;self.write(path,changed)
                with self.assertRaises(ValueError):audit.flight(path,{'Ship':'ShuttlePB'})
            self.write(path,rows[:-1])
            with self.assertRaises(ValueError):audit.flight(path,{'Ship':'ShuttlePB'})
            self.write(path,rows+[rows[1]])
            with self.assertRaises(ValueError):audit.flight(path,{'Ship':'ShuttlePB'})

    def test_completed_failed_trial_is_auditable_but_foreign_source_runner_or_digest_is_not(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'raw.zip';path.write_bytes(b'original retained trial')
            api=dict(run=dict(id=audit.RUN,head_sha=audit.SOURCE,head_branch='qualification/assembly-contact-component-v3',run_attempt=1,status='completed',conclusion='failure',repository=dict(full_name='dcajacob/orbiter-cross-platform',private=False)),jobs=[dict(name='trial',head_sha=audit.SOURCE,run_id=audit.RUN,status='completed',conclusion='failure',labels=['ubuntu-24.04'])],artifact=dict(name='assembly-contact-component-trial-raw',expired=False,workflow_run=dict(id=audit.RUN,head_sha=audit.SOURCE),size_in_bytes=path.stat().st_size,digest='sha256:'+hashlib.sha256(path.read_bytes()).hexdigest()))
            audit.api_binding(api,path)
            for field,value in [('head_sha','0'*40),('status','in_progress')]:
                changed=copy.deepcopy(api);changed['run'][field]=value
                with self.assertRaises(ValueError):audit.api_binding(changed,path)
            changed=copy.deepcopy(api);changed['jobs'][0]['labels']=['self-hosted']
            with self.assertRaises(ValueError):audit.api_binding(changed,path)
            changed=copy.deepcopy(api);changed['artifact']['digest']='sha256:'+'0'*64
            with self.assertRaises(ValueError):audit.api_binding(changed,path)

    def test_fresh_original_reader_roundtrip_uses_real_json_and_original_configuration(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d);folder=base/'fixture';folder.mkdir();self.table(folder/'flight-state.csv');(folder/'console.log').write_text('')
            atomic_json(folder/'graphics-lifecycle.json',dict(rendered_frames=60,successful_presents=60,context_deleted=True))
            atomic_json(folder/'process-receipt.json',dict(terminal=True,cancelled=False,actual_collector_pid=12345,actual_returncode=0))
            name='2024 Edition/Space Shuttle ascent autopilot.scn';producer.original_case_control('stage',name,folder)
            result=audit.original_inspection(folder,dict(ships={'Ship':'ShuttlePB'},dependency_problems={},startup_configuration_policy='original-propagators-v1'),name,0,base/'inspection.json')
            self.assertEqual(result['status'],'passed');self.assertEqual(json.loads((base/'inspection.json').read_text()),result)
