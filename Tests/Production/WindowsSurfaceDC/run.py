#!/usr/bin/env python3
"""Run real GDI interop controls alongside the accepted Windows scene/numerical gate."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT/'Tests/Production/Client'),str(ROOT/'Tests/Production')]
import run_client


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def sha_lf(path):return hashlib.sha256(path.read_bytes().replace(b'\r\n',b'\n')).hexdigest()


def main():
    parser=argparse.ArgumentParser(add_help=False)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--baseline',type=Path,required=True)
    args,remaining=parser.parse_known_args()
    output=args.output.resolve()
    baseline=args.baseline.resolve()
    if json.loads((baseline/'client-summary.json').read_text())['status']!='passed':
        raise ValueError('A passed ordinary real-client run is required')
    sys.argv=[sys.argv[0],*remaining,'--output',str(output)]
    source_paths={*HERE.glob('*.py'),*HERE.glob('*.cpp'),*HERE.glob('CMakeLists.txt')}
    source_paths.update(ROOT/'Src/Vessel/Dragonfly'/name for name in ('WglBitmapTarget.h','WglContext.h'))
    for module in list(sys.modules.values()):
        name=getattr(module,'__file__',None)
        if name:
            path=Path(name).resolve()
            if ROOT in path.parents and path.suffix=='.py':source_paths.add(path)
    raw_source={path.relative_to(ROOT).as_posix():sha(path) for path in source_paths}
    source={path.relative_to(ROOT).as_posix():sha_lf(path) for path in source_paths}
    producer=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
    for name,expected in source.items():
        body=subprocess.check_output(['git','-C',str(ROOT),'show',producer+':'+name])
        if hashlib.sha256(body.replace(b'\r\n',b'\n')).hexdigest()!=expected:
            raise ValueError('GDI observer differs from producer after LF normalization: '+name)
    original_stage=run_client.stage
    def stage(*stage_args,**options):
        before=options.pop('before_launch')
        def configure(directory):
            before(directory)
            config=directory/'Orbiter.cfg'
            text=config.read_text()
            if text.count('  OGLClient\n')!=1:raise ValueError('Actual client activation differs')
            config.write_text(text.replace('  OGLClient\n','  OGLClient\n  ProductionSurfaceDCDriver\n'))
        return original_stage(*stage_args,**options,before_launch=configure)
    run_client.stage=stage
    run_client.main()
    results={}
    for name in ('scene','scene-repeat'):
        folder=output/name
        if (folder/'surface-dc-failure.txt').exists():raise ValueError((folder/'surface-dc-failure.txt').read_text())
        result=json.loads((folder/'surface-dc-result.json').read_text())
        if result['status']!='passed' or result['roundtrips']!=100 or result['pixel_checks']!=18200 or \
                result['foreign_context_roundtrips']!=50 or result['offscreen_target_readbacks']!=2 or \
                result['gdi_objects_after']>result['gdi_objects_before']:
            raise ValueError('Real GDI round-trip/context/lifetime controls incomplete')
        client=json.loads((folder/'client-report.json').read_text())
        expected=sha(folder/'Modules/Plugin/ProductionSurfaceDCDriver.dll')
        if not any(Path(item['path']).name.lower()=='productionsurfacedcdriver.dll' and item['sha256']==expected
                   for item in client['loaded_modules']):raise ValueError('Actual surface test DLL is not loaded')
        for filename in ('scene.rgba','behavior-state.csv','behavior-events.csv',
                         'behavior-propellant.csv','behavior-animations.csv'):
            if (folder/filename).read_bytes()!=(baseline/name/filename).read_bytes():
                raise ValueError('GDI exercise changed the ordinary real scene: '+filename)
        results[name]=dict(result,driver_sha256=expected,client_report_sha256=sha(folder/'client-report.json'),
                          result_sha256=sha(folder/'surface-dc-result.json'),
                          ordinary_frame_sha256=sha(baseline/name/'scene.rgba'))
    if raw_source!={name:sha(ROOT/name) for name in raw_source}:raise ValueError('GDI observer changed during execution')
    report=dict(status='passed',producer_commit=producer,source_sha256_lf=source,source_raw_sha256=raw_source,runs=results,
                scope='Real Windows public surface API/GDI/OpenGL pixel, context and ownership controls; '
                      'accepted complete Sol/ISS/ShuttlePB scene and original numerical comparison run twice. '
                      'This does not qualify Dragonfly stock cockpits or complete Phase 6.')
    (output/'surface-dc-verification.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
