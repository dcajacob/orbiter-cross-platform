#!/usr/bin/env python3
"""Exercise retained real native captures and damaged copies of their evidence."""
import argparse
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
from unittest import mock
import zipfile

import observations
from observations import bind_owner,inspect_native,require,sha
import transport

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('complete_persistence_gate',HERE/'audit.py')
gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)


def rejects(name,action,reason,controls):
    try:action()
    except (ValueError,KeyError,OSError) as error:
        require(reason in str(error),'Wrong rejection for '+name+': '+str(error))
        controls.append(dict(control=name,reason=str(error)))
        print(name,'rejected:',str(error)[:160],flush=True)
    else:raise ValueError('Damaged real persistence observation accepted: '+name)


def altered_read(path,body):
    """Read one damaged manifest copy in place of its owner without writing the owner."""
    original=Path.read_text
    def read(self,*args,**kwargs):
        return body if self==path else original(self,*args,**kwargs)
    return mock.patch.object(Path,'read_text',read)


def native_controls(root,owner,reader,profile,phase,selected,controls):
    path=root/'capture.json';original=json.loads(path.read_text())
    first=original['cases'][original['cases_requested'][0]]['runs'][0]
    damages={
        'nonterminal_capture':lambda d:d.update(status='running'),
        'diagnostic_as_full':lambda d:d.update(diagnostic_only=False),
        'omitted_case':lambda d:d['cases'].pop(d['cases_requested'][-1]),
        'omitted_repeat':lambda d:d['cases'][d['cases_requested'][0]]['runs'].pop(),
        'changed_reader_identity':lambda d:d['source_sha256_lf'].update({'Tests/Production/RemainingVessels/NativeProbe.cpp':'0'*64}),
        'changed_actual_frame_hash':lambda d:d['cases'][d['cases_requested'][0]]['runs'][0]['files_sha256'].update({'scene.rgba':'0'*64}),
        'discarded_saved_vessel':lambda d:d['cases'][d['cases_requested'][0]]['runs'][0]['saved_state']['ships'].pop(next(iter(first['saved_state']['ships']))),
        'discarded_module_field':lambda d:d['cases'][d['cases_requested'][0]]['runs'][0]['saved_state']['ships'][next(iter(first['saved_state']['ships']))]['records'].pop(),
    }
    reasons=['Complete terminal','full/selected','Complete terminal','Both complete','immutable producer',
             'Actual captured bytes changed','Complete actual native saved content differs','Complete actual native saved content differs']
    for (name,damage),reason in zip(damages.items(),reasons):
        changed=copy.deepcopy(original);damage(changed)
        with altered_read(path,json.dumps(changed)):
            rejects(name,lambda:inspect_native(root,owner,reader,profile,phase,selected),reason,controls)
    invocation=root/(original['cases_requested'][0]+'-1')/'invocation.json'
    changed=json.loads(invocation.read_text());changed['sanitizer_environment']['ASAN_OPTIONS']+=':detect_leaks=0'
    with altered_read(invocation,json.dumps(changed)):
        rejects('disabled_leak_detection',lambda:inspect_native(root,owner,reader,profile,phase,selected),
                'Native sanitizer configuration differs',controls)
    rejects('selected_capture_as_complete_matrix',lambda:inspect_native(root,owner,reader,profile,phase),
            'Complete terminal',controls)


