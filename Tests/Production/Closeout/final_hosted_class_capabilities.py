"""Join complete independently replayed observer and exact SDK receipts; close only capabilities."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import subprocess
from functools import lru_cache
from contracts import ROOT, PROFILES, load, sha, require, atomic_json
from class_eligibility import capability_profile_cases
from final_hosted_class_lifetimes import decode
import inspect_published_class_capabilities as reader
import verify_published_full_SDK as sdk_reader
from checklist import requirements
LOCK = ROOT / 'Tests/Production/Closeout/capability-facet-published-inputs-v1.lock.json'
CI = PurePosixPath('/home/runner/work/orbiter-cross-platform/orbiter-cross-platform')
FLAGS = ('complete_class_eligibility_qualified', 'normal_admission_qualified', 'phase6_complete', 'hands_on_ready')

@lru_cache(maxsize=None)
def gitsha(commit, name):
    p = PurePosixPath(name)
    require(p.parts[0] == 'Tests' and str(p) == name and (not p.is_absolute()) and ('..' not in p.parts) and (':' not in name), 'Exact immutable original test source required')
    return hashlib.sha256(subprocess.check_output(['git', '-C', str(ROOT), 'show', commit + ':' + name])).hexdigest()

def validate_api(record, pin):
    run = record['run']
    jobs = record['jobs']
    artifact = record['artifact']
    require(record['repository'] == dict(owner='dcajacob', repo='orbiter-cross-platform') and run['repository']['private'] is False and (run['repository']['full_name'] == 'dcajacob/orbiter-cross-platform') and (run['id'] == pin['run_id']) and (run['head_sha'] == pin['source']) and (run['head_branch'] == pin['branch']) and (run['path'] == pin['workflow']) and (run['run_attempt'] == 1) and (run['status'] == 'completed') and (run['conclusion'] == 'success'), 'Exact complete public independent receipt source/run required')
    require(len(jobs) == len(pin['jobs']) and len({j['id'] for j in jobs}) == len(jobs) and ({str(j['id']): j['name'] for j in jobs} == pin['jobs']) and all((j['run_id'] == run['id'] and j['head_sha'] == pin['source'] and (j['status'] == 'completed') and (j['conclusion'] == 'success') and (j['labels'] == ['ubuntu-24.04']) for j in jobs)), 'Every exact closed standard hosted receipt job required')
    require(artifact['id'] == pin['artifact_id'] and artifact['name'] == pin['artifact_name'] and (artifact['expired'] is False) and (artifact['size_in_bytes'] == pin['archive_bytes']) and (artifact['digest'] == 'sha256:' + pin['archive_sha256']) and (artifact['workflow_run']['id'] == run['id']) and (artifact['workflow_run']['head_sha'] == run['head_sha']), 'Exact independently published receipt/API bytes required')

def restore(base, pin):
    validate_api(load(base / 'api.json'), pin)
    archive = base / 'producer.zip'
    require(archive.stat().st_size == pin['archive_bytes'] and sha(archive) == pin['archive_sha256'], 'Actual bounded independent receipt ZIP digest differs')
    payload = base / 'decoded'
    members = decode(archive, payload)
    return ({n: (payload / n).read_bytes() for n in members}, members)

def controls(bodies, name, source, count):
    value = json.loads(bodies[name])
    require(value['status'] == 'passed' and value['tests_run'] == count and (value['producer_commit'] == source) and (value['sources_match_producer'] is True) and (value['failures'] == value['errors'] == value['skipped'] == 0), 'Every original and publication helper control must pass at its immutable owner')
    for absolute, digest in value['sources_sha256'].items():
        require(gitsha(source, PurePosixPath(absolute).relative_to(CI).as_posix()) == digest, 'Immutable receipt helper source differs')

def inspect_observer(profile, bodies, members, source, inventory):
    old_lock = reader.load(reader.LOCK)
    pin = old_lock['profiles'][profile]
    capture_source = old_lock['source']
    ci = CI
    families = {r[0] for r in inventory['unique_signatures']}
    config = load(ROOT / 'Tests/Production/RemainingStock/cases.json')
    prefix = 'capability-independent/' + profile + '/'
    proof = json.loads(bodies[prefix + 'proof.json'])
    raw = json.loads(bodies[prefix + 'raw-members.json'])
    audit = json.loads(bodies[prefix + 'original-capabilities-audit.json'])
    binding = json.loads(bodies[prefix + 'original-reference-bindings.json'])
    api_name = 'class-capability-published/' + profile + '/api.json'
    api = json.loads(bodies[api_name])
    reader.validate_api(api, profile)
    require(proof['protocol'] == 'phase6-independent-published-original-capability-profile-v1' and proof['status'] == 'verified-published-original-nine-scene-capability-and-observer-profile-only' and (proof['auditor_source'] == source) and (proof['profile'] == profile) and (proof['actual_auditor_pid'] > 0), 'Exact independently replayed capability receipt invariant differs')
    require(proof['original_source'] == capture_source and proof['original_run_id'] == 42755158018 and (proof['original_job_id'] == pin['job_id']) and (proof['original_artifact_id'] == pin['artifact_id']) and (proof['original_archive_bytes'] == pin['archive_bytes']) and (proof['original_archive_sha256'] == pin['archive_sha256']), 'Exact independently replayed capability receipt invariant differs')
    require(proof['source_api_sha256'] == members[api_name] and proof['new_simulator_processes'] == 0 and (proof['actual_original_capability_processes'] == 36) and (proof['actual_raw_members'] == len(raw) == 1858) and (proof['actual_raw_decoded_bytes'] == sum((r['bytes'] for r in raw.values()))), 'Exact independently replayed capability receipt invariant differs')
    require(proof['original_capability_audit_reproduced_byte_identically'] is True and proof['all_original_published_members_unchanged'] is True and (proof['other_profiles_and_formal_class_facets_pending'] is True), 'Exact independently replayed capability receipt invariant differs')
    require(all((proof[k] is False for k in ('complete_class_eligibility_qualified', 'normal_admission_qualified', 'phase6_complete', 'hands_on_ready'))), 'Exact independently replayed capability receipt invariant differs')
    require(proof['raw_members_sha256'] == members[prefix + 'raw-members.json'] and proof['original_capability_audit_sha256'] == members[prefix + 'original-capabilities-audit.json'] and (proof['original_reference_bindings_sha256'] == members[prefix + 'original-reference-bindings.json']), 'Exact independently replayed capability receipt invariant differs')
    require(raw['hosted-native-class-capabilities/' + profile + '/original-capabilities-audit.json']['sha256'] == proof['original_capability_audit_sha256'] and raw['hosted-native-class-capabilities/' + profile + '/collection.json']['sha256'] == proof['original_collection_sha256'], 'Exact independently replayed capability receipt invariant differs')
    cap = 'native-class-capabilities/' + profile + '/capabilities.json'
    require(audit['capture_sha256'] == raw[cap]['sha256'], 'Exact independently replayed capability receipt invariant differs')
    require(audit['status'] == 'audited-original-Windows-native-capabilities-and-observer-controls-diagnostic-only' and audit['runtime_identity']['profile'] == profile and (audit['runtime_identity']['runtime_source_commit'] == reader.original.COMPILED) and (audit['runtime_identity']['sanitizer_linked'] is True), 'Exact independently replayed capability receipt invariant differs')
    require(audit['actual_processes'] == 36 and audit['repeats'] == 2 and (audit['owning_bytes_unchanged'] is True) and (audit['diagnostic_only'] is True) and (audit['native_admission_qualified'] is False) and (audit['phase6_complete'] is False) and (audit['capture_original_status'] == 'captured-capability-controls-awaiting-independent-audit') and (audit['capture_original_failures'] == {}), 'Exact independently replayed capability receipt invariant differs')
    require(audit['collector_producer_commit'] == capture_source and audit['collector_source_owner'] == str(ci) and (audit['historical_original_launch_receipts_reconstructed'] is False), 'Exact independently replayed capability receipt invariant differs')
    cases, runtime_sources, processes = capability_profile_cases([audit], profile, reader.original.CASES)
    require(runtime_sources == {reader.original.COMPILED} and processes == 36, 'Exact independently replayed capability receipt invariant differs')
    signatures = set()
    for case, runs in cases.items():
        require(len(runs) == 2, 'Exact independently replayed capability receipt invariant differs')
        for entry in runs:
            require(math.isfinite(entry['observer_equivalence_ssim']) and entry['observer_equivalence_ssim'] >= config['image_ssim_minimum'], 'Exact independently replayed capability receipt invariant differs')
            for value in entry['actual_capabilities'].values():
                require(set(value) == {'class', *reader.original.FIELDS}, 'Exact independently replayed capability receipt invariant differs')
                if value['class'] in families:
                    signatures.add((value['class'], *(float(value[k]) for k in reader.original.FIELDS)))
    require(signatures == {tuple(v) for v in inventory['profiles'][profile]['selected_case_signatures']}, 'Exact independently replayed capability receipt invariant differs')
    scope = proof['original_facets']
    require(scope['status'] == 'captured-and-audited-original-nine-scene-capability-observer-controls-only' and scope['profile'] == profile and (scope['cases'] == reader.original.CASES) and (scope['repeats'] == 2) and (scope['observer_lanes'] == ['off', 'on']) and (scope['actual_processes'] == 36), 'Exact independently replayed capability receipt invariant differs')
    require(scope['full_17_field_signatures_observed'] == inventory['profiles'][profile]['selected_case_signatures'] and scope['non_mass_structural_combinations'] == 16 and (scope['all_22_full_17_field_variants_independent_audit_pending'] is True) and (scope['published_raw_independent_replay_pending'] is True), 'Exact independently replayed capability receipt invariant differs')
    require(all((scope[k] is False for k in ('complete_class_eligibility_qualified', 'normal_admission_qualified', 'phase6_complete', 'hands_on_ready'))), 'Exact independently replayed capability receipt invariant differs')
    require(scope['metadata_sha256'][str(ci / 'out' / cap)] == raw[cap]['sha256'] and scope['metadata_sha256'][str(ci / 'out/hosted-native-class-capabilities' / profile / 'original-capabilities-audit.json')] == proof['original_capability_audit_sha256'], 'Exact independently replayed capability receipt invariant differs')
    require(binding['old_reference_owner'] == capture_source and binding['current_reference_owner'] == source and (binding['old_API_receipts_preserved'] is True) and (binding['old_capture_relabelled'] is False) and (len(binding['old_guarded_inputs']) == 293), 'Exact independently replayed capability receipt invariant differs')
    comparison = binding['independent_original_retry_comparison']
    require(comparison['raw_API_and_log_transport_identities_preserved'] is True and comparison['API_attempts_normalized'] is False and (comparison['old_failed_attempt_relabelled'] is False), 'Exact independently replayed capability receipt invariant differs')
    historical = 0
    source_guards = 0
    for old_name, entry in binding['old_guarded_inputs'].items():
        p = PurePosixPath(old_name)
        relative = p.relative_to(ci).as_posix()
        require(len(entry['sha256']) == 64, 'Exact independently replayed capability receipt invariant differs')
        if entry['identity'] == 'exact-published-historical-reference-receipt':
            rel = p.relative_to(ci / 'out').as_posix()
            require(rel.startswith(reader.RECEIPTS[0]) or rel in reader.RECEIPTS[1:], 'Exact independently replayed capability receipt invariant differs')
            require(entry['path'] == str(ci / 'out/capability-independent' / profile / 'original-artifact' / rel) and raw[rel]['sha256'] == entry['sha256'], 'Exact independently replayed capability receipt invariant differs')
            historical += 1
        else:
            require(entry['identity'] == 'same-actual-input-or-source' and entry['path'] == old_name, 'Exact independently replayed capability receipt invariant differs')
            if relative.startswith('Tests/'):
                require(gitsha(capture_source, relative) == entry['sha256'], 'Exact independently replayed capability receipt invariant differs')
                source_guards += 1
    for absolute, value in audit['auditor_sources_sha256'].items():
        relative = PurePosixPath(absolute).relative_to(ci).as_posix()
        require(gitsha(reader.original.COMPILED, relative) == value, 'Exact independently replayed capability receipt invariant differs')
    controls(bodies, 'published-capability-controls.json', source, 352)
    expected_labels = ['stock-data', 'planet-data', 'base-assets', 'test-font', 'complete-stock-assets', 'unchanged-complete-original-capability-audit']
    require([i['label'] for i in proof['commands']] == expected_labels, 'Exact independently replayed capability receipt invariant differs')
    for item in proof['commands']:
        require(item['actual_returncode'] == 0 and item['actual_pid'] > 0 and (not item.get('timed_out')) and (item['log_sha256'] == members[prefix + item['label'] + '.log']), 'Exact independently replayed capability receipt invariant differs')
    return dict(profile=profile, actual_processes=36, cases=reader.original.CASES, repeats=2, observer_lanes=['off', 'on'], full_17_field_signatures=[list(v) for v in sorted(signatures)], non_mass_structural_combinations=16, original_audit_sha256=proof['original_capability_audit_sha256'], original_capture_sha256=raw[cap]['sha256'], independent_proof_sha256=members[prefix + 'proof.json'], raw_members=len(raw), raw_decoded_bytes=proof['actual_raw_decoded_bytes'], old_and_current_source_reference_guards=293, historical_reference_receipts=historical, compiled_runtime_source=reader.original.COMPILED, new_simulator_processes=0)

def inspect_sdk(mode, bodies, receipt_members, source, inventory):
    producer = '714f1d455a6726122ce611f447e17332bfdda3ed'
    all_profiles = {}
    rawpins = sdk_reader.sdk.matrix_cli.plan()['cohorts']['stock-writer']['pins']
    prefix = 'full-SDK-published-verification/' + mode + '/'
    proof = json.loads(bodies[prefix + 'proof.json'])
    members = json.loads(bodies[prefix + 'members.json'])
    api_name = 'full-SDK-published/' + mode + '/api.json'
    api = json.loads(bodies[api_name])
    lock, pin = sdk_reader.validate_api(api, mode)
    require(proof['protocol'] == 'phase6-verified-published-full-original-native-SDK-cohort-v1' and proof['status'] == 'verified-published-complete-two-profile-SDK-and-port-variants-only' and (proof['auditor_source'] == source) and (proof['math_profile'] == mode), 'Exact independently replayed capability receipt invariant differs')
    require(proof['producer_source'] == producer and proof['producer_run_id'] == 42759840013 and (proof['producer_job_id'] == pin['job_id']) and (proof['producer_artifact_id'] == pin['artifact_id']) and (proof['producer_archive_bytes'] == pin['archive_bytes']) and (proof['producer_archive_sha256'] == pin['archive_sha256']), 'Exact independently replayed capability receipt invariant differs')
    require(proof['source_api_sha256'] == receipt_members[api_name] and proof['members_sha256'] == receipt_members[prefix + 'members.json'], 'Exact independently replayed capability receipt invariant differs')
    require(proof['fields'] == list(sdk_reader.sdk.reference.FIELDS) and proof['actual_initial_pairs'] == 152 and (proof['full_variants_per_profile'] == 22) and (proof['source_controls_passed'] == 343) and (proof['new_simulator_processes'] == 0), 'Exact independently replayed capability receipt invariant differs')
    require(proof['producer_run_status'] == 'completed' and proof['producer_run_conclusion'] == 'success' and (proof['original_nine_scene_144_process_controls_pending'] is True), 'Exact independently replayed capability receipt invariant differs')
    require(all((proof[k] is False for k in ('complete_class_eligibility_qualified', 'normal_admission_qualified', 'phase6_complete', 'hands_on_ready'))), 'Exact independently replayed capability receipt invariant differs')
    require(members['class-full-SDK-variant-audits/' + mode + '.json']['sha256'] == proof['full_report_sha256'] and members['class-capability-inventory/reference/inventory.json']['sha256'] == proof['full_inventory_sha256'] == sha(ROOT / 'out/class-capability-inventory/reference/inventory.json'), 'Exact independently replayed capability receipt invariant differs')
    require(len(proof['published_source_witnesses_sha256']) == 392 and proof['historical_source_guards_verified'] == 398, 'Exact independently replayed capability receipt invariant differs')
    for name, value in proof['published_source_witnesses_sha256'].items():
        parts = PurePosixPath(name).parts
        require(parts[0] == 'class-full-SDK-source-witnesses' and parts[1] in {c + '-' + mode for c in ('Debug', 'Release')}, 'Exact independently replayed capability receipt invariant differs')
        relative = sdk_reader.sdk.source_relative(PurePosixPath(*parts[2:]).as_posix())
        require(value == members[name]['sha256'] == gitsha('6ca9af318e625e263deed144e62525e3632fb9ee', relative), 'Exact independently replayed capability receipt invariant differs')
    require(set(proof['profiles']) == {c + '-' + mode for c in ('Debug', 'Release')}, 'Exact independently replayed capability receipt invariant differs')
    for profile, value in proof['profiles'].items():
        require(profile not in all_profiles and value['profile'] == profile and (value['actual_initial_pairs'] == 76) and (value['complete_scenes'] == 38) and (value['repeats'] == 2), 'Exact independently replayed capability receipt invariant differs')
        require(value['full_17_field_signatures'] == inventory['profiles'][profile]['unique_signatures'] and value['additional_full_variants_observed'] == inventory['full_17_field_variants_not_in_original_nine_cases'], 'Exact independently replayed capability receipt invariant differs')
        require(value['all_original_17_fields_exact'] is True and value['docking_geometry_budget'] == 0 and (value['attachment_budgets_unchanged'] is True) and (value['new_simulator_processes'] == 0), 'Exact independently replayed capability receipt invariant differs')
        require(value['original_nine_scene_144_process_controls_pending'] is True and all((value[k] is False for k in ('complete_class_eligibility_qualified', 'normal_admission_qualified', 'phase6_complete', 'hands_on_ready'))), 'Exact independently replayed capability receipt invariant differs')
        require(value['raw_native_archive_sha256'] == rawpins[profile][4], 'Exact independently replayed capability receipt invariant differs')
        require(len(value['native_capture_sha256']) == 64, 'Exact independently replayed capability receipt invariant differs')
        all_profiles[profile] = value
    controls(bodies, 'published-SDK-controls.json', source, 346)
    return (all_profiles, dict(independent_proof_sha256=receipt_members[prefix + 'proof.json'], initial_pairs=152, historical_source_guards=398, historical_source_witnesses=392, full_report_sha256=proof['full_report_sha256'], full_inventory_sha256=proof['full_inventory_sha256']))

def combine(observers, sdk, inventory):
    require(set(observers) == set(sdk) == set(PROFILES), 'All four independently verified observer and SDK profiles required')
    for profile, observed in observers.items():
        exact = sdk[profile]
        require(observed['profile'] == exact['profile'] == profile and observed['actual_processes'] == 36 and (observed['cases'] == reader.original.CASES) and (observed['repeats'] == exact['repeats'] == 2) and (observed['observer_lanes'] == ['off', 'on']) and (observed['new_simulator_processes'] == exact['new_simulator_processes'] == 0), 'Complete original nine-scene two-repeat off/on scope required in every profile')
        require(observed['compiled_runtime_source'] == reader.original.COMPILED and observed['non_mass_structural_combinations'] == 16 and (observed['full_17_field_signatures'] == inventory['profiles'][profile]['selected_case_signatures']) and (exact['full_17_field_signatures'] == inventory['profiles'][profile]['unique_signatures']) and (len(exact['full_17_field_signatures']) == 22) and (len(observed['full_17_field_signatures']) == 17) and (exact['additional_full_variants_observed'] == inventory['full_17_field_variants_not_in_original_nine_cases']) and ({tuple(v) for v in observed['full_17_field_signatures']} | {tuple(v) for v in exact['additional_full_variants_observed']} == {tuple(v) for v in exact['full_17_field_signatures']}), 'Full exact SDK superset and every original observer signature required without dropping any field')
        require(exact['actual_initial_pairs'] == 76 and exact['complete_scenes'] == 38 and (exact['all_original_17_fields_exact'] is True) and (exact['docking_geometry_budget'] == 0) and (exact['attachment_budgets_unchanged'] is True) and all((exact[k] is False for k in FLAGS)), 'All original SDK/docking/attachment comparisons and pending wider gates required')
    return dict(profiles=list(PROFILES), original_observer_processes=144, exact_initial_SDK_pairs=304, original_cases=reader.original.CASES, repeats=2, observer_lanes=['off', 'on'], full_variants_per_profile=22, selected_observer_variants_per_profile=17, exact_SDK_fields=list(reader.original.FIELDS), docking_geometry_budget=0, attachment_budgets_unchanged=True, non_mass_structural_combinations=16, new_simulator_processes=0)

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--inputs', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    require(os.environ.get('GITHUB_ACTIONS') == 'true' and os.environ.get('RUNNER_OS') == 'Linux' and (Path(os.environ['GITHUB_WORKSPACE']).resolve() == ROOT), 'Actual independent standard hosted worker required')
    require(not a.output.exists() and a.output.resolve().is_relative_to(ROOT / 'out'), 'Fresh separate narrow capability facet output required')
    a.output.mkdir(parents=True)
    lock = load(LOCK)
    inventory = reader.original.reference_inventory()
    conserved = reader.original.sources()
    require(set(lock['observers']) == set(PROFILES) and set(lock['sdk']) == {'automatic', 'sse2'}, 'Exact closed observer and SDK input roster required')
    observers = {}
    sdk = {}
    inputs = {}
    for group in ('observers', 'sdk'):
        for key, pin in lock[group].items():
            base = a.inputs / group / key
            bodies, members = restore(base, pin)
            if group == 'observers':
                observers[key] = inspect_observer(key, bodies, members, pin['source'], inventory)
                detail = {}
            else:
                values, detail = inspect_sdk(key, bodies, members, pin['source'], inventory)
                require(not set(sdk) & set(values), 'Duplicate SDK profile')
                sdk.update(values)
            inputs[group + '/' + key] = dict(source=pin['source'], run_id=pin['run_id'], artifact_id=pin['artifact_id'], archive_sha256=pin['archive_sha256'], archive_bytes=pin['archive_bytes'], api_sha256=sha(base / 'api.json'), decoded_members_sha256=members, details=detail)
    coverage = combine(observers, sdk, inventory)
    require(reader.original.reference_inventory() == inventory and reader.original.sources() == conserved, 'Original capability owners or complete SDK inventory changed during final scope verification')
    report = dict(protocol='phase6-renewed-independent-capability-facet-v1', status='verified-four-profile-original-capability-facet-only', auditor_source=os.environ['GITHUB_SHA'], passed_class_facets=['capabilities'], remaining_class_facets_requiring_separate_evidence=['source-abi', 'interactions', 'persistence', 'resource-ownership', 'twenty-cycle-teardown', 'rejection-controls'], coverage=coverage, observers=observers, full_SDK_profiles=sdk, inputs=inputs, original_auditors_conserved=conserved, inventory_sha256=sha(ROOT / 'out/class-capability-inventory/reference/inventory.json'), input_lock_sha256=sha(LOCK), all_original_observer_audits_reproduced_byte_identically=True, all_original_source_and_reference_guards_retained=True, historical_structural_inventory_restored=False, historical_23_evidence_records_restored=False, old_capture_or_pending_flags_relabelled=False, full_original_raw_captures_and_source_witnesses_stayed_on_GitHub=True, new_simulator_processes=0, scope='Original nine-scene/two-repeat/four-profile observer-off/on controls plus every full 17-field/22-variant original SDK and exact port comparison. Complete class, normal admission and hands-on acceptance require their own evidence.', **{k: False for k in FLAGS})
    atomic_json(a.output / 'capability-facet.json', report)
    print(report['status'])
if __name__ == '__main__':
    main()
