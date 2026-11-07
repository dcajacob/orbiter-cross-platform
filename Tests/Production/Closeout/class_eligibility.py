"""Independently inspect scoped class evidence; partial facets never admit a class."""
import argparse
import csv
import hashlib
import importlib.util
import math
import subprocess
from pathlib import Path
import sys

from contracts import atomic_json, load, require, sha, Scope, PHASES
from checklist import requirements

OBJECTS = {'ISS': 'ProjectAlpha_ISS', 'STS-101': 'Atlantis', 'Leonardo': 'Leonardo_mplm'}
STRINGS = {'object', 'class', 'dock', 'focus', 'attached'}
BAD = ('ERROR: AddressSanitizer', 'ERROR: LeakSanitizer', 'runtime error:',
       'AddressSanitizer:DEADLYSIGNAL', 'Production teardown:',
       'LeakSanitizer has encountered', 'Suppressions used:')


def rows(path):
    with Path(path).open(newline='') as stream:
        return list(csv.DictReader(stream))


def inspect_paused(path):
    path = Path(path).resolve()
    report = load(path)
    require(report['status'] == 'passed-actual-paused-attached-docked-world-lifetimes' and
            report['requested_worlds'] == report['worlds_observed_ready'] == report['clean_contexts'] == 20 and
            report['actual_exitcode'] == 0 and report['actual_pid'] > 0 and
            report['no_preload_observer'] is True and report['sanitizer_suppressions'] is False and
            report['all_guarded_inputs_unchanged'] is True and
            report['native_admission_qualified'] is False and report['phase6_complete'] is False and
            report['original_objects'] == OBJECTS, 'Incomplete paused attachment control')
    require(all(sha(p) == value for p, value in report['guarded_files_sha256'].items()),
            'Paused control owning source, binary, resource or runner changed')
    require(report['guarded_files_sha256'].get(report['actual_executable']) ==
            report['actual_executable_sha256'] == sha(report['actual_executable']),
            'Actual paused executable binding missing')
    require(not any(v in (path.parent / 'console.log').read_text(errors='replace') for v in BAD),
            'Paused control runtime/sanitizer diagnostic')
    keys = report['physical_keys']
    require([(k['code'], k['down']) for k in keys] == [(63, True), (63, False)] * 19 + [(1, True)] and
            all(a['monotonic_ns'] < b['monotonic_ns'] for a, b in zip(keys, keys[1:])),
            'Physical nineteen-F5/normal-Escape schedule differs')
    worlds = []
    for index in range(1, 21):
        folder = path.parent if index == 1 else path.parent / ('session-' + str(index))
        life = load(folder / 'graphics-lifecycle.json')
        require(life == report['lifecycles'][index - 1] and life['context_deleted'] is True and
                life['rendered_frames'] == life['successful_presents'] >= 60,
                'Paused graphics lifetime differs')
        require((folder / 'scene.rgba').stat().st_size == 1280 * 720 * 4,
                'Paused full frame incomplete')
        actual = rows(folder / 'flight-state.csv')
        require(len(actual) == 3 and {r['object']: r['class'] for r in actual} == OBJECTS and
                all(r['tick'] == r['seconds'] == '0' and
                    all(math.isfinite(float(v)) for k, v in r.items() if k not in STRINGS)
                    for r in actual), 'Original finite paused world differs')
        by_name = {r['object']: r for r in actual}
        require(by_name['STS-101']['dock'] == 'ISS' and
                by_name['STS-101']['attached'] == 'Leonardo;' and
                by_name['Leonardo']['attached'] == 'STS-101;', 'Reciprocal paused graph differs')
        events = rows(folder / 'input-events.csv')
        # Escape closes through graphics Poll before the flight event logger;
        # F5 is consumed by the original buffered-flight dispatch in each world.
        require([(int(r['key']), int(r['down'])) for r in events] ==
                ([(63, 1), (63, 0)] if index < 20 else []),
                'Actual dispatch did not consume the nineteen recorded F5 pairs')
        worlds.append(dict(lifecycle=life, files_sha256={p.name: sha(p) for p in folder.iterdir()
                            if p.is_file() and p.name != 'verification.json' and
                            not p.name.startswith('independent-audit')}))
    require(report['successful_presents'] == sum(w['lifecycle']['successful_presents'] for w in worlds) and
            report['finite_original_vessel_rows'] == 60, 'Paused aggregate differs')
    return dict(status='audited-paused-attachment-lifetime-facet-only',
                capture_sha256=sha(path), runtime_identity=report['runtime_identity'],
                auditor_sources_sha256={str(p): sha(p) for p in
                    (Path(__file__).resolve(), Path(__file__).with_name('contracts.py').resolve())},
                actual_simulator_pid=report['actual_pid'], actual_exitcode=report['actual_exitcode'],
                worlds=worlds, real_F5_reloads=19, original_vessels=OBJECTS,
                owning_bytes_unchanged=True, no_preload_observer=True, sanitizer_suppressions=False,
                scope='Twenty paused original ISS/Atlantis/Leonardo worlds. Original bytes seed F5; '
                      'does not establish actual-save persistence, unpaused lifetime, interactions, '
                      'normal admission or a complete class-eligibility gate.',
                native_admission_qualified=False, phase6_complete=False)


