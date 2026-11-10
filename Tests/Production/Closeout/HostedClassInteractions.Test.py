"""Controls retain original plans and isolate transport/backend provisioning from acceptance."""
import ast
import copy
import hashlib
from pathlib import Path
import tempfile
import unittest
from contracts import ROOT
import hosted_class_interactions as hosted
import capture_hosted_native_writer_runtime as runtime


class HostedClassInteractionsTests(unittest.TestCase):
    def test_every_original_plan_outcome_and_source_is_frozen_at_the_compiled_runtime(self):
        lock,flows=hosted.conserved_sources();self.assertEqual(len(flows),9);self.assertEqual(len(lock['source_sha256']),20)
        self.assertEqual(sum(f['frames'] for f in flows.values())*2*4,56192)
        self.assertEqual(flows['atlantis-original-launch-staging']['frames'],2304)
        self.assertEqual(flows['rms-six-joint-and-stow']['window_system'],'x11')
        self.assertIn('Tests/Production/RemainingVessels/Interactions/atlantis-launch-staging-v1.json',lock['source_sha256'])
        self.assertIn('Tests/Production/RemainingVessels/Interactions/actuator-controls-v1.json',lock['source_sha256'])

    def test_population_path_binding_preserves_exact_published_bytes_and_rejects_overwrite_or_redirect(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp);source=base/'source.csv';target=base/'historic/table.csv';source.write_bytes(b'exact original population\n')
            digest=hashlib.sha256(source.read_bytes()).hexdigest();result=hosted.bind_population_bytes(source,target,digest)
            self.assertEqual(source.read_bytes(),target.read_bytes());self.assertFalse(result['historical_capture_relabelled'])
            hosted.bind_population_bytes(source,target,digest)
            target.write_bytes(b'wrong')
            with self.assertRaises(ValueError):hosted.bind_population_bytes(source,target,digest)
            self.assertEqual(target.read_bytes(),b'wrong');target.unlink();target.symlink_to(source)
            with self.assertRaises(ValueError):hosted.bind_population_bytes(source,target,digest)
            target.unlink()
            with self.assertRaises(ValueError):hosted.bind_population_bytes(source,target,'0'*64)
            self.assertFalse(target.exists())

    def test_declared_X11_candidate_must_be_a_single_exact_signed_repository_version(self):
        self.assertEqual(hosted.candidate_version('xvfb:\n  Installed: (none)\n  Candidate: 2:21.1.20-1ubuntu1\n'),'2:21.1.20-1ubuntu1')
        for text in ('Candidate: (none)\n','Candidate: 1\nCandidate: 2\n','Candidate: 1;cmd\n','Candidate: latest\n','Installed: 1\n'):
            with self.assertRaises(ValueError):hosted.candidate_version(text)

    def test_original_runtime_prefix_post_guards_and_all_profiles_remain_intact(self):
        original=runtime.prepared_body();actual=hosted.prepared_body();ast.parse(actual)
        self.assertIn("'--repeats','2','--runtime-role','diagnostic','--jobs','1'",actual)
        self.assertIn("'--interaction-plan',str(plan)",actual);self.assertIn('verify(reference);verify_x11',actual)
        end="        require(sha(ROOT/'out/mesa-topology-restoration/restoration.json')"
        self.assertIn(original[original.index(end):original.index("        report.update(status='captured-and-independently-audited-native-writers-only'")],actual)
        self.assertLess(actual.index("report['original_X11_backend']=install_x11"),actual.index('report[\'native_host_dependencies\']=install_native_runtime'))
        folder=ROOT/'Tests/Production/Closeout';new=(folder/'prepare_hosted_class_interactions_network.sh').read_text();old=(folder/'prepare_hosted_class_capabilities_network.sh').read_text()
        self.assertEqual(new.replace('prepare_hosted_class_interactions.sh|Tests/Production/Closeout/prepare_hosted_class_interactions_userspace.sh','prepare_hosted_class_capabilities.sh').replace('out/native-interaction-network/','out/native-capability-network/'),old)
        workflow=(ROOT/'.github/workflows/phase6-native-class-interactions.yml').read_text();self.assertIn('needs: readiness',workflow)
        self.assertIn('max-parallel: 2',workflow);self.assertIn('profile: [Debug-automatic, Debug-sse2, Release-automatic, Release-sse2]',workflow)
        self.assertIn('ORBITER_XVFB_VERSION: ${{ needs.readiness.outputs.xvfb_version }}',workflow)

    def test_partial_flow_repetitions_frames_outcomes_source_or_duplicate_process_cannot_pass(self):
        _,flows=hosted.conserved_sources();profile='Debug-sse2';audits=[];pid=1
        for name in hosted.load(hosted.LOCK)['selected_plans']:
            selected=hosted.load(hosted.PLAN_DIR/name)['flows'];cells={}
            for flow in selected:
                runs=[]
                for repeat in range(2):
                    runs.append(dict(actual_pid=pid,actual_exitcode=0,lifecycle=dict(rendered_frames=flow['frames'],successful_presents=flow['frames'],context_deleted=True),assertions=[dict(check=check,left=0,right=0) for check in flow['checks']]));pid+=1
                cells[flow['id']]=runs
            audits.append(dict(status='audited-selected-original-input-interactions-only',runtime_identity=dict(profile=profile,runtime_source_commit=hosted.COMPILED,sanitizer_linked=True),actual_processes=len(cells)*2,flows=cells,owning_bytes_unchanged=True,diagnostic_only=True,native_admission_qualified=False,phase6_complete=False))
        self.assertEqual(hosted.profile_coverage(profile,audits,flows)['actual_processes'],18)
        for mutate in (lambda v:v.pop(),lambda v:v[0]['runtime_identity'].update(runtime_source_commit='e'*40),
                       lambda v:v[0]['flows']['hst-keys'].pop(),lambda v:v[0]['flows']['hst-keys'][0]['lifecycle'].update(successful_presents=1),
                       lambda v:v[0]['flows']['hst-keys'][0]['assertions'].pop(),lambda v:v[0]['flows']['hst-keys'][1].update(actual_pid=1)):
            value=copy.deepcopy(audits);mutate(value)
            with self.assertRaises(ValueError):hosted.profile_coverage(profile,value,flows)
