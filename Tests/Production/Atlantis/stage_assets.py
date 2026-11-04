#!/usr/bin/env python3
"""Extend a verified native asset tree with unchanged remaining-vessel installation resources."""
import argparse
import errno
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[3]
SOURCE='f725194209634f7fd5d1d44d426cfa9b5e303e37'


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def require(value,message):
    if not value:raise ValueError(message)


def link_or_copy(source,target):
    try:return os.link(source,target)
    except OSError as error:
        if error.errno!=errno.EXDEV:raise
        return shutil.copy2(source,target)


def tree(root):
    paths=sorted(root.rglob('*'));require(not any(p.is_symlink() for p in paths),'Symlink in native asset tree')
    result={};aliases=set()
    for p in paths:
        key=p.relative_to(root).as_posix().casefold()
        require(key not in aliases,'Ambiguous native resource alias: '+key);aliases.add(key)
        if p.is_file():result[p.relative_to(root).as_posix()]=digest(p)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('base-assets','output'):parser.add_argument('--'+name,type=lambda p:Path(p).resolve(),required=True)
    a=parser.parse_args();require(not a.output.exists(),'Fresh native asset destination required')
    before=tree(a.base_assets)
    require('resources.json' in before,'Base native resource manifest missing')
    manifest=json.loads((a.base_assets/'resources.json').read_text())
    for name,item in manifest['source_resources'].items():
        require(before[name]==item['sha256'],'Base native asset no longer matches its source manifest: '+name)
    shutil.copytree(a.base_assets,a.output,copy_function=link_or_copy)
    chosen={name.casefold():name for name in before};additions={};rules={}
    locked_data={name.casefold():value for name,value in manifest['locked_data'].items()}

    def frozen(path):
        name=path.relative_to(ROOT).as_posix()
        body=subprocess.check_output(['git','-C',str(ROOT),'show',SOURCE+':'+name])
        actual=path.read_bytes()
        if path.suffix.lower() in ('.cfg','.msh','.txt'):
            require(actual.replace(b'\r\n',b'\n')==body.replace(b'\r\n',b'\n'),'Original text resource changed: '+name)
        else:require(actual==body,'Original binary resource changed: '+name)
        return name

    families=[('Atlantis/Atlantis_SRB','Atlantis'),('Atlantis/Atlantis_Tank','Atlantis'),
              ('Atlantis/Atlantis','Atlantis'),('Carina',''),('Leonardo','ISS'),
              ('Dragonfly','Dragonfly'),('HST',''),('LDEF',''),('Solarsail',''),('Quadcopter','Quadcopter')]
    for family,subdirectory in families:
        source=ROOT/'Src/Vessel'/family
        rule=source/'CMakeLists.txt';name=frozen(rule);rules[name]=digest(rule)
        for directory,destination in (('Config','Config/Vessels'),('Meshes','Meshes'),
                ('Textures','Textures'),('Textures2','Textures2'),('Thumbnail','Images/Vessels/Default')):
            folder=source/directory
            if not folder.is_dir():continue
            target=Path(destination)
            if subdirectory and directory in ('Meshes','Textures','Textures2'):target/=subdirectory
            for path in sorted(folder.rglob('*')):
                if not path.is_file():continue
                original=frozen(path);relative=(target/path.relative_to(folder)).as_posix()
                relative=chosen.setdefault(relative.casefold(),relative)
                output=a.output/relative;output.parent.mkdir(parents=True,exist_ok=True)
                if relative.casefold() in locked_data:
                    require(relative in before and before[relative]==locked_data[relative.casefold()],
                            'Original final locked-data overlay differs: '+relative)
                    # The original staging copies stock data after vessel resources.
                    # Keep that final input even if a source texture differs.
                    additions[relative]=dict(source=original,source_sha256=digest(path),sha256=before[relative],
                        install_rule=name,final_overlay='retained locked stock data')
                    continue
                if output.exists():output.unlink()  # Only remove the fresh destination's link.
                shutil.copy2(path,output)
                additions[relative]=dict(source=original,source_sha256=digest(path),sha256=digest(output),
                    install_rule=name,final_overlay='original vessel installation')
    # Windows embeds these exact original bitmaps through panel.rc. The native
    # module loads the same bytes at explicit resource-ID installation paths.
    sys_path=ROOT/'Tests/Production'
    import sys
    sys.path.insert(0,str(sys_path))
    from Dragonfly.prepare_native import resources as dragonfly_resources
    rc=frozen(ROOT/'Src/Vessel/Dragonfly/panel.rc');rules[rc]=digest(ROOT/rc)
    resource_header=frozen(ROOT/'Src/Vessel/Dragonfly/resource.h')
    rules[resource_header]=digest(ROOT/resource_header)
    for resource_id,filename in dragonfly_resources():
        source=ROOT/'Src/Vessel/Dragonfly'/filename;original=frozen(source)
        relative='Textures/Dragonfly/Panels/'+filename
        require(relative.casefold() not in chosen,'Native Dragonfly bitmap delivery path already exists')
        chosen[relative.casefold()]=relative;target=a.output/relative;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source,target)
        additions[relative]=dict(source=original,source_sha256=digest(source),sha256=digest(target),
            install_rule=rc,resource_id=resource_id,final_overlay='original embedded bitmap delivered for native module')
    config=json.loads((ROOT/'Tests/Production/RemainingStock/cases.json').read_text())
    for kind,item in config['classes'].items():
        path=a.output/chosen.get(item['target'].casefold(),item['target'])
        require(path.is_file() and hashlib.sha256(path.read_bytes().replace(b'\r\n',b'\n')).hexdigest()==item['sha256_lf'],
                'Complete original remaining-scene class configuration absent: '+kind)
    for case in config['cases']:
        name=case['scenario_entry_point']
        require((a.output/name).read_bytes()==(ROOT/name).read_bytes(),'Original complete scenario changed: '+name)
        if case.get('recording_directory'):
            prefix='Flights/'+case['recording_directory']+'/'
            expected={name for name in config['recording_files_sha256_lf'] if name.startswith(prefix)}
            actual={path.relative_to(a.output).as_posix() for path in (a.output/prefix).iterdir() if path.is_file()}
            require(actual==expected,'Complete original recording directory differs: '+prefix)
    for name,checksum in config['recording_files_sha256_lf'].items():
        require(hashlib.sha256((a.output/name).read_bytes().replace(b'\r\n',b'\n')).hexdigest()==checksum,
                'Original remaining-scene recording changed: '+name)
    require(before==tree(a.base_assets),'Retained native base assets changed during staging')
    files=tree(a.output)
    report=dict(status='staged-awaiting-runtime-qualification',phase6_complete=False,native_admission_qualified=False,
        original_source=SOURCE,base_assets=str(a.base_assets),base_manifest_sha256=before['resources.json'],
        retained_base_unchanged=True,base_files_sha256=before,installation_rules_sha256=rules,
        overlay_resources=additions,staged_files_sha256=files,complete_remaining_scenes=38,initial_declared_classes=19,
        recording_files=len(config['recording_files_sha256_lf']),stager_sha256=digest(Path(__file__)),
        scope='Unchanged original install resources for all remaining stock vessel families, over the retained native tree. No module implementation, successful scene, hardware or runtime admission is implied by resource presence.')
    (a.output/'remaining-vessels-resources.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Staged',len(additions),'original remaining-vessel resources;',len(files),'files total; all 38 scene and 19 class inputs verified')


if __name__=='__main__':main()
