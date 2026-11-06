#!/usr/bin/env python3
"""Root/role controls are fixtures; no Windows execution is claimed by these tests."""
import copy
import unittest
from LocalVM.runtime_descriptor_v2 import ORIGINAL, PROTOCOL, validate


def descriptor():
    roots = {k: 'C:/Phase6/' + k for k in ('source','output','build','preserved','data','planets','mesa')}
    roots['share'] = 'Z:/Phase6'
    return dict(transport_protocol=PROTOCOL, roots=roots, **{k:v for k,v in roots.items() if k!='share'},
        roles={role:dict(commit=ORIGINAL if role in ('application','sdk') else 'a'*40, manifest_sha256='b'*64, manifest_path=('C:/Phase6/preserved/test-runtime.json' if role in ('application','sdk') else 'C:/Phase6/build/build.json' if role=='observer' else 'Z:/Phase6/runners.json'))
               for role in ('application','sdk','observer','runner')}, source_commit='a'*40,
        cohort='original-windows', reference_variant='remaining-stock-repaired-sources-v4',
        worker_script='Z:/Phase6/scripts/worker.py', worker_sha256='c'*64,
        bootstrap_script='Z:/Phase6/scripts/bootstrap.py', bootstrap_sha256='d'*64,
        export='Z:/Phase6/export', minimum_free_bytes=8*1024**3)


class TransportTests(unittest.TestCase):
    def test_explicit_working_share_and_other_local_drive(self):
        value = descriptor()
        self.assertEqual(str(validate(value)['share']), 'Z:\\Phase6')
        value['roots']['share'] = 'W:/OtherShare'
        value['roles']['runner']['manifest_path']='W:/OtherShare/runners.json'
        value.update(worker_script='W:/OtherShare/scripts/worker.py',
                     bootstrap_script='W:/OtherShare/scripts/bootstrap.py', export='W:/OtherShare/export')
        self.assertEqual(validate(value)['share'].drive, 'W:')

    def test_missing_roots_role_substitution_unc_and_overlap_rejected(self):
        mutations = [lambda v:v['roots'].pop('share'), lambda v:v['roles'].pop('observer'),
            lambda v:v['roles']['application'].update(commit='a'*40),
            lambda v:v['roles']['observer'].update(commit='c'*40),
            lambda v:v.update(output='C:/wrong'), lambda v:v.update(minimum_free_bytes=1),
            lambda v:v.update(worker_script='O:/old/worker.py'),
            lambda v:v.update(export='Y:/Dropbox/export'),
            lambda v:v['roots'].update(share=r'\\server\share'),
            lambda v:(v['roots'].update(output='C:/Phase6/source/out'),v.update(output='C:/Phase6/source/out')),
            lambda v:(v['roots'].update(output='C:/Phase6'),v.update(output='C:/Phase6')),
            lambda v:v.update(worker_script='Z:/Phase6/../elsewhere/worker.py')]
        for mutate in mutations:
            value = descriptor(); mutate(value)
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate(value)

    def test_diagnostic_capacity_is_scoped_and_cannot_shorten_full_scope(self):
        value=descriptor();value['capture_scope']=dict(kind='diagnostic',cases=['remaining_stock_003'])
        value['minimum_free_bytes']=1024**3;validate(value)
        value['capture_scope']['kind']='full38'
        with self.assertRaises(ValueError):validate(value)
        value['capture_scope']=dict(kind='diagnostic',cases=['unknown'])
        with self.assertRaises(ValueError):validate(value)

    def test_current_roles_require_matching_sdk(self):
        value = descriptor();value['cohort']='current-windows'
        value['roles']['application']['commit']='c'*40
        with self.assertRaisesRegex(ValueError, 'SDK must match'):
            validate(value)
        value['roles']['sdk']['commit']='c'*40
        validate(value)


if __name__ == '__main__':
    unittest.main()
