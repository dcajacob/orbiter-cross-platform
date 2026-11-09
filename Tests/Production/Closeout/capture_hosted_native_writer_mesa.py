#!/usr/bin/env python3
"""Use the conserved complete writer collector with the separately verified Mesa repair."""
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[3]
ORIGINAL=ROOT/'Tests/Production/Closeout/capture_hosted_native_writer.py'
BASE='d23d371a510dd464cde95a301dbc685514391f9c'


def prepared_body():
    body=ORIGINAL.read_bytes();expected=subprocess.check_output(['git','-C',str(ROOT),'show',BASE+':Tests/Production/Closeout/capture_hosted_native_writer.py'])
    if body!=expected:raise ValueError('Original complete native writer collector changed')
    text=body.decode()
    replacements=[
        ("protocol='phase6-hosted-native-stock-writer-v1'","protocol='phase6-hosted-native-stock-writer-Mesa-v2'"),
        ("compiled_provider_source='60ba46377f236c2d4705f444c0174e0f5af8252f'","base_compiled_provider_source='60ba46377f236c2d4705f444c0174e0f5af8252f',compiled_mesa_source='6d17e4f18e4eade72fa295c3d03a38a58182d35f'"),
        ("report['compiled_provider_source']","report['base_compiled_provider_source']"),
        ("        inventory=package_inventory((providers/'system-packages.txt').read_text())",
         "        from restore_hosted_mesa_topology import verify_restored\n        mesa=verify_restored(ROOT/'out/mesa-topology-restoration/restoration.json',ROOT,report['collector_source'])\n        report['mesa_restoration_sha256']=sha(ROOT/'out/mesa-topology-restoration/restoration.json')\n        inventory=package_inventory((providers/'system-packages.txt').read_text())"),
        ("providers/'mesa/install/share/glvnd/egl_vendor.d/50_mesa.json'","mesa/'install/share/glvnd/egl_vendor.d/50_mesa.json'"),
        ("        for folder in ('fontconfig-candidate','gdk-candidate','mesa'):argv+=['--library',str(providers/folder/'install/lib/x86_64-linux-gnu')]",
         "        for folder in ('fontconfig-candidate','gdk-candidate'):argv+=['--library',str(providers/folder/'install/lib/x86_64-linux-gnu')]\n        argv+=['--library',str(mesa/'install/lib/x86_64-linux-gnu')]"),
        ("        report.update(status='captured-and-independently-audited-native-writers-only'",
         "        require(sha(ROOT/'out/mesa-topology-restoration/restoration.json')==report['mesa_restoration_sha256'],'Mesa restoration receipt changed during collection')\n        verify_restored(ROOT/'out/mesa-topology-restoration/restoration.json',ROOT,report['collector_source'])\n        report.update(status='captured-and-independently-audited-native-writers-only'")]
    for before,after in replacements:
        if text.count(before)!=1:raise ValueError('Conserved writer role/path anchor changed: '+before)
        text=text.replace(before,after,1)
    return text


if __name__=='__main__':
    exec(compile(prepared_body(),str(ORIGINAL),'exec'),{'__name__':'__main__','__file__':str(ORIGINAL)})
