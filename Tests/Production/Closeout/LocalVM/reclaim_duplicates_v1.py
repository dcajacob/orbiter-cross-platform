"""Reclaim only declared generated files after independent host archive restoration."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import sys

from runtime_descriptor_v2 import require, sha

request_path = Path(sys.argv[1])
request = json.loads(request_path.read_text())
report_path = request_path.with_name(request_path.stem + '-result.json')
require(not report_path.exists(), 'Fresh reclamation receipt required')
report = dict(status='preflight', request_sha256=sha(request_path), removed=[], removed_bytes=0,
              free_bytes_before=shutil.disk_usage(request['volume']).free,
              source_dependencies_reference_packages_untouched=True)


def save():
    temporary = report_path.with_suffix('.tmp')
    temporary.write_text(json.dumps(report, indent=2) + '\n')
    temporary.replace(report_path)


try:
    require(sys.platform == 'win32', 'Windows duplicate reclamation only')
    audit_path = request_path.parent / request['restoration_audit']
    require(sha(audit_path) == request['restoration_audit_sha256'], 'Independent archive audit differs')
    audit = json.loads(audit_path.read_text())
    require(audit['status'] == 'passed-independent-all-archive-restorations', 'Full host restoration audit required')
    targets = []
    seen = set()
    for profile, item in request['profiles'].items():
        root = Path(item['vm_root'])
        require(root.is_dir() and root.resolve() == root and root.name == 'Full38-' + profile + '-v1',
                'Exact closed full38 output root required')
        restored = audit['profiles'][profile]
        require(item['archive_sha256'] == restored['archive_sha256'], 'Profile archive identity differs')
        for phase, status in [('remaining-stock-repaired','captured-awaiting-independent-audit'),
                              ('remaining-stock-persistence','captured-awaiting-independent-persistence-audit')]:
            manifest = root / phase / 'capture.json'
            require(sha(manifest) == restored['restored_files'][phase + '/capture.json']['sha256'],
                    'Closed VM capture differs from restored archive')
            require(json.loads(manifest.read_text())['status'] == status, 'Closed VM output required')
        for name in item['generated_files']:
            pure = PurePosixPath(name)
            require(len(pure.parts) == 3 and pure.parts[0] in ('remaining-stock-repaired','remaining-stock-persistence') and
                    re.fullmatch(r'remaining_stock_[0-9]{3}-[12]', pure.parts[1]) and
                    pure.name in ('scene.rgba','scene.png','camera.csv','stock-clock.csv','stock-step-clock.csv',
                                  'stock-animations.csv','stock-controls.csv','stock-input.csv','stock-thrust.csv',
                                  'stock-playback.csv','stock-population.csv') or
                    (len(pure.parts) == 3 and pure.parts[0] in ('remaining-stock-repaired','remaining-stock-persistence') and
                     re.fullmatch(r'remaining_stock_[0-9]{3}-[12]', pure.parts[1]) and
                     re.fullmatch(r'stock-vessel-[a-z-]+\.csv', pure.name)),
                    'Only explicitly generated trace/frame duplicates may be removed')
            require(name in restored['restored_files'], 'Reclamation file was not restored')
            path = root / pure
            require(path not in seen and path.is_file() and not path.is_symlink(), 'Missing/duplicate/replaced VM output')
            record = restored['restored_files'][name]
            require(path.stat().st_size == record['bytes'] and sha(path) == record['sha256'],
                    'VM duplicate differs from independently restored bytes: ' + str(path))
            seen.add(path)
            targets.append((path, record))
    report.update(status='all-duplicates-verified-before-removal', files=len(targets))
    save()
    for path, record in targets:
        # Recheck each exact target immediately before unlink, retain all manifests,
        # scenarios, modules, data, dependency caches and reference packages.
        require(sha(path) == record['sha256'], 'VM output changed before removal')
        path.unlink()
        report['removed'].append(dict(path=str(path), **record))
        report['removed_bytes'] += record['bytes']
        if len(report['removed']) % 100 == 0:
            save()
    report.update(status='completed-verified-duplicate-reclamation',
                  free_bytes_after=shutil.disk_usage(request['volume']).free)
except BaseException as error:
    report.update(status='failed', error=str(error))
    raise
finally:
    save()
