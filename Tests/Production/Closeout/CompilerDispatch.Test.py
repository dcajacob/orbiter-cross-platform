#!/usr/bin/env python3
"""Conserve every runtime byte outside the explicit compiler dispatch binding."""
import importlib.util
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location('compiler_dispatch_source_controls', ROOT/'Tests/Production/random_source.py')
source = importlib.util.module_from_spec(spec); spec.loader.exec_module(source)


class CompilerDispatchTests(unittest.TestCase):
    def test_selected_pointer_capture_is_the_only_rigid_body_delta(self):
        before = subprocess.check_output(['git', '-C', str(ROOT), 'show',
            '4fbeb21dd93bec9a78396aae38a97d184e78c5a8:Src/Orbiter/Rigidbody.cpp']).decode('cp1252').replace('\r\n', '\n')
        current = (ROOT/'Src/Orbiter/Rigidbody.cpp').read_bytes().decode('cp1252').replace('\r\n', '\n')
        self.assertEqual(source.restore_rigid_dispatch(current), before)

    def test_source_reader_rejects_changed_selection_arguments_or_duplicate_binding(self):
        current = (ROOT/'Src/Orbiter/Rigidbody.cpp').read_bytes().decode('cp1252').replace('\r\n', '\n')
        for body in (
            current.replace('const LinAngPropagator propagate = PropMode[PropLevel].propagator;',
                            'const LinAngPropagator propagate = PropMode[PropLevel+1].propagator;'),
            current.replace('((*this).*propagate) (dt, nPropSubsteps, i);',
                            '((*this).*propagate) (dt, 1, i);'),
            current + current,
        ):
            with self.assertRaises(ValueError):
                source.restore_rigid_dispatch(body)

    def test_complete_original_free_spin_assertions_and_steps_remain_byte_identical(self):
        path = 'Tests/Production/Boundary/RigidBody.Test.cpp'
        before = subprocess.check_output(['git', '-C', str(ROOT), 'show', '4fbeb21d:'+path])
        self.assertEqual((ROOT/path).read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
