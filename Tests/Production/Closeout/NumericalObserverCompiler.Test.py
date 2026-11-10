from pathlib import Path
import unittest
import build_native_numerical_observers as observers


class NumericalObserverCompiler(unittest.TestCase):
    def test_only_two_exact_sanitized_source_commands_are_allowed(self):
        for kind in ['sdk','internal']:
            argv=observers.command(kind,'Debug-automatic',Path('/fixture/out'));observers.validate_command(argv,kind,'Debug-automatic',Path('/fixture/out'))
            self.assertIn('-fsanitize=address,undefined',argv)
            self.assertIn('-fno-omit-frame-pointer',argv)

    def test_compiler_macro_spoofing_is_rejected(self):
        argv=observers.command('sdk','Debug-automatic',Path('/fixture/out'));argv.insert(1,'-D__VERSION__="forged"')
        with self.assertRaises(ValueError):observers.validate_command(argv,'sdk','Debug-automatic',Path('/fixture/out'))

    def test_uninstrumented_observer_is_rejected(self):
        argv=observers.command('internal','Debug-automatic',Path('/fixture/out'));argv.remove('-fsanitize=address,undefined')
        with self.assertRaises(ValueError):observers.validate_command(argv,'internal','Debug-automatic',Path('/fixture/out'))

    def test_foreign_observer_source_is_rejected(self):
        argv=observers.command('internal','Debug-automatic',Path('/fixture/out'));argv[argv.index(str(observers.ROOT/observers.SOURCES['internal']))]='/tmp/foreign.cpp'
        with self.assertRaises(ValueError):observers.validate_command(argv,'internal','Debug-automatic',Path('/fixture/out'))


if __name__=='__main__':unittest.main()