def transport_controls(archive,decoded,controls,temporary):
    members=transport.inspect_archive(archive,decoded,sha(archive),archive.stat().st_size)
    rejects('changed_zip_hash',lambda:transport.inspect_archive(archive,decoded,'0'*64,archive.stat().st_size),
            'ZIP bytes/hash/size differ',controls)
    rejects('changed_zip_size',lambda:transport.inspect_archive(archive,decoded,sha(archive),archive.stat().st_size+1),
            'ZIP bytes/hash/size differ',controls)
    # A small closed copy retains actual Windows saved, invocation and capture
    # bytes. It tests transport integrity only and earns no runtime/process credit.
    chosen=[n for n in members if n.endswith('Scenarios/(Current state).scn')][:1]
    chosen += [n for n in members if n.endswith('/invocation.json')][:1]
    chosen += [n for n in members if n.endswith('/capture.json')][:1]
    require(len(chosen)==3,'Real Windows save/invocation/capture controls missing')
    root=temporary/'decoded';root.mkdir()
    for name in chosen:
        target=root/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((decoded/name).read_bytes())
    def zipped(name,extra=None):
        target=temporary/(name+'.zip')
        with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as stream:
            for item in chosen:stream.writestr(item,(decoded/item).read_bytes())
            if extra:extra(stream)
        return target
    positive=zipped('closed-real-inputs')
    transport.inspect_archive(positive,root,sha(positive),positive.stat().st_size)
    damaged=root/chosen[0];body=damaged.read_bytes();damaged.write_bytes(body+b'\n')
    rejects('changed_decoded_saved_bytes',lambda:transport.inspect_archive(positive,root,sha(positive),positive.stat().st_size),
            'differs from retained ZIP',controls)
    damaged.write_bytes(body)
    extra=root/'extra.txt';extra.write_text('unrecorded')
    rejects('unmanifested_decoded_file',lambda:transport.inspect_archive(positive,root,sha(positive),positive.stat().st_size),
            'Unmanifested decoded',controls)
    extra.unlink()
    for name,extra,reason in (
        ('case_collision',lambda z:z.writestr(chosen[0].upper(),(decoded/chosen[0]).read_bytes()),'case-colliding'),
        ('path_traversal',lambda z:z.writestr('../outside.txt',b'x'),'Unsafe artifact member'),
        ('windows_path',lambda z:z.writestr('D:\\outside.txt',b'x'),'Unsafe artifact member'),
    ):
        candidate=zipped(name,extra)
        rejects(name,lambda:transport.inspect_archive(candidate,root,sha(candidate),candidate.stat().st_size),reason,controls)
    def symlink(z):
        member=zipfile.ZipInfo('link');member.create_system=3;member.external_attr=0o120777<<16
        z.writestr(member,'target')
    candidate=zipped('symlink',symlink)
    rejects('symlink_member',lambda:transport.inspect_archive(candidate,root,sha(candidate),candidate.stat().st_size),'symlink',controls)
    parent=json.loads((decoded/'remaining-stock-repaired/capture.json').read_text())
    values={'remaining-stock-repaired/capture.json':sha(decoded/'remaining-stock-repaired/capture.json'),
            'remaining-stock-repaired-build/build.json':sha(decoded/'remaining-stock-repaired-build/build.json')}
    for identity,case in parent['cases'].items():
        for repeat,run in enumerate(case['runs'],1):
            directory='remaining-stock-repaired/'+identity+'-'+str(repeat)+'/'
            values.update({directory+n:v for n,v in run['files_sha256'].items()})
            saved=directory+'Scenarios/(Current state).scn';values[saved]=sha(decoded/saved)
    # Reconstruct a Windows path descriptor from retained real parent bytes.
    # This is a path-reader control, never claimed as a Windows reload process.
    windows=lambda name:'D:\\retained\\out\\'+name.replace('/','\\')
    guards={windows(n):v for n,v in values.items()}
    require(transport.parent_guards(decoded,dict(guarded_parent_files_sha256=guards),parent)==values,
            'Exact Windows path to retained-byte positive failed')
    for name,damage,reason in (
        ('omitted_parent_guard',lambda d:d.pop(next(iter(d))),'Complete Windows parent guard closure'),
        ('changed_parent_guard_hash',lambda d:d.update({next(iter(d)):'0'*64}),'guard omitted, substituted or changed'),
        ('different_parent_owner',lambda d:d.update({next(iter(d)).replace('D:','E:'):d.pop(next(iter(d)))}),'one owning output root'),
        ('outside_parent_guard',lambda d:d.update({'D:\\outside\\other.json':'0'*64}),'missing or ambiguous retained root'),
        ('relative_parent_guard',lambda d:d.update({'remaining-stock-repaired\\capture.json':'0'*64}),'Unsafe original Windows guarded path'),
    ):
        changed=dict(guards);damage(changed)
        rejects(name,lambda:transport.parent_guards(decoded,dict(guarded_parent_files_sha256=changed),parent),reason,controls)
    return dict(actual_zip_sha256=sha(archive),actual_zip_bytes=archive.stat().st_size,decoded_members=len(members),
                closed_real_input_copy_members=len(chosen),reconstructed_windows_parent_guard_files=len(values))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('native-owner','windows-archive','windows-decoded','output'):
        p.add_argument('--'+name,type=lambda v:Path(v).resolve(),required=True)
    p.add_argument('--native-capture',action='append',required=True,help='PHASE/PROFILE=PATH (retained actual diagnostic captures)')
    a=p.parse_args();require(not a.output.exists(),'Fresh reader-controls output required')
    guarded={};report=dict(status='failed',native_positives=[],controls=[],native_admission_qualified=False,phase6_complete=False,
        scope='Actual selected capture readers, exact artifact transport and rejection controls only. No full38/four-profile persistence qualification inferred.')
    try:
        reader=None
        for value in a.native_capture:
            label,separator,path=value.partition('=');require(separator,'PHASE/PROFILE=PATH required')
            phase,profile=label.split('/',1);root=Path(path).resolve();manifest=root/'capture.json'
            captured=json.loads(manifest.read_text());guarded[str(manifest)]=sha(manifest)
            if reader is None:reader=bind_owner(a.native_owner,captured['producer_commit'])
            require(captured['producer_commit']==subprocess.check_output(
                ['git','-C',str(a.native_owner),'rev-parse','HEAD'],text=True).strip(),'Retained test owner/source producer differs')
            selected=captured['cases_requested'];require(captured['diagnostic_only'],'Reader controls require explicit real selected captures')
            result=inspect_native(root,a.native_owner,reader,profile,phase,selected)
            report['native_positives'].append({k:result[k] for k in ('phase','profile','actual_processes','actual_presentations','capture_sha256','process_files')})
            # One complete native report supplies all damaged-report controls;
            # the other supplied runs are independently re-read positives.
            if len(report['native_positives'])==1:native_controls(root,a.native_owner,reader,profile,phase,selected,report['controls'])
            print(phase,profile,'actual native capture independently re-read',flush=True)
        profiles=sorted(gate.PROFILES);complete=[name+'=/retained/'+name for name in profiles]
        require(set(gate.profile_paths(complete))==gate.PROFILES,'Full profile-selector positive failed')
        for name,entries in [('missing_profile',complete[:-1]),('duplicate_profile',complete+[complete[0]]),
                             ('unknown_profile',complete[:-1]+['Debug-fast=/retained/unknown'])]:
            rejects(name,lambda:gate.profile_paths(entries),'required' if name!='missing_profile' else 'subsets cannot qualify',report['controls'])
        with tempfile.TemporaryDirectory(prefix='orbiter-persistence-reader-controls-') as temporary:
            report['transport_positive']=transport_controls(a.windows_archive,a.windows_decoded,report['controls'],Path(temporary))
        windows_parent=a.windows_decoded/'remaining-stock-repaired'
        windows_report=json.loads((windows_parent/'capture.json').read_text())
        profile=windows_report['configuration']+'-'+windows_report['math_profile']
        matches=[v for v in a.native_capture if v.startswith('stock-writer/'+profile+'=')]
        require(len(matches)==1,'Matching real stock-writer profile required for comparison-reader positive')
        native_root=Path(matches[0].partition('=')[2]).resolve()
        native_report=json.loads((native_root/'capture.json').read_text())
        require(set(native_report['cases'])==set(windows_report['cases']),'Actual selected Windows/native comparison cases differ')
        config=reader.native.settings(reader.protocols.V2);comparisons={}
        for identity in native_report['cases']:
            comparisons[identity]=[gate.compare_pair(windows_parent/(identity+'-'+str(repeat)),native_root/(identity+'-'+str(repeat)),reader,config)
                                  for repeat in (1,2)]
        report['historical_windows_comparison_reader_positives']=dict(profile=profile,cases=comparisons,
            producer=windows_report['producer_commit'],scope='Historical Windows source-v3 comparisons exercise readers only; no fresh Windows reload/startup-witness qualification inferred.')
        require(all(sha(Path(n))==v for n,v in guarded.items()),'Owning native manifests changed during reader controls')
        report.update(status='passed-persistence-reader-controls',owning_manifests_unchanged=True,
            test_sha256=sha(Path(__file__)),reader_sha256={name:sha(HERE/name) for name in ('audit.py','observations.py','transport.py')},
            actual_native_processes=sum(v['actual_processes'] for v in report['native_positives']),
            actual_native_presentations=sum(v['actual_presentations'] for v in report['native_positives']))
    except BaseException as error:report['error']=str(error);raise
    finally:
        a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n')
    print(report['actual_native_processes'],'actual native runs;',len(report['controls']),'damaged evidence controls rejected',flush=True)


if __name__=='__main__':main()
