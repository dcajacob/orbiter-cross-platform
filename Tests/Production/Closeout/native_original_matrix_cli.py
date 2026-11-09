#!/usr/bin/env python3
"""Hosted-only all-eight proof closure and direct original/native Debug/Release gates."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import native_original_matrix as matrix
import audit_native_original_cli as native_cli
from contracts import ROOT,PROFILES,PHASES,require,sha,load,atomic_json
from audit_current_shader_phase_cli import independent_reference,compare_reference,scalar_binding

PAIRS={(mode,phase) for mode in ('automatic','sse2') for phase in PHASES}
WORKFLOW='.github/workflows/phase6-native-original-matrix.yml'
BRANCH='qualification/native-original-matrix-audit-v1'
PAIR_STEPS=('Independently restore all actual original reference members and both real attempts',
    'Restore the exact independently proven scalar and all controls',
    'Independently compare all direct native and original Debug Release pairs',
    'Run actions/upload-artifact@v7')


def plan():
    cohorts={}
    for phase,reader in [('stock-writer',matrix.physical.writers),('windows-save-reload',matrix.physical.reloads)]:
        cohorts[phase]=dict(source=reader.SOURCE,pins=reader.PINS,
            branch='qualification/native-runtime-writer-' if phase=='stock-writer' else 'qualification/native-stock-reload-',
            suffix='-v2' if phase=='stock-writer' else '-v3',
            workflow='.github/workflows/phase6-native-runtime-network-writers.yml' if phase=='stock-writer' else '.github/workflows/phase6-native-retry-stock-reloads.yml',
            artifact='normal-native-runtime-stock-writer-' if phase=='stock-writer' else 'retry-native-stock-reload-')
    return dict(physical_source=matrix.SOURCE,physical_run_id=matrix.RUN,physical_jobs={str(j):'Independently compare original native '+p+' '+q for (p,q),j in matrix.JOBS.items()},
        profiles=list(PROFILES),phases=list(PHASES),cohorts=cohorts,qualification_granted=False)


def context():
    require(sys.platform=='linux' and os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('RUNNER_OS')=='Linux' and
        os.environ.get('ImageOS')=='ubuntu24' and os.environ.get('GITHUB_REPOSITORY')=='dcajacob/orbiter-cross-platform' and
        Path(os.environ['GITHUB_WORKSPACE']).resolve()==ROOT,'Standard hosted Ubuntu24 matrix audit only; no local heavy work')
    head=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
    require(head==os.environ['GITHUB_SHA'] and not subprocess.check_output(['git','-C',str(ROOT),'status','--porcelain','--untracked-files=all','--','Tests/Production','.github'],text=True).strip(),
        'Clean actual same-source hosted matrix auditor required')
    for name in ('audit.py','observations.py','capture_native.py'):
        path='Tests/Production/RemainingStockPersistence/'+name
        require((ROOT/path).read_bytes()==subprocess.check_output(['git','-C',str(ROOT),'show',matrix.SOURCE+':'+path]),
            'Original physical/observation/capture reader changed: '+path)
    return head


def phase_proofs(config):
    result=[];guards={}
    for profile in PROFILES:
        for phase in PHASES:
            cell=profile+'-'+phase;base=ROOT/'out/native-matrix-phase-inputs'/cell
            api=base/'api.json';archive=base/'producer.zip';payload=ROOT/'out/native-matrix-phase-payload'/cell
            proof=matrix.inspect_phase(load(api),archive,payload,profile,phase,config)
            result.append(proof);guards.update({str(api):sha(api),str(archive):sha(archive)})
            guards.update({str(payload/name):value for name,value in proof['decoded_members_sha256'].items()})
    return result,matrix.complete_phase_matrix(result,config),guards


def bind_raw(profile,phase,proof,payload=None,decode=True):
    base=ROOT/'out/native-matrix-native-inputs'/(profile+'-'+phase);api_file=base/'api.json';archive=base/'producer.zip';api=load(api_file)
    payload=Path(payload) if payload else ROOT/'out/native-matrix-native-payload'/(profile+'-'+phase)
    if decode:native_cli.decode(api,archive,payload,profile,phase)
    collector=matrix.physical.writers if phase=='stock-writer' else matrix.physical.reloads
    raw=collector.inspect(api,archive,profile);report=proof['report']
    require(raw==report['raw_native_proof'] and api['artifact']['digest']==report['native_API_archive_sha256'],
        'Actual native raw source/member proof must equal its independently audited phase artifact')
    prefix='native-stock-writer' if phase=='stock-writer' else 'native-stock-reload';native=payload/prefix/profile
    require(native.is_dir() and not any(p.is_symlink() for p in native.rglob('*')),'Canonical actual retained native observations required')
    files={p.relative_to(native).as_posix():sha(p) for p in native.rglob('*') if p.is_file()}
    require(files==report['native_decoded_tree_sha256'] and sha(native/'capture.json')==report['independent_native_observations']['capture_sha256'],
        'Every native byte and actual capture must equal its full physical phase proof')
    return native,dict(raw_proof=raw,files_sha256=files,api_sha256=sha(api_file),archive_sha256=sha(archive),payload=str(payload))


def partial_output(output,protocol,head):
    output=Path(output).resolve()
    require(output.is_relative_to(ROOT/'out/native-original-matrix-results') and not output.exists(),
        'Fresh separate hosted matrix partial output required')
    output.parent.mkdir(parents=True,exist_ok=True)
    result=dict(protocol=protocol,status='running',auditor_source=head,cases={},
        current_native_comparisons_pending=True,other_class_lifetime_full157_and_hardware_gates_pending=True,
        qualification_granted=False,phase6_complete=False,native_admission_qualified=False)
    atomic_json(output,result);return result


def direct_pairs(mode,phase,output):
    require((mode,phase) in PAIRS,'Exact complete direct-build phase required');head=context()
    result=partial_output(output,'phase6-direct-native-original-build-phase-v1',head)
    result.update(math_profile=mode,phase=phase,actual_native_build_pairs=0,actual_original_build_pairs=0,required_cases=38,required_repeats=2,required_frames=960)
    def save():atomic_json(output,result)
    save()
    try:
        reader=matrix.physical.persistence.bind_owner(ROOT,matrix.physical.writers.SOURCE if phase=='stock-writer' else matrix.physical.reloads.SOURCE)
        config=reader.native.settings(reader.protocols.V2);proofs,aggregate,guards=phase_proofs(config)
        index={(p['profile'],p['phase']):p for p in proofs}
        reference,reference_files,restored=independent_reference(head);originals=matrix.physical.original_bindings()
        scalar_api=ROOT/'out/native-matrix-scalar/api.json';scalar_archive=ROOT/'out/native-matrix-scalar/producer.zip';original_ssim=reader.windows.image_ssim
        scalar=scalar_binding(scalar_api,scalar_archive,reader,head,original_ssim);reader.native.shared.image_ssim=reader.windows.image_ssim
        source_guards=matrix.physical.guarded_sources(reader)|{str(Path(__file__).resolve()):sha(__file__),str(Path(matrix.__file__).resolve()):sha(matrix.__file__)}
        native={};bindings={};reference_comparisons={}
        for configuration in ('Debug','Release'):
            profile=configuration+'-'+mode;selected=index[(profile,phase)]
            native[profile],bindings[profile]=bind_raw(profile,phase,selected)
            captured=load(ROOT/'out/native-matrix-phase-payload'/(profile+'-'+phase)/'reference-audit-restoration/restoration.json')
            reference_comparisons[profile]=compare_reference(captured,restored)
        left_report=index[('Debug-'+mode,phase)]['report'];right_report=index[('Release-'+mode,phase)]['report']
        require(left_report['independent_original_observations']['stock']['actual_math']==right_report['independent_original_observations']['stock']['actual_math'],
            'Original Debug/Release stock writers selected different CRT implementations')
        result.update(complete_phase_aggregation=aggregate,original_reference=reference,original_api_bindings=originals,
            original_retry_reference_comparisons=reference_comparisons,raw_native_bindings=bindings,actual_scalar_binding=scalar,
            guarded_sources_sha256=source_guards,guarded_phase_and_reference_inputs_sha256=guards|reference_files,
            unchanged_budgets=config['budgets'],unchanged_image_ssim_minimum=config['image_ssim_minimum']);save()
        relative='remaining-stock-repaired' if phase=='stock-writer' else 'remaining-stock-persistence'
        for case in config['cases']:
            runs=[];result['cases'][case['id']]=dict(runs=runs)
            for repeat in (1,2):
                result.update(active_case=case['id'],active_repeat=repeat);save();name=case['id']+'-'+str(repeat)
                actual=[p['independent_native_observations']['cases'][case['id']]['runs'][repeat-1]['actual_math'] for p in (left_report,right_report)]
                require(actual[0]==actual[1],'Native Debug/Release observations selected different actual math implementations')
                observed={}
                runs.append(observed)
                observed['native']=matrix.compare_build_pair(native['Debug-'+mode]/name,native['Release-'+mode]/name,reader,config)
                result['actual_native_build_pairs']+=1;save()
                original_root=ROOT/'out/original-stock-audit/transport'
                observed['original']=matrix.compare_build_pair(original_root/('Debug-'+mode)/relative/name,original_root/('Release-'+mode)/relative/name,reader,config)
                result['actual_original_build_pairs']+=1;save()
        require(len(result['cases'])==38 and result['actual_native_build_pairs']==result['actual_original_build_pairs']==76,
            'Every original and native direct build pair required; no transitive or subset comparison')
        for profile,binding in bindings.items():
            require(bind_raw(profile,phase,index[(profile,phase)],Path(binding['payload']),decode=False)[1]==binding,
                'Native actual raw observations changed during direct build comparison')
        require(matrix.complete_phase_matrix(proofs,config)==aggregate and matrix.physical.original_bindings()==originals and
            independent_reference(head)==(reference,reference_files,restored) and
            scalar_binding(scalar_api,scalar_archive,reader,head,original_ssim)==scalar and
            matrix.physical.guarded_sources(reader)|{str(Path(__file__).resolve()):sha(__file__),str(Path(matrix.__file__).resolve()):sha(matrix.__file__)}==source_guards and
            all(sha(path)==value for path,value in (guards|reference_files|source_guards).items()),
            'Physical phase ZIP/member/reference/source/scalar/raw build comparison inputs changed')
        result.update(status='passed-one-complete-native-original-direct-build-phase-only',full_four_pair_aggregation_pending=True)
    except BaseException as error:result.update(status='failed',error=str(error));raise
    finally:save()
    return result


def pair_api(record,head,run_id,mode,phase):
    require((mode,phase) in PAIRS and record['repository']==dict(owner='dcajacob',repo='orbiter-cross-platform'),'Exact direct pair source API required')
    run=record['run'];artifact=record['artifact'];jobs=record['jobs']
    require(run['id']==run_id and run['head_sha']==head and run['run_attempt']==1 and run['head_branch']==BRANCH and run['path']==WORKFLOW and
        run['repository']['full_name']=='dcajacob/orbiter-cross-platform' and run['repository']['private'] is False,
        'Actual same-run same-source direct pair producer required; overall final job may still be active')
    names={'Direct native original builds '+m+' '+p for m,p in PAIRS};selected=[j for j in jobs if j['name'] in names|{'readiness'}]
    require(len(selected)==5 and {j['name'] for j in selected}==names|{'readiness'} and
        all(j['run_id']==run_id and j['head_sha']==head and j['run_attempt']==1 and j['status']=='completed' and j['conclusion']=='success' and
            'ubuntu-24.04' in j['labels'] and 'self-hosted' not in j['labels'] for j in selected),'All four actual direct-build jobs and readiness must pass')
    for job in selected:
        for name in (('Require every actual original native physical phase before comparison',) if job['name']=='readiness' else PAIR_STEPS):
            steps=[s for s in job['steps'] if s['name']==name]
            require(len(steps)==1 and steps[0]['status']=='completed' and steps[0]['conclusion']=='success','Required actual matrix producer step missing: '+name)
    require(artifact['name']=='native-original-direct-build-'+mode+'-'+phase and artifact['expired'] is False and
        type(artifact['id']) is int and artifact['id']>0 and type(artifact['size_in_bytes']) is int and 0<artifact['size_in_bytes']<4*1024**3 and
        matrix.re.fullmatch('sha256:[0-9a-f]{64}',artifact['digest']) and artifact['workflow_run']['id']==run_id and artifact['workflow_run']['head_sha']==head,
        'Exact same-source successful direct-build artifact required')


def final_matrix(output):
    head=context();result=partial_output(output,'phase6-independent-native-original-matrix-and-builds-v1',head)
    def save():atomic_json(output,result)
    try:
        reader=matrix.physical.persistence.bind_owner(ROOT,matrix.physical.writers.SOURCE);config=reader.native.settings(reader.protocols.V2)
        proofs,aggregate,guards=phase_proofs(config);results={};artifact_ids=set();run_id=int(os.environ['GITHUB_RUN_ID'])
        sources=matrix.physical.guarded_sources(reader)|{str(Path(__file__).resolve()):sha(__file__),str(Path(matrix.__file__).resolve()):sha(matrix.__file__)}
        guards.update(sources);result['guarded_sources_sha256']=sources
        result['complete_phase_aggregation']=aggregate;result['direct_build_phases']=results;save()
        for mode,phase in sorted(PAIRS):
            label=mode+'-'+phase;base=ROOT/'out/native-matrix-pair-inputs'/label;api=load(base/'api.json');pair_api(api,head,run_id,mode,phase)
            artifact=api['artifact'];archive=base/'producer.zip';payload=ROOT/'out/native-matrix-pair-payload'/label
            require(artifact['id'] not in artifact_ids and archive.stat().st_size==artifact['size_in_bytes'] and 'sha256:'+sha(archive)==artifact['digest'],
                'Unique exact actual direct-build API archive bytes required');artifact_ids.add(artifact['id'])
            with matrix.zipfile.ZipFile(archive) as zipped:
                require(matrix.shutil.disk_usage(payload.parent if payload.parent.exists() else ROOT/'out').free>=sum(i.file_size for i in zipped.infolist())+8*1024**3,
                    'Direct build proof decode must retain the unchanged eight-GiB reserve')
            matrix.unpack(archive,payload);members=matrix.physical.original.legacy.inspect_archive(archive,payload,artifact['digest'][7:],artifact['size_in_bytes'])
            path=payload/'native-original-matrix-results'/(label+'.json');record=load(path)
            require(record['protocol']=='phase6-direct-native-original-build-phase-v1' and record['status']=='passed-one-complete-native-original-direct-build-phase-only' and
                record['auditor_source']==head and record['math_profile']==mode and record['phase']==phase and
                record['required_cases']==38 and record['required_repeats']==2 and record['required_frames']==960 and
                record['actual_native_build_pairs']==record['actual_original_build_pairs']==76 and record['complete_phase_aggregation']==aggregate and
                record['unchanged_budgets']==config['budgets'] and record['unchanged_image_ssim_minimum']==config['image_ssim_minimum'] and
                set(record['cases'])=={c['id'] for c in config['cases']} and all(len(v['runs'])==2 and all(set(r)=={'native','original'} for r in v['runs']) for v in record['cases'].values()) and
                all(record[k] is False for k in ('qualification_granted','phase6_complete','native_admission_qualified')) and
                all(record[k] is True for k in ('full_four_pair_aggregation_pending','current_native_comparisons_pending','other_class_lifetime_full157_and_hardware_gates_pending')),
                'Complete independently API-bound direct original and native DebugRelease phase required')
            for case in record['cases'].values():
                for run in case['runs']:
                    for cohort in ('native','original'):
                        pair=run[cohort]
                        require(set(pair)=={'state','camera','ssim','detail_calibration_only'} and
                            type(pair['ssim']) in (int,float) and matrix.math.isfinite(pair['ssim']) and pair['ssim']>=config['image_ssim_minimum'],
                            'Every actual direct build full-frame result must preserve its complete original budget')
            guards.update({str(base/'api.json'):sha(base/'api.json'),str(archive):sha(archive),**{str(payload/n):v for n,v in members.items()}})
            results[label]=dict(artifact_id=artifact['id'],archive_sha256=artifact['digest'],report_sha256=sha(path),actual_native_build_pairs=76,actual_original_build_pairs=76);save()
        require(len(results)==4 and all(sha(p)==v for p,v in guards.items()),'All eight phase and four direct-build archive/member proofs must remain unchanged')
        result.update(status='passed-complete-native-original-physical-matrix-and-direct-build-gates-only',actual_native_processes=608,
            actual_direct_original_native_pairs=608,actual_native_build_pairs=304,actual_original_build_pairs=304,guarded_inputs_sha256=guards)
    except BaseException as error:result.update(status='failed',error=str(error));raise
    finally:save()
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--plan',action='store_true');p.add_argument('--check-readiness',action='store_true')
    p.add_argument('--final',action='store_true');p.add_argument('--math-profile',choices=['automatic','sse2']);p.add_argument('--phase',choices=PHASES)
    args=p.parse_args()
    if args.plan:print(json.dumps(plan()));return
    if args.check_readiness:
        context();records=load(ROOT/'out/native-matrix-readiness.json');require(len(records)==8,'Every actual phase API record required')
        for record in records:matrix.api_identity(record['api'],record['profile'],record['phase'])
        require({(r['profile'],r['phase']) for r in records}==set(matrix.JOBS),'Complete physical phase readiness matrix required')
        print('All eight actual source-bound physical phase jobs and artifacts are ready; no qualification granted');return
    if args.final:result=final_matrix(ROOT/'out/native-original-matrix-results/native-original-matrix.json')
    else:result=direct_pairs(args.math_profile,args.phase,ROOT/'out/native-original-matrix-results'/(str(args.math_profile)+'-'+str(args.phase)+'.json'))
    print(json.dumps({k:result[k] for k in ('status','phase6_complete','native_admission_qualified')}))


if __name__=='__main__':main()
