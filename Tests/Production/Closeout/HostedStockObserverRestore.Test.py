"""A passive observer restore must retain its complete original SDK and assertion-only variant."""
import copy
import hashlib
import sys
import unittest
from contracts import ROOT
sys.path.insert(0,str(ROOT/'Tests/Production/CurrentWindows/Hosted'))
import restore_observer as reader


class HostedStockObserverRestoreTests(unittest.TestCase):
    def record(self,configuration='Debug'):
        ident,size,digest,jobid=reader.PINS[configuration]
        return dict(repository=dict(owner='dcajacob',repo='orbiter-cross-platform'),
            run=dict(id=reader.RUN,head_sha=reader.PRODUCER,head_branch='qualification/current-stock-preparation',
                     path='.github/workflows/phase6-current-stock-preparation.yml',run_attempt=1,status='completed',conclusion='success'),
            artifact=dict(id=ident,name='current-stock-preparation-'+configuration,expired=False,size_in_bytes=size,digest='sha256:'+digest,
                          workflow_run=dict(id=reader.RUN,head_sha=reader.PRODUCER)),
            jobs=[dict(id=jobid,name='Prepare exact current SDK and passive stock observer '+configuration,run_id=reader.RUN,
                       head_sha=reader.PRODUCER,status='completed',conclusion='success',labels=['windows-2025'],
                       steps=[dict(name=name,status='completed',conclusion='success') for name in reader.STEPS]),
                  dict(id=128881042657,run_id=reader.RUN,head_sha=reader.PRODUCER,status='completed',conclusion='success')])

    def test_actual_preparation_sdk_verification_and_source_controls_are_bound(self):
        for configuration in reader.PINS:self.assertEqual(reader.validate_api(self.record(configuration),configuration)['id'],reader.PINS[configuration][3])
        for change in (lambda r:r['run'].update(head_sha='a'*40),lambda r:r['run'].update(run_attempt=2),
                       lambda r:r['artifact'].update(expired=True),lambda r:r['artifact'].update(size_in_bytes=1),
                       lambda r:r['artifact'].update(digest='sha256:'+'f'*64),lambda r:r['jobs'][0].update(labels=['windows-2022']),
                       lambda r:r['jobs'][0]['steps'][0].update(conclusion='skipped'),lambda r:r['jobs'][1].update(conclusion='failure'),
                       lambda r:r['jobs'].append(copy.deepcopy(r['jobs'][0]))):
            record=self.record();change(record)
            with self.assertRaises(ValueError):reader.validate_api(record,'Debug')

    def test_every_passive_observation_and_delay_byte_survives_restoration(self):
        original=b'observe();\r\ndelay(120);\r\nrequire(frames==60,"Incomplete original stock observation");\r\n'
        compiled=original.replace(b'\r\n',b'\n').replace(b'frames==60,"Incomplete original stock observation"',b'frames==960,"Incomplete repaired stock observation"')
        variant=dict(compiled_sha256=hashlib.sha256(compiled).hexdigest(),only_change='Validate 960 finalized ticks instead of 60; all observation calls and delays unchanged')
        reader.verify_variant(original,compiled,variant)
        for changed in (compiled.replace(b'observe();',b''),compiled.replace(b'120',b'0'),compiled.replace(b'960',b'60')):
            updated=variant|dict(compiled_sha256=hashlib.sha256(changed).hexdigest())
            with self.assertRaises(ValueError):reader.verify_variant(original,changed,updated)
        with self.assertRaises(ValueError):reader.verify_variant(original+original,compiled,variant)
        with self.assertRaises(ValueError):reader.verify_variant(original,compiled,variant|dict(compiled_sha256='f'*64))


if __name__=='__main__':unittest.main()
