#!/usr/bin/env python3
"""Validate ledger bindings and checklist completeness; this is not a runtime gate auditor."""
import argparse
from pathlib import Path
import re

from checklist import requirements
from contracts import ROOT, atomic_json, load, require, sha

STATUSES = ('not-run','in-progress','failed','blocked','passed')


def validate(path, verify_files=True):
    manifest = load(path)
    expected = requirements()
    require(manifest['schema'] == 1 and manifest['protocol'] == 'phase6-closeout-v1', 'Unknown closeout protocol')
    require(manifest['checkpoint_commit'] == '0842893ba8b3807f67245c78d729a4758dab3fdd', 'Preserved checkpoint differs')
    require(set(manifest['gates']) == set(expected), 'Finite gate checklist differs')
    for name, specification in expected.items():
        gate = manifest['gates'][name]
        require(gate['expected'] == specification and gate['result'] in STATUSES, 'Gate requirement/status differs: ' + name)
        if gate['result'] == 'passed':
            require(gate['evidence'] and all(manifest['gates'][p]['result'] == 'passed' for p in specification['depends_on']),
                    'Passed gate lacks evidence or completed dependencies: ' + name)
            require(gate['coverage'] == specification and gate['diagnostic_only'] is False,
                    'Diagnostic or partial evidence cannot close a gate: ' + name)
            if specification.get('final_candidate_required', True):
                require(manifest['candidate']['frozen'] is True and gate['candidate_id'] == manifest['candidate']['id'],
                        'Gate evidence is not bound to the frozen candidate: ' + name)
        for record in gate['evidence']:
            require(re.fullmatch('[0-9a-f]{64}', record['sha256']) and Path(record['path']).is_absolute(),
                    'Absolute local evidence path and SHA256 required')
            if verify_files:
                require(sha(record['path']) == record['sha256'], 'Gate evidence bytes differ: ' + name)
    candidate = manifest['candidate']
    if candidate['frozen']:
        require(re.fullmatch('[0-9a-f]{40}', candidate['source_commit']) and candidate['id'] and
                set(candidate['identities']) == {'application','sdk','observer','runner','reference','dependencies','runtime'},
                'Frozen candidate identity closure missing')
        require(all(candidate['identities'].values()), 'Frozen candidate identity closure empty')
    software = all(g['result'] == 'passed' for n,g in manifest['gates'].items() if n != 'controller')
    complete = software and manifest['gates']['controller']['result'] == 'passed'
    require(manifest['software_complete'] is software and manifest['phase6_complete'] is complete,
            'Completion flags differ from complete gates')
    for record in manifest['protected_documents']:
        if verify_files:
            require(sha(ROOT / record['path']) == record['sha256'], 'Locked acceptance input changed')
    return dict(status='passed-ledger-structure-and-evidence-bindings',
                runtime_acceptance_reaudited=False, software_complete=software, phase6_complete=complete,
                closed_gates=[n for n,g in manifest['gates'].items() if g['result']=='passed'],
                open_gates=[n for n,g in manifest['gates'].items() if g['result']!='passed'])


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',type=Path,default=ROOT/'Docs/Production/Phase6Closeout.json')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    require(not args.output.exists(), 'Fresh ledger validation output required')
    atomic_json(args.output,validate(args.manifest))
