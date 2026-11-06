#!/usr/bin/env python3
"""Prepare an isolated source snapshot, passive observer and actual-CRT diagnostic locally."""
import datetime
import hashlib
import json
import os
from pathlib import Path
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
        require(package['source_commit']=='f725194209634f7fd5d1d44d426cfa9b5e303e37','Preserved original SDK required')
        guarded={n:v for n,v in package['files'].items() if n.startswith('Orbitersdk/') or n=='Orbiter.exe'}
        require(all(sha(sdk/n)==v for n,v in guarded.items()),'Actual original application/SDK bytes differ')
        report['sdk']=dict(source=package['source_commit'],manifest_sha256=sha(manifest),files_sha256=guarded)
        binary=work/'ProductionReloadMathObserver.dll';obj=work/'Observer.obj'
        compiler=shutil.which('cl.exe',path=environment['PATH']);require(compiler,'Actual MSVC compiler missing from validated environment')
        report['compiler']=dict(path=compiler,sha256=sha(compiler))
        command=[compiler,'/nologo','/EHsc','/std:c++17','/W3','/fp:precise','/Oi-','/MDd','/Od','/LD',
            '/DNOMINMAX','/I'+str(sdk/'Orbitersdk/include'),str(source/'Tests/Production/ReloadMath/Observer.cpp'),
            '/Fo'+str(obj),'/Fe'+str(binary),'/link',str(sdk/'Orbitersdk/lib/Orbiter.lib'),str(sdk/'Orbitersdk/lib/Orbitersdk.lib')]
        run('observer-build',command,work,environment)
        report['observer']=dict(binary=str(binary),sha256=sha(binary),configuration='Debug',
            source_commit=cfg['source_commit'],source_sha256=sha(source/'Tests/Production/ReloadMath/Observer.cpp'),
            header_sha256=sha(source/'Src/Orbiter/Production/MathObservation.h'))
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
        if (work/'ProductionReloadMathObserver.dll').is_file():shutil.copy2(work/'ProductionReloadMathObserver.dll',request.parent/'ProductionReloadMathObserver.dll')


if __name__=='__main__':main()
