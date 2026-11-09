#!/usr/bin/env python3
"""Keep the complete unchanged native writer and supply its declared runtime dependencies."""
from pathlib import Path
import subprocess
import capture_hosted_native_writer_mesa as mesa_writer

ROOT=Path(__file__).resolve().parents[3]
SOURCE='026cc581467b3d1417e5dfbdfcc9de8cd4b7cc5e'


def prepared_body():
    path=Path(mesa_writer.__file__)
    if path.read_bytes()!=subprocess.check_output(['git','-C',str(ROOT),'show',SOURCE+':'+path.relative_to(ROOT).as_posix()]):
        raise ValueError('Original verified Mesa writer adapter changed')
    body=mesa_writer.prepared_body()
    changes=[
        ("protocol='phase6-hosted-native-stock-writer-Mesa-v2'","protocol='phase6-hosted-native-stock-writer-runtime-v3'"),
        ("        report['compositor_host_dependencies']=install(providers,output,inventory,run,package_inventory);save()",
         "        report['compositor_host_dependencies']=install(providers,output,inventory,run,package_inventory);save()\n        from hosted_native_runtime_dependencies import install as install_native_runtime,verify as verify_native_runtime\n        report['native_host_dependencies']=install_native_runtime(providers,output,a.profile,run,package_inventory,mesa);save()"),
        ("        report.update(status='captured-and-independently-audited-native-writers-only'",
         "        require(verify_native_runtime(output/'native-runtime-dependencies.json')==report['native_host_dependencies'],'Actual native runtime dependency proof changed')\n        report.update(status='captured-and-independently-audited-native-writers-only'")]
    for before,after in changes:
        if body.count(before)!=1:raise ValueError('Conserved complete writer anchor changed: '+before)
        body=body.replace(before,after,1)
    return body


if __name__=='__main__':
    exec(compile(prepared_body(),str(mesa_writer.ORIGINAL),'exec'),{'__name__':'__main__','__file__':str(mesa_writer.ORIGINAL)})
