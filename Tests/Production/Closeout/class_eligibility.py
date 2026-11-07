"""Independently inspect scoped class evidence; partial facets never admit a class."""
import argparse
import csv
import math
from pathlib import Path
import sys

from contracts import atomic_json, load, require, sha
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
        capture=Path(work['captures'][profile]);checked=audit(capture)
        require(checked['runtime_identity']['profile']==profile and checked['repeats']==2 and
                list(checked['cases'])==work['expected_cases'],'Capability profile/case/repetition incomplete')
        observed=set()
        for runs in checked['cases'].values():
            for run in runs:
                for row in run['actual_capabilities'].values():
                    if row['class'] in expected['families']:
                        observed.add((row['class'],*(float(row[k]) for k in fields)))
        require(observed==signatures,'Native capability selection misses an original structural combination')
        sources.add(checked['runtime_identity']['runtime_source_commit']);processes+=checked['actual_processes']
        results[profile]=dict(capture=str(capture),audit=checked)
    require(len(sources)==1 and processes==work['expected_processes'],'Mixed or incomplete capability runtime cohort')
    return dict(status='audited-all-family-capability-variants-and-passive-observer-controls-only',
        profiles=results,families=expected['families'],structural_signatures=len(signatures),
        actual_processes=processes,successful_presents=processes*60,passed_facet='capabilities',
        inventory_sha256=sha(inventory_path),auditor_source_sha256=sha(Path(__file__)),
        scope='Every original stock initial structural combination is covered in native SDK snapshots, '
              'four profiles and two observer-off/on repetitions. Sixty-frame diagnostics do not '
              'qualify complete stock parity, interactions, persistence, rejection or normal admission.',
        diagnostic_only=True,native_admission_qualified=False,phase6_complete=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    kind=parser.add_mutually_exclusive_group(required=True)
    kind.add_argument('--paused-capture', type=Path)
    kind.add_argument('--family-manifest',type=Path)
    kind.add_argument('--capability-manifest',type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), 'Fresh independent class-evidence audit required')
    result=inspect_paused(args.paused_capture) if args.paused_capture else \
        inspect_family_lifetimes(args.family_manifest) if args.family_manifest else inspect_capability_matrix(args.capability_manifest)
    atomic_json(args.output,result)
