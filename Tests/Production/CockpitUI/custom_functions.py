"""Build the test-only public-SDK custom function module against this engine."""
from pathlib import Path
import subprocess
import shlex

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]

def build_probe(build,output):
    build=build.resolve()
    cache=(build/'CMakeCache.txt').read_text().splitlines()
    compiler=next(line.split('=',1)[1] for line in cache
                  if line.startswith('CMAKE_CXX_COMPILER:FILEPATH='))
    flags=shlex.split(next(line.split('=',1)[1] for line in cache if line.startswith('CMAKE_CXX_FLAGS:STRING=')))
    probe=output/'custom-function-probe.so'
    subprocess.run([compiler,*flags,'-std=c++17','-shared','-fPIC','-Wl,--no-undefined',
                    '-I'+str(ROOT/'Orbitersdk/include'),'-I'+str(ROOT/'Src/Orbiter'),
                    str(HERE/'CustomFunctionProbe.cpp'),'-L'+str(build),'-lorbiter_production_vessels',
                    '-lorbiter_production_boundary','-ldl','-o',str(probe)],check=True)
    preload=[str(probe.resolve())]
    if any(flag.startswith('-fsanitize=') and 'address' in flag for flag in flags):
        # GCC requires its runtime ahead of instrumented preload modules.
        runtime=Path(subprocess.check_output([compiler,'-print-file-name=libasan.so'],text=True).strip())
        if not runtime.is_file():raise ValueError('Cannot locate the matching address-sanitizer runtime')
        preload.insert(0,str(runtime.resolve()))
    return dict(LD_PRELOAD=':'.join(preload),LD_LIBRARY_PATH=str(build))