def family_coverage(captures, specification, family_cases, cases):
    profiles=specification['profiles'];families=specification['families']
    require(set(family_cases)==set(families),'Finite family lifetime map differs')
    expected_cases=set(family_cases.values())
    require(all(name in cases and family in cases[name]['declared_vessels'].values()
                for family,name in family_cases.items()),'Lifetime case does not contain its original family')
    cells={profile:{} for profile in profiles};sources=set()
    for capture in captures:
        identity=capture['audit']['runtime_identity'];profile=identity['profile']
        require(profile in cells,'Unknown family lifetime profile')
        sources.add(identity['runtime_source_commit'])
        for name,result in capture['audit']['cases'].items():
            require(name in expected_cases and name not in cells[profile],
                    'Unexpected or duplicate family lifetime case')
            require(len(result['worlds'])==20,'Incomplete family twenty-world cell')
            cells[profile][name]=dict(capture=capture['capture'],capture_sha256=capture['audit']['capture_sha256'],
                                     actual_module_lifetimes=result['module_lifetimes'])
    require(len(sources)==1 and all(set(row)==expected_cases for row in cells.values()),
            'Missing family/profile/case or mixed source identities')
    return {family:{profile:cells[profile][family_cases[family]] for profile in profiles} for family in families}


def inspect_family_lifetimes(path):
    path=Path(path).resolve();ledger=load(path);gate=ledger['gates']['class-eligibility']
    specification=requirements()['class-eligibility']
    require(gate['expected']==specification and
            all(ledger['gates'][name]['result']=='passed' for name in specification['depends_on']),
            'Fixed family requirements or prerequisite gates differ')
    progress=gate['qualification_progress'];family_cases={name:value['lifetime_case']
        for name,value in progress['family_results'].items()}
    entries=[Path(p) for p in progress['active_lifetime_captures'].values()]
    entries.append(Path(progress['unpaused_hst_canary']['capture']['path']))
    require(len(entries)==len(set(entries))==5,'Exact four captures plus retained HST canary required')
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'RemainingVessels'))
    from lifetimes import audit
    captures=[dict(capture=str(p),audit=audit(p)) for p in entries]
    cases={c['id']:c for c in load(Path(__file__).resolve().parents[1]/'RemainingStock/cases.json')['cases']}
    covered=family_coverage(captures,specification,family_cases,cases)
    facets=['source-abi','resource-ownership','twenty-cycle-teardown']
    return dict(status='audited-family-positive-ABI-ownership-and-twenty-cycle-facets-only',
        ledger_sha256=sha(path),families=covered,captures=captures,
        actual_simulator_processes=sum(len(c['audit']['cases']) for c in captures),
        complete_worlds=sum(c['audit']['worlds'] for c in captures),
        successful_presents=sum(c['audit']['successful_presents'] for c in captures),
        passed_facets=facets,remaining_facets=[v for v in specification['required'] if v not in facets],
        auditor_sources_sha256={str(p):sha(p) for p in (Path(__file__).resolve(),
            Path(__file__).with_name('checklist.py').resolve(),Path(__file__).with_name('contracts.py').resolve())},
        scope='Complete original selected scenes in all four source-matched profiles. Actual checked native '
              'factories/SDK ABI load, source/runtime/resource guards, twenty active worlds, module unloads, '
              'clean contexts and unsuppressed sanitizer exits. Positive ABI loading does not satisfy '
              'incompatible-module rejection controls. Capabilities, interactions and persistence remain open.',
        diagnostic_only=True,native_admission_qualified=False,phase6_complete=False)


