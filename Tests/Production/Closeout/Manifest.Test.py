#!/usr/bin/env python3
"""Incomplete evidence or a shortened checklist cannot assert Phase 6 completion."""
import copy
from pathlib import Path
import tempfile
import unittest
from contracts import ROOT,atomic_json,load
from manifest import validate


class ManifestTests(unittest.TestCase):
    def test_initial_manifest_is_explicitly_incomplete(self):
        result=validate(ROOT/'Docs/Production/Phase6Closeout.json',verify_files=False)
        self.assertFalse(result['software_complete'])
        self.assertFalse(result['phase6_complete'])
        self.assertIn('controller',result['open_gates'])

    def test_shortened_coverage_and_unearned_completion_rejected(self):
        source=load(ROOT/'Docs/Production/Phase6Closeout.json')
        mutations=[lambda v:v['gates'].pop('controller'),lambda v:v.update(phase6_complete=True),
            lambda v:v.update(software_complete=True),
            lambda v:v['gates']['remaining-stock']['expected'].update(runs_per_cohort=607),
            lambda v:v['gates']['normal-admission']['expected']['entry_points'].pop(),
            lambda v:v['gates']['numerical-reload'].update(result='passed'),
            lambda v:v['gates']['remaining-stock'].update(result='audited-incomplete')]
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'manifest.json'
            for mutate in mutations:
                value=copy.deepcopy(source);mutate(value);atomic_json(path,value)
                with self.subTest(mutate=mutate),self.assertRaises(ValueError):validate(path,verify_files=False)


if __name__=='__main__':unittest.main()
