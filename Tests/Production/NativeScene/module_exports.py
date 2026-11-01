#!/usr/bin/env python3
"""Prevent ELF interposition of the renderer's private implementation classes."""
import argparse,subprocess,re
from pathlib import Path
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('module',type=Path);args=parser.parse_args()
symbols=subprocess.check_output(['nm','-D','-C','--defined-only',str(args.module)],text=True)
assert 'OrbiterNativeQuery' in symbols,'Explicit native renderer entry is absent'
for name in ('ZTreeMgr','TreeFileHeader','Scene::','OGLClient::','OGLMesh::','vVessel::'):
    assert name not in symbols,'Private renderer symbol can collide with engine: '+name
assert not re.search(r'\b[TW] Renderer::',symbols), 'Renderer namespace functions are exported'
print('Native entry exported; renderer implementation symbols remain private')