def capability_profile_cases(audits,profile,expected_cases):
    cases={};sources=set();processes=0
    for checked in audits:
        require(checked['runtime_identity']['profile']==profile and checked['repeats']==2,
                'Capability profile/repetition incomplete')
        sources.add(checked['runtime_identity']['runtime_source_commit'])
        for name,runs in checked['cases'].items():
            require(name not in cases,'Duplicate completed capability cell')
            cases[name]=runs
        processes+=checked['actual_processes']
    require(len(sources)==1 and set(cases)==set(expected_cases),'Missing capability case or mixed runtime source')
    return cases,sources,processes


def inspect_capability_matrix(path):
    path=Path(path).resolve();ledger=load(path);gate=ledger['gates']['class-eligibility']
    expected=requirements()['class-eligibility'];require(gate['expected']==expected,'Fixed capability requirements differ')
    work=gate['qualification_progress']['capability_controls'];inventory_path=Path(work['inventory']['path'])
    require(sha(inventory_path)==work['inventory']['sha256'],'Original structural capability inventory changed')
    inventory=load(inventory_path)
    require(inventory['status']=='hashed-original-Windows-initial-structural-capability-inventory-only' and
            all(sha(p)==value for p,value in inventory['reference_files_sha256'].items()) and
            set(work['captures'])==set(expected['profiles']) and work['repeats']==2 and
            work['observer_lanes']==['off','on'] and work['expected_cases']==inventory['proposed_native_cases'],
            'Complete actual capability inventory/profile/repeat scope required')
    fields=inventory['fields'];signatures={tuple(v) for v in inventory['unique_signatures']}
    require(len(signatures)==inventory['signature_count']==work['original_structural_signature_count'],
            'Original capability signature inventory differs')
    # Re-read the hashed Windows initial fields, instead of trusting a proposed
    # signature list or a scene selection that happens to name every family.
    actual=set()
    for filename in inventory['reference_files_sha256']:
        if Path(filename).name!='stock-vessel-state.csv':continue
        with Path(filename).open(newline='') as stream:
            for row in csv.DictReader(stream):
                if row['tick']!='0':break
                if row['class'] in expected['families']:
                    actual.add((row['class'],*(float(row[k]) for k in fields)))
    require(actual==signatures,'Proposed signatures omit or substitute actual original SDK fields')
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'RemainingVessels'))
    from capabilities import audit
    results={};sources=set();processes=0
    for profile in expected['profiles']:
        stages=work.get('stages',{}).get(profile,[dict(capture=work['captures'][profile])])
        checked_stages=[]
        for stage in stages:
            capture=Path(stage['capture'])
            checked=audit(capture,stage.get('selected_completed_cases'),stage.get('source_owner'))
            checked_stages.append(dict(capture=str(capture),audit=checked))
        cases,actual_sources,actual_processes=capability_profile_cases(
            [s['audit'] for s in checked_stages],profile,work['expected_cases'])
        observed=set()
        for runs in cases.values():
            for run in runs:
                for row in run['actual_capabilities'].values():
                    if row['class'] in expected['families']:
                        observed.add((row['class'],*(float(row[k]) for k in fields)))
        require(observed==signatures,'Native capability selection misses an original structural combination')
        sources.update(actual_sources);processes+=actual_processes
        results[profile]=dict(stages=checked_stages)
    require(len(sources)==1 and processes==work['expected_processes'],'Mixed or incomplete capability runtime cohort')
    return dict(status='audited-all-family-capability-variants-and-passive-observer-controls-only',
        profiles=results,families=expected['families'],structural_signatures=len(signatures),
        actual_processes=processes,successful_presents=processes*60,passed_facet='capabilities',
        inventory_sha256=sha(inventory_path),auditor_source_sha256=sha(Path(__file__)),
        scope='Every original stock initial structural combination is covered in native SDK snapshots, '
              'four profiles and two observer-off/on repetitions. Sixty-frame diagnostics do not '
              'qualify complete stock parity, interactions, persistence, rejection or normal admission.',
        diagnostic_only=True,native_admission_qualified=False,phase6_complete=False)


