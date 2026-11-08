"""Finite capture scope and terminal contracts; collection never grants acceptance."""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

PROFILES = ('Debug-automatic', 'Debug-sse2', 'Release-automatic', 'Release-sse2')
PHASES = ('stock-writer', 'windows-save-reload')
COHORTS = ('original-windows', 'current-windows', 'native')
ROOT = Path(__file__).resolve().parents[3]


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


def atomic_json(path, value):
    path = Path(path)
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
    temporary.replace(path)


def case_ids():
    cases = load(ROOT / 'Tests/Production/RemainingStock/cases.json')['cases']
    ids = tuple(case['id'] for case in cases)
    require(len(ids) == len(set(ids)) == 38, 'Locked complete 38-scene inventory required')
    return ids


@dataclass(frozen=True)
class Scope:
    cases: tuple
    selected: bool

    @classmethod
    def make(cls, selected=None):
        all_cases = case_ids()
        if selected is None:
            return cls(all_cases, False)
        require(type(selected) is list and selected and len(set(selected)) == len(selected),
                'Nonempty unique explicit diagnostic selection required')
        require(set(selected) <= set(all_cases), 'Unknown diagnostic scene')
        require(selected == [case for case in all_cases if case in selected],
                'Diagnostic scenes must retain canonical order')
        return cls(tuple(selected), True)

    @property
    def selection(self):
        return list(self.cases) if self.selected else None

    @property
    def terminal(self):
        return 'captured-diagnostic-only' if self.selected else 'captured-awaiting-independent-persistence-audit'

    def inspect_terminal(self, report, profile, phase):
        require(profile in PROFILES and phase in PHASES, 'Unknown profile or phase')
        require(report['status'] == self.terminal and report['diagnostic_only'] is self.selected,
                'Terminal capture scope/status differs')
        require(report['cases_requested'] == list(self.cases) and set(report['cases']) == set(self.cases),
                'Terminal capture case closure differs')
        require(report['repeats'] == 2 and report['frames'] == 960 and not report['failures'] and
                report['phase'] == phase and report['runtime_identity']['profile'] == profile,
                'Terminal capture protocol or result differs')
        require(report['native_admission_qualified'] is False and report['phase6_complete'] is False,
                'A capture cannot claim acceptance')
        require(all(len(report['cases'][case]['runs']) == 2 for case in self.cases),
                'Both completed repetitions required')
        return len(self.cases) * 2


def reusable_capture(root, expected_sha, scope, profile, phase, producer, runtime, inspect):
    """Re-read closed bytes with the owning independent reader, even on reuse."""
    path = Path(root) / 'capture.json'
    require(sha(path) == expected_sha, 'Closed capture digest differs')
    report = load(path)
    scope.inspect_terminal(report, profile, phase)
    require(report['producer_commit'] == producer and report['runtime_source_commit'] == runtime,
            'Closed capture source/runtime identity differs')
    actual = inspect(Path(root), profile, phase, scope.selection)
    require(actual['status'] == 'audited-native-phase-only' and
            actual['diagnostic_only'] is scope.selected and actual['capture_sha256'] == expected_sha and
            actual['actual_processes'] == len(scope.cases) * 2 and actual['owning_bytes_unchanged'] is True,
            'Closed capture independent audit differs')
    require(sha(path) == expected_sha, 'Closed capture changed during reuse')
    return actual
