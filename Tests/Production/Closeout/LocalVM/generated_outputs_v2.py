"""Finite task-output roots and generated-file rules for duplicate reclamation."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
from runtime_descriptor_v2 import windows_path,require

PROTECTED_PARTS={'source','src','config','modules','orbitersdk','meshes','textures','textures2','images',
                 'fonts','script','kernels','gravitymodels','tools','inputs','inputs-v1','data','planets','runtime','build','cmake','.git'}
TERMINAL={'passed','passed-unchanged-current-Windows-cockpit-suite',
          'captured-current-Windows-stock-and-paired-exact-save-reloads',
          'passed-existing-NTFS-captures-and-shared-exports'}


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(65536),b''):h.update(block)
    return h.hexdigest()


def relative(name):
    require(isinstance(name,str),'Relative generated output name required')
    path=PurePosixPath(name.replace('\\','/'))
    require(str(path)==name.replace('\\','/') and not path.is_absolute() and '..' not in path.parts and
            ':' not in name and path.parts,'Unsafe generated output name')
    return path


def output_root(value):
    root=windows_path(value)
    require(root.is_relative_to(windows_path('C:/OrbiterPhase6')), 'Task-owned local C: output root required')
    valid=(re.fullmatch('CurrentStock-(Debug|Release)-v[0-9]+',root.name) is not None or
           root.name=='qualification-v1' and root.parent.name.startswith('CurrentQualification-') or
           re.fullmatch('CurrentCockpit-[A-Za-z0-9-]+-v[0-9]+',root.name) is not None and root.parent.name=='Runs')
    require(valid,'Only declared closed stock/regression/cockpit output roots may be reclaimed')
    return root


def generated(name):
    path=relative(name)
    if any(part.lower() in PROTECTED_PARTS for part in path.parts[:-1]):return False
    if path.name.lower() in ('replay.csv','input-schedule.csv'):return False
    return path.suffix.lower() in ('.csv','.rgba','.png')


def closures(records):
    require(records,'Closed collector receipts required')
    for record in records:
        require(sha(record['path'])==record['sha256'],'Closed collector receipt changed')
        body=json.loads(Path(record['path']).read_text())
        require(record['status'] in TERMINAL and body['status']==record['status'], 'Collector output is not closed')


def file_map(record):
    require(sha(record['path'])==record['sha256'], 'Closed output file map differs')
    source=json.loads(Path(record['path']).read_text())[record['field']];result={};seen=set()
    for name,value in source.items():
        path=relative(name);key=str(path);checksum=value['sha256'] if isinstance(value,dict) else value
        require(key.casefold() not in seen and re.fullmatch('[0-9a-f]{64}',checksum), 'Duplicate/invalid output byte identity')
        seen.add(key.casefold());result[key]=checksum
    require(result,'Nonempty closed output map required')
    return result
