"""Bounded controls for full initial SDK inventory; no runtime credit."""
import csv
from pathlib import Path
import tempfile
import unittest
import hosted_capability_reference as reference


class HostedCapabilityReferenceTests(unittest.TestCase):
    def test_initial_sdk_population_is_complete_and_fields_are_original(self):
        self.assertEqual(len(reference.FIELDS),17)
        self.assertIn('remaining_stock_032',reference.CASES);self.assertEqual(len(reference.CASES),9)
        reference.sources()
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'sdk.csv';fields=['tick','object','class',*reference.FIELDS]
            row=dict(tick='0',object='HST',**{'class':'HST'},**{k:'1' for k in reference.FIELDS})
            with path.open('w',newline='') as stream:
                writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerow(row)
                writer.writerow(dict(row,tick='1'))
            self.assertEqual(reference.initial_signatures(path,{'HST':'HST'},{'HST'}),{('HST',*(1.0 for _ in reference.FIELDS))})

    def test_missing_duplicate_or_nonfinite_original_sdk_population_is_rejected(self):
        for damage in ('missing','duplicate','nonfinite','header'):
            with self.subTest(damage=damage),tempfile.TemporaryDirectory() as temp:
                path=Path(temp)/'sdk.csv';fields=['tick','object','class',*reference.FIELDS]
                row=dict(tick='0',object='HST',**{'class':'HST'},**{k:'1' for k in reference.FIELDS})
                if damage=='missing':row['object']='other'
                if damage=='nonfinite':row['size']='nan'
                if damage=='header':fields.remove('size');row.pop('size')
                with path.open('w',newline='') as stream:
                    writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerow(row)
                    if damage=='duplicate':writer.writerow(row)
                with self.assertRaises(ValueError):reference.initial_signatures(path,{'HST':'HST'},{'HST'})
