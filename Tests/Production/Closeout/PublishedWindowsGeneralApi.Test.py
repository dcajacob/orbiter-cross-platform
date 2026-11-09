"""Reject changed publication provenance and evidence path substitutions."""
import copy
import json
from pathlib import Path
import sys
import unittest
from contracts import ROOT
sys.path.insert(0,str(ROOT/'Tests/Production/GeneralApiCorrection/Hosted'))
import inspect_published_general_api as published


class PublishedWindowsGeneralApiTests(unittest.TestCase):
    def test_closed_actual_windows_audit_API_cannot_be_substituted(self):
        record=json.loads((Path(__file__).parent/'Windows-api-published-audit.fixture.json').read_text())
        self.assertEqual(published.validate_api(record,'Debug')['name'],'Reaudit existing Windows API Debug')
        for mutate in (lambda r:r['run'].update(conclusion='failure'),
                       lambda r:r['run'].update(head_sha='f'*40),
                       lambda r:r['run'].update(run_attempt=2),
                       lambda r:r['jobs'].pop(),
                       lambda r:r['jobs'][-1].update(conclusion='failure'),
                       lambda r:r['jobs'][-1].update(labels=['self-hosted','windows-2025']),
                       lambda r:r['artifact'].update(expired=True),
                       lambda r:r['artifact'].update(size_in_bytes=16*1024**2),
                       lambda r:r['artifact'].update(digest='wrong'),
                       lambda r:r['artifact']['workflow_run'].update(head_sha='f'*40)):
            changed=copy.deepcopy(record);mutate(changed)
            with self.assertRaises(ValueError):published.validate_api(changed,'Debug')

    def test_original_windows_evidence_namespace_is_explicit_and_bounded(self):
        tree=Path('/tmp/disposable-published');payload=Path('/tmp/disposable-sdk');runtime=Path('/tmp/disposable-runtime');outer=Path('/tmp/disposable-outer.zip')
        prefix='D:/a/orbiter-cross-platform/orbiter-cross-platform/out/'
        self.assertEqual(published.evidence_path(prefix+'current-sdk-source/producer.zip',tree,payload,runtime,outer),outer)
        self.assertEqual(published.evidence_path(prefix+'current-windows-sdk/source-artifact/runtime.zip',tree,payload,runtime,outer),payload/'runtime.zip')
        self.assertEqual(published.evidence_path(prefix+'current-windows-sdk/runtime/test-runtime.json',tree,payload,runtime,outer),runtime/'test-runtime.json')
        self.assertEqual(published.evidence_path(prefix+'current-api-exports/Debug-GeneralApi/original.log',tree,payload,runtime,outer),tree/'current-api-exports/Debug-GeneralApi/original.log')
        for value in ('C:/outside/source.json','//server/share/source.json',prefix+'../outside.json','relative.json'):
            with self.assertRaises(ValueError):published.evidence_path(value,tree,payload,runtime,outer)
