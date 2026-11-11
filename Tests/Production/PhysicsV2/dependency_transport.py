"""Fill the exact signed apt dependency plan from identical official Ubuntu pool bytes."""
import hashlib,json,shlex,shutil,subprocess,time
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT/'Tests/Production/Closeout'))
from contracts import require,sha,atomic_json
SNAPSHOT='https://snapshot.ubuntu.com/ubuntu/20261109T212432Z/'
POOL='https://archive.ubuntu.com/ubuntu/'


def parse_plan(body):
    result=[];seen=set()
    for line in body.splitlines():
        if not line.startswith("'"):continue
        row=shlex.split(line);require(len(row)==4,'Exact original apt URI filename length hash required')
        uri,filename,length,digest=row
        require(uri.startswith(SNAPSHOT+'pool/') and not any(s in uri for s in ('..','\\','\n','\r')) and filename.endswith('.deb') and filename==Path(filename).name and not filename.startswith('.') and all(c.isalnum() or c in '-+_.%:~' for c in filename),'Canonical original signed snapshot package required')
        require(length.isdigit() and 0<int(length)<2*1024**3 and digest.startswith('SHA256:') and len(digest)==71 and all(c in '0123456789abcdef' for c in digest[7:]) and filename not in seen,'Exact original SHA256 size and unique package required');seen.add(filename)
        result.append(dict(original=uri,official=POOL+uri[len(SNAPSHOT):],filename=filename,bytes=int(length),sha256=digest[7:]))
    require(len(result)<400,'Bounded declared dependency-only package plan required')
    return result


def prepare(label,argv,output):
    require(label in ('satisfy-declared-compositor-host-dependencies','satisfy-declared-native-host-dependencies') and argv[:2]==['apt-get','satisfy'] and argv[2:5]==['-y','--no-install-recommends','--no-upgrade'] and len(argv)==6,'Only complete unchanged declared dependency argv may prefill exact bytes')
    output=Path(output)/('exact-official-transport-'+label);output.mkdir(exist_ok=False)
    config=[Path('/etc/apt/apt.conf.d/99-orbiter-ci-https'),Path('/etc/apt/apt.conf.d/99-orbiter-class-snapshot'),Path('/run/orbiter-ci-system-ca.pem')]
    config += [p for p in [Path('/etc/apt/sources.list'),*Path('/etc/apt/sources.list.d').glob('*.sources'),*Path('/etc/apt/sources.list.d').glob('*.list')] if p.is_file()]
    before={str(p):sha(p) for p in config};require('20261109T212432Z' in config[1].read_text(),'Unchanged original signed archive timestamp required')
    plan_argv=['apt-get','-o','Acquire::ForceHash=sha256','--print-uris','--download-only',*argv[1:]]
    result=subprocess.run(plan_argv,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=180);(output/'original-signed-plan.log').write_text(result.stdout)
    require(result.returncode==0,'Actual original signed dependency plan must resolve before transport');plan=parse_plan(result.stdout)
    report=dict(protocol='phase6-v2-identical-declared-host-dependency-transport-v1',original_argv=argv,plan_argv=plan_argv,actual_plan_returncode=result.returncode,packages=plan,commands=[],original_archive_config_sha256=before,qualification_granted=False)
    atomic_json(output/'transport.json',report)
    for index,item in enumerate(plan):
        target=Path('/var/cache/apt/archives')/item['filename'];require(not target.is_symlink(),'Actual package cache target must be a regular file')
        if target.is_file() and target.stat().st_size==item['bytes'] and sha(target)==item['sha256']:continue
        require(shutil.disk_usage(target.parent).free>=item['bytes']+8*1024**3,'Preserve original eight-GiB reserve')
        sources=[item['official'],item['original']]
        for attempt,uri in enumerate(sources):
            log=output/(str(index)+'-'+str(attempt)+'.log');command=['/usr/lib/apt/apt-helper','-o','Acquire::ForceHash=sha256','download-file',uri,str(target),'SHA256:'+item['sha256']]
            with log.open('wb') as stream:child=subprocess.Popen(command,stdout=stream,stderr=subprocess.STDOUT);code=child.wait(timeout=180)
            report['commands'].append(dict(actual_pid=child.pid,argv=command,actual_returncode=code,log_sha256=sha(log)));atomic_json(output/'transport.json',report)
            if code==0:break
            # Preserve every prior partial before a byte-identical source fallback.
            for number,partial in enumerate((target,Path(str(target)+'.partial'))):
                if partial.is_file():shutil.copy2(partial,output/(str(index)+'-'+str(attempt)+'-partial-'+str(number)+'.deb'))
            text=log.read_text(errors='replace')
            require(not any(s in text.lower() for s in ('hash sum mismatch','checksum mismatch','signature verification failed')),'Any hash/signature failure stops without transport substitution')
            require(attempt==0 and any(s in text for s in ('404  Not Found','404 Not Found','500  Internal Server Error','500 Internal Server Error','502  Bad Gateway','502 Bad Gateway','503  Service Unavailable','503 Service Unavailable','504  Gateway')),'Only observed official-pool absence/transient server failures can use the unchanged original snapshot URL')
        require(code==0 and target.stat().st_size==item['bytes'] and sha(target)==item['sha256'],'Every complete package must match the unchanged signed apt plan size/SHA256')
    require(all(sha(p)==h for p,h in before.items()),'Original archive source, TLS trust and dated snapshot config must remain unchanged')
    report['status']='prefilled-only-exact-original-signed-package-bytes';atomic_json(output/'transport.json',report)
