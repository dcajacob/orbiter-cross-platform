"""Reclamation must reject sources, SDKs, input schedules and unclosed receipts."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parent/'LocalVM'))
from generated_outputs_v2 import generated,output_root,closures,sha,file_map


class GeneratedOutputTests(unittest.TestCase):
    def test_declared_capture_roots_only(self):
        for root in ('C:/OrbiterPhase6/CurrentStock-Debug-v2','C:/OrbiterPhase6/CurrentQualification-f3e8-v1/qualification-v1',
                     'C:/OrbiterPhase6/Runs/CurrentCockpit-847-v2'):self.assertTrue(output_root(root))
        for root in ('C:/OrbiterPhase6/Tools','C:/OrbiterPhase6/full38-preserved-Debug-v1','C:/OrbiterPhase6/CurrentStockObserver-v1',
                     'Z:/CurrentStock-Debug-v2','C:/OrbiterPhase6/Tools/CurrentStock-Debug-v2'):
            with self.assertRaises(ValueError):output_root(root)
    def test_keep_source_sdk_assets_and_input_schedules(self):
        for name in ('Config/test.csv','Modules/test.png','source/plot.png','Inputs/scene.csv','case/replay.csv',
                     'case/flight.scn','case/Orbiter.cfg','case/observer.dll','case/worker.json','Help/example.png',
                     'case/icon.png','case/custom-replay.csv','Flights/input.csv'):self.assertFalse(generated(name))
        for name in ('automatic-stock/remaining_stock_003-1/scene.rgba','Debug/controls/scene.png','case/stock-vessel-state.csv'):
            self.assertTrue(generated(name))
        for name in ('../scene.csv','C:/scene.csv','/scene.csv'):
            with self.assertRaises(ValueError):generated(name)
    def test_open_or_changed_closure_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'worker.json';path.write_text(json.dumps(dict(status='running')))
            with self.assertRaises(ValueError):closures([dict(path=str(path),sha256=sha(path),status='running')])
            path.write_text(json.dumps(dict(status='passed')));record=dict(path=str(path),sha256=sha(path),status='passed');closures([record])
            path.write_text(json.dumps(dict(status='running')))
            with self.assertRaises(ValueError):closures([record])
    def test_file_map_aliases_and_unsafe_names_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'files.json'
            for files in ({'case/scene.csv':'0'*64,'case/SCENE.csv':'0'*64},{'../scene.csv':'0'*64}):
                path.write_text(json.dumps(dict(files=files)))
                with self.assertRaises(ValueError):file_map(dict(path=str(path),sha256=sha(path),field='files'))
    def test_large_closed_metadata_map_retains_every_identity(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'large.json';files={'case-'+str(i)+'/scene.csv':'0'*64 for i in range(16000)}
            path.write_text(json.dumps(dict(files=files)))
            actual=file_map(dict(path=str(path),sha256=sha(path),field='files'))
            self.assertGreater(path.stat().st_size,1024**2);self.assertEqual(actual,files)
