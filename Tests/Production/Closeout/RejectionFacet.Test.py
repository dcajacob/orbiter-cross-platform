import unittest
import final_hosted_class_rejections as final


class OriginalRejectionCoverage(unittest.TestCase):
    def fixture(self):
        # Synthetic metadata only: this can test rejection of forged receipts,
        # never produce a hosted qualification or replace any actual capture.
        frozen=final.original.conserved_sources();profile='Debug-sse2';producer='0'*40;prefix='out/native-class-rejections/'+profile+'/'
        executable=str(final.CI/'out/phase6-hosted-native'/profile/'engine/orbiter-production');digest='a'*64
        runtime=dict(profile=profile,runtime_source_commit=final.original.COMPILED,sanitizer_linked=True)
        controls={};identities=[];files={}
        for i,control in enumerate(frozen['exact_original_controls'],1):
            name=control['id'];hashes={'process-receipt.json':digest,'invocation.json':digest}
            controls[name]=dict(actual_pid=i,actual_exitcode=1,lifecycle=dict(rendered_frames=0,successful_presents=0,context_deleted=True),expected_error='synthetic negative-control fixture',files_sha256=hashes)
            identities.append(dict(control=name,pid=i,start_ticks=i+100,argv=[executable],receipt_sha256=digest,invocation_sha256=digest))
            files.update({prefix+name+'/'+n:dict(sha256=h) for n,h in hashes.items()})
        source='Tests/Production/RemainingVessels/rejections.py';files[source]=dict(sha256=digest)
        capture=dict(producer_commit=producer,runtime_owner=str(final.CI),status='passed-negative-loader-and-class-controls-only',failures={},controls_requested=frozen['exact_original_controls'],cases_requested=final.original.CASES,controls=controls,runtime_role='normal',runtime_executable=executable,runtime_identity=runtime,diagnostic_only=True,native_admission_qualified=False,phase6_complete=False,guarded_files_sha256={str(final.CI/source):digest})
        audit=dict(runtime_role='normal',runtime_identity=runtime,status='audited-negative-loader-and-class-controls-only',families=final.requirements()['class-eligibility']['families'],actual_processes=45,controls=controls,owning_bytes_unchanged=True,sanitizer_suppressions=False,diagnostic_only=True,native_admission_qualified=False,phase6_complete=False)
        scope=dict(status='captured-and-audited-original-normal-host-rejection-controls-only',profile=profile,compiled_runtime_source=final.original.COMPILED,exact_original_controls=frozen['exact_original_controls'],actual_original_processes=45,actual_original_process_identities=identities,**{k:True for k in ('no_frames_presented','all_contexts_clean','no_rejected_world_saved','no_invalid_fixture_initialized','unsuppressed_original_sanitizers')},**{k:False for k in final.FLAGS})
        return [profile,capture,audit,scope,dict(files=files),frozen,producer]

    def test_complete_synthetic_scope_stays_only_a_coverage_result(self):
        result=final.original_coverage(*self.fixture())
        self.assertEqual(result['actual_unique_PID_start_identities'],45)
        self.assertNotIn('complete_class_eligibility_qualified',result)

    def test_reused_actual_process_is_rejected(self):
        args=self.fixture();args[3]['actual_original_process_identities'][1].update(pid=1,start_ticks=101);args[2]['controls'][args[3]['actual_original_process_identities'][1]['control']]['actual_pid']=1
        with self.assertRaises(ValueError):final.original_coverage(*args)

    def test_old_capture_cannot_be_relabelled(self):
        args=self.fixture();args[1]['producer_commit']='1'*40
        with self.assertRaises(ValueError):final.original_coverage(*args)

    def test_missing_original_control_is_rejected(self):
        args=self.fixture();args[1]['controls'].pop(next(iter(args[1]['controls'])))
        with self.assertRaises(ValueError):final.original_coverage(*args)

    def test_changed_original_guard_is_rejected(self):
        args=self.fixture();args[4]['files']['Tests/Production/RemainingVessels/rejections.py']['sha256']='b'*64
        with self.assertRaises(ValueError):final.original_coverage(*args)


if __name__=='__main__':unittest.main()
