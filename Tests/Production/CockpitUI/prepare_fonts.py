#!/usr/bin/env python3
"""Stage the original manuscript font for local/CI cockpit verification only.

The general asset provisioner excludes this publication-restricted font. This
helper uses the already present original source asset, checks its stock-data
identity and copies it into a disposable test resource tree. Do not include that
file in published data bundles or installed release packages.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[3]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assets',type=Path,required=True)
    args = parser.parse_args()
    source = ROOT/'Extern/imgui/architext.regular.ttf'
    checksum = json.loads((ROOT/'Tests/Production/stock-data.lock.json').read_text())['data_files']['Fonts/architext.regular.ttf']['sha256']
    if hashlib.sha256(source.read_bytes()).hexdigest() != checksum:
        raise ValueError('Original manuscript font differs from the stock data lock')
    target = args.assets/'Fonts/architext.regular.ttf'
    if target.exists():
        if hashlib.sha256(target.read_bytes()).hexdigest() != checksum:
            raise ValueError('Existing test manuscript font differs')
    else:
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(source,target)
    (args.assets/'cockpit-test-font.json').write_text(json.dumps(dict(scope='disposable local and CI cockpit tests',file='Fonts/architext.regular.ttf',source=str(source),sha256=checksum),indent=2)+'\n')
    print('Verified original manuscript font for disposable cockpit tests')

if __name__ == '__main__':
    main()
