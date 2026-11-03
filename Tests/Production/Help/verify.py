#!/usr/bin/env python3
"""Check source hashes, all delivered document text and local navigation targets."""
import argparse
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
from urllib.parse import unquote, urlsplit
from prepare import ROOT, Text, decode

class Links(HTMLParser):
    def __init__(self):super().__init__();self.urls=[]
    def handle_starttag(self,tag,attrs):
        self.urls.extend(value for name,value in attrs if name in ('href','src','background') and value)

def verify(root):
    manifest=json.loads((root/'manifest.json').read_text())
    assert not manifest['unresolved_links'], manifest['unresolved_links']
    for name,expected in manifest['generator_inputs'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==expected, 'Documentation generator input changed: '+name
    topics=0;links=0
    for name,record in manifest['sources'].items():
        original=root/name;data=original.read_bytes()
        assert hashlib.sha256(data).hexdigest()==record['sha256'],name
        if record['source']!='original LDoc output':
            assert (ROOT/record['source']).read_bytes()==data,'Original input changed: '+name
        delivered=root/'books'/Path(name).relative_to('sources')
        assert delivered.is_file(), delivered
        if original.suffix not in ('.htm','.html'):continue
        before=Text();before.feed(decode(data))
        after=Text();after.feed(decode(delivered.read_bytes()))
        # The camera page has a broken quote in its original link, causing the
        # old HTML parser to swallow one label. All other prose must be identical.
        if name.endswith('/camera.htm'):
            before=Text();before.feed(decode(data).replace('href="cam_mode.htm>','href="cam_mode.htm">'))
        assert before.parts==after.parts,'Help prose changed: '+name
        parsed=Links();parsed.feed(delivered.read_text())
        for value in parsed.urls:
            url=urlsplit(value)
            if url.scheme or url.netloc or not url.path:continue
            target=(delivered.parent/unquote(url.path)).resolve()
            assert target.is_relative_to(root.resolve()), ('Help link escapes root',name,value)
            assert target.is_file(),('Broken local help link',name,value)
            links+=1
        topics+=1
    for line in (root/'catalog.tsv').read_text().splitlines():
        _,viewer,default=line.split('\t')
        base=root.parent/viewer
        assert base.is_file() and (base.parent/default).is_file(),line
    report=dict(status='passed',books=len(manifest['books']),sources=len(manifest['sources']),topics=topics,local_links=links,original_prose=True)
    print(json.dumps(report,indent=2));return report

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--help-root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();result=verify(args.help_root)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
