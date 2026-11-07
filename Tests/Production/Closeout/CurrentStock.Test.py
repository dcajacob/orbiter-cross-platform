"""Current-SDK adapter keeps diagnostic scope and its capacity contract explicit."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest
import sys

file=Path(__file__).resolve().parents[1]/'CurrentWindows/stock.py'
spec=importlib.util.spec_from_file_location('current_stock_controls',file)
stock=importlib.util.module_from_spec(spec);spec.loader.exec_module(stock)
sys.path.insert(0,str(file.parent))
import audit_stock


class CurrentStockSelectionTests(unittest.TestCase):
    def test_cross_volume_receipt_cannot_hide_totals_or_escape_output(self):
        protocol='phase6-guarded-local-staging-v2';checksum='a'*64
        cfg=dict(staging_protocol=protocol,output='P:/Qualification')
        source='C:/Frozen/input.bin';cache='P:/Qualification/immutable-input-cache-v2/'+checksum
        sample=dict(source=source,target='P:/Qualification/case/input.bin',linked_source=cache)
        worker=dict(staging_controls=dict(protocol=protocol,status='passed-real-local-volume-copy-cache-and-hardlink-byte-equivalence'),
            staging_receipt=dict(protocol=protocol,linked_input_counts={source:140},actual_link_count=140,
                link_samples=[sample]*128,link_sample_limit=128,cache_files_sha256={cache:checksum}))
        self.assertEqual(audit_stock.inspect_staging(cfg,worker)['actual_link_count'],140)
        for change in (dict(actual_link_count=139),dict(link_samples=[sample]*127),dict(link_sample_limit=127),
                       dict(cache_files_sha256={'C:/outside/'+checksum:checksum}),
                       dict(linked_input_counts={source:-140})):
            bad=copy.deepcopy(worker);bad['staging_receipt'].update(change)
            with self.subTest(change=change),self.assertRaises(ValueError):audit_stock.inspect_staging(cfg,bad)
        bad=copy.deepcopy(worker);bad['staging_receipt']['link_samples'][0]['target']='C:/outside/input.bin'
        with self.assertRaises(ValueError):audit_stock.inspect_staging(cfg,bad)

    def test_historical_and_cross_volume_runner_closures_are_distinct(self):
        legacy=dict(audit_stock.RUNNER_SOURCES)
        self.assertEqual(audit_stock.runner_sources(legacy),legacy)
        current=dict(legacy)
        del current['static_binary_link_staging_v1.py']
        current['static_binary_link_staging_v2.py']='Closeout/LocalVM/static_binary_link_staging_v2.py'
        self.assertEqual(audit_stock.runner_sources(current),current)
        for bad in ({},dict(current,extra='unowned'),dict(current,**{'static_binary_link_staging_v1.py':'legacy'})):
            with self.subTest(bad=bad),self.assertRaises(ValueError):audit_stock.runner_sources(bad)

    def setUp(self):
        cases=json.loads((Path(__file__).resolve().parents[1]/'RemainingStock/cases.json').read_text())['cases']
        self.config=dict(cases=cases)
        self.cfg=dict(capture_scope=dict(kind='diagnostic',gate='remaining-stock',cases=['remaining_stock_003']),
                      math_profile='matrix',scene_workers=1,minimum_free_bytes=1024**3)
    def test_selected_scope_is_diagnostic(self):
        cases,selected=stock.selection(self.cfg,self.config)
        self.assertTrue(selected);self.assertEqual([case['id'] for case in cases],['remaining_stock_003'])
    def test_full_38_selected_remains_diagnostic(self):
        self.cfg['capture_scope']['cases']=[case['id'] for case in self.config['cases']]
        self.assertTrue(stock.selection(self.cfg,self.config)[1])
    def test_complete_scope_requires_inventory_and_capacity(self):
        self.cfg['capture_scope']['kind']='complete'
        with self.assertRaises(ValueError):stock.selection(self.cfg,self.config)
        self.cfg['capture_scope']['cases']=[case['id'] for case in self.config['cases']]
        with self.assertRaises(ValueError):stock.selection(self.cfg,self.config)
        self.cfg['minimum_free_bytes']=8*1024**3
        self.assertFalse(stock.selection(self.cfg,self.config)[1])
    def test_invalid_scope_and_concurrency_rejected(self):
        for key,value in [('math_profile','automatic'),('scene_workers',2),('minimum_free_bytes',0)]:
            bad=copy.deepcopy(self.cfg);bad[key]=value
            with self.assertRaises(ValueError):stock.selection(bad,self.config)
        for ids in [[],['unknown'],['remaining_stock_003','remaining_stock_003']]:
            bad=copy.deepcopy(self.cfg);bad['capture_scope']['cases']=ids
            with self.assertRaises(ValueError):stock.selection(bad,self.config)
