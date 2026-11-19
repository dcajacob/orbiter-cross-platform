"""Stage optional NASSP content for an existing native Linux Orbiter engine."""
import argparse
import os
from pathlib import Path
import shutil
import tempfile


def add_files(source, target, *, skip=()):
    """Preserve existing stock files and never install old binaries with the data."""
    if not source.is_dir():
        raise FileNotFoundError(source)
    for directory, children, files in os.walk(source):
        relative = Path(directory).relative_to(source)
        if relative == Path('.'):
            children[:] = [name for name in children if name not in skip]
        dest = target / relative
        dest.mkdir(parents=True, exist_ok=True)
        for name in files:
            file = dest / name
            if not file.exists() and file.suffix.lower() not in {'.dll', '.so', '.exe'}:
                shutil.copy2(Path(directory) / name, file)


def stage(args, root):
    pkg = args.apollo_package
    resources = root / 'resources'
    add_files(args.stock_assets, resources)
    add_files(args.stock_sound / 'XRSound', resources / 'XRSound')
    add_files(pkg / 'resources', resources, skip={'Modules'})
    # The two distributions enable different ScriptMFD entries. Keep all active entries.
    registry = Path('Config/MFD/ScriptMFD.cfg')
    existing = (resources / registry).read_text().splitlines()
    active = {line.strip().casefold() for line in existing}
    for entry in (pkg / 'resources' / registry).read_text().splitlines():
        if entry.strip() and not entry.lstrip().startswith(';') and entry.strip().casefold() not in active:
            existing.append(entry)
            active.add(entry.strip().casefold())
    (resources / registry).write_text('\n'.join(existing) + '\n')
    add_files(args.stock_data, root / 'celestial-data')
    add_files(pkg / 'celestial-data' / 'Config', root / 'celestial-data' / 'Config')
    target = root / 'NativeModules'
    shutil.copytree(args.engine / 'NativeModules', target)
    apollo = args.nassp_build / 'NativeModules'
    shutil.copytree(apollo / 'Vessel/ProjectApollo', target / 'Vessel/ProjectApollo')
    for plugin in ('ApolloRTCCMFD', 'ProjectApolloMFD'):
        shutil.copy2(apollo / 'Plugin' / (plugin + '.so'), target / 'Plugin')
    for file in (args.stage_build / 'stage.so', args.vesselbuilder_build / 'VesselBuilder1.so'):
        shutil.copy2(file, target / 'Vessel')
    # Use the original bundle only for its manifests, notices and data. All modules
    # must be present in the new build, which performs its own ABI check on load.
    for original in (pkg / 'engine/NativeModules').rglob('*.so'):
        expected = target / original.relative_to(pkg / 'engine/NativeModules')
        if not expected.is_file():
            raise FileNotFoundError(f'Missing newly built module: {expected}')
    shutil.copytree(pkg / 'licenses', root / 'licenses')
    shutil.copy2(pkg / 'engine/NativeModules/Licenses/VesselBuilder1-LICENSE.txt', target / 'Licenses')
    shutil.copy2(pkg / 'qualification/build.json', root / 'apollo-input-build.json')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('engine', 'stock-assets', 'stock-data', 'stock-sound', 'apollo-package',
                 'nassp-build', 'stage-build', 'vesselbuilder-build', 'destination'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    destination = args.destination.resolve()
    if destination.exists():
        parser.error(f'Choose a new staging directory: {destination} exists')
    with tempfile.TemporaryDirectory(dir=destination.parent) as temp:
        staged = Path(temp) / 'content'
        stage(args, staged)
        staged.rename(destination)


if __name__ == '__main__':
    main()
