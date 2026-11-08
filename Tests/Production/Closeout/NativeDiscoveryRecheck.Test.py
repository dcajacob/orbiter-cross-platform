#!/usr/bin/env python3
"""Reject mixed producer identities and partial/substituted retained case catalogues."""
import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('native_discovery_recheck_controls',HERE/'recheck_native_discovery.py')
reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader)


class NativeDiscoveryRecheckTests(unittest.TestCase):
    def record(self):
        return dict(repository={'owner':'dcajacob','repo':'orbiter-cross-platform'},
            run=dict(id=reader.RUN,head_sha=reader.PRODUCER,head_branch='qualification/native-package-retry',
                     path='.github/workflows/phase6-hosted-closeout.yml',run_attempt=1),
            artifact=dict(name='phase6-full-native-Debug-automatic',expired=False,digest='sha256:'+'a'*64,
                          workflow_run=dict(id=reader.RUN,head_sha=reader.PRODUCER)),
            jobs=[dict(id=1,run_id=reader.RUN,name='Complete sanitized native package Debug automatic',
                       status='completed',conclusion='failure',labels=['ubuntu-24.04'],steps=[
                dict(name='Build all stock families, normal host and unchanged upstream unit bodies with sanitizers',conclusion='success'),
                dict(name='Run every registered engine and upstream unit with ASan loaded before the Python math probe',conclusion='failure'),
                dict(name='Seal exact runtime, generated sources and actual test results without acceptance credit',conclusion='failure'),
                dict(name='Run actions/upload-artifact@v7',conclusion='success')])])

    def test_exact_failed_source_job_binding(self):
        self.assertEqual(reader.validate_api(self.record(),'Debug-automatic')['id'],1)
        for mutate in (
            lambda r:r['run'].update(head_sha='b'*40),
            lambda r:r['run'].update(id=reader.RUN+1),
            lambda r:r['run'].update(head_branch='another-branch'),
            lambda r:r['run'].update(run_attempt=2),
            lambda r:r['repository'].update(owner='another-owner'),
            lambda r:r['artifact'].update(expired=True),
            lambda r:r['artifact'].update(name='phase6-full-native-Release-automatic'),
            lambda r:r['jobs'][0]['steps'][0].update(conclusion='failure'),
            lambda r:r['jobs'][0]['steps'][1].update(conclusion='skipped'),
            lambda r:r['jobs'].append(copy.deepcopy(r['jobs'][0])),
        ):
            record=self.record();mutate(record)
            with self.assertRaises(ValueError):reader.validate_api(record,'Debug-automatic')

    def test_catalogue_must_include_every_original_name_tag_and_source_line(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'Unit.cpp';source.write_text('TEST_CASE("alpha", "[original]") {}\n')
            expected=reader.expected_cases(source.read_text());path=root/'discovery.xml'
            good=f'<MatchingTests><TestCase><Name>alpha</Name><Tags>[original]</Tags><SourceInfo><File>{source}</File><Line>1</Line></SourceInfo></TestCase></MatchingTests>'
            path.write_text(good);self.assertEqual(reader.inspect_discovery(path,expected,source)['cases'],['alpha'])
            for value in (good.replace('alpha','beta'),good.replace('[original]','[substitute]'),
                          good.replace('<Line>1</Line>','<Line>2</Line>'),'<MatchingTests/>',
                          good.replace('</MatchingTests>',good.split('<MatchingTests>')[1])):
                path.write_text(value)
                with self.assertRaises(ValueError):reader.inspect_discovery(path,expected,source)

    def test_actual_execution_rejects_missing_duplicate_skipped_or_failed_cases(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'execution.xml';source=Path(directory)/'Unit.cpp'
            case=f'<TestCase name="alpha" tags="[original]" filename="{source}" line="1"><Section><Expression success="true"/></Section><OverallResult success="true"/></TestCase>'
            good='<Catch><Group>'+case+'</Group><OverallResults successes="3" failures="0" expectedFailures="0"/><OverallResultsCases successes="1" failures="0" expectedFailures="0"/></Catch>'
            expected={'alpha':dict(tags=['[original]'],line=1)}
            p.write_text(good);self.assertEqual(reader.inspect_execution(p,expected,source)['cases'],['alpha'])
            for value in (good.replace('alpha','beta'),good.replace(case,''),good.replace(case,case*2),
                          good.replace('success="true"','success="false"'),good.replace('failures="0"','failures="1"'),
                          good.replace('expectedFailures="0"','expectedFailures="1"'),
                          good.replace('successes="1"','successes="0"'),good.replace('successes="3"','successes="0"'),
                          good.replace('[original]','[substitute]'),good.replace('line="1"','line="2"'),
                          good.replace('</Section>','<Skip/></Section>')):
                p.write_text(value)
                with self.assertRaises(ValueError):reader.inspect_execution(p,expected,source)

    def test_recheck_workflow_does_not_rebuild_or_modify_the_original_units(self):
        body=(reader.ROOT/'.github/workflows/phase6-native-discovery-recheck.yml').read_text()
        self.assertNotIn('cmake --build',body)
        self.assertIn('run_id = 42519601899',body)
        self.assertIn('digest !== artifact.digest',body)
        build=(reader.ROOT/'.github/workflows/phase6-hosted-closeout.yml').read_text()
        self.assertIn('existing_lua_unit" "$PACKAGE/upstream-units/assets" --list-tests',build)

    def test_archive_member_paths_cannot_escape(self):
        for name in ('../outside','/absolute','C:/outside','folder\\outside','folder/./alias'):
            with self.assertRaises(ValueError):reader.safe(name)

    def test_a_zero_exit_cannot_hide_native_sanitizer_diagnostics(self):
        reader.clean_sanitizers('All tests passed, 100 assertions in 15 test cases')
        for text in ('==12==ERROR: LeakSanitizer: detected memory leaks',
                     '==12==ERROR: AddressSanitizer: heap-use-after-free',
                     '/original/Rigidbody.cpp:254:12: runtime error: index out of bounds'):
            with self.assertRaises(ValueError):reader.clean_sanitizers(text)


if __name__=='__main__':unittest.main()
