"""Independent audit inputs retain source jobs and allow only the passive observer override."""
import copy
import sys
import unittest
from contracts import ROOT
sys.path.insert(0,str(ROOT/'Tests/Production/CurrentWindows/Hosted'))
import inspect_retained_inputs as inputs
import restore_hosted_ssim as scalar


class HostedIndependentInputsTests(unittest.TestCase):
    def test_only_the_passive_observer_role_differs_from_the_immutable_runtime(self):
        sdk={'Orbiter.exe':'a'*64,'Modules/Plugin/OGLClient.dll':'b'*64,'Modules/Plugin/ProductionCockpitDriver.dll':'c'*64}
        original=dict(sdk);actual=inputs.executed_runtime(sdk,'d'*64)
        self.assertEqual(sdk,original);self.assertEqual(actual['Orbiter.exe'],sdk['Orbiter.exe'])
        self.assertEqual(actual['Modules/Plugin/OGLClient.dll'],sdk['Modules/Plugin/OGLClient.dll'])
        self.assertEqual(actual['Modules/Plugin/ProductionCockpitDriver.dll'],'d'*64)
        for value in ('','d'*63,'z'*64):
            with self.assertRaises(ValueError):inputs.executed_runtime(sdk,value)
        without_observer={name:value for name,value in sdk.items() if name!='Modules/Plugin/ProductionCockpitDriver.dll'}
        self.assertEqual(inputs.executed_runtime(without_observer,'d'*64),actual)
        self.assertEqual(without_observer,{'Orbiter.exe':'a'*64,'Modules/Plugin/OGLClient.dll':'b'*64})
        with self.assertRaises(ValueError):inputs.executed_runtime({'Orbiter.exe':'a'*64},'d'*64)

    def test_scalar_restoration_requires_the_exact_complete_equivalence_job(self):
        record=dict(repository=dict(owner='dcajacob',repo='orbiter-cross-platform'),
            run=dict(id=scalar.RUN,head_sha=scalar.SOURCE,head_branch='qualification/hosted-ssim-controls',
                     path='.github/workflows/phase6-hosted-ssim-controls.yml',run_attempt=1,status='completed',conclusion='success'),
            artifact=dict(id=13639682979,name='hosted-bit-identical-scalar-ssim-controls',expired=False,size_in_bytes=3935729,
                          digest='sha256:'+scalar.DIGEST,workflow_run=dict(id=scalar.RUN,head_sha=scalar.SOURCE)),
            jobs=[dict(id=128905495973,run_id=scalar.RUN,head_sha=scalar.SOURCE,status='completed',conclusion='success',labels=['ubuntu-24.04'],
                       steps=[dict(name=name,status='completed',conclusion='success') for name in
                         ('Prove exact original scalar arithmetic on five controls and two real nonidentical full-frame pairs','Run actions/upload-artifact@v7')])])
        scalar.validate_api(record)
        for change in (lambda r:r['run'].update(head_sha='f'*40),lambda r:r['artifact'].update(digest='sha256:'+'f'*64),
                       lambda r:r['jobs'][0].update(conclusion='failure'),lambda r:r['jobs'][0]['steps'][0].update(conclusion='skipped')):
            changed=copy.deepcopy(record);change(changed)
            with self.assertRaises(ValueError):scalar.validate_api(changed)


if __name__=='__main__':unittest.main()
