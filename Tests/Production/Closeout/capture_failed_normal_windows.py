#!/usr/bin/env python3
"""Diagnose the four original failed scenes at the unchanged .25-second clock on current Windows."""
import csv,hashlib,importlib.util,io,json,math,os
from pathlib import Path
import shutil,subprocess,sys,time
from contracts import ROOT,atomic_json,load,require,sha
from rejection_input_bundle import pack

APPLICATION='c08f93151827949ee3ad498f8021f35c11753fde'


def original_configuration():
    # The original collector imports generic module names. Give it its own module namespace.
    program="import pathlib,sys; p=pathlib.Path('Tests/Production/StockScenarios').resolve(); sys.path.insert(0,str(p)); import run as original; assert pathlib.Path(original.__file__).resolve()==p/'run.py'; sys.stdout.write(original.configuration(False))"
    return subprocess.check_output([sys.executable,'-B','-c',program],cwd=ROOT,text=True)


def compiler_batch(vc):
    require(not any(c in str(vc) for c in ('"','\r','\n')),'One actual compiler environment path required')
    return '@call "'+str(vc)+'" -arch=x64 -host_arch=x64 >nul\n@if errorlevel 1 exit /b %errorlevel%\n@set\n'


def read_compiler_environment(cmd,batch,read=subprocess.check_output):
    return read([str(cmd),'/d','/c',str(batch)],text=True)


def stage_observer(source,target):
    require(source.is_file() and not target.is_symlink(),'Actual original observer and owned staged destination required')
    target.parent.mkdir(parents=True,exist_ok=True)
    require(target.parent.resolve()==target.parent,'Observer staging parent must not redirect')
    if target.exists():
        require(target.is_file(),'Existing staged observer must be a regular file')
        target.unlink()
    shutil.copy2(source,target)
    require(sha(source)==sha(target),'Exact original passive observer copy required')




def observed_scene_run(argv,**kwargs):
    directory=Path(kwargs['cwd']);timeout=kwargs.pop('timeout');check=kwargs.pop('check',False)
    started=time.monotonic_ns();record=dict(argv=list(map(str,argv)),actual_pid=None,actual_returncode=None,timed_out=False)
    try:
        child=subprocess.Popen(argv,**kwargs);record['actual_pid']=child.pid
        try:record['actual_returncode']=child.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            record['timed_out']=True;child.kill();record['actual_returncode']=child.wait();raise
        if check and record['actual_returncode']:raise subprocess.CalledProcessError(record['actual_returncode'],argv)
        return subprocess.CompletedProcess(argv,record['actual_returncode'])
    finally:
        record['elapsed_ns']=time.monotonic_ns()-started
        atomic_json(directory/'process-receipt.json',record)

