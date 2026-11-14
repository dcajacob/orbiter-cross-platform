"""Run only the Linux Phase 7 selected stock scenarios in the real Windows client."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

PRODUCTION = Path.cwd() / "Tests/Production"
sys.path.insert(0, str(PRODUCTION / 'RemainingStock'))
from original import inspect_artifacts, mesa_files, shared
from inputs import ROOT, digest, settings, sha_lf
from stage_original import run as stage
from inventory import initial_ships, ships
from inputs import playback_vessels

SCENARIOS = (
    'Delta-glider/Docked at ISS.scn',
    'Shuttle-A/ISS Approach.scn',
    '2024 Edition/Space Shuttle ascent autopilot.scn',
    'Satellites and Probes/Hubble Space Telescope/HST Animation.scn',
    'Tutorials/DG to the moon.scn',
    '2024 Edition/3 Minute Tour of Kennedy Space Center.scn',
    '2024 Edition/Space Shuttle to ISS.scn',
    'Space Shuttle Atlantis/Atlantis ISS Resupply.scn',
    'Satellites and Probes/Hubble Space Telescope/HST Launch.scn',
    'Dragonfly/v1.0.0b PoweredUp.scn',
    'Navigation/Space Physics/Solar sail.scn',
    'Quadcopter/Quadcopter at KSC.scn',
    'Shuttle-A/Shuttle-A Drop.scn',
    'Delta-glider/Atmospheric autopilot.scn',
    'Shuttle-A/Olympus spaceport on Mars.scn',
    'The Solar System/Eclipses/Lunar eclipse 2004.scn',
)
VESSEL_DLLS = {
    'Atlantis', 'Atlantis_SRB', 'Atlantis_Tank', 'DeltaGlider', 'Dragonfly',
    'HST', 'Quadcopter', 'ShuttleA', 'ShuttleA_PL', 'ShuttlePB', 'SolarSail',
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def selection(config, producer):
    lock = json.loads((PRODUCTION / 'production-source.lock.json').read_text())
    hashes = {item['path']: item['sha256'] for item in lock['scenarios']}
    cases = {item['scenario']: item for item in config['cases']}
    for number, scenario in enumerate(SCENARIOS, 1):
        entry = 'Scenarios/' + scenario
        path = ROOT / entry
        require(sha_lf(path) == hashes[entry], 'Frozen scenario differs: ' + entry)
        text = path.read_bytes().decode('cp1252')
        case = cases.get(scenario, dict(scenario=scenario, scenario_entry_point=entry,
                         sha256_lf=hashes[entry], declared_vessels=ships(text),
                         playback_vessels=playback_vessels(text))).copy()
        case['id'] = f'phase7-stock-{number:02d}'
        if case['playback_vessels'] and 'recording_directory' not in case:
            name = Path(scenario).stem
            case['recording_directory'] = name
            folder = ROOT / 'Flights' / name
            for path in sorted(folder.iterdir()):
                if path.is_file():
                    relative = path.relative_to(ROOT).as_posix()
                    original = subprocess.check_output(['git','show',f'{producer}:{relative}'])
                    checksum = hashlib.sha256(original.replace(b'\r\n', b'\n')).hexdigest()
                    require(checksum == sha_lf(path), 'Recorded flight data differs: ' + relative)
                    config['recording_files_sha256_lf'][relative] = checksum
        yield case


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('runtime','data','planets','mesa','output'):
        p.add_argument('--'+name,type=lambda value: Path(value).resolve(),required=True)
    p.add_argument('--validate-selection',action='store_true')
    a=p.parse_args()
    producer=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    config = settings()
    cases = list(selection(config, producer))
    if a.validate_selection:
        print(f'Validated {len(cases)} locked stock scenes, 60 frames per scene.')
        return
    require(sys.platform=='win32', 'This test requires native Windows')
    os.environ.update(LIBGL_ALWAYS_SOFTWARE='true',GALLIUM_DRIVER='llvmpipe', ORBITER_TEST_OBSERVER_SSE2='1')
    application = a.runtime / 'Orbiter.exe'
    manifest = json.loads((a.runtime / 'test-runtime.json').read_text())
    require(manifest['source_commit'] == producer, 'The application and stock harness use different sources')
    expected = {}
    protected = dict(manifest['files'])
    for name in ('Modules/Plugin/ProductionCockpitDriver.dll', 'Modules/Plugin/OGLClient.dll'):
        protected[name] = digest(a.runtime/name)
    for name, checksum in protected.items():
        require(digest(a.runtime/name) == checksum, 'Runtime changed: ' + name)
        expected.setdefault(Path(name).name.lower(), set()).add(checksum)
    for item in config['delivery_repairs']:
        target = a.runtime / item['target']
        if target.is_file():
            require(sha_lf(target) == item['sha256_lf'], 'Current Dragonfly mesh differs')
            config = {**config, 'delivery_repairs': []}
    a.output.mkdir()
    result = dict(scope='Windows Phase 7 selected 60-frame stock smoke', source=producer,
                  math_profile='sse2', full_run=False, phase7_complete=False, cases={})
    report = a.output/'stock-report.json'
    coverage = set()
    for case in cases:
        directory = a.output/case['id']
        scenario_name = case['scenario']
        record = dict(scenario=scenario_name, status='failed')
        try:
            source = ROOT/case['scenario_entry_point']
            expected_vessels = initial_ships(source.read_bytes().decode('cp1252'))
            def configure(out):
                cfg=out/'Orbiter.cfg'
                text=cfg.read_text().replace('  ProductionBehaviorDriver','  ProductionCockpitDriver\n  OGLClient')
                if scenario_name == 'Delta-glider/Atmospheric autopilot.scn':
                    text=text.replace('  OGLClient','  OGLClient\n  LuaMFD')
                for line in ('PropStages = 1\n','PropStage0 = 1 1 1\n','PropSubsampling = 1\n'):
                    require(text.count(line)==1,'Original test fixture propagator setting differs')
                    text=text.replace(line,'')
                text+='\nFPS = 0\nMenubarMode = 1\nInfobarMode = 1\nInstrumentUpdateInterval = 0.25\n'
                cfg.write_text(text, encoding='ascii')
                target=out/case['scenario_entry_point']
                target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes(source.read_bytes())
                (out/'ogl-evidence.enabled').touch()
                mesa_files(a.mesa,out)
            stage(application,a.data,a.planets,directory,config,case,configure,process_timeout=120)
            record.update(inspect_artifacts(directory,case,config))
            require(record['actual_math']=='sse2','Actual stock process did not use SSE2')
            initial = {row['object']:row['class'].casefold() for row in shared.rows(directory/'stock-vessel-state.csv')
                       if row['tick']=='0'}
            require(all(initial.get(name)==kind.casefold() for name,kind in expected_vessels.items()),
                    'An expected original/generated vessel is missing or changed')
            mapped=shared.loaded_modules(directory,expected)
            names={Path(row['path']).name.casefold() for row in mapped}
            # The existing immutable class inventory covers the remaining modules.
            require(all(Path(item['original_module']).name.casefold() in names
                        for kind,item in config['classes'].items()
                        if kind in case['declared_vessels'].values() and item['module']),
                    'An expected class module is missing from the process map')
            if scenario_name == 'Delta-glider/Atmospheric autopilot.scn':
                require('luamfd.dll' in names or 'luaterminal.dll' in names, 'Lua Terminal DLL missing')
            coverage.update(name for name in VESSEL_DLLS if name.lower()+'.dll' in names)
            record.update(status='passed', loaded_modules=mapped)
        except Exception as error:
            record.update(status='failed', error=str(error))
        result['cases'][case['id']]=record
        print(case['id'], record['status'], scenario_name, record.get('error',''), flush=True)
        report.write_text(json.dumps(result,indent=2)+'\n')
    require(all(digest(a.runtime/name)==checksum for name,checksum in protected.items()),
            'Source-built Windows runtime changed during the checks')
    result.update(vessel_modules=sorted(coverage),
                  status='passed-sparse-stock' if len(coverage)==len(VESSEL_DLLS) and
                  all(case['status']=='passed' for case in result['cases'].values()) else 'failed')
    report.write_text(json.dumps(result,indent=2)+'\n')
    return result['status'] != 'passed-sparse-stock'


if __name__ == '__main__':
    sys.exit(main())
