#!/usr/bin/env python3
"""Observe CRT version/dispatch differences; this is not the simulator parity gate."""
import argparse
import csv
import hashlib
import io
import json
import math
import os
from pathlib import Path
import platform
import struct
import subprocess
import sys

HERE = Path(__file__).resolve().parent
CRITICAL = float.fromhex('0x1.e92199644661ep-2')
PROFILES = ('default', 'sse2', 'fma3')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def bits(value):
    return struct.pack('>d', value).hex()


def number(value):
    return struct.unpack('>d', bytes.fromhex(value))[0]


def corpus():
    values = [CRITICAL, 0., -0., 1., -1., math.ulp(0.), -math.ulp(0.)]
    values += [i / 4096 for i in range(-4096, 4097)]
    for centre in (CRITICAL, -CRITICAL, .5, -.5, 1., -1.):
        for direction in (-math.inf, math.inf):
            x = centre
            for _ in range(32):
                x = math.nextafter(x, direction)
                if abs(x) <= 1:
                    values.append(x)
    return list(dict.fromkeys(map(bits, values)))


def parse(raw, inputs, profile, configuration, external):
    first, rows = raw.split('\n', 1)
    metadata = json.loads(first)
    rows = list(csv.DictReader(io.StringIO(rows)))
    require(metadata['configuration'] == configuration, 'Wrong probe build')
    require([row['input'] for row in rows] == inputs, 'Incomplete or reordered probe corpus')
    require(metadata['active_fma3'] in (0, 1), 'Invalid CRT dispatch state')
    require(profile != 'sse2' or metadata['active_fma3'] == 0, 'SSE2 was not selected')
    require(profile != 'default' or metadata['active_fma3'] == metadata['initial_fma3'],
            'Default dispatch was modified')
    require(metadata['cpuid_fma'] or metadata['active_fma3'] == 0,
            'CRT enabled FMA3 without CPU support')
    require(metadata['mxcsr'] & 0x6000 == 0, 'Non-default rounding mode')
    for row in rows:
        require(set(row) == {'input', 'linked', 'exported'}, 'Unexpected probe columns')
        for field in ('linked', 'exported'):
            require(len(row[field]) == 16 and math.isfinite(number(row[field])) and
                    abs(number(row[field])) <= math.pi / 2, 'Invalid arcsine result')
        require(external or row['linked'] == row['exported'], 'Linked call differs from its CRT export')
    return metadata, rows


def ordered(value):
    n = int(value, 16)
    return (~n) & ((1 << 64) - 1) if n >> 63 else n | (1 << 63)


