"""Unlink only exact generated duplicates independently restored from sealed archives."""
import json
from pathlib import Path
import shutil
import sys
from generated_outputs_v2 import sha,require,relative,output_root,closures,generated,load,windows_path


def verify_completed(request,cfg):
    output=request.parent/cfg['result'];require(not output.exists(),'Fresh independent reclamation verification required')
    receipt=Path(cfg['reclamation_result']);require(sha(receipt)==cfg['reclamation_result_sha256'],'Completed reclamation receipt changed')
    actual=load(receipt);plan=load(cfg['reclamation_request'])
    require(actual['status']=='completed-verified-generated-duplicate-reclamation' and
            actual['request_sha256']==sha(cfg['reclamation_request']), 'Completed exact reclamation request/result required')
    expected={str(Path(output_root(item['vm_root']))/relative(name)) for item in plan['profiles'].values() for name in item['generated_files']}
    removed={item['path'] for item in actual['removed']}
    require(len(actual['removed'])==len(removed) and removed==expected and all(not Path(path).exists() for path in expected) and
            sum(item['bytes'] for item in actual['removed'])==actual['removed_bytes'],'Actual removed set/bytes/absence differs')
    for item in plan['profiles'].values():
        closures(item['closures']);require(sha(item['archive'])==item['archive_sha256'],'Sealed archive changed after reclamation')
    built=load(cfg['current_build']);require(sha(cfg['current_build'])==cfg['current_build_sha256'] and built['owning_sources_unchanged'],
                                          'Current retained build record differs')
    source=Path(cfg['current_source'])
    for name,value in built['source_guard_sha256_lf'].items():
        require(__import__('hashlib').sha256((source/name).read_bytes().replace(b'\r\n',b'\n')).hexdigest()==value,
                'Owning application/SDK source changed: '+name)
    packages={}
    for configuration,item in built['configurations'].items():
        root=Path(item['runtime']);require(all(sha(root/name)==value for name,value in item['runtime_files_sha256'].items()),
                                         'Current retained runtime/SDK/input changed')
        packages['current-'+configuration]=len(item['runtime_files_sha256'])
    for configuration,root in cfg['original_packages'].items():
        root=Path(root);manifest=load(root/'test-runtime.json')
        require(manifest['source_commit']=='f725194209634f7fd5d1d44d426cfa9b5e303e37' and
                all(sha(root/name)==value for name,value in manifest['files'].items()),'Original application/SDK reference package changed')
        packages['original-'+configuration]=len(manifest['files'])
    free=shutil.disk_usage('C:/').free
    result=dict(status='passed-independent-reclamation-and-retained-package-audit',removed_files=len(expected),
        removed_bytes=actual['removed_bytes'],source_inputs_verified=len(built['source_guard_sha256_lf']),retained_packages=packages,
        free_bytes=free,full_campaign_minimum_free_bytes=8*1024**3,full_campaign_capacity_ready=free>=8*1024**3,
        reclamation_result_sha256=sha(receipt),reclamation_request_sha256=sha(cfg['reclamation_request']),
        source_dependencies_reference_packages_untouched=True,phase6_complete=False)
    output.write_text(json.dumps(result,indent=2)+'\n')


def main():
    request=Path(sys.argv[1]);cfg=load(request);path=request.parent/cfg['result']
    if cfg.get('action')=='verify-completed-reclamation':verify_completed(request,cfg);return
    require(sys.platform=='win32' and not path.exists(),'Windows and a fresh reclamation receipt required')
    report=dict(status='preflight',request_sha256=sha(request),removed=[],removed_bytes=0,
        free_bytes_before=shutil.disk_usage('C:/').free,source_dependencies_reference_packages_untouched=True,phase6_complete=False)
    def save():
        temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(report,indent=2)+'\n');temporary.replace(path)
    try:
        require(sha(cfg['restoration_audit'])==cfg['restoration_audit_sha256'],'Independent restoration audit changed')
        audit=load(cfg['restoration_audit']);share=windows_path(cfg['share_root'])
        require(audit['status']=='passed-independent-all-archive-restorations','Complete independent restoration required')
        targets=[];seen=set()
        for profile,item in cfg['profiles'].items():
            root=Path(output_root(item['vm_root']));require(root.is_dir() and root.resolve()==root,'Actual closed output root differs')
            closures(item['closures']);restored=audit['profiles'][profile]
            require(restored['archive_sha256']==item['archive_sha256'],'Restored archive identity differs')
            require(windows_path(item['archive']).is_relative_to(share) and sha(item['archive'])==restored['archive_sha256'],
                    'Actual sealed local archive missing or changed before reclamation')
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
