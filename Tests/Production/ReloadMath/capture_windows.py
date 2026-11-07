#!/usr/bin/env python3
"""Capture one exact original-Windows save with the passive observer off and on."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import traceback
from win_local_process_v1 import context
from runtime_descriptor_v2 import preflight, sha, require
from static_binary_link_staging_v2 import BinaryLinks,PROTOCOL as STAGING_PROTOCOL


def load(path):return json.loads(Path(path).read_text())


def main():
    request=Path(sys.argv[1]);cfg=load(request);share=request.parent;output=Path(cfg['output']);source=Path(cfg['source'])
    report=dict(status='running',source=cfg['source_commit'],roles=cfg['roles'],context=context(),
        transport_protocol=cfg['transport_protocol'],configuration=cfg['configuration'],math_profile=cfg['math_profile'],
        request_sha256=sha(request),script_sha256=sha(__file__),captures={},cloud_builds_used=False,
        native_admission_qualified=False,phase6_complete=False,diagnostic_only=True)
    status=share/'worker-result.json';links=None
    def save():
        temp=status.with_suffix('.tmp');temp.write_text(json.dumps(report,indent=2)+'\n');temp.replace(status)
    try:
        require(report['context']==dict(session=cfg['active_session'],window_station='WinSta0',desktop=cfg['desktop']),
                'Actual private desktop context differs')
        report['root_preflight']=preflight(cfg)
        selection=cfg['capture_scope']
        require(selection['kind']=='diagnostic' and len(selection['cases'])==1,'One explicit exact-save diagnostic case required')
        require(cfg['staging_protocol']==STAGING_PROTOCOL and
                sha(Path(__file__).with_name('static_binary_link_staging_v2.py'))==cfg['staging_script_sha256'],
                'Explicit validated local staging adapter required')
        os.environ['PATH']=str(Path(cfg['git']).parent)+';'+os.environ['PATH']
        os.environ.update(PYTHONDONTWRITEBYTECODE='1',LIBGL_ALWAYS_SOFTWARE='true',GALLIUM_DRIVER='llvmpipe')
        require(cfg['configuration'] in ('Debug','Release') and cfg['math_profile'] in ('automatic','sse2'),'Explicit diagnostic build/math profile required')
        if cfg['math_profile']=='sse2':os.environ['ORBITER_TEST_OBSERVER_SSE2']='1'
        else:os.environ.pop('ORBITER_TEST_OBSERVER_SSE2',None)
        os.environ['ORBITER_PHASE6_MATH_VESSEL']=cfg.get('math_vessel','Atlantis')
        require(subprocess.check_output([cfg['git'],'-C',source,'rev-parse','HEAD'],text=True).strip()==cfg['source_commit'],
                'Original owning capture producer differs')
        sys.path[:0]=[str(source/'Tests/Production/RemainingStockRepaired'),str(source/'Tests/Production/RemainingStockPersistence')]
        import capture as original
        import protocols
        from saved_inputs import derived_case
        spec=importlib.util.spec_from_file_location('reload_math_original_auditor',source/'Tests/Production/RemainingStockRepaired/audit.py')
        auditor=importlib.util.module_from_spec(spec);spec.loader.exec_module(auditor)
        config=original.settings(protocols.V2);case=next(c for c in config['cases'] if c['id']==selection['cases'][0])
        require(os.environ['ORBITER_PHASE6_MATH_VESSEL'] in case['declared_vessels'],'Diagnostic math target is not an original vessel')
        build=Path(cfg['build']);built,runtime_identity=auditor.runtime_variant(build,cfg['source_commit'],cfg['configuration'],Path(cfg['preserved']),protocols.V2)
        require(sha(build/'build.json')==cfg['roles']['observer']['manifest_sha256'],'Original observer build role differs')
        observer=Path(cfg['diagnostic_observer']['path']);require(sha(observer)==cfg['diagnostic_observer']['sha256'],'Passive observer binary differs')
        pacing=cfg.get('primary_observer_pacing_control',False)
        require(type(pacing) is bool,'Explicit observer diagnostic mode required')
        if pacing:
            preparation=Path(cfg['diagnostic_observer']['preparation_manifest'])
            prepared=load(preparation)
            require(sha(preparation)==cfg['diagnostic_observer']['preparation_sha256'] and
                    prepared['observer']['kind']=='remaining-stock' and
                    prepared['observer']['sha256']==sha(observer) and
                    prepared['observer_source_variant']['observer_delay_ms']==0,
                    'Compiled zero-delay primary observer identity required')
            report['primary_observer_pacing_control']=True
        guarded={str(build/'runtime'/n):v for n,v in built['runtime_files_sha256'].items()}
        if pacing:guarded[str(observer)]=sha(observer)
        mesa=Path(cfg['mesa']);provider=load(mesa/'mesa-runtime.json')
        guarded.update({str(mesa/n):v['sha256'] for n,v in provider['files'].items()})
        for lock,root in [('stock-data.lock.json',Path(cfg['data'])),('standard-planets.lock.json',Path(cfg['planets']))]:
            for relative,value in load(source/'Tests/Production'/lock)['data_files'].items():
                path=root/relative
                if path.is_file():
                    require(path.stat().st_size==value['bytes'] and sha(path)==value['sha256'],'Actual guarded simulation data differs')
                    guarded[str(path)]=value['sha256']
        output.mkdir();links=BinaryLinks(guarded,output);report['staging_controls']=links.controls(mesa);links.install()
        report['primary_runtime_identity']=runtime_identity;report['diagnostic_observer']=cfg['diagnostic_observer'];save()
        saved=Path(cfg['saved_input']['path']);require(sha(saved)==cfg['saved_input']['sha256'],'Exact Windows input bytes differ')
        derived,provenance=derived_case(case,config,saved,sha(saved))
        base_variant=dict(protocol=config['protocol'],protocol_sha256_lf=original.sha_lf(protocols.path(protocols.V2)),
            original_application_and_sdk_source=config['application_source'],producer_commit=cfg['source_commit'],
            runtime_variant_manifest_sha256=sha(build/'runtime/runtime-variant.json'),frames=config['frames'],
            fixed_step=config['fixed_step'],capture_tick=config['capture_tick'],diagnostic_only=True,cases_requested=[case['id']])
        folders={}
        for mode in ('off','on'):
            reuse=cfg.get('reuse_off') if mode=='off' else None
            if reuse:
                prior=Path(reuse['report']);require(sha(prior)==reuse['report_sha256'],'Closed off-capture report changed')
                previous=load(prior);folder=Path(reuse['folder'])
                require(previous['status']=='captured-identical-observer-off-on-diagnostic-only' and
                        previous['saved_input_sha256']==sha(saved) and
                        previous['primary_runtime_identity']==runtime_identity and
                        previous['captures']['off']['folder']==str(folder),'Reusable off-capture identity/scope differs')
                require(all(sha(folder/n)==v for n,v in previous['observer_on_off_sha256'].items()),'Closed off-capture bytes changed')
                actual=original.inspect_artifacts(folder,derived,config)
                require(actual==previous['captures']['off']['canonical_primary_audit'] and
                        load(folder/'process-timing.json')==previous['captures']['off']['process'], 'Recomputed closed off-capture differs')
                folders[mode]=folder
                report['captures'][mode]=dict(previous['captures']['off'],reused_report_sha256=sha(prior))
                save();continue
            folder=output/('observer-'+mode);folders[mode]=folder
            def configure(directory):
                path=directory/'Orbiter.cfg';text=path.read_text()
                for line in ('PropStages = 1\n','PropStage0 = 1 1 1\n','PropSubsampling = 1\n'):
                    require(text.count(line)==1,'Original propagator fixture differs');text=text.replace(line,'')
                text=text.replace('  ProductionBehaviorDriver','  ProductionCockpitDriver\n  OGLClient')
                if mode=='on':
                    if pacing:
                        replacement=directory/'Modules/Plugin/ProductionCockpitDriver.dll'
                        replacement.unlink();shutil.copy2(observer,replacement)
                    else:
                        text=text.replace('END_MODULES','  ProductionReloadMathObserver\nEND_MODULES')
                        shutil.copy2(observer,directory/'Modules/Plugin/ProductionReloadMathObserver.dll')
                path.unlink();path.write_text(text+'\nFPS = 0\nMenubarMode = 1\nInfobarMode = 1\nInstrumentUpdateInterval = 0.25\n')
                target=directory/derived['scenario_entry_point'];target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(saved.read_bytes())
                (directory/'persistence-input.json').write_text(json.dumps(provenance,indent=2)+'\n')
                variant=dict(base_variant)
                if pacing:variant['primary_observer_pacing_variant']=dict(delay_ms=0 if mode=='on' else 120,
                    replacement_sha256=sha(observer) if mode=='on' else None,
                    preparation_manifest_sha256=cfg['diagnostic_observer']['preparation_sha256'])
                (directory/'reference-variant.json').write_text(json.dumps(variant,indent=2)+'\n')
                (directory/protocols.MARKER).write_bytes(protocols.marker_bytes(config));(directory/'ogl-evidence.enabled').touch()
                original.mesa_files(mesa,directory)
            original.stage(build/'runtime/Orbiter.exe',Path(cfg['data']),Path(cfg['planets']),folder,config,derived,configure,process_timeout=900)
            actual_data=original.data_inputs.inspect(folder,folder)
            (folder/'actual-data-inputs.json').write_text(json.dumps(actual_data,indent=2)+'\n')
            expected=dict(built['runtime_files_sha256'])
            if pacing and mode=='on':expected['Modules/Plugin/ProductionCockpitDriver.dll']=sha(observer)
            require(all(sha(folder/n)==v for n,v in expected.items() if n.lower().endswith(('.dll','.exe'))),
                    'Original runtime was altered by diagnostic staging')
            life=load(folder/'graphics-lifecycle.json')
            require(life==dict(rendered_frames=960,successful_presents=960,context_deleted=True),'Complete real graphics lifetime required')
            require((folder/'stock-vessel-complete.txt').read_text().strip()=='960','Complete actual finalized boundaries required')
            text=(folder/'console.txt').read_text(errors='replace')+(folder/'Orbiter.log').read_text(errors='replace')
            require(not any(s in text for s in ('LuaCall (','Lua error:','Assertion failed','Could not find a module','runtime error:')),'Runtime diagnostic in capture')
            require((folder/'math-profile.txt').read_text().strip()==('sse2' if cfg['math_profile']=='sse2' else 'fma3'),'Actual diagnostic CRT math path differs')
            primary=None
            if mode=='off' or pacing:primary=original.inspect_artifacts(folder,derived,config)
            else:require((folder/'reload-math.csv').is_file(),'Actual passive observation missing')
            report['captures'][mode]=dict(folder=str(folder),process=load(folder/'process-timing.json'),graphics=life,
                canonical_primary_audit=primary,staged_input_sha256=sha(folder/derived['scenario_entry_point']))
            save()
        # Trust the extra observer only after exact on/off equality over all
        # original physical/resource/event, clocks, camera, saved and frame bytes.
        names=[*original.shared.TRACES,'stock-clock.csv','stock-step-clock.csv','camera.csv','scene.rgba','Scenarios/(Current state).scn']
        unchanged={name:sha(folders['off']/name) for name in names}
        require(all(sha(folders['on']/n)==v for n,v in unchanged.items()),'Passive observer changed original simulation/camera/save/frame results')
        require(all(sha(Path(n))==v for n,v in guarded.items()),'Original runtime/provider changed')
        report.update(status='captured-identical-primary-observer-pacing-diagnostic-only' if pacing else
            'captured-identical-observer-off-on-diagnostic-only',observer_on_off_sha256=unchanged,
            passive_observer_equivalence=not pacing,primary_observer_pacing_equivalence=pacing,
            guarded_runtime_files=len(guarded),saved_input_sha256=sha(saved))
        # Export raw observations, complete invocations and actual receipts only;
        # immutable original runtime/data caches remain in C:.
        export=Path(cfg['export']);export.mkdir()
        folders={}
        for mode in ('off','on'):
            reuse=cfg.get('reuse_off') if mode=='off' else None
            if reuse:
                prior=Path(reuse['report']);require(sha(prior)==reuse['report_sha256'],'Closed off-capture report changed')
                previous=load(prior);folder=Path(reuse['folder'])
                require(previous['status']=='captured-identical-observer-off-on-diagnostic-only' and
                        previous['saved_input_sha256']==sha(saved) and
                        previous['primary_runtime_identity']==runtime_identity and
                        previous['captures']['off']['folder']==str(folder),'Reusable off-capture identity/scope differs')
                require(all(sha(folder/n)==v for n,v in previous['observer_on_off_sha256'].items()),'Closed off-capture bytes changed')
                actual=original.inspect_artifacts(folder,derived,config)
                require(actual==previous['captures']['off']['canonical_primary_audit'] and
                        load(folder/'process-timing.json')==previous['captures']['off']['process'], 'Recomputed closed off-capture differs')
                folders[mode]=folder
                report['captures'][mode]=dict(previous['captures']['off'],reused_report_sha256=sha(prior))
                save();continue
            folder=output/('observer-'+mode);folders[mode]=folder;target=export/folder.name;target.mkdir()
            paths={p.relative_to(folder).as_posix() for p in folder.iterdir() if p.is_file() and p.suffix.lower() not in ('.exe','.dll')}
            paths|={p.relative_to(folder).as_posix() for p in (folder/'Scenarios').rglob('*') if p.is_file()}
            for name in paths:
                destination=target/name;destination.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(folder/name,destination)
        report['export_files_sha256']={p.relative_to(export).as_posix():sha(p) for p in export.rglob('*') if p.is_file()}
    except BaseException as error:
        report.update(status='failed',error=str(error),traceback=traceback.format_exc());raise
    finally:
        if links:
            links.close();report['staging_receipt']=links.receipt()
        save()


if __name__=='__main__':main()
