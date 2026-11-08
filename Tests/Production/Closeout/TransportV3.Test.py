"""Current-runtime roles can have an independently versioned test observer."""
import copy
import unittest
from LocalVM.runtime_descriptor_v3 import validate,PROTOCOL


def descriptor():
    roots={n:'C:/Api/'+n for n in ('source','output','build','preserved','data','planets','mesa')};roots['share']='Z:/Api'
    roles={r:dict(commit=('a'*40 if r in ('application','sdk') else 'b'*40),manifest_sha256='c'*64,
        manifest_path=('C:/Api/preserved/test-runtime.json' if r in ('application','sdk') else
                       'C:/Api/build/observer-build.json' if r=='observer' else 'Z:/Api/runners.json'))
        for r in ('application','sdk','observer','runner')}
    return dict(transport_protocol=PROTOCOL,roots=roots,roles=roles,source_role='application',source_commit='a'*40,
        **{n:v for n,v in roots.items() if n!='share'},cohort='current-windows',minimum_free_bytes=1024**3,
        worker_script='Z:/Api/scripts/worker.py',worker_sha256='d'*64,
        bootstrap_script='Z:/Api/scripts/bootstrap.py',bootstrap_sha256='e'*64,export='Z:/Api/export',
        capture_scope=dict(kind='diagnostic',gate='general-api',cases=['Scenarios/Tests/GeneralApiTest.scn']))


class TransportV3Tests(unittest.TestCase):
    def test_independent_observer_and_source_owner(self):
        value=descriptor();validate(value)
        self.assertNotEqual(value['roles']['observer']['commit'],value['source_commit'])
        for mutate in (lambda v:v['roles']['sdk'].update(commit='f'*40),
                       lambda v:v.update(source_role='observer'),
                       lambda v:v.update(source_commit='f'*40),
                       lambda v:v.update(transport_protocol='unknown'),
                       lambda v:v['roles']['observer'].update(manifest_path='C:/Elsewhere/build.json')):
            changed=copy.deepcopy(value);mutate(changed)
            with self.assertRaises(ValueError):validate(changed)

    def test_unscoped_redirected_and_unsafe_requests_rejected(self):
        for mutate in (lambda v:v['capture_scope'].update(cases=[]),
                       lambda v:v['capture_scope'].update(cases=['../Scenarios/Test.scn']),
                       lambda v:v['roots'].update(share=r'\\server\share'),
                       lambda v:v.update(export='Y:/Dropbox/raw'),
                       lambda v:v.update(minimum_free_bytes=1)):
            changed=descriptor();mutate(changed)
            with self.assertRaises(ValueError):validate(changed)
