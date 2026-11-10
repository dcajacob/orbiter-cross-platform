"""Actual failed ABI inspection cannot confuse SDK strings, unbounded text or a different source."""
import copy
import unittest
import inspect_rejection_cpp_abi as reader


class RejectionCppAbiTests(unittest.TestCase):
    TOKEN=b'gcc-13.3.0:libstdc++-20240521-abi-1-normal-gxx-1018:201703L'

    def test_only_actual_NUL_bounded_gcc_library_language_identity_is_scanned(self):
        self.assertEqual(reader.abi_tokens(b'\x7fELF\x00'+self.TOKEN+b'\x00'),[self.TOKEN.decode()])
        self.assertEqual(reader.abi_tokens(b'\x7fELFprefix'+self.TOKEN+b'\x00'),[])
        self.assertEqual(reader.abi_tokens(b'\x7fELF\x00'+self.TOKEN),[])
        with self.assertRaises(ValueError):reader.abi_tokens(b'MZ\x00'+self.TOKEN+b'\x00')

    def test_distinct_compiler_library_and_language_tokens_are_never_normalized_to_one_identity(self):
        changed=self.TOKEN.replace(b'20240521',b'20260101')
        self.assertEqual(len(reader.abi_tokens(b'\x7fELF\x00'+self.TOKEN+b'\x00'+changed+b'\x00')),2)
        for changed in (self.TOKEN.replace(b'13.3.0',b'15.2.0'),self.TOKEN.replace(b'201703L',b'202002L')):
            self.assertNotEqual(reader.abi_tokens(b'\x7fELF\x00'+self.TOKEN+b'\x00'),reader.abi_tokens(b'\x7fELF\x00'+changed+b'\x00'))

    def test_only_exact_actual_failed_standard_profile_and_original_raw_digest_are_inspected(self):
        source=reader.SOURCE;api=dict(repository=dict(owner='dcajacob',repo='orbiter-cross-platform'),run=dict(repository=dict(private=False,full_name='dcajacob/orbiter-cross-platform'),id=reader.RUN,head_sha=source,head_branch='qualification/native-class-rejections-v6',path='.github/workflows/phase6-native-class-rejections-official-pool-uri.yml',run_attempt=1),jobs=[dict(id=j,name='Original normal host class and loader rejection controls '+reader.PROFILE if j==reader.JOB else 'other original job',run_id=reader.RUN,head_sha=source,labels=['ubuntu-24.04'],status='completed' if j==reader.JOB else 'in_progress',conclusion='failure' if j==reader.JOB else None) for j in (reader.JOB,130041001771,130041486278,130041486280,130041486413)],artifact=dict(id=reader.ARTIFACT,name='original-class-normal-host-rejection-controls-'+reader.PROFILE,size_in_bytes=reader.SIZE,digest='sha256:'+reader.DIGEST,expired=False,workflow_run=dict(id=reader.RUN,head_sha=source)))
        reader.validate(api)
        for change in (lambda a:a['artifact'].update(digest='sha256:'+'0'*64),lambda a:a['run'].update(head_sha='0'*40),lambda a:a['jobs'][0].update(conclusion='success'),lambda a:a['jobs'][0].update(labels=['self-hosted'])):
            value=copy.deepcopy(api);change(value)
            with self.assertRaises(ValueError):reader.validate(value)
