"""Explicit corrected-API variant for the normal stock runner and its auditor."""
import json
from pathlib import Path, PurePosixPath
import shutil
import stat

from prepare import ROOT, ORIGINAL, EARTH, corrected, digest, require
import qualification
import startup_contract


def reference(path):
    if path is None:return None
    path=Path(path).resolve();body=qualification.inspect(path)
    return dict(path=str(path),sha256=digest(path.read_bytes()),body=body)


def policy(name,case,selected):
    if selected is None or name!=startup_contract.settings()['scenario']:return None
    cfg=startup_contract.settings()
    require(case['sha256_lf']==cfg['scenario_sha256_lf'] and case['ships']==cfg['vessels'],
            'Qualified API scenario or original vessel roster differs')
    require(selected['body']['status']=='qualified-general-api-correction-v2' and selected['body']['policy']==cfg,
            'Specific API correction/exit qualification missing')
    return cfg


def stage_assets(assets,output):
    """Make a private byte copy. Never edit the canonical stock script or inputs."""
    assets=Path(assets);output=Path(output);require(not output.exists(),'Fresh private API asset variant required')
    original=(assets/ORIGINAL).read_bytes();require(original==(ROOT/ORIGINAL).read_bytes(),'Canonical original API script differs')
    shutil.copytree(assets,output,copy_function=shutil.copy2)
    for folder in [output,*(p for p in output.rglob('*') if p.is_dir())]:
        folder.chmod(stat.S_IMODE(folder.stat().st_mode)|stat.S_IWUSR|stat.S_IXUSR)
    script=output/ORIGINAL;script.unlink();body,oracle=corrected(original,(ROOT/EARTH).read_bytes(),'v2');script.write_bytes(body)
    files={}
    for path in assets.rglob('*'):
        if path.is_file():
            name=path.relative_to(assets).as_posix();before=digest(path.read_bytes());after=digest((output/name).read_bytes())
            require(after==(digest(body) if name==ORIGINAL else before),'API private variant changed another asset: '+name)
            files[name]=dict(original=before,variant=after)
    require((assets/ORIGINAL).read_bytes()==original,'Canonical original API script changed')
    manifest=dict(protocol='general-api-private-stock-assets-v1',test_variant='general-api-spice-test-correction-v2',
                  canonical_assets=str(assets.resolve()),variant_assets=str(output.resolve()),files_sha256=files,oracle=oracle)
    return manifest


def inspect(out,case,selected,profile,returncode):
    cfg=policy(startup_contract.settings()['scenario'],case,selected);require(cfg is not None,'Specific API variant not enabled')
    out=Path(out);argv=json.loads((out/'invocation.json').read_text())
    def argument(flag):
        require(argv.count(flag)==1 and argv.index(flag)+1<len(argv),'API invocation flag missing/duplicated: '+flag)
        return argv[argv.index(flag)+1]
    assets=Path(argument('--assets'));scenario=Path(argument('--scenario'));saved=Path(argument('--save'))
    manifest=json.loads((out/'api-asset-variant.json').read_text())
    require(manifest['protocol']=='general-api-private-stock-assets-v1' and manifest['variant_assets']==str(assets) and
            manifest['test_variant']==cfg['test_variant'] and scenario==assets/'Scenarios'/cfg['scenario'] and saved==out/'saved.scn' and
            argument('--frames')=='60' and float(argument('--fixed-step'))==cfg['fixed_step'],
            'Actual corrected API private assets/entry point/exit protocol differs')
    canonical=Path(manifest['canonical_assets'])
    require(set(manifest['files_sha256'])=={p.relative_to(canonical).as_posix() for p in canonical.rglob('*') if p.is_file()}==
            {p.relative_to(assets).as_posix() for p in assets.rglob('*') if p.is_file()}, 'Complete private API asset inventory differs')
    for name,record in manifest['files_sha256'].items():
        path=PurePosixPath(name)
        require(str(path)==name and not path.is_absolute() and '..' not in path.parts and ':' not in name and '\\' not in name,
                'Unsafe API asset manifest path')
        require(digest((assets/name).read_bytes())==record['variant'] and
                digest((canonical/name).read_bytes())==record['original'] and
                (name==ORIGINAL or record['variant']==record['original']), 'Actual API variant/canonical asset bytes differ')
    result=startup_contract.inspect_native(out,profile,returncode,assets/ORIGINAL,scenario,saved)
    result['qualification_sha256']=selected['sha256']
    result['asset_variant_sha256']=digest((out/'api-asset-variant.json').read_bytes())
    return result
