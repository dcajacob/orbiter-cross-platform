#!/usr/bin/env python3
"""Guard config-only vessels, required modules, resource aliases and stock parsing."""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile

from inventory import Dependencies,LOCK,ROOT,digest,index,normalize,require,ships,initial_ships


def rejected(action):
    try:action()
    except ValueError:return True
    return False


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    require(not a.output.exists(),'Inventory control output exists')
    parsed=ships('BEGIN_SHIPS\n  Wheel:Wheel\n  STATUS Orbiting Moon\n  VROT 0 0 10\n  END\nMir\n STATUS Orbiting Earth\n END\nEND_SHIPS\n')
    require(parsed=={'Wheel':'Wheel','Mir':'Mir'},'Indented stock blocks or class-name shorthand differ')
    require(rejected(lambda:ships('BEGIN_SHIPS\nA:Wheel\nEND\nA:Mir\nEND\nEND_SHIPS')),
            'Duplicate stock vessel headers were hidden')
    def shuttle(configuration=''):
        return 'BEGIN_SHIPS\nSTS:Atlantis\n'+configuration+'\nEND\nEND_SHIPS\n'
    require(initial_ships(shuttle())=={'STS':'Atlantis'},'Original Atlantis default configuration differs')
    require(initial_ships(shuttle('CONFIGURATION 2'))=={'STS':'Atlantis','STS_ET':'Atlantis_Tank'},
            'Original tank-only initialization differs')
    require(initial_ships(shuttle('CONFIGURATION 0'))==dict(STS='Atlantis',STS_ET='Atlantis_Tank',
            **{'STS-SRB1':'Atlantis_SRB','STS-SRB2':'Atlantis_SRB'}),'Original launch-stack initialization differs')
    require(rejected(lambda:initial_ships('BEGIN_SHIPS\nSTS:Atlantis\nCONFIGURATION 0\nEND\nSTS_ET:Wheel\nEND\nEND_SHIPS\n')),
            'An incompatible generated-vessel name collision was accepted')
    require(rejected(lambda:normalize('../outside')) and normalize('Vessels\\.\\MiR')=='vessels/mir',
            'Resource path normalization differs')
    with tempfile.TemporaryDirectory(prefix='orbiter-stock-dependencies-') as temporary:
        base=Path(temporary);assets=base/'assets';modules=base/'modules'
        (assets/'Config/Vessels').mkdir(parents=True);(modules/'Vessel').mkdir(parents=True)
        (assets/'Config/Vessels/Wheel.cfg').write_text('MeshName = Wheel\nMass = 1e6\n')
        (assets/'Config/Vessels/Required.cfg').write_text('Module = Missing ; explicit required module\n')
        dep=Dependencies(assets,modules)
        wheel=dep.vessel('WHEEL');missing=dep.vessel('Required')
        require(not wheel['problems'] and wheel['module'] is None,'Intentional config-only vessel was classified as a missing DLL')
        require(missing['problems']==['missing native module: Missing'] and missing['module']['present'] is False,
                'Required missing module was treated as a generic fallback')
        (assets/'Config/Case').mkdir();(assets/'Config/case').mkdir()
        require(rejected(lambda:index(assets/'Config')),'Directory case aliases were silently accepted')
    lock=json.loads(LOCK.read_text());mismatches=[]
    require(len(lock['scenarios'])==157,'Frozen corpus count differs')
    for entry in lock['scenarios']:
        raw=(ROOT/entry['path']).read_bytes().replace(b'\r\n',b'\n')
        require(hashlib.sha256(raw).hexdigest()==entry['sha256'],'Frozen source bytes differ')
        actual=ships(raw.decode('cp1252'))
        require(initial_ships(raw.decode('cp1252')).items()>=actual.items(),
                'Initialization manifest omitted an original vessel')
        if actual!={s['name']:s['vessel_class'] for s in entry['objects']}:mismatches.append(entry['path'])
    result=dict(status='passed',source_sha256=digest(Path(__file__)),lock_sha256=digest(LOCK),
        locked_scenarios_verified=157,config_only_vessel_preserved=True,required_module_fallback_rejected=True,
        directory_aliases_rejected=True,corrected_parse_metadata=mismatches,
        frozen_scenario_bytes_and_lock_unchanged=True)
    a.output.write_text(json.dumps(result,indent=2)+'\n');print('Stock parser and dependency negative controls passed')


if __name__=='__main__':main()
