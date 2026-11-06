"""Preserve exact closed VM generated outputs on the explicitly declared local share."""
import json
from pathlib import Path
import sys
import zipfile
from generated_outputs_v2 import sha,require,relative,output_root,closures,file_map,generated


def main():
    request=Path(sys.argv[1]);cfg=json.loads(request.read_text());manifest=request.parent/cfg['manifest']
    require(sys.platform=='win32' and not manifest.exists(),'Windows and fresh preservation manifest required')
    result=dict(status='running',profiles={},request_sha256=sha(request),phase6_complete=False,raw_evidence_uploaded=False)
    def save():manifest.write_text(json.dumps(result,indent=2)+'\n')
    try:
        for profile,item in cfg['profiles'].items():
            root=Path(output_root(item['vm_root']));require(root.is_dir() and root.resolve()==root,'Actual output root missing/redirected')
            closures(item['closures']);files=file_map(item['file_map']);selected={name:value for name,value in files.items() if generated(name)}
            require(selected,'Generated duplicates required');archive=request.parent/relative(item['archive'])
            require(not archive.exists(),'Fresh local preservation archive required');archive.parent.mkdir(parents=True,exist_ok=True)
            for name,value in selected.items():
                path=root/name;require(path.is_file() and not path.is_symlink() and sha(path)==value,'Actual closed output differs: '+name)
            with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=1) as target:
                for name,value in selected.items():
                    path=root/name
                    with path.open('rb') as source,target.open(name,'w') as destination:
                        for block in iter(lambda:source.read(65536),b''):destination.write(block)
                    require(sha(path)==value,'Output changed during archival: '+name)
            closures(item['closures']);require(file_map(item['file_map'])==files,'Closed output metadata changed')
            result['profiles'][profile]=dict(archive=str(relative(item['archive'])),sha256=sha(archive),files_sha256=selected,
                vm_root=str(root),closures=item['closures'],file_map=item['file_map'],bytes=archive.stat().st_size)
            save()
        result['status']='preserved-closed-generated-outputs-awaiting-independent-restoration'
    except BaseException as error:result.update(status='failed',error=str(error));raise
    finally:save()


if __name__=='__main__':main()