def persistence_coverage(stages, profiles, expected_cases):
    cells = {(profile, phase): {} for profile in profiles for phase in PHASES}
    sources = set()
    processes = 0
    for stage in stages:
        checked = stage['audit']
        key = (checked['profile'], checked['phase'])
        require(key in cells and checked['diagnostic_only'] is True and
                checked['owning_bytes_unchanged'] is True,
                'Unknown or unverified persistence scope')
        sources.add(checked['runtime_source'])
        for name, case in checked['cases'].items():
            require(name in expected_cases and name not in cells[key] and len(case['runs']) == 2,
                    'Unexpected, duplicate or incomplete persistence case')
            cells[key][name] = stage['capture']
        require(checked['actual_processes'] == len(checked['cases']) * 2,
                'Persistence actual process count differs')
        processes += checked['actual_processes']
    require(len(sources) == 1 and all(set(row) == set(expected_cases) for row in cells.values()),
            'Missing persistence profile, phase, case or mixed runtime source')
    return cells, processes


def inspect_persistence_matrix(path):
    path = Path(path).resolve(); ledger = load(path)
    gate = ledger['gates']['class-eligibility']; expected = requirements()['class-eligibility']
    require(gate['expected'] == expected, 'Fixed persistence requirements differ')
    progress = gate['qualification_progress']; work = progress['persistence_controls']
    entry = work['execution_plan']; plan_path = Path(entry['path'])
    require(sha(plan_path) == entry['sha256'], 'Persistence execution plan changed')
    plan = load(plan_path); names = plan['required_cases']
    require(names == progress['capability_controls']['expected_cases'] == work['expected_cases'] and
            plan['required_runs'] == work['expected_runs'] == len(names) * len(expected['profiles']) * 4,
            'Exact finite family persistence matrix required')
    entries = plan['requests'] if plan.get('schema')==2 else [plan[k] for k in ('new_request','retained_request')]
    declared = {entry['path']:entry['sha256'] for entry in entries}
    require({item['request'] for item in plan['coordinators']} == set(declared) and
            len(plan['coordinators']) == len(declared) == len(entries) and len(entries)>=2,
            'Exact nonduplicated declared coordinator scopes required')
    stages = []; coordinators = []; reader = None; owning_root = None
    for item in plan['coordinators']:
        request_path = Path(item['request']); status_path = Path(item['status'])
        require(sha(request_path) == declared[str(request_path)], 'Persistence request changed')
        request = load(request_path); status = load(status_path); status_sha = sha(status_path)
        owner = Path(request['owner']).resolve(); scope = Scope.make(request['selected_cases'])
        require(scope.selected and set(scope.cases) <= set(names) and
                request['profiles'] == expected['profiles'] and request['jobs_per_collector'] in (1, 2),
                'Persistence coordinator profile, case or process scope differs')
        runner=Path(__file__).with_name('run_native.py')
        if plan.get('schema')==2:
            source=item['coordinator_source'];runner=Path(source['owner'])/source['path']
            body=subprocess.check_output(['git','-C',source['owner'],'show',source['commit']+':'+source['path']])
            require(hashlib.sha256(body).hexdigest()==source['sha256']==sha(runner),
                    'Actual coordinator differs from its explicit immutable producer')
        require(status['status'] in ('audited-reusable-captures-only','diagnostic-collected-and-audited') and
                status['failures'] == {} and
                status['request_sha256'] == declared[str(request_path)] and
                status['diagnostic_only'] is True and status['cases'] == list(scope.cases) and
                status['native_admission_qualified'] is False and status['phase6_complete'] is False and
                status['coordinator_sha256'] == sha(runner) and
                status['maximum_native_simulators'] <= 4 and
                set(status['stages']) == {p + '/' + phase for p in expected['profiles'] for phase in PHASES},
                'Incomplete, failed or changed persistence coordinator')
        if reader is None:
            owning_root = owner
            sys.path.insert(0, str(owner / 'Tests/Production/RemainingStockPersistence'))
            from observations import bind_owner, inspect_native
            reader = bind_owner(owner, request['collector_commit'])
            spec = importlib.util.spec_from_file_location('family_persistence_comparisons',
                owner / 'Tests/Production/RemainingStockPersistence/audit.py')
            comparator = importlib.util.module_from_spec(spec); spec.loader.exec_module(comparator)
            config = reader.native.settings(reader.protocols.V2)
            if 'audit_frame_comparator' in plan:
                from ssim_kernel import bind
                descriptor=plan['audit_frame_comparator']
                function,kernel=bind(descriptor['verification'],descriptor['verification_sha256'],reader.windows.image_ssim)
                reader.windows.image_ssim=reader.native.shared.image_ssim=function
        require(owner == owning_root, 'Mixed persistence owning checkouts')
        for profile in expected['profiles']:
            for phase in PHASES:
                key = profile + '/' + phase; stage = status['stages'][key]; capture = Path(stage['output'])
                reused = request.get('reuse', {}).get(key)
                require(status['status']!='audited-reusable-captures-only' or reused,
                        'Reuse-only coordinator contains a newly collected stage')
                if reused:
                    require(stage['status'] == 'reused-after-independent-audit' and
                            capture == Path(reused['path']) and sha(capture / 'capture.json') == reused['capture_sha256'],
                            'Retained persistence capture binding differs')
                else:
                    process = stage['process']; actual = [r for r in process['owned_process_identities']
                        if r['pid'] == process['actual_collector_pid']]
                    require(stage['status'] == 'collected-compared-and-independently-audited' and
                            process['terminal'] is True and process['cancelled'] is False and
                            process['actual_returncode'] == 0 and len(actual) == 1 and
                            actual[0]['start_ticks'] > 0 and actual[0]['argv'] == stage['argv'],
                            'Actual persistence collector PID/start/argv/exit receipt differs')
                recorded = load(capture / 'capture.json'); scope.inspect_terminal(recorded, profile, phase)
                require(recorded['producer_commit'] == (reused['collector_commit'] if reused else request['collector_commit']) and
                        recorded['runtime_source_commit'] == request['runtime_commit'],
                        'Persistence capture producer or runtime differs')
                checked = inspect_native(capture, owner, reader, profile, phase, scope.selection)
                require(checked == stage['audit'], 'Closed persistence independent audit differs')
                comparisons = {}
                for name in scope.cases:
                    comparisons[name] = {}
                    for repeat in (1, 2):
                        folder = name + '-' + str(repeat); windows = request['windows'][profile]
                        reference = Path(windows['writer' if phase == 'stock-writer' else 'reload']) / folder
                        if phase == 'windows-save-reload':
                            native_input = load(capture / folder / 'persistence-input.json')
                            windows_input = load(reference / 'persistence-input.json')
                            saved = Path(windows['windows-parent-capture']) / folder / 'Scenarios/(Current state).scn'
                            require(native_input['saved_input_sha256'] == windows_input['saved_input_sha256'] == sha(saved),
                                    'Paired persistence reloads did not consume the same exact Windows save')
                        parent = load(reference.parent / 'capture.json')['cases'][name]['runs'][repeat - 1]
                        require(all(sha(reference / filename) == checksum for filename, checksum in parent['files_sha256'].items()),
                                'Original Windows persistence observation changed')
                        comparisons[name][str(repeat)] = comparator.compare_pair(reference, capture / folder, reader, config)
                require(comparisons == stage['comparisons'], 'Recomputed persistence comparisons differ')
                stages.append(dict(capture=str(capture), audit=checked, comparisons=comparisons))
        require(sha(status_path) == status_sha, 'Persistence coordinator changed during audit')
        coordinators.append(dict(status=str(status_path), sha256=status_sha, request_sha256=declared[str(request_path)]))
    cells, processes = persistence_coverage(stages, expected['profiles'], names)
    require(processes == plan['required_runs'], 'Incomplete persistence process matrix')
    return dict(status='audited-all-family-writer-and-exact-Windows-save-reload-persistence-only',
        profiles={profile:{phase:cells[(profile,phase)] for phase in PHASES} for profile in expected['profiles']},
        coordinators=coordinators, stages=stages, actual_processes=processes,
        successful_presents=processes * 960, passed_facet='persistence',
        auditor_source_sha256=sha(Path(__file__)), execution_plan_sha256=sha(plan_path),
        frame_comparator=locals().get('kernel'),
        scope='Selected complete original scenes, full serialized content and matching exact Windows-save reloads. '
              'No full38, actual operator save/F5 workflow, interaction, normal admission or final-candidate credit. '
              'Historical missing launch receipts remain missing.',
        diagnostic_only=True, native_admission_qualified=False, phase6_complete=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    kind=parser.add_mutually_exclusive_group(required=True)
    kind.add_argument('--paused-capture', type=Path)
    kind.add_argument('--family-manifest',type=Path)
    kind.add_argument('--capability-manifest',type=Path)
    kind.add_argument('--persistence-manifest',type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), 'Fresh independent class-evidence audit required')
    result=inspect_paused(args.paused_capture) if args.paused_capture else \
        inspect_family_lifetimes(args.family_manifest) if args.family_manifest else \
        inspect_capability_matrix(args.capability_manifest) if args.capability_manifest else inspect_persistence_matrix(args.persistence_manifest)
    atomic_json(args.output,result)