def compare(left, right, field='exported'):
    require([r['input'] for r in left] == [r['input'] for r in right], 'Comparison corpora differ')
    differences = [dict(input=a['input'], left=a[field], right=b[field],
                        ulps=abs(ordered(a[field]) - ordered(b[field])))
                   for a, b in zip(left, right) if a[field] != b[field]]
    return dict(samples=len(left), different=len(differences),
                maximum_ulps=max((x['ulps'] for x in differences), default=0),
                first_differences=differences[:10])


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    require(sys.platform == 'win32', 'This diagnostic requires native Windows')
    require(not args.output.exists(), 'Diagnostic output already exists')
    output = args.output.resolve()
    output.mkdir(parents=True)
    inputs = corpus()
    input_text = '\n'.join(inputs) + '\n'
    (output / 'inputs.txt').write_text(input_text, encoding='ascii')
    report = dict(status='pending', purpose='CRT diagnostic, not simulator acceptance',
                  source=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
                  platform=platform.platform(), windows_version=list(sys.getwindowsversion()),
                  image={key: os.environ.get(key) for key in ('ImageOS', 'ImageVersion')},
                  samples=len(inputs), corpus_sha256=hashlib.sha256(input_text.encode()).hexdigest(),
                  captures={}, comparisons={}, build_commands={})
    save(output / 'report.json', report)
    try:
        executables = {}
        for configuration, flags in [('Debug', ['/MDd', '/Od']), ('Release', ['/MD', '/O2'])]:
            executable = output / (configuration + '.exe')
            command = ['cl.exe', '/nologo', '/EHsc', '/std:c++17', '/W4', '/WX', '/fp:precise',
                       '/Oi-', *flags, str(HERE / 'Probe.cpp'), '/Fe' + str(executable),
                       '/Fo' + str(output / (configuration + '.obj')), '/link', 'version.lib']
            report['build_commands'][configuration] = command
            result = subprocess.run(command, capture_output=True, text=True, timeout=120)
            (output / (configuration + '-build.log')).write_text(result.stdout + result.stderr, encoding='utf-8')
            require(result.returncode == 0, configuration + ' probe compilation failed: ' + result.stdout + result.stderr)
            executables[configuration] = executable
        kits = Path(os.environ['ProgramFiles(x86)']) / 'Windows Kits/10'
        candidates = sorted(set(kits.glob('bin/*/x64/ucrt/ucrtbased.dll')) |
                            set(kits.glob('Redist/*/ucrt/DLLs/x64/ucrtbase.dll')) |
                            set(kits.glob('Redist/ucrt/DLLs/x64/ucrtbase.dll')))
        report['sdk_candidates'] = [str(p) for p in candidates]
        targets = [('Debug', 'Debug', None), ('Release', 'Release', None)]
        targets += [(f'sdk-{i}', 'Release', path) for i, path in enumerate(candidates)]
        captures = {}
        for target, configuration, dll in targets:
            for profile in PROFILES:
                name = target + '-' + profile
                command = [str(executables[configuration]), profile] + ([str(dll)] if dll else [])
                repeats = []
                for repeat in range(2):
                    result = subprocess.run(command, input=input_text, capture_output=True,
                                            text=True, encoding='utf-8', timeout=60)
                    (output / f'{name}-{repeat}.txt').write_text(result.stdout, encoding='utf-8')
                    (output / f'{name}-{repeat}.stderr').write_text(result.stderr, encoding='utf-8')
                    require(result.returncode == 0, name + ' failed: ' + result.stderr)
                    repeats.append(parse(result.stdout, inputs, profile, configuration, dll is not None))
                require(repeats[0] == repeats[1], name + ' changed across fresh processes')
                metadata, rows = repeats[0]
                for key in ('linked_provider', 'exported_provider'):
                    path = Path(metadata[key]['path'])
                    metadata[key]['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
                metadata.update(profile=profile, requested_dll=str(dll) if dll else None,
                                repeat_exact=True, critical=rows[0],
                                linked_vs_exported_different=sum(r['linked'] != r['exported'] for r in rows))
                if dll:
                    metadata['requested_sha256'] = hashlib.sha256(dll.read_bytes()).hexdigest()
                    metadata['loaded_requested_file'] = os.path.samefile(dll, metadata['exported_provider']['path'])
                report['captures'][name] = metadata
                captures[name] = rows
                print(name, json.dumps(metadata['exported_provider']), metadata['critical'], flush=True)
                save(output / 'report.json', report)
            report['comparisons'][target + '-default-vs-sse2'] = compare(captures[target + '-default'], captures[target + '-sse2'])
            report['comparisons'][target + '-default-vs-fma3'] = compare(captures[target + '-default'], captures[target + '-fma3'])
            if dll:
                for profile in PROFILES:
                    report['comparisons'][target + '-vs-Release-' + profile] = compare(captures[target + '-' + profile], captures['Release-' + profile])
        for profile in PROFILES:
            report['comparisons']['Debug-vs-Release-' + profile] = compare(captures['Debug-' + profile], captures['Release-' + profile])
        # Compare actual co-version providers directly, rather than inferring
        # equivalence from their separate difference counts against the OS CRT.
        for i, (left, _, _) in enumerate(targets):
            for right, _, _ in targets[i + 1:]:
                a = report['captures'][left + '-default']['exported_provider']
                b = report['captures'][right + '-default']['exported_provider']
                if a['product_version'] == b['product_version']:
                    for profile in PROFILES:
                        report['comparisons']['same-version-' + left + '-vs-' + right + '-' + profile] = compare(
                            captures[left + '-' + profile], captures[right + '-' + profile])
        report['status'] = 'observed'
        print(json.dumps(report['comparisons'], indent=2))
    except Exception as error:
        report.update(status='capture-failed', error=str(error))
        raise
    finally:
        save(output / 'report.json', report)


if __name__ == '__main__':
    main()