def main():
    require(sys.platform=='win32' and os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('ImageOS') in {'win25','win25-vs2026'},'Ordinary standard hosted Windows session required')
    config=os.environ['CONFIGURATION'];require(config in ('Debug','Release'),'Exact retained Windows SDK configuration required')
    owner=ROOT/'application-source';sdk=ROOT/'out/current-windows-sdk';restored=load(sdk/'restoration.json');runtime=Path(restored['runtime'])
    require(restored['compiled_source']==APPLICATION and restored['configuration']==config and restored['collector_source']==os.environ['GITHUB_SHA'] and
            subprocess.check_output(['git','-C',str(owner),'rev-parse','HEAD'],text=True).strip()==APPLICATION,'Exact separately owned current SDK required')
    guards=restored['runtime_files_sha256'];require(all(sha(runtime/n)==h for n,h in guards.items()),'Entire pristine SDK must remain exact')
    output=ROOT/'out/failed-normal-Windows'/config;require(not output.exists(),'Fresh explicitly diagnostic Windows output required');output.mkdir(parents=True)
    report=dict(protocol='phase6-four-original-failed-normal-Windows-diagnostic-v1',status='running-diagnostic-only',source=os.environ['GITHUB_SHA'],
                application_source=APPLICATION,configuration=config,frames=60,fixed_step=.25,cases={},commands=[],phase6_complete=False,
                normal_admission_qualified=False,hands_on_ready=False,application_rebuilt=False)
    def save():atomic_json(output/'collection.json',report)
    def run(label,argv,env=None):
        log=output/(label+'.log');started=time.monotonic_ns()
        with log.open('wb') as stream:
            child=subprocess.Popen(list(map(str,argv)),cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT)
            code=child.wait(timeout=300)
        report['commands'].append(dict(label=label,argv=list(map(str,argv)),actual_pid=child.pid,actual_returncode=code,elapsed_ns=time.monotonic_ns()-started,log_sha256=sha(log)));save()
        require(code==0,'Actual declared preparation failed: '+label)
    save()
    try:
        relative='Tests/Production/RemainingStock/Driver.cpp';source=owner/relative
        require(source.read_bytes().replace(b'\r\n',b'\n')==subprocess.check_output(['git','-C',str(owner),'show',APPLICATION+':'+relative]).replace(b'\r\n',b'\n') and
                source.read_bytes().count(b'require(frames==60,"Incomplete original stock observation")')==1,
                'Unedited original60frame passive observer source required')
        vswhere=Path(os.environ['ProgramFiles(x86)'])/'Microsoft Visual Studio/Installer/vswhere.exe'
        found=json.loads(subprocess.check_output([str(vswhere),'-latest','-products','*','-requires','Microsoft.VisualStudio.Component.VC.Tools.x86.x64','-format','json'],text=True))
        require(len(found)==1,'One actual standard runner MSVC installation required')
        vcvars=Path(found[0]['installationPath'])/'Common7/Tools/VsDevCmd.bat';require(vcvars.is_file(),'Actual standard MSVC environment missing')
        batch=output/'compiler-environment.bat';batch.write_text(compiler_batch(vcvars),encoding='ascii')
        report['compiler_environment_batch_sha256']=sha(batch);save()
        cmd=str(Path(os.environ['SystemRoot'])/'System32/cmd.exe')
        raw=read_compiler_environment(cmd,batch)
        environment={k.upper():v for k,v in os.environ.items()}
        for line in raw.splitlines():
            k,sep,v=line.partition('=')
            if sep and k:environment[k.upper()]=v
        compiler=shutil.which('cl.exe',path=environment['PATH']);require(compiler,'Actual runner compiler missing')
        observer=output/'ProductionCockpitDriver.dll'
        run('compile-unedited-original60frame-passive-observer',[compiler,'/nologo','/EHsc','/std:c++17','/W3','/fp:precise','/Oi-',
            '/MDd' if config=='Debug' else '/MD','/Od' if config=='Debug' else '/O2','/LD','/DNOMINMAX',
            '/I'+str(runtime/'Orbitersdk/include'),'/I'+str(owner/'Tests/Production'),'/I'+str(owner/'Tests/Production/RemainingStock'),
            source,'/Fo'+str(output/'Observer.obj'),'/Fe'+str(observer),'/link',runtime/'Orbitersdk/lib/Orbiter.lib',runtime/'Orbitersdk/lib/Orbitersdk.lib'],environment)
        report['observer']=dict(source_commit=APPLICATION,source_relative=relative,source_sha256=sha(source),binary_sha256=sha(observer),
                                compiler=str(compiler),compiler_sha256=sha(compiler),application_rebuilt=False,source_modified=False);save()
        sys.path[:0]=[str(ROOT/'Tests/Production/StockScenarios'),str(ROOT/'Tests/Production'),str(ROOT/'Tests/Production/Client'),str(ROOT/'Tests/Production/Cockpit'),str(ROOT/'Tests/Production/CurrentWindows/Hosted')]
        spec=importlib.util.spec_from_file_location('original_cockpit_stage',ROOT/'Tests/Production/Cockpit/stage.py')
        original_stage=importlib.util.module_from_spec(spec);spec.loader.exec_module(original_stage)
        from types import SimpleNamespace
        original_stage.subprocess=SimpleNamespace(run=observed_scene_run) # Observe the unchanged argv/timeout without mutating the original source.
        from run_client import mesa_files
        import current_client_shaders as shaders
        # Both scene cohorts use the unchanged runner's original-propagators policy.
        normal_configuration=original_configuration()
        lock=load(ROOT/'Tests/Production/Closeout/failed-normal-admission-v4.lock.json')
        plan=shaders.build_plan(sdk/'restoration.json',owner,config,os.environ['GITHUB_SHA'],config+'-automatic-stock')
        atomic_json(output/'original-shader-plan.json',plan)
        failures=[]
        for mode in ('automatic','sse2'):
            if mode=='sse2':os.environ['ORBITER_TEST_OBSERVER_SSE2']='1'
            else:os.environ.pop('ORBITER_TEST_OBSERVER_SSE2',None)
            os.environ.update(LIBGL_ALWAYS_SOFTWARE='true',GALLIUM_DRIVER='llvmpipe')
            for scene,number in lock['failed_cases'].items():
                folder=output/(mode+'-'+number);scene_path=ROOT/'Scenarios'/scene;body=scene_path.read_bytes()
                require(body.replace(b'\r\n',b'\n')==subprocess.check_output(['git','-C',str(owner),'show',APPLICATION+':Scenarios/'+scene]).replace(b'\r\n',b'\n'),'Exact original complete scene required')
                def configure(directory):
                    (directory/'Scenarios/Behavior.scn').write_bytes(body)
                    cfg=normal_configuration+'\nACTIVE_MODULES\n  ProductionCockpitDriver\n  OGLClient\nEND_MODULES\n'
                    (directory/'Orbiter.cfg').write_text(cfg)
                    target=directory/'Modules/Plugin/ProductionCockpitDriver.dll'
                    stage_observer(observer,target)
                    for target,item in plan['files'].items():
                        p=directory/target;p.parent.mkdir(parents=True,exist_ok=True)
                        if p.exists():require(sha(p)==item['sha256'],'Conflicting same-source shader input')
                        else:shutil.copy2(owner/item['source'],p)
                        require(sha(p)==item['sha256'],'Actual original shader bytes differ')
                    (directory/'ogl-evidence.enabled').touch();mesa_files(ROOT/'out/current-stock-mesa',directory)
                error=None
                try:original_stage.run(runtime/'Orbiter.exe',ROOT/'out/current-stock-data',ROOT/'out/current-stock-planets',folder,dict(frames=60,fixed_step=.25),configure)
                except BaseException as e:error=str(e)
                require(folder.is_dir(),'Original Windows scene staging failed before producing any evidence')
                state=folder/'stock-vessel-state.csv';rows=list(csv.DictReader(io.StringIO(state.read_text()))) if state.is_file() else []
                invalid=[]
                for row in rows:
                    for key,value in row.items():
                        if key in ('object','class'):continue
                        try:valid=value is not None and math.isfinite(float(value))
                        except (ValueError,TypeError):valid=False
                        if not valid:invalid.append(dict(tick=row.get('tick'),object=row.get('object'),field=key,value=value))
                ticks={r['tick'] for r in rows};complete=(folder/'stock-vessel-complete.txt')
                reached=complete.is_file() and complete.read_text().strip()=='60'
                process=load(folder/'process-receipt.json') if (folder/'process-receipt.json').is_file() else None
                item=dict(scene=scene,math_profile=mode,original_scenario_sha256=sha(scene_path),process=process,error=error,rows=len(rows),
                          ticks=len(ticks),reached_original60frame_observer_end=reached,first_nonfinite=invalid[:8],native_admission_qualified=False,
                          files_sha256={p.relative_to(folder).as_posix():sha(p) for p in folder.iterdir() if p.is_file() and p.suffix.lower() in ('.csv','.json','.txt','.log','.cfg','.rgba')})
                report['cases'][mode+'-'+number]=item
                if error or invalid or not reached or ticks!={str(n) for n in range(61)}:failures.append(mode+'-'+number)
                require(all(sha(runtime/n)==h for n,h in guards.items()),'Pristine SDK changed during diagnostic scene')
                save()
        report.update(status='diagnostic-completed-with-original-simulation-failures' if failures else 'completed-diagnostic-only',
                      failed_cells=failures,attempted_scene_staging=len(report['cases']),actual_scene_processes=sum(c['process'] is not None and c['process']['actual_pid'] is not None for c in report['cases'].values()),pristine_sdk_unchanged=True);save()
        require(not failures,'Original Windows matched-clock diagnostics failed; all original partial outputs preserved')
    except BaseException as error:
        report['error']=str(error);save();raise
    finally:
        paths={p for p in output.rglob('*') if p.is_file() and ((p.parent==output and p.suffix.lower() in ('.json','.log','.dll','.obj','.lib','.exp','.pdb','.bat')) or
               (len(p.relative_to(output).parts)==2 and p.suffix.lower() in ('.csv','.json','.txt','.log','.cfg','.rgba')) or
               ('Scenarios' in p.relative_to(output).parts and p.suffix.lower()=='.scn'))}
        pack(ROOT,paths,output/'diagnostic-raw.tar.gz',output/'diagnostic-raw-index.json')


if __name__=='__main__':main()
