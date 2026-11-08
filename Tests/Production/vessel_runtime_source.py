#!/usr/bin/env python3
"""Conserve the complete 311a4c31 vessel implementation across native SDK services.

This is a second conservation stage. Only after each current implementation is
verified may the first-stage audit inspect its immutable 311a4c31 predecessor.
No state reference, input profile or numerical budget is updated here.
"""
from pathlib import Path
import functools
import re
import subprocess
ROOT=Path(__file__).resolve().parents[2]
PRIOR='311a4c31'
def old(name):return subprocess.check_output(['git','-C',str(ROOT),'show',PRIOR+':'+name]).replace(b'\r\n',b'\n').decode('cp1252')
def raw(name):return (ROOT/name).read_bytes().replace(b'\r\n',b'\n').decode('cp1252')
def tokens(s):
    s=re.sub(r'/\*.*?\*/|//[^\n]*','',s,flags=re.S)
    return re.findall(r'"(?:\\.|[^"\\])*"|\w+|[^\s]',s)
def equal(a,b,label):
    if tokens(a)!=tokens(b):
        import difflib
        x,y=tokens(a),tokens(b)
        changes=['old: '+' '.join(x[max(0,i-4):j+4])+'\nnew: '+' '.join(y[max(0,k-4):l+4]) for op,i,j,k,l in difflib.SequenceMatcher(None,x,y,autojunk=False).get_opcodes() if op!='equal']
        raise ValueError(label+' changed beyond declared services:\n'+'\n'.join(changes)[:2400])
def aliases(s):
    for a,b in [('oapi::UInt32','DWORD'),('oapi::UInt16','WORD'),('oapi::UInt','UINT'),('std::uintptr_t','DWORD_PTR'),('oapi::SdkDrawContext','HDC'),('oapi::SdkRectangle','RECT')]:s=s.replace(a,b)
    return s
def clock_adapters(s):
    clock='GetRigidBodyServices().Time().'
    s=s.replace('new Elements('+clock+'MJD_ref);','new Elements;')
    s=s.replace('Elements els('+clock+'MJD_ref);','Elements els;')
    for prefix in ['el->Set (a, e, i*RAD, theta*RAD, omegab*RAD, L*RAD, elmjd',
                   'els.Set (el.a, el.e, el.i, el.theta, el.omegab, el.L, mjd_ref',
                   'els.Setup (0, ref->Mass(), mjd_ref',
                   'el->Setup (mass, cbody->Mass(), el->MJDepoch()']:
        s=s.replace(prefix+', '+clock+'MJD_ref);',prefix+');')
    for prefix in ['el->Update (rpos, rvel','els.Update (p, v']:
        s=s.replace(prefix+', '+clock+'SimT1);',prefix+');')
    s=s.replace('mjd_ref ? mjd_ref : '+clock+'MJD0, '+clock+'MJD_ref);','mjd_ref ? mjd_ref : '+clock+'MJD0);')
    return s

