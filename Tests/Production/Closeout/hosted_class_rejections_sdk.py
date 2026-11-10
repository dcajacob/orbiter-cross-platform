#!/usr/bin/env python3
"""Supply only the omitted exact SDK header before every unchanged original rejection control."""
from pathlib import Path
import sys
from contracts import ROOT,PROFILES,load,require
import hosted_class_rejections as original
import rejection_input_bundle as bundle
import restore_rejection_sdk_header as sdk
ORIGINAL_PREPARED=original.prepared_body
ORIGINAL_PACK=bundle.pack
ANCHOR="        sdk={str(path):sha(path) for path in (build/'engine/native-sdk').rglob('*') if path.is_file()}"
INSERT="        from restore_rejection_sdk_header import restore as restore_original_sdk_header\n        report['original_omitted_SDK_header']=restore_original_sdk_header(a.profile,build/'build.json',output/'original-SDK-header-restoration.json');save()\n"


def prepared_body():
    body=ORIGINAL_PREPARED();require(body.count(ANCHOR)==1,'One exact unchanged original fixture SDK preflight required')
    return body.replace(ANCHOR,INSERT+ANCHOR,1)


def pack_with_sdk(root,paths,archive,index):
    root=Path(root);archive=Path(archive);profile=archive.parent.name
    require(profile in PROFILES and archive==root/'out/hosted-native-class-rejections'/profile/'raw-original-inputs.tar.gz','Exact original rejection input bundle destination required')
    report=load(archive.parent/'original-SDK-header-restoration.json')
    require(report['profile']==profile and report['compiled_source']==sdk.COMPILED and report['header_was_in_original_retained_archive'] is False,'Explicit reconstructed SDK provenance required')
    declared=load(archive.parent/'original-fixture-SDK.json')['files_sha256'];require(declared.get(report['header'])==report['header_sha256'],'Actual new fixture SDK input must equal its declared derivation')
    extra={Path(name) for name in declared}|{Path(__file__),Path(sdk.__file__)}
    for field in ('original_sources_sha256','original_binary_and_cache_sha256'):extra.update(Path(name) for name in report[field])
    return ORIGINAL_PACK(root,set(paths)|extra,archive,index)


def main():
    require('--profile' in sys.argv and sys.argv[sys.argv.index('--profile')+1] in PROFILES,'Exact original rejection profile required')
    original.prepared_body=prepared_body;bundle.pack=pack_with_sdk
    try:original.main()
    finally:original.prepared_body=ORIGINAL_PREPARED;bundle.pack=ORIGINAL_PACK


if __name__=='__main__':main()
