#!/usr/bin/env python3
"""Audit all complete Windows/native persistence phases in all four profiles."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from observations import bind_owner,inspect_native,require,sha,git,check_files
import transport

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
PROFILES={c+'-'+m for c in ('Debug','Release') for m in ('automatic','sse2')}
CURRENT='Scenarios/(Current state).scn'


def profile_paths(values):
    result={}
    for value in values:
        profile,separator,path=value.partition('=')
        require(separator and profile in PROFILES and profile not in result and path,'Unique PROFILE=PATH entries required')
        result[profile]=Path(path).resolve()
    require(set(result)==PROFILES,'Exactly Debug/Release automatic/SSE2 profiles required; subsets cannot qualify')
    return result


def observe_files(report,owner):
    hashes=report['source_raw_sha256'];require(hashes,'Actual persistence observer source closure missing')
    tracked=set(subprocess.check_output(['git','-C',str(owner),'ls-tree','-r','--name-only',
        report['producer_commit'],'--','Tests/Production/RemainingStockPersistence'],text=True).splitlines())
    require(tracked<=set(hashes),'Complete immutable Windows persistence observer closure missing')
    for name,value in hashes.items():
        original=git(owner,report['producer_commit'],name).replace(b'\r\n',b'\n')
        allowed={hashlib.sha256(original).hexdigest(),hashlib.sha256(original.replace(b'\n',b'\r\n')).hexdigest()}
        require(value in allowed,'Actual persistence observer source differs from its immutable producer: '+name)


def inspect_windows(decoded,profile,reader,original,mesa,mesa_imports):
    capture=reader.windows;audit=reader.original_audit;config=capture.settings(reader.protocols.V2)
    parent_root=decoded/'remaining-stock-repaired';reload_root=decoded/'remaining-stock-persistence';build_root=decoded/'remaining-stock-repaired-build'
    parent=json.loads((parent_root/'capture.json').read_text());producer=parent['producer_commit']
    require(json.loads((build_root/'module-sources/source-variant.json').read_text())['protocol']=='remaining-stock-repaired-sources-v4',
            'Complete persistence requires fresh Windows gauge-storage source v4')
    stock=audit.audit_profile(decoded,profile,config,producer,original,mesa,mesa_imports)
    build,runtime=audit.runtime_variant(build_root,producer,profile.split('-',1)[0],original,reader.protocols.V2)
    source_control=json.loads((build_root/'source-variant-controls.json').read_text())
    require(source_control['status']=='passed' and source_control['producer_commit']==producer and source_control['owning_sources_unchanged'] and
            len(source_control['controls'])==13 and source_control['test_sha256'] in audit.raw_source_hashes(producer,'Tests/Production/RemainingStockRepaired/SourceVariant.Test.py'),
            'Actual Windows gauge/initialization/source controls incomplete')
    manifest=reload_root/'capture.json';report=json.loads(manifest.read_text());checksum=sha(manifest)
    require(report['status']=='captured-awaiting-independent-persistence-audit' and report['protocol']==reader.protocol()['protocol'] and
            report['host']=='repaired-original-windows' and report['producer_commit']==producer and report['configuration']==profile.split('-',1)[0] and
            report['math_profile']==profile.split('-',1)[1] and report['diagnostic_only'] is False and not report['failures'] and
            report['cases_requested']==[c['id'] for c in config['cases']] and set(report['cases'])==set(parent['cases']) and len(report['cases'])==38 and
            report['parent_capture_sha256']==sha(parent_root/'capture.json') and report['independently_checked_runtime']==runtime and
            report['actual_original_data']==parent['actual_original_simulation_data'] and report['owning_sources_runtime_parent_saved_inputs_and_data_unchanged'] and
            report['native_admission_qualified'] is False and report['phase6_complete'] is False,'Complete matching Windows reload matrix required')
    observe_files(report,reader.ROOT)
    parent_files=transport.parent_guards(decoded,report,parent)
    result={};system={};observed_files={}
    for case in config['cases']:
        recorded=report['cases'][case['id']];require(len(recorded['runs'])==2,'Two actual Windows reload repetitions required')
        runs=[];folders=[]
        for repeat,prior in enumerate(recorded['runs'],1):
            folder=reload_root/(case['id']+'-'+str(repeat));folders.append(folder)
            saved=parent_root/(case['id']+'-'+str(repeat))/CURRENT;derived,provenance=reader.derived_case(case,config,saved,sha(saved))
            require(prior['derived_case']==derived and all(prior['persistence_input'][k]==v for k,v in provenance.items()) and
                    prior['persistence_input']['parent_run']==case['id']+'-'+str(repeat) and
                    prior['persistence_input']['parent_capture_sha256']==sha(parent_root/'capture.json'),
                    'Windows reload discarded or substituted an exact saved input')
            check_files(folder,prior['files_sha256'])
            observed_files.update({str(folder/n):v for n,v in prior['files_sha256'].items()})
            actual=capture.inspect_artifacts(folder,derived,config)
            require(all(prior[k]==v for k,v in actual.items()) and 'configuration_input' in actual,'Actual complete Windows reload observation differs')
            require(sha(folder/derived['scenario_entry_point'])==sha(saved),'Executed Windows reload input changed')
            invocation=json.loads((folder/'invocation.json').read_text())
            require(invocation['case']==derived and json.loads((folder/'persistence-input.json').read_text())==prior['persistence_input'],
                    'Executed Windows reload descriptor/provenance differs')
            require(prior['persistence_input']['parent_finalized_clock']==parent['cases'][case['id']]['runs'][repeat-1]['matched_clock_observation'] and
                    prior['persistence_input']['parent_run_files_sha256']==parent['cases'][case['id']]['runs'][repeat-1]['files_sha256'],
                    'Windows reload changed actual parent clock/observation closure')
            providers=audit.loaded_modules(folder,prior['loaded_modules'],build['runtime_files_sha256'],derived,config,mesa,mesa_imports,original)
            for name,value in providers.items():system.setdefault(name,set()).add(value)
            parsed=reader.parse_saved(folder/CURRENT);require(parsed==prior['saved_state'],'Complete Windows reload saved content differs')
            runs.append(dict(directory=str(folder),saved_state=parsed,derived_case=derived,persistence_input=prior['persistence_input'],
                             actual_math=actual['actual_math']))
        for name in (*capture.shared.TRACES,'stock-clock.csv','stock-step-clock.csv','camera.csv'):
            require((folders[0]/name).read_bytes()==(folders[1]/name).read_bytes(),'Windows repeated complete reload trace differs: '+name)
        require(not reader.content_differences(runs[0]['saved_state'],runs[1]['saved_state']),'Windows repeated complete saved content differs')
        similarity=capture.image_ssim((folders[0]/'scene.rgba').read_bytes(),(folders[1]/'scene.rgba').read_bytes(),1280,720)
        require(similarity>=config['image_ssim_minimum'] and similarity==recorded['repeat_ssim'],'Windows repeated reload image budget failed')
        result[case['id']]=dict(runs=runs,repeat_ssim=similarity)
    require(sha(manifest)==checksum and all(sha(decoded/n)==v for n,v in parent_files.items()) and
            all(sha(Path(n))==v for n,v in observed_files.items()),'Owning Windows reload or parent changed during audit')
    return dict(stock=stock,reload=dict(cases=result,capture_sha256=checksum,actual_processes=76),producer_commit=producer,
                system_module_observed_hashes={n:sorted(v) for n,v in system.items()},parent_root=str(parent_root),reload_root=str(reload_root))


def serialization_calibration(parent,reloaded,reader):
    """Measure actual original Windows final-to-reloaded-initial state; invent no budget."""
    left={r['object']:r for r in reader.windows.shared.rows(parent/'stock-vessel-state.csv') if r['tick']=='960'}
    right={r['object']:r for r in reader.windows.shared.rows(reloaded/'stock-vessel-state.csv') if r['tick']=='0'}
    result={}
    for name in sorted(set(left)|set(right)):
        a=left.get(name);b=right.get(name)
        if a is None or b is None:result[name]=dict(parent=a,reloaded=b);continue
        changes={}
        for key in a:
            if key in ('tick','seconds') or a[key]==b.get(key):continue
            x=a[key];y=b.get(key)
            try:changes[key]=dict(parent=x,reloaded=y,delta=float(y)-float(x))
            except (ValueError,TypeError):changes[key]=dict(parent=x,reloaded=y)
        result[name]=changes
    return dict(actual_field_changes=result,scope='Measured original Windows serialization/reinitialization only. No numerical tolerance, source change or continuity waiver inferred; cross-runtime reload comparisons retain original budgets.')


def compare_pair(win,native,reader,config):
    require(all((win/n).read_bytes().replace(b'\r\n',b'\n')==(native/n).read_bytes().replace(b'\r\n',b'\n')
                for n in ('stock-clock.csv','stock-step-clock.csv')),'Actual Windows/native begin/end clocks differ')
    differences=reader.content_differences(reader.parse_saved(win/CURRENT),reader.parse_saved(native/'saved.scn'),reader.protocol()['operator_description_blocks'])
    require(not differences,'Complete Windows/native saved content differs: '+json.dumps(differences[:10]))
    result=dict(state=reader.original_audit.compare_state(win,native,config),camera=reader.original_audit.camera_comparison(win,native,config),
        ssim=reader.windows.image_ssim((win/'scene.rgba').read_bytes(),(native/'scene.rgba').read_bytes(),1280,720),
        complete_saved_content_identical=True,actual_clocks_identical_lf=True,
        detail_calibration_only=reader.original_audit.detail_calibration(win,native))
    require(result['ssim']>=config['image_ssim_minimum'],'Windows/native complete framebuffer exceeds unchanged budget')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('native-owner','preserved-debug','preserved-release','mesa-runtime','download-manifest','archive-root','output'):
        p.add_argument('--'+name,type=lambda v:Path(v).resolve(),required=True)
    for name in ('native-stock','native-reload','windows'):
        p.add_argument('--'+name,action='append',required=True,help='All four unique PROFILE=PATH entries required')
    a=p.parse_args();require(not a.output.exists(),'Fresh persistence audit output required')
    stock=profile_paths(a.native_stock);reload=profile_paths(a.native_reload);windows=profile_paths(a.windows)
    first=json.loads((stock['Debug-automatic']/'capture.json').read_text())
    reader=bind_owner(a.native_owner,first['producer_commit']);config=reader.native.settings(reader.protocols.V2)
    def verifier_inputs():
        paths={Path(__file__).resolve(),HERE/'observations.py',HERE/'transport.py'}
        return dict(owning_readers=reader.original_audit.verifier_inputs(),
                    persistence_readers={str(p):sha(p) for p in sorted(paths)})
    readers=verifier_inputs()
    report=dict(status='failed',protocol=reader.protocol()['protocol'],profiles={},build_pairs={},reader_sha256=readers,
        native_admission_qualified=False,phase6_complete=False,
        scope='Complete all38/two-repeat/four-profile stock-writer and exact-Windows-save reload comparisons. This does not by itself admit classes or complete controls, in-process lifetime, hardware/performance, full157 or Phase6 acceptance.')
    try:
        download_sha=sha(a.download_manifest);downloads=json.loads(a.download_manifest.read_text())
        report['windows_transport']=transport.inspect_matrix(downloads,a.archive_root,windows,downloads['source_commit'])
        report['download_manifest_sha256']=download_sha
        for profile in sorted(PROFILES):
            native_stock=inspect_native(stock[profile],a.native_owner,reader,profile,'stock-writer')
            native_reload=inspect_native(reload[profile],a.native_owner,reader,profile,'windows-save-reload')
            producer=json.loads((windows[profile]/'remaining-stock-repaired/capture.json').read_text())['producer_commit']
            require(producer==downloads['source_commit'],'Actual Windows producer differs from retained artifact transport')
            mesa,mesa_imports=reader.original_audit.independent_mesa(a.mesa_runtime,producer)
            original=a.preserved_debug if profile.startswith('Debug-') else a.preserved_release
            observed=inspect_windows(windows[profile],profile,reader,original,mesa,mesa_imports)
            comparisons={}
            for case in config['cases']:
                cases=[]
                for repeat in (1,2):
                    ws=Path(observed['parent_root'])/(case['id']+'-'+str(repeat));wr=Path(observed['reload_root'])/(case['id']+'-'+str(repeat))
                    ns=stock[profile]/(case['id']+'-'+str(repeat));nr=reload[profile]/(case['id']+'-'+str(repeat))
                    saved=ws/CURRENT
                    native_record=native_reload['cases'][case['id']]['runs'][repeat-1]
                    require(native_record['persistence_input']['saved_input_sha256']==sha(saved)==sha(nr/native_record['executed_case']['scenario_entry_point']),
                            'Native/Windows reloads did not consume the same exact saved file')
                    cases.append(dict(stock_writer=compare_pair(ws,ns,reader,config),reload=compare_pair(wr,nr,reader,config),
                        original_windows_roundtrip=serialization_calibration(ws,wr,reader)))
                comparisons[case['id']]=cases
            report['profiles'][profile]=dict(native_stock=native_stock,native_reload=native_reload,windows=observed,comparisons=comparisons)
            print(profile,'all38 stock writers and exact-save reloads independently compared twice',flush=True)
        require(len(report['profiles'])==4,'Complete four-profile persistence matrix required')
        # Retain the original full Windows candidate's direct Debug/Release
        # comparisons as well as each Windows/native comparison. No transitive
        # comparison or doubled budget substitutes for this original gate.
        for math_profile in ('automatic','sse2'):
            require(report['profiles']['Debug-'+math_profile]['windows']['stock']['actual_math']==
                    report['profiles']['Release-'+math_profile]['windows']['stock']['actual_math'],
                    'Original Debug/Release stock writers selected different CRT implementations')
            pairs={}
            for phase,relative in (('stock-writer','remaining-stock-repaired'),('reload','remaining-stock-persistence')):
                phase_pairs={}
                for case in config['cases']:
                    comparisons=[]
                    for repeat in (1,2):
                        left=windows['Debug-'+math_profile]/relative/(case['id']+'-'+str(repeat))
                        right=windows['Release-'+math_profile]/relative/(case['id']+'-'+str(repeat))
                        similarity=reader.windows.image_ssim((left/'scene.rgba').read_bytes(),(right/'scene.rgba').read_bytes(),1280,720)
                        require(similarity>=config['image_ssim_minimum'],'Original Debug/Release full-frame budget failed')
                        comparisons.append(dict(state=reader.original_audit.compare_state(left,right,config),
                            camera=reader.original_audit.camera_comparison(left,right,config),ssim=similarity,
                            detail_calibration_only=reader.original_audit.detail_calibration(left,right)))
                    phase_pairs[case['id']]=comparisons
                pairs[phase]=phase_pairs
            report['build_pairs'][math_profile]=pairs
        report.update(status='passed-complete-persistence-comparison-candidate',actual_native_processes=608,actual_windows_processes=608,
            actual_native_presentations=608*960,actual_windows_presentations=608*960)
        require(readers==verifier_inputs() and sha(a.download_manifest)==download_sha,'Independent readers or transport manifest changed during full audit')
        for profile,binding in report['windows_transport'].items():
            require(sha(Path(binding['archive']))==binding['archive_sha256'],'Retained Windows ZIP changed during full comparison')
            check_files(windows[profile],binding['decoded_members_sha256'])
    except BaseException as error:report.update(status='failed',error=str(error));raise
    finally:
        a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
