#!/usr/bin/env python3
"""Compare complete passive internal-state rows, with no acceptance credit."""
import argparse
import csv
import json
import math
from pathlib import Path

from compare import bits, sha


KEYS = ('tick', 'seconds', 'object', 'kind')


def read(path, first, last):
    with path.open() as stream:
        reader = csv.DictReader(stream)
        fields = reader.fieldnames
        if not fields or tuple(fields[:4]) != KEYS or len(set(fields)) != len(fields):
            raise ValueError('Unique internal-state field closure required')
        rows = list(reader)
    result = {}
    ticks = []
    for row in rows:
        if set(row) != set(fields) or any(value is None for value in row.values()):
            raise ValueError('Incomplete internal-state row')
        tick = int(row['tick'])
        key = (tick, row['object'], row['kind'])
        if key in result or not row['object'] or row['kind'] not in ('vessel', 'aggregate'):
            raise ValueError('Unique actual object/kind observations required')
        if any(not math.isfinite(float(row[f])) for f in fields if f not in ('object', 'kind')):
            raise ValueError('Nonfinite internal-state observation')
        result[key] = row
        ticks.append(tick)
    if ticks != sorted(ticks):
        raise ValueError('Ordered internal-state ticks required')
    identities = {(obj, kind) for tick, obj, kind in result}
    expected = {(tick, obj, kind) for tick in range(first, last + 1) for obj, kind in identities}
    if not identities or set(result) != expected:
        raise ValueError('Complete investigated ticks and stable object/kind roster required')
    return fields, result


def compare(windows, native, first=1, last=243):
    guarded = {str(path): sha(path) for path in (windows, native)}
    fields, left = read(windows, first, last)
    other_fields, right = read(native, first, last)
    if fields != other_fields or set(left) != set(right):
        raise ValueError('Internal-state field or object/kind closure differs')
    first_differences = {}
    counts = {}
    for key in sorted(left):
        tick, obj, kind = key
        a, b = left[key], right[key]
        if bits(a['seconds']) != bits(b['seconds']):
            raise ValueError('Observed internal-state clocks differ')
        for field in fields[4:]:
            if bits(a[field]) == bits(b[field]):
                continue
            identity = obj + '/' + kind
            counts.setdefault(identity, {}).setdefault(field, 0)
            counts[identity][field] += 1
            entity = first_differences.setdefault(identity, {})
            entity.setdefault(field, dict(tick=tick, seconds=a['seconds'], windows=a[field], native=b[field],
                windows_bits=bits(a[field]), native_bits=bits(b[field]), delta=float(b[field])-float(a[field])))
    if any(sha(Path(path)) != value for path, value in guarded.items()):
        raise ValueError('Internal-state inputs changed during comparison')
    return dict(status='compared-complete-internal-state-diagnostic-only', ticks=[first, last],
        rows_per_runtime=len(left), object_kinds=sorted({obj+'/'+kind for tick,obj,kind in left}),
        first_differing_fields=first_differences, differing_row_counts=counts, evidence_sha256=guarded,
        abi_fences='Observer requires exact public/internal position, velocity and matrix agreement before each row',
        simulator_acceptance=False, phase6_complete=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--windows', type=Path, required=True)
    parser.add_argument('--native', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--first',type=int,default=1)
    parser.add_argument('--last',type=int,default=243)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Fresh internal-state comparison output required')
    if not 1<=args.first<=args.last<=960:raise ValueError('Bounded complete internal tick interval required')
    result = compare(args.windows, args.native,args.first,args.last)
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({key: min(v['tick'] for v in fields.values())
                      for key, fields in result['first_differing_fields'].items()}, indent=2))
