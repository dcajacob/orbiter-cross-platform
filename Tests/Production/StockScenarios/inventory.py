"""Dependencies derived from locked stock bytes and the native loader's actual rules."""
import hashlib
import json
from pathlib import Path, PurePosixPath

ROOT=Path(__file__).resolve().parents[3]
LOCK=ROOT/'Tests/Production/production-source.lock.json'


def require(ok,message):
    if not ok:raise ValueError(message)


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def normalize(name):
    require(name and name[0] not in '/\\','Resource path must be relative')
    require(not any(c==':' or ord(c)<32 for c in name),'Invalid resource path')
    parts=[]
    for part in name.replace('\\','/').split('/'):
        require(part!='..','Resource path escapes its root')
        if part and part!='.':parts.append(part.translate(str.maketrans('ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz')))
    require(parts,'Empty resource path')
    return '/'.join(parts)


def index(root):
    result={};names=set()
    for path in sorted(root.rglob('*')):
        require(not path.is_symlink(),'Symlink in resource root: '+str(path))
        key=normalize(path.relative_to(root).as_posix())
        require(key not in names,'Conflicting resource aliases: '+key);names.add(key)
        if path.is_file():
            result[key]=path
    return result


def trim(line):
    return line.split(';',1)[0].strip()


def ships(text):
    """Read complete vessel blocks, including original indented headers/ENDs."""
    result={};current=None;found=False
    for raw in text.splitlines():
        line=trim(raw)
        if not found:
            if line.upper()=='BEGIN_SHIPS':found=True
            continue
        if line.upper()=='END_SHIPS':
            require(current is None,'Vessel block missing END')
            return result
        if current is not None:
            if line.upper()=='END':current=None
        elif line:
            name,separator,kind=line.partition(':')
            name=name.strip();kind=kind.strip() if separator else name
            require(name and kind and name not in result,'Invalid or duplicate stock vessel header: '+line)
            result[name]=kind;current=name
    require(not found,'Scenario ship list missing END_SHIPS')
    return result


def fields(path):
    # Match GetItemString: strip semicolon comments, use the first key and stop
    # before END_PARSE. Module is read from the class file, not its base class.
    result={}
    for raw in path.read_bytes().decode('cp1252').splitlines():
        line=trim(raw)
        if line.upper()=='END_PARSE':break
        key,separator,value=line.partition('=')
        if separator and key.strip().lower() not in result:result[key.strip().lower()]=value.strip()
    return result


class Dependencies:
    def __init__(self,assets,modules):
        self.assets=assets;self.modules=modules
        self.config=index(assets/'Config');self.module=index(modules)

    def config_path(self,name):
        key=normalize(name)
        if not PurePosixPath(key).suffix:key+='.cfg'
        return key,self.config.get(key)

    def vessel(self,kind):
        # Vessel::OpenConfigFile first searches Config/Vessels, then Config.
        key,path=self.config_path('Vessels/'+kind)
        if path is None:key,path=self.config_path(kind)
        record=dict(class_name=kind,configs=[],module=None,problems=[])
        if path is None:
            record['problems'].append('missing class configuration: '+kind)
            return record
        values=fields(path)
        seen=set()
        def configuration(config_key,config_path,role):
            require(config_key not in seen,'Configuration inheritance cycle: '+config_key)
            seen.add(config_key)
            record['configs'].append(dict(path=config_path.relative_to(self.assets).as_posix(),role=role,sha256=digest(config_path)))
            base=fields(config_path).get('baseclass')
            if base:
                base_key,base_path=self.config_path(base)
                if base_path is None:record['problems'].append('missing base configuration: '+base)
                else:configuration(base_key,base_path,'base')
        configuration(key,path,'class')
        module=values.get('module')
        if module:
            module_key=normalize('Vessel/'+module+'.so')
            binary=self.module.get(module_key)
            record['module']=dict(name=module,path=module_key,present=binary is not None,
                                  sha256=digest(binary) if binary else None)
            if binary is None:record['problems'].append('missing native module: '+module)
            record['implementation']='configured module; runtime ABI/SDK check still required'
        else:
            record['implementation']='original configuration-defined VESSEL; no module declared'
        return record


def corpus(assets,modules):
    lock=json.loads(LOCK.read_text())
    require(lock['scenario_count']==len(lock['scenarios'])==157,'Frozen stock corpus identity differs')
    dependencies=Dependencies(assets,modules)
    classes={};cases={}
    for item in lock['scenarios']:
        source=ROOT/item['path'];raw=source.read_bytes();data=raw.replace(b'\r\n',b'\n')
        require(hashlib.sha256(data).hexdigest()==item['sha256'],'Frozen scenario bytes differ: '+item['path'])
        relative=source.relative_to(ROOT/'Scenarios')
        staged=assets/'Scenarios'/relative
        require(staged.is_file() and staged.read_bytes()==raw,'Staged scenario bytes differ: '+str(relative))
        text=data.decode('cp1252');vessels=ships(text)
        for kind in vessels.values():
            if kind not in classes:classes[kind]=dependencies.vessel(kind)
        problem_classes={kind:classes[kind]['problems'] for kind in sorted(set(vessels.values())) if classes[kind]['problems']}
        original={v['name']:v['vessel_class'] for v in item['objects']}
        cases[relative.as_posix()]=dict(sha256_lf=item['sha256'],sha256_raw=hashlib.sha256(raw).hexdigest(),
            ships=vessels,locked_inventory_metadata_differs=original!=vessels,
            inventory_ready=not problem_classes,dependency_problems=problem_classes,status='not-run')
    return dict(lock_sha256=digest(LOCK),scenario_count=len(cases),cases=cases,classes=classes)
