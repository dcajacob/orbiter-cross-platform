"""Install only host dependencies declared by the exact privately retained Weston packages."""
import json
from pathlib import Path
import re
import subprocess
from hosted_native_package import ROOT,require,sha,load


DEPENDENCY=re.compile(r'([a-z0-9][a-z0-9+.-]*(?::(?:any|native|amd64))?)(?:\s+\((<<|<=|=|>=|>>)\s+([A-Za-z0-9.+:~_-]+)\))?')


def clauses(body):
    require(len(body)<24000,'Bounded binary dependency metadata required')
    result=[]
    for clause in body.split(','):
        text=clause.strip()
        if not text:continue
        alternatives=[]
        for item in text.split('|'):
            match=DEPENDENCY.fullmatch(item.strip());require(match is not None,'Unsupported original binary dependency clause')
            alternatives.append(dict(name=match[1],operator=match[2],version=match[3]))
        result.append((text,alternatives))
    require(len(result)<200,'Bounded binary runtime dependency count required')
    return result


def compare(actual,operator,wanted):
    return operator is None or (actual is not None and subprocess.run(['dpkg','--compare-versions',actual,operator,wanted]).returncode==0)


def host_clauses(body,private_versions):
    result=[]
    for text,alternatives in clauses(body):
        private=[item for item in alternatives if item['name'].split(':')[0] in private_versions]
        if private:
            require(any(compare(private_versions[item['name'].split(':')[0]],item['operator'],item['version']) for item in private),
                    'Privately retained Weston dependency version differs')
        else:result.append(text)
    return result


def original_packages_unchanged(original,actual):
    require(all(actual.get(name)==version for name,version in original.items()),
            'Installing compositor host dependencies changed an original provider package/version')
    return {name:version for name,version in actual.items() if name not in original}


def install(providers,output,original,run,inventory_reader):
    lock=load(ROOT/'Tests/Production/WaylandInput/dependencies.lock.json')
    private={item['name']:item['version'] for item in lock['packages']};requirements=[];metadata=[]
    for entry in lock['packages']:
        if entry['name'] not in ('weston','libweston-14-0'):continue
        package=providers/'cache/compositor'/entry['filename']
        require(package.stat().st_size==entry['size'] and sha(package)==entry['sha256'],'Actual locked compositor package differs')
        def field(name):return subprocess.check_output(['dpkg-deb','--field',str(package),name],text=True).strip()
        require(field('Package')==entry['name'] and field('Version')==entry['version'] and field('Architecture')=='amd64',
                'Actual original compositor binary metadata differs')
        fields={name:field(name) for name in ('Depends','Pre-Depends')}
        for body in fields.values():requirements.extend(host_clauses(body,private))
        metadata.append(dict(package=entry['name'],version=entry['version'],package_sha256=sha(package),fields=fields))
    require(len(metadata)==2 and requirements,'Both original runtime packages and their host dependencies required')
    expression=', '.join(dict.fromkeys(requirements))
    # apt parses the verified binary dependency grammar; no package or shell text is evaluated.
    run('satisfy-declared-compositor-host-dependencies',['apt-get','satisfy','-y','--no-install-recommends','--no-upgrade',expression],1200)
    actual_body=subprocess.check_output(['dpkg-query','-W','-f=${binary:Package}=${Version}\n'],text=True)
    (output/'compositor-system-packages.txt').write_text(actual_body);actual=inventory_reader(actual_body)
    additions=original_packages_unchanged(original,actual)
    provided={}
    provides=subprocess.check_output(['dpkg-query','-W','-f=${binary:Package}\t${Provides}\n'],text=True)
    (output/'compositor-system-provides.txt').write_text(provides)
    for row in provides.splitlines():
        owner,_,body=row.partition('\t')
        for _,items in clauses(body):
            require(len(items)==1 and items[0]['operator'] in (None,'='),'Unsupported actual Debian Provides metadata')
            item=items[0];provided.setdefault(item['name'],[]).append(item['version'])
    for _,alternatives in clauses(expression):
        satisfied=False
        for item in alternatives:
            name=item['name'].split(':')[0];versions=[value for key,value in actual.items() if key==name or key==name+':amd64']
            versions+=provided.get(name,[])
            satisfied=satisfied or any(compare(value,item['operator'],item['version']) for value in versions)
        require(satisfied,'Actual installed compositor dependency does not meet its original binary requirement')
    require(not any(name.split(':')[0] in {'weston','libweston-14-0','libweston-14-dev'} for name in additions),
            'The owned compositor packages must remain privately extracted, never system-installed')
    report=dict(protocol='phase6-hosted-compositor-host-dependencies-v1',status='installed-original-declared-host-dependencies-only',
        package_metadata=metadata,host_dependency_expression=expression,actual_supplemental_packages=additions,
        actual_full_inventory_sha256=sha(output/'compositor-system-packages.txt'),original_provider_packages_unchanged=True,
        private_compositor_not_system_installed=True,phase6_complete=False,native_admission_qualified=False)
    (output/'compositor-host-dependencies.json').write_text(json.dumps(report,indent=2)+'\n')
    return report
