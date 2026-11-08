#!/usr/bin/env python3
"""Prepare locked inputs and retain the real full-stock build/test outputs on Actions."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tarfile
import urllib.request
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[3]
DEPENDENCIES = ROOT / 'out/phase6-hosted-build-dependencies'


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def load(path):
    return json.loads(Path(path).read_text())


def fetch(url, path, checksum, size=None):
    require(url.startswith('https://codeload.github.com/'), 'Only locked upstream archive host allowed')
    if not path.is_file() or sha(path) != checksum:
        with urllib.request.urlopen(url, timeout=180) as source:
            body = source.read()
        require(hashlib.sha256(body).hexdigest() == checksum and (size is None or len(body) == size),
                'Downloaded locked build input differs')
        path.write_bytes(body)
    require(sha(path) == checksum and (size is None or path.stat().st_size == size),
            'Cached locked build input differs')


def dependencies():
    subprocess.run(['python3', '-B', str(ROOT/'Tests/Production/NativeScene/dependencies.py'),
                    '--cache', str(ROOT/'out/ogl-dependencies')], check=True, cwd=ROOT)
    DEPENDENCIES.mkdir(parents=True, exist_ok=True)
    locked = load(ROOT/'Tests/Production/dependencies.lock.json')['dependencies']
    lua_cmake = (ROOT/'Src/Module/LuaScript/Native/CMakeLists.txt').read_text()
    lua_hash = re.findall(r'URL_HASH SHA256=([0-9a-f]{64})', lua_cmake)
    require(len(lua_hash) == 1, 'One original Lua archive digest required')
    fetch('https://codeload.github.com/lua/lua/zip/'+locked['lua']['commit'],
          DEPENDENCIES/'lua.zip', lua_hash[0])
    plot = load(ROOT/'Tests/Production/Atlantis/dependencies.lock.json')['implot']
    require(plot['url'] == 'https://codeload.github.com/epezent/implot/zip/'+locked['implot']['commit'],
            'Existing full-stock ImPlot locks disagree')
    fetch(plot['url'], DEPENDENCIES/'implot.zip', plot['sha256'], plot['bytes'])
    catch = DEPENDENCIES/'Catch2'; identity = locked['Catch2']
    require(identity['repository'] == 'https://github.com/catchorg/Catch2' and
            re.fullmatch('[0-9a-f]{40}', identity['commit']), 'Existing upstream Catch identity differs')
    if not catch.exists():
        subprocess.run(['git', 'clone', '--no-checkout', '--filter=blob:none',
                        identity['repository'], str(catch)], check=True)
        subprocess.run(['git', '-C', str(catch), 'checkout', '--detach', identity['commit']], check=True)
    require(subprocess.check_output(['git', '-C', str(catch), 'rev-parse', 'HEAD'], text=True).strip()
            == identity['commit'], 'Cached Catch source revision differs')
    require(not subprocess.check_output(['git', '-C', str(catch), 'status', '--porcelain'], text=True).strip(),
            'Cached Catch source has local changes')
    print('All original full-stock dependency pins verified')


def checked_member(root, name, checksum):
    relative = Path(name)
    require(not relative.is_absolute() and '..' not in relative.parts and '\\' not in name and ':' not in name,
            'Unsafe source-bound package member')
    path = root/relative
    require(path.is_file() and not path.is_symlink() and sha(path) == checksum,
            'Source-bound runtime or generated input differs: '+name)
    return path


def test_result(inventory, result):
    names = [item['name'] for item in load(inventory)['tests']]
    xml = ET.parse(result).getroot()
    cases = xml.findall('.//testcase')
    require(names and len(names) == len(set(names)) and len(cases) == len(names) and
            {case.attrib['name'] for case in cases} == set(names), 'Actual unit execution differs from complete inventory')
    require(all(not any(case.find(tag) is not None for tag in ('failure', 'error', 'skipped')) for case in cases),
            'A failed or skipped unit cannot qualify the package')
    return dict(registered_processes=len(names), executed_processes=len(cases),
                inventory_sha256=sha(inventory), junit_sha256=sha(result))


def package(folder):
    folder = folder.resolve(); require(folder.is_relative_to(ROOT/'out'), 'Package must belong to this build checkout')
    build = folder/'build.json'; record = load(build)
    producer = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip()
    require(record['status'] == 'built' and record['source_base'] == producer and
            record['owning_sources_unchanged'] is True and record['instrumentation'] == 'address,undefined',
            'Complete current-source build with unsuppressed ASan/UBSan required')
    protected = {**record['source_sha256_lf'], **record['dependency_sha256_lf']}
    for name, value in protected.items():
        actual = (ROOT/name).read_bytes().replace(b'\r\n', b'\n')
        immutable = subprocess.check_output(['git', '-C', str(ROOT), 'show', producer+':'+name]).replace(b'\r\n', b'\n')
        require(hashlib.sha256(actual).hexdigest() == value == hashlib.sha256(immutable).hexdigest(),
                'Owning package source differs: '+name)
    tests = {kind: test_result(folder/inventory, folder/result) for kind, inventory, result in (
        ('engine', 'registered-unit-tests.json', 'engine-tests.xml'),
        ('upstream', 'upstream-registered-unit-tests.json', 'upstream-tests.xml'))}
    members = {}
    for field in ('runtime_files_sha256', 'candidate_runtime_files_sha256', 'generated_source_files_sha256'):
        for name, value in record[field].items():
            members[name] = checked_member(ROOT, name, value)
    for path in folder.iterdir():
        if path.is_file() and path.suffix in ('.json', '.log', '.xml', '.txt'):
            members[path.relative_to(ROOT).as_posix()] = path
    for path in folder.glob('engine/Math/*.json'):
        members[path.relative_to(ROOT).as_posix()] = path
    for kind in ('lua', 'collision'):
        path = folder/('upstream-'+kind+'-case-inventory.txt')
        require(path.is_file() and path.read_text().strip() and '0 test cases' not in path.read_text(),
                'Actual nonempty upstream Catch case discovery required')
    closure = {name: sha(path) for name, path in sorted(members.items())}
    output = folder.with_suffix('.tar.gz'); require(not output.exists(), 'Fresh sealed package required')
    with tarfile.open(output, 'w:gz', compresslevel=6) as archive:
        for name, path in sorted(members.items()):
            archive.add(path, arcname=name, recursive=False)
    require(all(sha(path) == closure[name] for name, path in members.items()), 'Package changed during retention')
    report = dict(protocol='phase6-hosted-full-native-package-v1', status='built-and-unit-tested-only',
        source_commit=producer, configuration=record['configuration'], math_profile=record['math_profile'],
        builder_sha256=record['builder_sha256'], retention_helper_sha256=sha(__file__),
        build_manifest_sha256=sha(build), archive_sha256=sha(output), archive_bytes=output.stat().st_size,
        archive_members_sha256=closure, tests=tests, cloud_builds_used=True,
        runtime_qualification_pending=True, full_stock_capture_pending=True,
        native_admission_qualified=False, phase6_complete=False)
    (folder/'hosted-package.json').write_text(json.dumps(report, indent=2)+'\n')
    print('Retained complete sanitized runtime and actual unit results:', output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('dependencies', 'package'))
    parser.add_argument('--package', type=Path)
    args = parser.parse_args()
    if args.action == 'dependencies':
        dependencies()
    else:
        require(args.package is not None, 'Explicit actual package root required')
        package(args.package)


if __name__ == '__main__':
    main()