def span(s,qualified):
    m=re.search(r'^[^\n]*\b'+re.escape(qualified)+r'\s*\(',s,re.M)
    if m is None:return None
    first=s.index('{',m.start());depth=0
    lexer=re.compile(r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[{}]',re.S)
    for token in lexer.finditer(s,first):
        if token.group()=='{':depth+=1
        elif token.group()=='}':
            depth-=1
            if not depth:return m.start(),token.end()
    raise ValueError('Unclosed method '+qualified)
GUI=('VESSEL::SetCameraDefaultDirection','VESSEL::SetCameraCatchAngle','VESSEL::TriggerPanelRedrawArea',
     'VESSEL::TriggerRedrawArea','VESSEL::GetDevMesh','VESSEL2::clbkDrawHUD','VESSEL3::SetPanelBackground',
     'VESSEL3::SetPanelScaling','VESSEL3::RegisterPanelMFDGeometry','VESSEL3::RegisterPanelArea',
     'VESSEL3::clbkDrawHUD','VESSEL3::clbkRenderHUD','VESSEL4::RegisterPanelArea')
LIGHTS=('AddPointLight','AddSpotLight','DelLightEmitter','ClearLightEmitters','LightEmitterState','ShiftLightEmitters')

def with_sparse_mesh_slots(source):
    """Apply only the deleted-slot lookup and allocation corrections to an original vessel source."""
    source=source.replace('idx < nmesh && meshlist[idx]->meshname','idx < nmesh && meshlist[idx] && meshlist[idx]->meshname')
    source=source.replace('if (meshidx < nmesh) {','if (meshidx < nmesh && meshlist[meshidx]) {')
    start,end=span(source,'Vessel::CopyMeshFromTemplate')
    copy=source[start:end].replace('Mesh *mesh = new Mesh; GetRigidBodyServices().TraceAllocation(__FILE__,__LINE__);','Mesh *mesh = nullptr;')
    copy=copy.replace('if (meshrec) {','if (meshrec) {\n\t\tmesh = new Mesh; GetRigidBodyServices().TraceAllocation(__FILE__,__LINE__);').replace('} else mesh = 0;','}')
    return source[:start]+copy+source[end:]

def restore_attachment_cleanup(source):
    """Accept only reciprocal unlinking when normal release lacks initial proxy state."""
    original='void Vessel::ClearAttachments ()\n{\n\tif (attach) DetachFromParent();\n\tif (npattach) {\n\t\tfor (oapi::UInt32 i = 0; i < npattach; i++)\n\t\t\tdelete pattach[i];\n\t\tdelete []pattach;\n\t\tpattach = NULL;\n\t\tnpattach = 0;\n\t}\n\tif (ncattach) {\n\t\tfor (oapi::UInt32 i = 0; i < ncattach; i++) {\n\t\t\tif (cattach[i]->mate) DetachChild (cattach[i]);\n\t\t\tdelete cattach[i];\n\t\t}\n\t\tdelete []cattach;\n\t\tcattach = NULL;\n\t\tncattach = 0;\n\t}\n}'
    repaired='void Vessel::ClearAttachments ()\n{\n\t// Before the first passive update an attached child has no proxy body, so\n\t// normal release cannot compute its free-flight state. Definitions are\n\t// still being destroyed: remove both links before either owner is freed.\n\tconst auto unlinkChild = [](Vessel *child) {\n\t\tAttachmentSpec *point = child->attach;\n\t\tif (!point) return;\n\t\tif (point->mate_attach) {\n\t\t\tpoint->mate_attach->mate = 0;\n\t\t\tpoint->mate_attach->mate_attach = 0;\n\t\t}\n\t\tpoint->mate = 0;\n\t\tpoint->mate_attach = 0;\n\t\tchild->attach = 0;\n\t};\n\tif (attach && !DetachFromParent()) unlinkChild(this);\n\tif (npattach) {\n\t\tfor (oapi::UInt32 i = 0; i < npattach; i++)\n\t\t\tdelete pattach[i];\n\t\tdelete []pattach;\n\t\tpattach = NULL;\n\t\tnpattach = 0;\n\t}\n\tif (ncattach) {\n\t\tfor (oapi::UInt32 i = 0; i < ncattach; i++) {\n\t\t\tif (cattach[i]->mate && !DetachChild (cattach[i])) unlinkChild(cattach[i]->mate);\n\t\t\tdelete cattach[i];\n\t\t}\n\t\tdelete []cattach;\n\t\tcattach = NULL;\n\t\tncattach = 0;\n\t}\n}'
    if source.count(repaired)!=1:
        raise ValueError('Declared uninitialized attachment cleanup differs')
    return source.replace(repaired,original,1)

def restore_startup_cleanup(source):
    """Accept only the declared dock lifetime, class-name, token and temporary-array cleanup."""
    source=restore_attachment_cleanup(source)
    source=restore_docking_cleanup(source)
    original='\tClearAttachments();'
    repaired=original+'\n\tdelete []attach_status.pname;\n\tattach_status.pname = nullptr;'
    if source.count(repaired)!=1:
        raise ValueError('Declared unresolved attachment-name cleanup differs')
    source=source.replace(repaired,original,1)
    original='\tif (!OpenConfigFile (classf))\n\t\tGetVesselServices().Fatal("Vessel initialization failed"); // PANIC!'
    repaired='\tif (!OpenConfigFile (classf)) {\n\t\tdelete []classname;\n\t\tclassname = nullptr;\n\t\tGetVesselServices().Fatal("Vessel initialization failed"); // PANIC!\n\t}'
    if source.count(repaired)!=3:
        raise ValueError('Declared failed class-configuration cleanup differs')
    source=source.replace(repaired,original)
    original='\t\t\tif (dock[i]->mate) Undock (i, 0, 0.0);'
    repaired='\t\t\tif (dock[i]->mate && GetRigidBodyServices().World()->isVessel(dock[i]->mate)) Undock (i, 0, 0.0);'
    if source.count(repaired)!=1:
        raise ValueError('Declared unresolved docking-token cleanup differs')
    source=source.replace(repaired,original)
    original='\t\tvs.thruster = NULL;\n\t}\n\treturn res;'
    repaired='\t\tvs.thruster = NULL;\n\t}\n\tdelete []vs.dockinfo;\n\tvs.dockinfo = NULL;\n\treturn res;'
    if source.count(repaired)!=1:
        raise ValueError('Declared temporary scenario dock-record cleanup differs')
    return source.replace(repaired,original)

def restore_docking_cleanup(source):
    """Defer only port reclamation; retain every undock and NAV callback in order."""
    original='''void Vessel::ClearDockDefinitions ()
{
	if (ndock) {
		for (oapi::UInt32 i = 0; i < ndock; i++) {
			if (dock[i]->mate && GetRigidBodyServices().World()->isVessel(dock[i]->mate)) Undock (i, 0, 0.0);
			if (dock[i]->ids) {
				GetRigidBodyServices().World()->BroadcastVessel (MSG_KILLNAVSENDER, dock[i]->ids);
				delete dock[i]->ids;
			}
			delete dock[i];
		}
		delete []dock;
		dock = NULL;
		ndock = 0;
	}
}'''
    repaired=original.replace('delete dock[i]->ids;', 'delete dock[i]->ids;\n\t\t\t\tdock[i]->ids = NULL;')
    repaired=repaired.replace('\t\t\tdelete dock[i];\n','').replace('\t\tdelete []dock;',
        '\t\t// Detach scans every port in the remaining superstructure. Keep the\n'
        '\t\t// already detached ports alive until all ordered undock callbacks and\n'
        '\t\t// navigation-source notifications have completed.\n'
        '\t\tfor (oapi::UInt32 i = 0; i < ndock; i++) delete dock[i];\n\t\tdelete []dock;')
    if source.count(repaired)!=1:raise ValueError('Declared ordered dock-port lifetime repair differs')
    return source.replace(repaired,original,1)

def restore_hull_transform_cleanup(source):
    cleanup="""// The SDK transform base has no virtual destructor. These copies
        // were allocated above as their concrete transform types.
        switch (pair.second->Type()) {
        case MGROUP_TRANSFORM::ROTATE: delete static_cast<MGROUP_ROTATE*>(pair.second); break;
        case MGROUP_TRANSFORM::TRANSLATE: delete static_cast<MGROUP_TRANSLATE*>(pair.second); break;
        case MGROUP_TRANSFORM::SCALE: delete static_cast<MGROUP_SCALE*>(pair.second); break;
        case MGROUP_TRANSFORM::NULLTRANSFORM: delete pair.second; break;
        }"""
    if source.count(cleanup)!=1:raise ValueError('Hull animation transform cleanup changed')
    return source.replace(cleanup,'delete pair.second;',1)

@functools.lru_cache(maxsize=1)
def previous_files():
    from random_source import canonical as random_bindings
    result={}
    for name in ['Vessel.cpp','Vesselstatus.cpp','SuperVessel.cpp']:
        path='Src/Orbiter/'+name
        current=clock_adapters(random_bindings(raw(path)).replace('#include "Production/Random.h"\n',''))
        if name=='Vessel.cpp':
            # Sanitizer-confirmed upstream array-delete mismatch; no numerical change.
            assert current.count('delete []A->comp;')==2
            current=current.replace('\t\tdelete []A->comp;','\t\tdelete A->comp;',1)
            # Bulk exhaust cleanup must free owned constant fields like DelExhaust.
            current=current.replace('\t\tfor (i = 0; i < nexhaust; i++) {\n\t\t\tif (exhaust[i]->level && (exhaust[i]->flags & EXHAUST_CONSTANTLEVEL))\n\t\t\t\tdelete exhaust[i]->level;\n\t\t\tif (exhaust[i]->lpos && (exhaust[i]->flags & EXHAUST_CONSTANTPOS))\n\t\t\t\tdelete exhaust[i]->lpos;\n\t\t\tif (exhaust[i]->ldir && (exhaust[i]->flags & EXHAUST_CONSTANTDIR))\n\t\t\t\tdelete exhaust[i]->ldir;\n\t\t\tdelete exhaust[i];\n\t\t}', '\t\tfor (i = 0; i < nexhaust; i++)\n\t\t\tdelete exhaust[i];')
        if name=='Vessel.cpp':current=restore_startup_cleanup(restore_hull_transform_cleanup(current))
        expected=with_sparse_mesh_slots(old(path)) if name=='Vessel.cpp' else old(path)
        equal(expected,current,path);result[path]=old(path)
    path='Src/Orbiter/Vessel.h'
    s=raw(path).replace('#ifndef _WIN32\n\tstatic void ReleaseNativeInterface(VESSEL* interface);\n#endif\n','')
    s=s.replace('#ifndef _WIN32\n\tconst char* NativeModuleName() const noexcept;\n#endif\n','')
    s=s.replace('public:\n\tvoid FRecorder_EndPlayback ();\n\t// terminates a running playback\nprivate:', '\tvoid FRecorder_EndPlayback ();\n\t// terminates a running playback')
    s=s.replace('public:\n\t// Session hosts activate the same recorder; sample buffers remain private.\n\tvoid FRecorder_Activate (bool active, const char *fname, bool append = false);\n\t// switch recorder on/off\nprivate:', '\tvoid FRecorder_Activate (bool active, const char *fname, bool append = false);\n\t// switch recorder on/off\n')
    equal(old(path),s,path);result[path]=old(path)
    # Retain every SDK wrapper. Platform-specific cockpit methods move intact;
    # the numerical and vessel-delegation methods remain one shared source.
    path='Src/Orbiter/VesselSdk.cpp';s=old(path);start=s.index('VESSEL::VESSEL (');original=s[start:];common=original;gui=[]
    for name in GUI:
        while (part:=span(common,name)) is not None:
            a,b=part;gui.append(common[a:b]);common=common[:a]+common[b:]
    current=raw(path);current=current[current.index('VESSEL::VESSEL ('):]
    current=clock_adapters(aliases(current))
    for a,b in [('GetRigidBodyServices().World()','g_psys'),('GetRigidBodyServices().Time().','td.'),
                ('GetSurfaceServices().Configuration().','g_pOrbiter->Cfg()->'),
                ('GetRigidBodyServices().TraceAllocation(__FILE__,__LINE__);','TRACENEW'),
                ('GetVesselServices().InsertVessel (vessel)','g_pOrbiter->InsertVessel (vessel)'),
                ('GetVesselServices().ManualControl (thgt, device)','g_pOrbiter->ManCtrlLevel (thgt, device)'),
                ('GetVesselServices().NotifyJump (*vessel, gdr)','g_pOrbiter->NotifyObjectJump (vessel, gdr)'),
                ('GetVesselServices().ShiftCockpit (*vessel, vs);','if ((g_pane) && (g_focusobj == vessel)) g_pane->ShiftVC (vs);')]:current=current.replace(a,b)
    current=re.sub(r'GetVesselServices\(\).Check\(bool\((.*?)\), ("[^"\n]*")\);',r'dCHECK(\1, \2)',current)
    common=common.replace('if (idx >= vessel->nmesh) return false;\n\tmemcpy (&ofs','if (idx >= vessel->nmesh || !vessel->meshlist[idx]) return false;\n\tmemcpy (&ofs')
    common=common.replace('idx < vessel->nmesh ? vessel->meshlist[idx]->vismode','idx < vessel->nmesh && vessel->meshlist[idx] ? vessel->meshlist[idx]->vismode')
    equal(common,current,'Complete production SDK vessel calculations/delegates')
    from cockpit_runtime_source import restore as restore_cockpit
    application=restore_cockpit('Src/Orbiter/VesselSdkApplication.cpp',raw('Src/Orbiter/VesselSdkApplication.cpp'))
    first=span(application,GUI[0]);equal('\n\n'.join(gui),application[first[0]:],'Original Windows cockpit SDK methods')
    result[path]=old(path)
    # Logical light objects and their vessel ownership remain CPU-side original
    # implementations. The graphics client owns only its GPU counterparts.
    path='Src/Orbiter/VesselApplication.cpp';s=old(path);lights=[]
    for name in LIGHTS:
        a,b=span(s,'Vessel::'+name);lights.append(s[a:b]);s=s[:a]+s[b:]
    equal(s,restore_cockpit(path,raw(path)),path);result[path]=old(path)
    light=raw('Src/Orbiter/VesselLights.cpp');a,b=span(light,'Vessel::'+LIGHTS[0])
    # Release SDK lights through the concrete type allocated by the vessel.
    light=light[a:]
    helper_start=light.index('// Vessel emitters')
    helper_end=light.index('bool Vessel::DelLightEmitter',helper_start)
    helper=light[helper_start:helper_end]
    assert 'delete static_cast<SpotLight*>(light);' in helper and 'delete static_cast<PointLight*>(light);' in helper
    light=(light[:helper_start]+light[helper_end:]).replace('DeleteVesselLight (le);','delete le;')
    light=light.replace('DeleteVesselLight (emitter[i]);','delete emitter[i];').replace('emitter = nullptr;', '')
    equal('\n\n'.join(lights),aliases(light),'Original vessel light ownership/events')
    path='Src/Orbiter/LightEmitter.cpp';s=raw(path).replace('#ifdef _WIN32\n#define OAPI_IMPLEMENTATION\n#include "OrbiterAPI.h"\n#else\n#include "NativeVesselAPI.h"\n#endif','#define OAPI_IMPLEMENTATION\n#include "OrbiterAPI.h"')
    equal(old(path),s,path);result[path]=old(path)
    path='Src/Orbiter/OrbiterAPI.cpp';s=old(path);a=s.index('DLLEXPORT double oapiGetInducedDrag');b=s.index('// ===========================================================================',a)
    math=raw('Src/Orbiter/VesselFlightMath.cpp');math=math[math.index('ORBITER_FLIGHT_EXPORT double oapiGetInducedDrag'):].replace('ORBITER_FLIGHT_EXPORT double','DLLEXPORT double')
    equal(s[a:b],math,'Original aerodynamic helper formulas')
    remaining=s[:a]+s[b:]
    flight=raw('Src/Orbiter/FlightSdk.cpp')
    implementation=flight[flight.index('OBJHANDLE oapiGetObjectByName'):]
    names=set(re.findall(r'^.*?\b(oapi\w+) ?\([^)]*\)\n\{',implementation,re.M))
    moved=[];spans=[]
    for match in re.finditer(r'^DLLEXPORT [^\n]*?\b(oapi\w+) ?\([^)]*\)\s*\{',remaining,re.M):
        if match[1] not in names:continue
        end=remaining.index('\n}',match.end())+2
        body=remaining[match.start():end]
        if 'LOGOUT_OBSOLETE' in body:continue
        spans.append((match.start(),end))
        body=body.removeprefix('DLLEXPORT ')
        for before,after in [('DWORD','oapi::UInt32'),('UINT','oapi::UInt'),('BOOL','int'),('TRUE','true'),('FALSE','false'),
                             ('g_focusobj','orbiter::production::CockpitFocus()'),('g_psys','orbiter::production::CockpitWorld()'),
                             ('td','orbiter::production::CockpitTime()')]:
            body=re.sub(r'\b'+before+r'\b',after,body)
        moved.append(body)
    equal('\n'.join(moved),implementation,'Shared flight SDK calculations and service delegates')
    for start,end in reversed(spans):remaining=remaining[:start]+remaining[end:]
    panel=raw('Src/Orbiter/CockpitSdk.cpp').split('bool oapiSetHUDMode',1)[1]
    panel=aliases('bool oapiSetHUDMode'+panel)
    panel=panel.replace('Pane *pane = orbiter::production::ActiveCockpitPane();','')
    panel=re.sub(r'\bpane\b','g_pane',panel).replace('orbiter::production::CockpitPane()','g_pane')
    for method in re.finditer(r'^([^\n]+\([^\n]*\)\n\{.*?^\})',panel,re.M|re.S):
        signature=method[1].splitlines()[0]
        start=remaining.index('DLLEXPORT '+signature+'\n')
        end=remaining.index('\n}',start)+2
        equal(remaining[start:end], 'DLLEXPORT '+method[1], 'Shared cockpit SDK: '+signature)
        remaining=remaining[:start]+remaining[end:]
    scenario=raw('Src/Orbiter/ScenarioSdk.cpp')
    begin=remaining.index('DLLEXPORT void oapiWriteScenario_string')
    end=remaining.index('DLLEXPORT void oapiOpenInputBox',begin)
    original=remaining[begin:end].replace('DLLEXPORT ','').replace('_stricmp (line, "END")','orbiter::production::CompareText(line, "END")')
    equal(original,scenario[scenario.index('void oapiWriteScenario_string'):],'Original scenario and item readers/writers')
    remaining=remaining[:begin]+remaining[end:]
    equal(remaining,raw(path),path);result[path]=old(path)
    fmt='// Floating point output stream formatter'
    for utility in ('Src/Orbiter/Util.h','Src/Orbiter/Util.cpp'):
        source=old(utility)
        start=source.index(fmt)
        if utility.endswith('.cpp'):start=source.rindex('// ----',0,start)
        end=source.index('// Convert a CSS color',start) if utility.endswith('.h') else len(source)
        if source[start:end].strip() not in scenario:raise ValueError('Original floating-point formatter differs: '+utility)
        equal(source[:start]+source[end:],raw(utility),utility);result[utility]=source
    # Preserve stock module capabilities, force-coefficient tables and animation
    # associations. Only exact Windows scalar aliases and its native entry differ.
    path='Src/Vessel/ShuttlePB/ShuttlePB.cpp';s=aliases(raw(path))
    s=s.replace('#ifdef ORBITER_NATIVE_MODULE\n#include "NativeVesselAPI.h"\n#define DLLCLBK static\n#else\n#include "orbitersdk.h"\n#endif','#include "orbitersdk.h"')
    s=s.replace('\n#ifdef ORBITER_NATIVE_MODULE\n#include "NativeShuttlePBFactory.inc"\n#endif','')
    equal(old(path),s,path);result[path]=old(path)
    verify_recorder(result)
    print('Complete stock vessel SDK, lights, recorder and ShuttlePB formulas conserved through native services')
    return result

def verify_recorder(result):
    path='Src/Orbiter/FlightRecorder.cpp';s=old(path)
    a=s.index('const double max_step');b=s.index('// ================================================================\n// System event recording/playback',a)
    helper=s.index('// convert Euler angles from given reference frame to quaternion')
    expected=s[:a]+'#include "Production/VesselRecorderState.h"\n\n'+s[b:helper]
    current=raw(path).replace('#include "Production/SystemPlayback.h"','')
    start,end=span(current,'Orbiter::FRecorder_Play')
    # Reconstitute the single shared system event loop with its Windows services.
    system=raw('Src/Orbiter/Production/SystemPlayback.h')
    loop=system[system.index('while (stream.good()'):system.index('\n}\n}')]
    for before,after in [
        ('stream.good()', 'FRsys_stream'),('clock.', 'td.'),('nextEvent','frec_sys_simt'),
        ('char cbuf[1024+12]{}','char cbuf[1024]'),('stream.getline','FRsys_stream->getline'),
        ('if (!stream && !stream.eof()) break;', ''),("if (auto *cr = strchr(cbuf, '\\r')) *cr = 0;",''),
        ('ComparePrefix','_strnicmp'),('options.','Cfg()->CfgRecPlayPrm.'),
        ('GetVesselServices().PlaybackWarp(RecordingSpeed,WarpDelay);','SetWarpFactor (RecordingSpeed, true, WarpDelay);'),
        ('Cfg()->CfgRecPlayPrm.bReplayCam && s && !_strnicmp','!_strnicmp'),
        ('if (sscanf (s+7, "%d", &i) == 1) camera.RecallPreset','sscanf (s+7, "%d", &i); g_camera->RecallPreset'),
        ('OwnedCameraMode cm(CameraMode::Create(s+4));','CameraMode *cm = CameraMode::Create(s+4);'),
        ('if (cm) camera.SetCMode(cm.get());','if(cm) g_camera->SetCMode(cm); delete cm;'),
        ('s ? GetRigidBodyServices().World()->GetVessel (s, true) : nullptr','g_psys->GetVessel (s, true)'),
        ('setFocus(vfocus)','g_pOrbiter->SetFocusObject(vfocus)'),
        ('sscanf (s+11, "%lf", &jumptime) == 1','sscanf (s+11, "%lf", &jumptime)'),
        ('jumpTo(tgtmjd)','g_pOrbiter->Timejump(tgtmjd,PROP_ORBITAL_FIXEDSURF)'),
        ('endSession();','if(hRenderWnd) PostMessage(hRenderWnd,WM_CLOSE,0,0);'),
        ('stream >> frec_sys_simt;', '*FRsys_stream >> frec_sys_simt; if (!FRsys_stream->good()) { delete FRsys_stream; FRsys_stream=0; }')
    ]:loop=loop.replace(before,after)
    note_body=raw('Src/Orbiter/Production/PlaybackAnnotation.inc')
    for checked,legacy in [
        ('if (sscanf (s+8, "%lf%lf%lf", &r, &g, &b)==3) {','sscanf (s+8, "%lf%lf%lf", &r, &g, &b);'),
        ('sa->SetColour (col);\n\t\t}', 'sa->SetColour (col);'),
        ('if (sscanf (s+9, "%lf", &scale)==1)', 'sscanf (s+9, "%lf", &scale);'),
        ('if (sscanf (s+8, "%lf%lf%lf%lf", &x1, &y1, &x2, &y2)==4)', 'sscanf (s+8, "%lf%lf%lf%lf", &x1, &y1, &x2, &y2);')
    ]:note_body=note_body.replace(checked,legacy)
    loop=loop.replace('GetVesselServices().PlaybackNote(s);','oapi::ScreenAnnotation *sa = SNotePB();\n'+note_body)
    assert 'PlaySystemEvents(*FRsys_stream,frec_sys_simt,td,*g_camera' in current[start:end]
    restored=current[:start]+'void Orbiter::FRecorder_Play ()\n{\n'+loop+'\n}'+current[end:]
    equal(expected,restored,'Original Windows system recorder');result[path]=old(path)
    original=s[a:b];actual=raw('Src/Orbiter/VesselRecorder.cpp');actual=actual[actual.index('const double max_step'):]
    helper_body=s[s.index('void Euler2Quaternion (double *a, Quaternion &q, int frm)\n{'):]
    original+='\n'+helper_body
    replay_binding='InterpolateRecordedAttitude (Q, frec_att[cfrec_att].q, frec_att[cfrec_att+1].q, w1);'
    legacy_interpolation='Q.interp (frec_att[cfrec_att].q, frec_att[cfrec_att+1].q, w1);'
    assert actual.count(replay_binding)==2 and legacy_interpolation not in actual
    actual=actual.replace(replay_binding,legacy_interpolation)
    actual=actual.replace('if (!append) {FRecorder_Clear(); FRecorder_Reset();}', 'if (!append) FRecorder_Reset();')
    actual=aliases(actual).replace('double Tofs =','static double Tofs =',1).replace('double MJDofs =','static double MJDofs =',1)
    for before,after in [('GetSurfaceServices().Configuration().','g_pOrbiter->Cfg()->'),('GetRigidBodyServices().Time().','td.'),
        ('GetRigidBodyServices().World()','g_psys'),('ComparePrefix','_strnicmp'),('CompareText','_stricmp'),
        ('GetRigidBodyServices().TraceAllocation(__FILE__,__LINE__);','TRACENEW'),
        ('GetVesselServices().PlaybackWarp (RecordingSpeed, WarpDelay)','g_pOrbiter->SetWarpFactor (RecordingSpeed, true, WarpDelay)'),
        ('GetVesselServices().RecallCameraPreset (i)','g_camera->RecallPreset (i)'),
        ('GetVesselServices().EndPlayback()','g_pOrbiter->EndPlayback()'),
        ('GetVesselServices().Check(s1 != nullptr, "Update state not available.");','dCHECK(s1, "Update state not available.")')]:actual=actual.replace(before,after)
    for name in ['FRfname','cbuf','fname']:
        for writing in ['true','false']:
            actual=actual.replace('GetVesselServices().RecorderFile('+name+','+writing+')',name)
    begin=original.index('\t\t\t\toapi::ScreenAnnotation *sa = ');end=original.index('\n\t\t\t} else if (modIntf.v->Version()',begin)
    note=original[begin:end]
    actual=actual.replace('\t\t\t\tGetVesselServices().PlaybackNote(s);',note)
    # Replace fixed-size playback paths in the expected source with the checked
    # string paths used by both builds. Missing/short samples cannot be indexed.
    a=original.index('int i;',original.index('bool Vessel::FRecorder_Read'))
    b=original.index('if (!ifs)',a)
    original=original[:a]+"""const std::string directory(scname);
    const auto start=directory.find_last_of("/\\\\");
    const std::string stem="Flights/"+directory.substr(start==std::string::npos ? 0 : start+1)+"/"+name;
    ifstream ifs (GetVesselServices().RecorderFile((stem+".pos").c_str(),false)); char cbuf[256];
    """+original[b:]
    original=original.replace('strcpy (fname+strlen(fname)-3, "att");\n\tifs.open (fname);',
        'ifs.open (GetVesselServices().RecorderFile((stem+".att").c_str(),false));')
    original=original.replace('strcpy (cbuf, fname); strcpy (cbuf+strlen(cbuf)-3, "atc");\n\tFRatc_stream = new ifstream (cbuf);',
        'FRatc_stream = new ifstream (GetVesselServices().RecorderFile((stem+".atc").c_str(),false));')
    original=original.replace('cfrec = 0;\n\tcfrec_att = 0;', 'if (nfrec < 2) {FRecorder_Clear(); return false;} cfrec = 0; cfrec_att = 0;')
    original=original.replace('sscanf (cbuf, "%lf%lf%lf%lf", &simt, a+0, a+1, a+2);','if (sscanf (cbuf, "%lf%lf%lf%lf", &simt, a+0, a+1, a+2)!=4) continue;')
    original=original.replace('if (td.SimT1 < frec_att[nfrec_att-1].simt)', 'if (nfrec_att >= 2 && td.SimT1 < frec_att[nfrec_att-1].simt)')
    original=original.replace('char cbuf[1024], *s, *e, c;', 'char cbuf[1024+12]{}, *s, *e, c;')
    original=original.replace('FRatc_stream->getline (cbuf, 1024);', "FRatc_stream->getline (cbuf, 1024); if(auto *cr=strchr(cbuf,'\\r')) *cr=0;")
    # Check scan counts, buffer sizes and missing tokens before dispatch.
    for old_input,checked_input in [
        ('sscanf (s, "%d%c%lf", &id','sscanf (s, "%u%c%lf", &id'),
        ('sscanf (s+strlen(THGROUPSTR[i])+1, "%lf", &lvl))','sscanf (s+strlen(THGROUPSTR[i])+1, "%lf", &lvl)==1)'),
        ('sscanf (s+11, "%d", &i);\n\t\t\t\t\tClrNavMode (i, false, true);','if (sscanf (s+11, "%d", &i)==1) ClrNavMode (i, false, true);'),
        ('sscanf (s+8, "%d", &i);\n\t\t\t\t\tSetNavMode (i, true);','if (sscanf (s+8, "%d", &i)==1) SetNavMode (i, true);'),
        ('sscanf (s+8, "%d", &i);\n\t\t\t\tSetAttMode (i, true);','if (sscanf (s+8, "%d", &i)==1) SetAttMode (i, true);'),
        ('sscanf (s+8, "%d", &i);\n\t\t\t\tSetADCtrlMode (i, true);','if (sscanf (s+8, "%d", &i)==1) SetADCtrlMode (i, true);'),
        ('sscanf (s, "%d", &dock);\n\t\t\t\t\tUndock (dock);','if (sscanf (s, "%d", &dock)==1) Undock (dock);'),
        ('sscanf (s+7, "%d%lf", &id','sscanf (s+7, "%u%lf", &id'),
        ('AttachmentSpec *as = GetAttachmentFromIndex (false, id);','AttachmentSpec *as = res>=1 ? GetAttachmentFromIndex (false, id) : nullptr;'),
        ('"%s%d%d%s", cname, &pidx, &cidx, modestr','"%127s%u%u%31s", cname, &pidx, &cidx, modestr'),
        ('Vessel *child = g_psys->GetVessel (cname, true);','Vessel *child = res>=3 ? g_psys->GetVessel (cname, true) : nullptr;'),
        ('if (sscanf (s, "%d", &idx) == 1','if (s && sscanf (s, "%u", &idx) == 1'),
        ('if (!_stricmp (s, "ACTIVATE"))','if (s && !_stricmp (s, "ACTIVATE"))'),
        ('sscanf (s+9, "%d", &flag)','sscanf (s+9, "%u", &flag)'),
        ('if (!_strnicmp (s, "PRESET", 6)) {\n\t\t\t\t\tsscanf (s+7, "%d", &i);','if (s && !_strnicmp (s, "PRESET", 6) && sscanf (s+7, "%d", &i)==1) {'),
    ]:original=original.replace(old_input,checked_input)
    equal(original,actual,'Complete original vessel recording/playback/interpolation')
    # The only removed drawing operations are preserved in the Windows adapter.
    adapter=raw('Src/Orbiter/Production/WindowsVesselServices.cpp')
    start=adapter.index('oapi::ScreenAnnotation *sa =')
    end=adapter.index('\n    }',start)
    equal(note,adapter[start:end].replace('#include "PlaybackAnnotation.inc"',note_body),'Original playback annotations')

if __name__=='__main__':previous_files()
