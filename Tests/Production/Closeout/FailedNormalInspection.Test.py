from unittest import TestCase
from inspect_failed_normal_admission import flight_summary


class FailedNormalInspection(TestCase):
    def test_preserves_partial_failed_row_and_exact_first_unwritten_field(self):
        result=flight_summary(b'tick,name,x,y,z\n0,Atlantis,1,2,3\n1,Atlantis,1,2\n')
        self.assertEqual(result['complete_rows'],1)
        self.assertEqual(result['partial_rows'][0]['first_unwritten_field'],'z')
        self.assertEqual(result['partial_rows'][0]['values'],dict(tick='1',name='Atlantis',x='1',y='2'))
        self.assertEqual(result['per_vessel']['Atlantis']['rows'],1)

    def test_refuses_ambiguous_original_trace_columns(self):
        with self.assertRaises(ValueError):flight_summary(b'tick,name,x,x\n0,A,1,2\n')

    def test_preserves_failure_bytes_without_normalizing_nonfinite_values(self):
        result=flight_summary(b'tick,name,x\n0,A,NaN\n1,A,1e309\n')
        self.assertEqual(result['per_vessel']['A']['first'],[dict(tick='0',name='A',x='NaN'),dict(tick='1',name='A',x='1e309')])
