"""The accelerated scalar comparator must preserve exact binary64 arithmetic and source ownership."""
import copy
import math
import unittest
import verify_hosted_ssim as reader


class HostedSsimTests(unittest.TestCase):
    def test_one_ulp_or_nonfinite_difference_cannot_pass(self):
        self.assertEqual(reader.equality('same',.75,.75)['actual_hex'],(.75).hex())
        for actual,expected in ((math.nextafter(.75,1.),.75),(math.inf,math.inf),(math.nan,.75),(-0.,0.)):
            with self.assertRaises(ValueError):reader.equality('changed',actual,expected)
        pairs=reader.small_pairs();self.assertEqual(len(pairs),5)
        self.assertTrue(all(len(a)==len(b)==w*h*4 and min(w,h)>=11 for _,a,b,w,h in pairs))
        self.assertTrue(any(a!=b and a[0::4]==b[0::4] and a[1::4]==b[1::4] and a[2::4]==b[2::4] for _,a,b,_,_ in pairs))

    def test_arithmetic_controls_cannot_substitute_an_unfinished_frame_job(self):
        api=dict(repository=dict(owner='dcajacob',repo='orbiter-cross-platform'),
            run=dict(id=42515116858,head_sha=reader.SOURCE,head_branch='codex/github-qualification',path='.github/workflows/phase6-qualification.yml',status='in_progress'),
            artifact=dict(id=13638968833,name='matched-clock-remaining-stock-v2-Debug-sse2',size_in_bytes=458096852,digest='sha256:'+reader.DIGEST,expired=False,
                workflow_run=dict(id=42515116858,head_sha=reader.SOURCE)),
            jobs=[dict(id=128839665625,run_id=42515116858,head_sha=reader.SOURCE,status='completed',conclusion='success',labels=['windows-2025'])])
        reader.validate_api(api)
        for change in (lambda a:a['jobs'][0].update(status='in_progress'),lambda a:a['jobs'][0].update(conclusion='failure'),
                       lambda a:a['artifact'].update(digest='sha256:'+'f'*64),lambda a:a['run'].update(head_sha='f'*40)):
            value=copy.deepcopy(api);change(value)
            with self.assertRaises(ValueError):reader.validate_api(value)


if __name__=='__main__':unittest.main()
