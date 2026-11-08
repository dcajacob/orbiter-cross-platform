#!/usr/bin/env python3
"""Observation preparation/comparison controls do not grant simulation acceptance."""
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from contracts import ROOT


def module(name,file):
    spec=importlib.util.spec_from_file_location(name,ROOT/'Tests/Production/ReloadMath'/file)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result


prepare=module('observer_prepare','prepare_native.py')
comparison=module('observer_comparison','compare.py')
sys.path.insert(0,str(ROOT/'Tests/Production/ReloadMath'))
internal=module('internal_observer_comparison','compare_internal.py')


class MathObserverTests(unittest.TestCase):
    def test_diagnostic_toggle_is_reversible_and_requires_one_anchor(self):
        source=('before\n'+prepare.ANCHOR+'\nafter\n').encode()
        generated=prepare.instrument(source)
        self.assertIn(prepare.ANCHOR.encode(),generated)
        self.assertEqual(generated.count(b'ORBITER_TEST_DISABLE_MATH_OBSERVER'),1)
        for bad in (b'no observation',source+prepare.ANCHOR.encode()):
            with self.assertRaises(ValueError):prepare.instrument(bad)

    def test_first_difference_and_wrong_clock_or_missing_tick(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);left=root/'windows.csv';right=root/'native.csv'
            body='tick,seconds,rounding,force\n'+''.join(str(t)+','+str(t/64)+',0,1\n' for t in range(1,244))
            left.write_text(body);right.write_text(body.replace('211,3.296875,0,1\n','211,3.296875,0,1.0000000000000002\n'))
            result=comparison.compare(left,right)
            self.assertEqual(result['first_differing_fields']['force']['tick'],211)
            self.assertFalse(result['simulator_acceptance'])
            right.write_text(body.replace('211,3.296875','211,3.3'))
            with self.assertRaisesRegex(ValueError,'clocks'):comparison.compare(left,right)
            right.write_text(body.replace('211,3.296875,0,1\n',''))
            with self.assertRaisesRegex(ValueError,'range'):comparison.compare(left,right)

    def test_internal_roster_coverage_clock_and_first_difference(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);left=root/'windows.csv';right=root/'native.csv'
            body='tick,seconds,object,kind,q\n'+''.join(
                f'{t},{t/64},{obj},{kind},1\n' for t in range(1,244)
                for obj,kind in [('ISS','vessel'),('Atlantis','aggregate')])
            left.write_text(body)
            changed=body.replace('211,3.296875,Atlantis,aggregate,1\n',
                                 '211,3.296875,Atlantis,aggregate,1.0000000000000002\n')
            right.write_text(changed)
            result=internal.compare(left,right)
            self.assertEqual(result['rows_per_runtime'],486)
            self.assertEqual(result['first_differing_fields']['Atlantis/aggregate']['q']['tick'],211)
            self.assertFalse(result['simulator_acceptance'])
            for invalid in (body.replace('211,3.296875,Atlantis,aggregate,1\n',''),
                            body+body.splitlines(keepends=True)[1],
                            body.replace('1,0.015625,ISS,vessel,1','1,0.015625,ISS,vessel,nan'),
                            body.replace('211,3.296875','211,3.3'),
                            body.replace('Atlantis','Changed')):
                right.write_text(invalid)
                with self.assertRaises(ValueError):internal.compare(left,right)


if __name__=='__main__':unittest.main()
