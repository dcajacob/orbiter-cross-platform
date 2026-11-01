#!/usr/bin/env python3
"""Verify preserved component evidence offline without refreshing references."""
import hashlib
import gzip
import json
from pathlib import Path, PurePosixPath
import re
import sys
import zipfile

sys.dont_write_bytecode = True
BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[3]
sys.path.insert(0, str(ROOT/'Tests/Production/Client'))
from compare_client import reference_pixels


def require(condition, message):
    if not condition:
        raise ValueError(message)


def local(root, name):
    path = PurePosixPath(name)
    require(not path.is_absolute() and '..' not in path.parts, 'invalid evidence path: '+name)
    result = (root/path).resolve()
    require(result.is_relative_to(root.resolve()), 'evidence escapes its root: '+name)
    return result


def check(data, expected, name):
    expected = expected.removeprefix('sha256:')
    require(bool(re.fullmatch('[0-9a-f]{64}', expected)), 'invalid SHA256: '+name)
    require(hashlib.sha256(data).hexdigest() == expected, 'evidence hash differs: '+name)


def verify():
    ledger = json.loads((BASE/'provenance.json').read_text())
    require(ledger['phase'] == 3 and ledger['phase_complete'] is False,
            'this historical evidence records a partial Phase 3 checkpoint')
    for entry in ledger['hosted']:
        require(entry['status'] == 'passed' and re.fullmatch('[0-9a-f]{40}', entry['source']),
                'invalid component provenance')
        data = local(BASE, entry['preserved_report']).read_bytes()
        check(data, entry['report_sha256'], entry['preserved_report'])
        report = json.loads(data)
        require(report['status'] == 'passed', 'failed client report')
        require(report['candidate_provenance']['application_source'] == entry['source'],
                'client/application source does not match the verified component')
        for configuration in ('debug', 'release'):
            require(report['frozen_'+configuration]['status'] == 'passed', 'failed frozen client comparison')
        if 'native_comparison' in entry:
            native = entry['native_comparison']
            check(local(BASE, native['preserved_report']).read_bytes(), native['report_sha256'],
                  native['preserved_report'])
        if 'local_verification' in entry:
            record = entry['local_verification']
            data = local(BASE, record['report']).read_bytes()
            check(data, record['sha256'], record['report'])
            report = json.loads(data)
            require(report['engine_source'] == entry['source'], 'local engine source differs')
            for name in ('debug_suite', 'release_suite', 'sanitizers', 'standalone_boundary'):
                require(report['checks'][name]['failed'] == 0 and report['checks'][name]['passed'] > 0,
                        'local checks did not pass')
            rejection = report['checks']['independent_build_rejection']
            check(local(BASE, rejection['log']).read_bytes(), rejection['log_sha256'], rejection['log'])
        for extra in entry.get('supplemental_reports', []):
            data = local(BASE, extra['file']).read_bytes()
            check(data, extra['sha256'], extra['file'])
            require(json.loads(data)['status'] == 'passed', 'supplemental component comparison failed')

    evidence = BASE/'Evidence'
    portable = json.loads((evidence/'portable-artifacts.json').read_text())
    require(len(portable['artifacts']) == 4, 'missing native build evidence')
    for artifact in portable['artifacts']:
        path = local(evidence, artifact['file'])
        check(path.read_bytes(), artifact['digest'], path.name)
        with zipfile.ZipFile(path) as archive:
            require(archive.testzip() is None, 'native evidence ZIP CRC failed')
            require(b'100% tests passed' in archive.read('ctest.log'), 'native tests did not pass')
            metadata = archive.read('out/portable/traces/production-scenario-metadata.csv')
            check(metadata, json.loads((BASE/'state-native-parity.json').read_text())[
                'production_scenario_metadata']['sha256'], 'scenario metadata')

    clients = json.loads((evidence/'windows-client-artifacts.json').read_text())
    require(clients['source'] == portable['source'], 'different source revisions in checkpoint archives')
    for artifact in clients['artifacts']:
        path = local(evidence, artifact['filtered_file'])
        check(path.read_bytes(), artifact['filtered_sha256'], path.name)
        with zipfile.ZipFile(path) as archive:
            expected = set()
            for member in artifact['members']:
                if 'storage' not in member:
                    expected.add(member['path'])
                    data = archive.read(member['path'])
                else:
                    storage = member['storage']
                    source = local(ROOT, storage['source'])
                    if storage['kind'] == 'existing_file':
                        data = source.read_bytes()
                    else:
                        require(storage['kind'] == 'lossless_decode' and storage['decoder'] ==
                            'Tests/Production/Client/compare_client.py:reference_pixels',
                            'unknown image reconstruction recipe')
                        data = reference_pixels(source)
                check(data, member['sha256'], member['path'])
            require(set(archive.namelist()) == expected and len(archive.namelist()) == len(expected),
                    'unmanifested or duplicate Windows evidence members')
    retry = BASE/'graphics-setup-retry.json'
    if retry.exists():
        log = json.loads(retry.read_text())['log']
        data = local(BASE, log['file']).read_bytes()
        check(data, log['sha256_gzip'], log['file'])
        check(gzip.decompress(data), log['sha256_decoded_lf_utf8'], 'decoded setup failure log')
    archive_local = BASE/'archive-local-linux.json'
    if archive_local.exists():
        report = json.loads(archive_local.read_text())
        require(re.fullmatch('[0-9a-f]{40}', report['engine_source']), 'invalid local archive source')
        for name in ('debug_suite', 'release_suite', 'sanitizers'):
            require(report['checks'][name]['failed'] == 0 and report['checks'][name]['passed'] > 0,
                    'local archive checks did not pass')
        artifact = report['evidence']
        path = local(BASE, artifact['file'])
        check(path.read_bytes(), artifact['sha256'], path.name)
        with zipfile.ZipFile(path) as archive:
            require(archive.testzip() is None and set(archive.namelist()) == set(artifact['members_sha256']),
                    'local archive log evidence differs')
            for name, checksum in artifact['members_sha256'].items():
                check(archive.read(name), checksum, name)
    archive_clients = BASE/'archive-client-artifacts.json'
    if archive_clients.exists():
        clients = json.loads(archive_clients.read_text())
        require(len(clients['artifacts']) == 2, 'expected both archive-extraction Windows client builds')
        for artifact in clients['artifacts']:
            path = local(BASE, artifact['filtered_file'])
            check(path.read_bytes(), artifact['filtered_sha256'], path.name)
            expected = set()
            with zipfile.ZipFile(path) as archive:
                require(archive.testzip() is None, 'archive client evidence ZIP is corrupt')
                for member in artifact['members']:
                    if 'storage' in member:
                        storage = member['storage']
                        source = local(ROOT, storage['source'])
                        require(storage['kind'] in ('existing_file', 'lossless_decode'), 'unknown image deduplication')
                        data = source.read_bytes() if storage['kind'] == 'existing_file' else reference_pixels(source)
                    else:
                        expected.add(member['path'])
                        data = archive.read(member['path'])
                    check(data, member['sha256'], member['path'])
                require(set(archive.namelist()) == expected, 'unmanifested archive client evidence')
    hosted_archives = BASE/'archive-hosted-artifacts.json'
    if hosted_archives.exists():
        record = json.loads(hosted_archives.read_text())
        original_root = ROOT/'Tests/Production/Archives/Reference'
        original = json.loads((original_root/'provenance.json').read_text())
        first = original['evidence'][0]
        path = local(original_root, first['file'])
        check(path.read_bytes(), first['sha256'], path.name)
        with zipfile.ZipFile(path) as archive:
            golden = json.loads(archive.read(first['capture_member']))
        builds = set()
        require(len(record['artifacts']) == 4, 'expected four shared archive builds')
        for artifact in record['artifacts']:
            path = local(BASE, artifact['file'])
            check(path.read_bytes(), artifact['sha256'], path.name)
            with zipfile.ZipFile(path) as archive:
                require(archive.testzip() is None and set(archive.namelist()) == set(artifact['members_sha256']),
                        'shared archive evidence differs')
                for name, checksum in artifact['members_sha256'].items():
                    check(archive.read(name), checksum, name)
                candidate = json.loads(archive.read(artifact['capture_member']))
            require(candidate['status'] == 'passed' and candidate['source'] == record['source'] and
                    candidate['working_tree_dirty'] is False and
                    candidate['protocol_sha256'] == original['protocol_sha256'] and
                    candidate['observations'] == golden['observations'], 'shared archive differs from original Windows')
            builds.add((candidate['host'].split('-')[0], candidate['configuration']))
        require(builds == {(host, config) for host in ('Linux', 'Windows') for config in ('Debug', 'Release')},
                'shared archive platform/configuration coverage differs')
    print('Verified', len(ledger['hosted']), 'component reports and preserved native/client/archive evidence; references were only read')


if __name__ == '__main__':
    try:
        verify()
    except (OSError, ValueError, KeyError, EOFError, zipfile.BadZipFile) as error:
        raise SystemExit(str(error)) from error
