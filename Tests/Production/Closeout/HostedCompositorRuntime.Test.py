"""Reject changed provider inventories and unsafe or mixed compositor dependency metadata."""
import unittest
from hosted_compositor_runtime import clauses,host_clauses,original_packages_unchanged


class HostedCompositorRuntimeTests(unittest.TestCase):
    def test_original_binary_grammar_retains_all_version_and_alternative_constraints(self):
        parsed=clauses('libinput10 (>= 1.25), libfoo:amd64 (= 1:2.0~rc1-1) | libbar, libc6 (>> 2.0)')
        self.assertEqual(len(parsed),3)
        self.assertEqual(parsed[0][1],[dict(name='libinput10',operator='>=',version='1.25')])
        self.assertEqual(parsed[1][1][0],dict(name='libfoo:amd64',operator='=',version='1:2.0~rc1-1'))
        self.assertEqual(parsed[1][1][1],dict(name='libbar',operator=None,version=None))
        for body in ('package;command','--option','package=$(command)','package (>= 1); command','lib | ../outside'):
            with self.assertRaises(ValueError):clauses(body)

    def test_only_exact_privately_retained_compositor_roles_are_removed(self):
        body='libweston-14-0, libinput10 (>= 1.25), libc6 | libc-other'
        self.assertEqual(host_clauses(body,{'libweston-14-0':'14.0.2-5'}),['libinput10 (>= 1.25)','libc6 | libc-other'])
        self.assertEqual(host_clauses(body,{}),['libweston-14-0','libinput10 (>= 1.25)','libc6 | libc-other'])

    def test_host_dependencies_cannot_upgrade_remove_or_relabel_original_providers(self):
        original={'libc6:amd64':'original-libc','libfontconfig1:amd64':'original-fontconfig'}
        self.assertEqual(original_packages_unchanged(original,original|{'libinput10:amd64':'required-host-version'}),
                         {'libinput10:amd64':'required-host-version'})
        for changed in ({'libc6:amd64':'replacement'},original|{'libfontconfig1:amd64':'replacement'}):
            with self.assertRaises(ValueError):original_packages_unchanged(original,changed)


if __name__=='__main__':unittest.main()
