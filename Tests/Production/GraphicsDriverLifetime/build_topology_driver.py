#!/usr/bin/env python3
"""Use the unchanged locked Mesa builder with one separate CPU-cache lifetime addition."""
import hashlib
from pathlib import Path
import subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
BUILDER=HERE/'build_driver.py'
BASE='60ba46377f236c2d4705f444c0174e0f5af8252f'


def prepared_body():
    body=BUILDER.read_bytes()
    original=subprocess.check_output(['git','-C',str(ROOT),'show',BASE+':Tests/Production/GraphicsDriverLifetime/build_driver.py'])
    if body!=original:raise ValueError('Original source-locked Mesa builder changed')
    text=body.decode();anchor="        run(['patch', '--batch', '-p1', '-i', str(patch)], 'cleanup-patch', source)\n"
    if text.count(anchor)!=1:raise ValueError('Original source cleanup anchor changed')
    addition='''        from topology_cleanup import apply as apply_topology_cleanup
        report['topology_lifetime_variant']=apply_topology_cleanup(source)
        (output/'topology-source-variant.json').write_text(json.dumps(report['topology_lifetime_variant'],indent=2)+'\\n')
'''
    text=text.replace(anchor,anchor+addition,1)
    anchor2='        shutil.copy2(patch, notices)\n'
    if text.count(anchor2)!=1:raise ValueError('Original source notice anchor changed')
    text=text.replace(anchor2,anchor2+'''        shutil.copy2(HERE/'topology_cleanup.py',notices)
        shutil.copy2(output/'topology-source-variant.json',notices)
''',1)
    return text


if __name__=='__main__':
    exec(compile(prepared_body(),str(BUILDER),'exec'),{'__name__':'__main__','__file__':str(BUILDER)})
