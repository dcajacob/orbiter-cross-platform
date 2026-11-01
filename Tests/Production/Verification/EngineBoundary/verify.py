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
    print('Verified', len(ledger['hosted']), 'component reports, four native archives, and both Windows client archives; references were only read')


if __name__ == '__main__':
    try:
        verify()
    except (OSError, ValueError, KeyError, EOFError, zipfile.BadZipFile) as error:
        raise SystemExit(str(error)) from error
