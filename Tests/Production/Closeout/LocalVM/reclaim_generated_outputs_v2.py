"""Unlink only exact generated duplicates independently restored from sealed archives."""
import json
from pathlib import Path
import shutil
import sys
from generated_outputs_v2 import sha,require,relative,output_root,closures,generated


def main():
    request=Path(sys.argv[1]);cfg=json.loads(request.read_text());path=request.parent/cfg['result']
    require(sys.platform=='win32' and not path.exists(),'Windows and a fresh reclamation receipt required')
    report=dict(status='preflight',request_sha256=sha(request),removed=[],removed_bytes=0,
        free_bytes_before=shutil.disk_usage('C:/').free,source_dependencies_reference_packages_untouched=True,phase6_complete=False)
    def save():path.write_text(json.dumps(report,indent=2)+'\n')
    try:
        require(sha(cfg['restoration_audit'])==cfg['restoration_audit_sha256'],'Independent restoration audit changed')
        audit=json.loads(Path(cfg['restoration_audit']).read_text())
        require(audit['status']=='passed-independent-all-archive-restorations','Complete independent restoration required')
        targets=[];seen=set()
        for profile,item in cfg['profiles'].items():
            root=Path(output_root(item['vm_root']));require(root.is_dir() and root.resolve()==root,'Actual closed output root differs')
            closures(item['closures']);restored=audit['profiles'][profile]
            require(restored['archive_sha256']==item['archive_sha256'],'Restored archive identity differs')
            for name in item['generated_files']:
                require(generated(name),'Input/source/SDK files cannot be reclaimed');name=str(relative(name));target=root/name
                require(target not in seen and target.is_file() and not target.is_symlink() and name in restored['restored_files'],
                        'Missing/duplicate/unrestored output target')
                value=restored['restored_files'][name]
                require(target.stat().st_size==value['bytes'] and sha(target)==value['sha256'],'VM duplicate differs from restored bytes')
                seen.add(target);targets.append((target,value))
        require(targets,'Explicit nonempty duplicate plan required')
        report.update(status='all-generated-duplicates-verified-before-removal',files=len(targets));save()
        for target,value in targets:
            require(sha(target)==value['sha256'],'Duplicate changed immediately before unlink')
            target.unlink();report['removed'].append(dict(path=str(target),**value));report['removed_bytes']+=value['bytes']
            if len(report['removed'])%100==0:save()
        report.update(status='completed-verified-generated-duplicate-reclamation',free_bytes_after=shutil.disk_usage('C:/').free)
    except BaseException as error:report.update(status='failed',error=str(error));raise
    finally:save()


if __name__=='__main__':main()
