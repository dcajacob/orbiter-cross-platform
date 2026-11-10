import unittest
import audit_retained_native_math as audit


class RetainedMathEvidence(unittest.TestCase):
    def fixture(self):
        mode=lambda label:dict(profile=label,windows_samples_exact=28800,reload_atan2_samples_exact=4225,mpfr_samples=7698,edge_cases='passed',maximum_ulps={name:0 for name in ['sin','cos','asin','atan2','exp']})
        return dict(status='passed',maximum_allowed_ulps=1,automatic_profile='amd-6121d02-fma3',equatorial_latitude_hex='0x1.fdf30f8d54923p-2',profiles=[mode('automatic'),mode('sse2')],oracle=dict(precision_bits=[256,512],version='synthetic-fixture-only',path='/synthetic/libmpfr.so',sha256='a'*64),probe_sha256='b'*64)

    def test_complete_metadata_stays_only_a_numerical_unit_scope(self):
        result=audit.math_scope(self.fixture(),'Debug-automatic')
        self.assertEqual(result['original_reload_atan2_samples_per_mode'],4225)
        self.assertNotIn('complete_numerical_reload_gate_qualified',result)

    def test_missing_frozen_windows_sample_is_rejected(self):
        value=self.fixture();value['profiles'][0]['windows_samples_exact']-=1
        with self.assertRaises(ValueError):audit.math_scope(value,'Debug-automatic')

    def test_missing_first_difference_neighbour_is_rejected(self):
        value=self.fixture();value['profiles'][0]['reload_atan2_samples_exact']-=1
        with self.assertRaises(ValueError):audit.math_scope(value,'Debug-automatic')

    def test_relaxed_original_MPFR_tolerance_is_rejected(self):
        value=self.fixture();value['maximum_allowed_ulps']=2
        with self.assertRaises(ValueError):audit.math_scope(value,'Debug-automatic')

    def test_missing_original_dispatch_mode_is_rejected(self):
        value=self.fixture();value['profiles'].pop()
        with self.assertRaises(ValueError):audit.math_scope(value,'Debug-automatic')

    def test_forced_SSE2_cannot_be_relabelled_automatic(self):
        value=self.fixture()
        with self.assertRaises(ValueError):audit.math_scope(value,'Debug-sse2')


if __name__=='__main__':unittest.main()
