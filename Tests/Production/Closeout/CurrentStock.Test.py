"""Current-SDK adapter keeps diagnostic scope and its capacity contract explicit."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest

file=Path(__file__).resolve().parents[1]/'CurrentWindows/stock.py'
spec=importlib.util.spec_from_file_location('current_stock_controls',file)
stock=importlib.util.module_from_spec(spec);spec.loader.exec_module(stock)


class CurrentStockSelectionTests(unittest.TestCase):
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
