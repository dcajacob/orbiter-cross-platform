#!/usr/bin/env python3
"""Prepare an isolated source snapshot, passive observer and actual-CRT diagnostic locally."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import traceback
import zipfile


def require(value,message):
    if not value:raise ValueError(message)


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    request=Path(sys.argv[1]);cfg=json.loads(request.read_text());work=Path(cfg['work'])
    require(sys.platform=='win32' and not work.exists(),'Native Windows and fresh preparation directory required')
    work.mkdir(parents=True);status=request.with_name(cfg['name']+'-status.json')
    report=dict(status='preparing',request_sha256=sha(request),worker_sha256=sha(__file__),
                commands=[],raw_evidence_uploaded=False,phase6_complete=False)
    def save():
        temporary=status.with_suffix('.tmp');temporary.write_text(json.dumps(report,indent=2)+'\n');temporary.replace(status)
        (work/'observer-build.json').write_text(json.dumps(report,indent=2)+'\n')
    def run(label,argv,cwd,env=None):
        record=dict(label=label,argv=list(map(str,argv)),cwd=str(cwd));report['commands'].append(record);save()
        with (work/(label+'.log')).open('w') as log:
            process=subprocess.Popen(record['argv'],cwd=cwd,env=env,stdout=log,stderr=subprocess.STDOUT)
            record['actual_pid']=process.pid;save();record['actual_returncode']=process.wait()
        record['log_sha256']=sha(work/(label+'.log'));save()
        require(record['actual_returncode']==0,'Preparation command failed: '+label)
    try:
        git=cfg['git']
        snapshot=cfg.get('source_snapshot')
        if snapshot:
            archive=Path(snapshot['archive']);manifest=Path(snapshot['manifest'])
            require(sha(archive)==snapshot['archive_sha256'] and sha(manifest)==snapshot['manifest_sha256'],'Sealed source snapshot differs')
            sealed=json.loads(manifest.read_text());require(sealed['commit']==cfg['source_commit'],'Snapshot source identity differs')
            source=work/'source';source.mkdir()
            with zipfile.ZipFile(archive) as z:
                require(len(z.namelist())==len(set(z.namelist())) and set(z.namelist())==set(sealed['files_sha256']),'Snapshot file closure differs')
                for name,digest in sealed['files_sha256'].items():
                    parts=Path(name).parts;require(not Path(name).is_absolute() and '..' not in parts and ':' not in name and '\\' not in name,'Unsafe snapshot path')
                    target=source/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(z.read(name))
                    require(sha(target)==digest,'Snapshot source file differs')
            report['source_snapshot']=sealed
        elif cfg.get('prepared_source'):
            source=Path(cfg['prepared_source']);require(source.is_dir(),'Declared prepared source missing')
            report['reused_prepared_source']=str(source)
        else:
            require(sha(cfg['bundle'])==cfg['bundle_sha256'],'Exact source bundle required')
            source=work/'source'
            run('clone',[git,'clone','--shared','--no-checkout',cfg['seed'],source],work)
            run('line-endings',[git,'-C',source,'config','core.autocrlf','false'],work)
            run('fetch',[git,'-C',source,'fetch',cfg['bundle'],'refs/heads/codex/phase6-closeout:refs/heads/source-snapshot'],work)
            run('checkout',[git,'-C',source,'checkout','--detach',cfg['source_commit']],work)
        if not snapshot:
            require(subprocess.check_output([git,'-C',source,'rev-parse','HEAD'],text=True).strip()==cfg['source_commit'],
                    'Actual isolated source snapshot differs')
        environment={k.upper():v for k,v in os.environ.items()}
        raw=subprocess.check_output([str(Path(environment['SYSTEMROOT'])/'System32/cmd.exe'),
            '/d','/c',cfg['compiler_environment']],env=environment,text=True)
        for line in raw.splitlines():
            key,separator,value=line.partition('=')
            if separator and key:environment[key.upper()]=value
        environment['PATH']=str(Path(git).parent)+';'+str(Path(sys.executable).parent)+';'+environment['PATH']
        environment['PYTHONDONTWRITEBYTECODE']='1'
        report['compiler_environment_script_sha256']=sha(cfg['compiler_environment'])
        sdk=Path(cfg['preserved']);manifest=sdk/'test-runtime.json';package=json.loads(manifest.read_text())
        sdk_source=cfg.get('sdk_source_commit','f725194209634f7fd5d1d44d426cfa9b5e303e37')
        require(re.fullmatch('[0-9a-f]{40}',sdk_source) and package['source_commit']==sdk_source,
                'Declared actual SDK source differs')
        guarded={n:v for n,v in package['files'].items() if n.startswith('Orbitersdk/') or n=='Orbiter.exe'}
        require(all(sha(sdk/n)==v for n,v in guarded.items()),'Actual original application/SDK bytes differ')
        report['sdk']=dict(source=package['source_commit'],manifest_sha256=sha(manifest),files_sha256=guarded)
        kind=cfg.get('observer_kind','reload-math')
        require(kind in ('reload-math','general-api','remaining-stock'),'Known test observer required')
        configuration=cfg.get('configuration','Debug');require(configuration in ('Debug','Release'),'Known configuration required')
        relative='Tests/Production/'+{'reload-math':'ReloadMath/Observer.cpp','general-api':'GeneralApiCorrection/Observer.cpp',
                                     'remaining-stock':'RemainingStock/Driver.cpp'}[kind]
        binary=work/{'reload-math':'ProductionReloadMathObserver.dll','general-api':'ProductionGeneralApiObserver.dll',
                     'remaining-stock':'ProductionCockpitDriver.dll'}[kind];obj=work/'Observer.obj'
        compiled=source/relative
        if kind=='remaining-stock':
            body=compiled.read_bytes().replace(b'\r\n',b'\n')
            old=b'require(frames==60,"Incomplete original stock observation")'
            require(body.count(old)==1,'Original stock observer frame assertion differs')
            compiled=compiled.with_name('Driver-960.cpp')
            delay=cfg.get('observer_delay_ms',120)
            require(type(delay) is int and delay in (0,120) and body.count(b'Sleep(120);')==1,
                    'Explicit original observer pacing required')
            changed=body.replace(old,b'require(frames==960,"Incomplete repaired stock observation")')
            if delay==0:changed=changed.replace(b'Sleep(120);',b'Sleep(0);')
            compiled.write_bytes(changed)
            report['observer_source_variant']=dict(original_sha256=sha(source/relative),compiled_sha256=sha(compiled),
                observer_delay_ms=delay,
                only_change='Validate 960 finalized ticks instead of 60; explicitly declared observer pacing; observation calls unchanged')
        compiler=shutil.which('cl.exe',path=environment['PATH']);require(compiler,'Actual MSVC compiler missing from validated environment')
        report['compiler']=dict(path=compiler,sha256=sha(compiler))
        command=[compiler,'/nologo','/EHsc','/std:c++17','/W3','/fp:precise','/Oi-',
            '/MDd' if configuration=='Debug' else '/MD','/Od' if configuration=='Debug' else '/O2','/LD',
            '/DNOMINMAX','/I'+str(sdk/'Orbitersdk/include'),str(compiled),
            '/Fo'+str(obj),'/Fe'+str(binary),'/link',str(sdk/'Orbitersdk/lib/Orbiter.lib'),str(sdk/'Orbitersdk/lib/Orbitersdk.lib')]
        if cfg.get('internal_headers'):
            last=cfg.get('internal_last_tick',243)
            require(type(last) is int and 1<=last<=960,'Explicit bounded internal observation interval required')
            command[1:1]=['/DORBITER_RELOAD_INTERNAL_OBSERVATION','/I'+str(source/'internal/Src/Orbiter'),
                           '/I'+str(Path(cfg['directx_sdk'])/'Include'),'/DORBITER_RELOAD_INTERNAL_LAST_TICK='+str(last)]
            report['internal_observation_ticks']=[1,last]
        if kind=='remaining-stock':command[1:1]=['/I'+str(source/'Tests/Production')]
        run('observer-build',command,work,environment)
        report['observer']=dict(binary=str(binary),sha256=sha(binary),configuration=configuration,kind=kind,
            sdk_source_commit=sdk_source,source_commit=cfg['source_commit'],source_sha256=sha(source/relative),
            header_sha256=sha(source/'Src/Orbiter/Production/MathObservation.h') if kind=='reload-math' else None)
        if cfg.get('run_crt',True):
            run('crt',[sys.executable,'-B',source/'Tests/Production/CrtDiagnostic/capture.py',
                       '--inputs',cfg['inputs'],'--output',work/'crt'],source,environment)
        require(all(sha(sdk/n)==v for n,v in guarded.items()),'Preserved SDK changed during diagnostic preparation')
        report.update(status='prepared-passive-observer-and-observed-actual-CRT' if cfg.get('run_crt',True) else 'prepared-passive-observer-only',source=str(source),
                      source_commit=cfg['source_commit'],crt_report_sha256=sha(work/'crt/report.json') if cfg.get('run_crt',True) else None,
                      free_bytes=shutil.disk_usage(work).free)
    except BaseException as error:
        report.update(status='failed',error=str(error),traceback=traceback.format_exc());raise
    finally:
        save()
        for path in work.glob('*.log'):shutil.copy2(path,request.parent/path.name)
        crt=work/'crt'
        if crt.is_dir():
            target=request.parent/'crt';target.mkdir(exist_ok=True)
            for path in crt.iterdir():
                if path.is_file() and path.suffix not in ('.exe','.obj'):shutil.copy2(path,target/path.name)
        for name in ('ProductionReloadMathObserver.dll','ProductionGeneralApiObserver.dll','ProductionCockpitDriver.dll'):
            if (work/name).is_file():shutil.copy2(work/name,request.parent/name)


if __name__=='__main__':main()
