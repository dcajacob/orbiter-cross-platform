#!/usr/bin/env python3
"""Conserve original cockpit algorithms while introducing real platform services."""
import subprocess
from pathlib import Path
from camera_source import windows
from vessel_runtime_source import equal,raw
ROOT=Path(__file__).resolve().parents[2]
BASE='f725194209634f7fd5d1d44d426cfa9b5e303e37'
FILES=('Pane.h','Pane.cpp','Mfd.h','Mfd.cpp','hud.h','hud.cpp','Panel.h','Panel.cpp',
       'Defpanel.h','Defpanel.cpp','Panel2D.h','Panel2D.cpp','VCockpit.h','VCockpit.cpp',
       'VectorMap.h','VectorMap.cpp','MfdSurface.cpp','Select.h',
       'MfdAlign.h','MfdComms.h','MfdDocking.h','MfdHsi.h','MfdLanding.h','MfdMap.h',
       'MfdMap_old.h','MfdOrbit.h','MfdSurface.h','MfdSync.h','MfdTransfer.h','Astro.h',
       'MfdOrbit.cpp','MfdAlign.cpp','MfdComms.cpp','MfdDocking.cpp','MfdHsi.cpp','MfdLanding.cpp',
       'MfdMap.cpp','MfdSync.cpp','MfdTransfer.cpp','Select.cpp')

def restore_geometry(name,current,original):
    """Prove the shared production conic implementation is an exact code move."""
    if name=='Mfd.cpp':
        body=original[original.index('// =======================================================================\n// local utility functions'):]
        expected='// Copyright (c) Martin Schweiger\n// Licensed under the MIT License\n\n#include "MfdOrbitGeometry.h"\n\nusing namespace std;\n\n'+body
        equal(expected,raw('Src/Orbiter/MfdOrbitGeometry.cpp'),'Original shared MFD conic implementation')
        current=current.rstrip()+'\n\n\n'+body
    elif name=='Mfd.h':
        constants=original[original.index('#define ELN '):original.index('const int MAXPEN')]
        start=original.index('// =======================================================================\n// local prototypes')
        declarations=original[start:original.index('#endif // !__MFD_H',start)]
        expected='// Copyright (c) Martin Schweiger\n// Licensed under the MIT License\n\n#ifndef ORBITER_MFD_ORBIT_GEOMETRY_H\n#define ORBITER_MFD_ORBIT_GEOMETRY_H\n#include "Element.h"\n#include "DrawAPI.h"\n\n'+constants+declarations+'#endif\n'
        equal(expected,raw('Src/Orbiter/MfdOrbitGeometry.h'),'Original shared MFD conic declarations and screen mapping')
        current=current.replace('#include "MfdOrbitGeometry.h"\n\n',constants,1)
        current=current.replace('#endif // !__MFD_H',declarations+'#endif // !__MFD_H',1)
    return current

def verify_focus_bars():
    def original(file):
        return subprocess.check_output(['git','-C',str(ROOT),'show',BASE+':Src/Orbiter/'+file]).replace(b'\r\n',b'\n').decode('utf-8')
    def current(file):
        return (ROOT/'Src/Orbiter'/file).read_bytes().replace(b'\r\n',b'\n').decode('utf-8')
    # Compare the actual original dialog/widget code after resolving the owning
    # application's read-only state and its real focus setter.
    old=original('MenuInfoBar.cpp')
    new=windows(current('MenuInfoBar.cpp'))
    def bars(s):
        return s[s.index('const ImGuiWindowFlags INFOFLAGS'):s.index('MenuInfoBar::MenuInfoBar')]
    new=bars(new)
    for adapter,expression in [('InfoClock()','td'),('InfoConfig()','g_pOrbiter->Cfg()->CfgUIPrm'),
            ('InfoCamera()','g_camera'),('InfoRecording()','g_pOrbiter->RecorderStatus() == 1'),
            ('InfoPlayback()','g_pOrbiter->IsPlayback()'),('InfoRunning()','g_pOrbiter->IsRunning()')]:
        new=new.replace(adapter,expression)
    # The movable menu item owns one surface. Erasing an item releases the
    # previous surface before transferring the next one into its slot.
    new=new.replace('SURFHANDLE texture = nullptr;','SURFHANDLE texture;').replace('MenuItem& operator=(MenuItem&&','MenuItem& MenuItem::operator=(MenuItem&&')
    new=new.replace('if (this == &other) return *this;','').replace('if (texture) oapiDestroySurface(texture);','')
    new=new.replace('FILE_IN_ZEROONFAIL','FILE_IN').replace('if (!f) continue;','')
    equal(bars(old),new,'Original time, target, FPS, animation and menu rendering')
    for filename,start,adapters in [
        ('DlgCamera.cpp','DlgCamera::DlgCamera()',[
            ('CockpitCamera()','g_camera'),('CockpitFocus()','g_focusobj'),('CockpitTime()','td'),
            ('CockpitWorld()','g_psys'),('CockpitPane()','g_pane'),('SetCameraView','g_pOrbiter->SetView'),
            ('oapi::UInt32','DWORD'),('ImGui::TextUnformatted(g_focusobj->Name())','ImGui::Text(g_focusobj->Name())')]),
        ('DlgTacc.cpp','static float SnapToDecimal',[
            ('SetDialogWarp','g_pOrbiter->SetWarpFactor'),('DialogWarp()','td.Warp()'),
            ('DialogRunning()','g_pOrbiter->IsRunning()'),('ToggleDialogPause()','g_pOrbiter->TogglePause()')]),
        ('DlgMenuCfg.cpp','DlgMenuCfg::DlgMenuCfg()',[
            ('mib->GetPreferences()','g_pane->MIBar()->GetPreferences()'),('mib->SyncPreferences()','g_pane->MIBar()->SyncPreferences()')]),
    ]:
        before=original(filename);after=windows(current(filename))
        for adapter,expr in adapters:after=after.replace(adapter,expr)
        equal(before[before.index(start):],after[after.index(start):],'Original '+filename+' interactions')
    widgets=current('Production/GuiAnimatedControls.inc').replace('ORBITER_WIDGET_EXPORT','DLLEXPORT')
    dialog_manager=original('DlgMgr.cpp')
    start=dialog_manager.index('/* \nNotification handling')
    end=dialog_manager.index('// ImGui utils',start)
    equal(dialog_manager[start:end],
          current('Production/GuiNotifications.inc').replace('ORBITER_NOTIFICATION_EXPORT','DLLEXPORT'),
          'Original notification widgets, timing, deduplication and dismissal')
    equal(dialog_manager[dialog_manager.index('DLLEXPORT bool BeginAnimatedCombo'):dialog_manager.rindex('\n}')],
          widgets,'Original combo and collapsing-header drawing, animation and input')
    before=original('DlgRecorder.cpp');after=windows(current('DlgRecorder.cpp'))
    for adapter,expr in [
            ('RecorderStatus()','g_pOrbiter->RecorderStatus()'),
            ('ToggleRecorder (m_ScenarioFile,true)','g_pOrbiter->ToggleRecorder (true)'),
            ('ToggleRecorder (m_ScenarioFile)','g_pOrbiter->ToggleRecorder ()'),
            ('RecorderConfig()','g_pOrbiter->Cfg()'),('StopPlayback()','g_pOrbiter->EndPlayback ()'),
            ('RecordedWarp(RecordingSpeed)','g_pOrbiter->SetWarpFactor (RecordingSpeed, true)'),
            ('RecorderFocus()','g_focusobj'),('RecordedFocus(vfocus)','g_pOrbiter->SetFocusObject (vfocus)'),
            ('OpenRecorderEditor()','g_pOrbiter->FRecorder_ToggleEditor()')]:
        after=after.replace(adapter,expr)
    equal(before[before.index('DlgRecorder::DlgRecorder()'):],after[after.index('DlgRecorder::DlgRecorder()'):],
          'Original recorder controls and playback options through real application services')
    before=original('PlaybackEd.cpp');after=windows(current('PlaybackEd.cpp'))
    for adapter,expr in [('EditorTime()','td.SimT0'),('EditorCamera()','g_camera'),
            ('orbiter::production::CompareText','_stricmp'),
            ('orbiter::production::OwnedCameraMode cm(g_camera->GetCMode());','CameraMode *cm = g_camera->GetCMode();'),
            ('delete *it;',''),
            ('strdup(_note ? _note : "")','strdup(_note)')]:
        after=after.replace(adapter,expr)
    # Only the destructor gains filename cleanup. Leave Load() untouched so its
    # original cleanup remains checked, including on CRLF Windows checkouts.
    destructor='DlgPlaybackEditor::~DlgPlaybackEditor() {\n\tfree(m_sysfname);'
    if after.count(destructor)!=1:raise ValueError('Playback editor destructor cleanup changed')
    after=after.replace(destructor,'DlgPlaybackEditor::~DlgPlaybackEditor() {',1)
    # Committing now writes a temporary file before suspending/reopening the
    # actual stream. The recorder round-trip test exercises that replacement.
    a=after.index('void DlgPlaybackEditor::SaveEventFile ()')
    b=after.index('void DlgPlaybackEditor::ClearEvents()',a)
    c=before.index('void DlgPlaybackEditor::SaveEventFile ()')
    d=before.index('void DlgPlaybackEditor::ClearEvents()',c)
    after=after[:a]+before[c:d]+after[b:]
    equal(before[before.index('static bool CompareEvents'):],after[after.index('static bool CompareEvents'):],
          'Original playback editor widgets and event serialization with owned events/camera modes')
    before=original('DlgFunction.cpp');after=windows(current('DlgFunction.cpp'))
    for adapter,expr in [
            ('for (const auto& command : CommandsForDisplay())','for (int i = 0; i < g_pOrbiter->ncustomcmd; i++)'),
            ('if(!CommandPresent(command.id))continue;',''),('ImGui::PushID(command.id);',''),('ImGui::PopID();',''),
            ('command.label.c_str()','g_pOrbiter->customcmd[i].label'),
            ('command.description.c_str()','g_pOrbiter->customcmd[i].desc'),
            ('InvokeCommand(command.id);','g_pOrbiter->customcmd[i].func (g_pOrbiter->customcmd[i].context);')]:
        after=after.replace(adapter,expr)
    equal(before[before.index('DlgFunction::DlgFunction()'):],after[after.index('DlgFunction::DlgFunction()'):],
          'Original custom function buttons and tooltips with stable callback snapshots')
    before=original('Orbiter.cpp');after=current('Orbiter.cpp')
    start='DWORD Orbiter::RegisterCustomCmd';end='int Orbiter::RegisterMenuCmd'
    equal(before[before.index(start):before.index(end)],
          after[after.index(start):after.index(end)].replace('delete []customcmd[i].label;',''),
          'Original Windows custom registration with removed-label ownership repaired')
    option_widgets=current('Production/GuiOptionControls.inc').replace('ORBITER_WIDGET_EXPORT','DLLEXPORT')
    expected=dialog_manager[dialog_manager.index('// Resettable slider'):dialog_manager.index('DLLEXPORT void PushFont')]
    expected+=dialog_manager[dialog_manager.index('DLLEXPORT bool SliderEnum'):dialog_manager.index('// "Animated" widgets')]
    equal(expected,option_widgets,'Original option slider and bounded input widgets')
    before=original('DlgOptions.cpp');after=windows(current('DlgOptions.cpp'))
    for adapter,expr in [('CockpitConfiguration()','g_pOrbiter->Cfg()'),('CockpitConfigPath(','g_pOrbiter->Cfg()->ConfigPath('),
            ('CockpitWorld()','g_psys'),('OptionsChanged(OPTCAT','g_pOrbiter->OnOptionChanged(OPTCAT'),
            ('auto &list =','std::vector<oapi::GraphicsClient::LABELLIST> &list ='),
            ('auto* list =','oapi::GraphicsClient::LABELLIST* list ='),
            ('const auto* lspec =','const oapi::GraphicsClient::LABELTYPE* lspec =')]:
        after=after.replace(adapter,expr)
    equal(before[before.index('DlgOptions::DlgOptions()'):],after[after.index('DlgOptions::DlgOptions()'):],
          'Original option pages, settings and change notifications')
    before=original('DlgMap.cpp');after=windows(current('DlgMap.cpp'))
    for adapter,expr in [('CockpitWorld()','g_psys'),('CockpitTime()','td'),('CockpitConfiguration()','g_pOrbiter->Cfg()'),
            ('ComparePrefix','_strnicmp'),('CompareText','_stricmp'),('oapi::UInt32','DWORD'),
            (' && vectormap)',' )'),('snprintf(searchbuf,sizeof(searchbuf),"%s",','strcpy(searchbuf,')]:
        after=after.replace(adapter,expr)
    equal(before[before.index('DlgMap::DlgMap()'):],after[after.index('DlgMap::DlgMap()'):],'Original map controls, selection, and drawing')
    before=original('DlgInfo.cpp');after=windows(current('DlgInfo.cpp')).replace('CockpitWorld()','g_psys')
    a=before.index('            strcpy (cbuf, "Generic");')
    b=before.index('            ImGui::TableNextRow();',a)
    after=after.replace('const auto& celestial=orbiter::production::GetCelestialServices();','const CELBODY *cb = cbody->GetModuleInterface();')
    after=after.replace('const ATMCONST *ap = planet->AtmParams();','char cbuf[128];\n            const ATMCONST *ap = planet->AtmParams();')
    after=after.replace('const char* model=celestial.AtmosphereName(*cbody);',before[a:b])
    after=after.replace('model ? model : "Generic"','cbuf').replace('celestial.HasModule(*cbody) ?','cb ?')
    equal(before[before.index('DlgInfo::DlgInfo()'):],after[after.index('DlgInfo::DlgInfo()'):],'Original object information display')
    old=original('DlgFocus.cpp')
    new=windows(current('DlgFocus.cpp'))
    for adapter,expression in [('FocusWorld()','g_psys'),('FocusCamera()','g_camera'),
            ('SelectFocus (','g_pOrbiter->SetFocusObject ('),('PriorFocus()','g_pfocusobj'),
            ('snprintf(cbuf,sizeof(cbuf),','sprintf(cbuf,')]:
        new=new.replace(adapter,expression)
    equal(old[old.index('DlgFocus::DlgFocus()'):],new[new.index('DlgFocus::DlgFocus()'):],
          'Original four spacecraft selection tabs and focus actions')
    button=current('Production/GuiMenuButton.inc').replace('ORBITER_MENU_EXPORT','DLLEXPORT')
    old=original('DlgMgr.cpp')
    equal(old[old.index('DLLEXPORT bool MenuButton'):old.index('DLLEXPORT ImTextureID GetImTextureID')],
          button,'Original title bar button placement and input')
    print('Verified original info bars, spacecraft selector and title bar button')

def restore_heading_marker_lifetime(current,original):
    start='void HUD::AddMesh_HeadingTape ('
    end='void HUD::AddMesh_AzimuthTape ('
    def method(source):return source[source.index(start):source.index(end)]
    before,after=method(original),method(current)
    pointers='\t\tdouble *vtxx, *vtxy, *vtxu, *vtxv;\n'
    writer_start=before.index('\t\tfor (i = 0; i < nidx; i++) {',before.index(pointers))
    writer_end=before.rindex('\t}\n}')
    writer=before[writer_start:writer_end]
    closure='\t\tauto append_marker = [&](const double *vtxx, const double *vtxy, const double *vtxu, const double *vtxv) {\n'
    closure+=''.join('\t'+line for line in writer.splitlines(keepends=True))+'\t\t};\n'
    expected=(before[:writer_start]+before[writer_end:]).replace(pointers,closure,1)
    for branch in (1,2,3):
        alias=f'vtxx = vtxx{branch}, vtxy = vtxy{branch}, vtxu = vtxu{branch}, vtxv = vtxv{branch};'
        expected=expected.replace(alias,f'append_marker(vtxx{branch}, vtxy{branch}, vtxu{branch}, vtxv{branch});',1)
    equal(expected,after,'Original HUD marker values and mesh writes, consumed before branch-local arrays expire')
    return current.replace(after,before,1)

def restore_transfer_initialization(current):
    # The hypothetical-orbit path reads this flag on its first draw, before
    # that draw's existing reset. Only initialize the pending-input flag;
    # every original maneuver calculation and callback remains checked.
    initialized='\tprocess_num = false;\n\tdv_manip = false;\n'
    if current.count(initialized)!=1:
        raise ValueError('Transfer MFD pending delta-v initialization changed')
    return current.replace(initialized,'\tprocess_num = false;\n',1)

def restore_transfer_rotation_lifetime(current):
    declaration='\tMatrix rot2, rot3, *workr;\n'
    expression='RotMatrix (shpel2->coso, shpel2->sino, shpel2->cost, shpel2->sint, shpel2->cosi, shpel2->sini)'
    assignment='\t\trot3.Set ('+expression+');'
    if current.count(declaration)!=1 or current.count(assignment)!=1:
        raise ValueError('Transfer MFD hypothetical rotation lifetime changed')
    return current.replace(declaration,'\tMatrix rot2, *workr;\n',1).replace(assignment,'\t\tMatrix rot3 ('+expression+');',1)

def restore_transfer_finite_indicators(current):
    line='\t\t\tskp->Line (ICNTX, ICNTY, ICNTX+(int)(v.x*pixrad), ICNTY-(int)(v.z*pixrad));'
    guarded='\t\t\tif (std::isfinite(v.x) && std::isfinite(v.z))\n\t'+line
    if current.count(guarded)!=2 or current.count('#include <cmath>')!=1:
        raise ValueError('Transfer MFD nonfinite indicator guards changed')
    return current.replace(guarded,line).replace('#include <cmath>\n','',1)

def verify():
    verify_focus_bars()
    original_dialogs = subprocess.check_output(['git','-C',str(ROOT),'show',BASE+':Src/Orbiter/DlgMgr.cpp']).decode().replace('\r\n','\n')
    style = original_dialogs[original_dialogs.index('static void ApplyGlowTheme'):original_dialogs.index('void DialogManager::InitImGui()')]
    native_dialogs = raw('Src/Orbiter/Production/NativeCockpitGui.cpp')
    native_style = native_dialogs[native_dialogs.index('static void ApplyGlowTheme'):native_dialogs.index('std::unique_ptr<Select> selection;')]
    equal(style.strip(),native_style.strip(),'Original cockpit GUI colors, geometry and styling')
    services=windows(raw('Src/Orbiter/Production/CockpitServices.h'))
    equal('''#ifndef ORBITER_PRODUCTION_COCKPIT_SERVICES_H
#define ORBITER_PRODUCTION_COCKPIT_SERVICES_H
#include "CameraServices.h"
#include "CockpitGraphics.h"
#include "BodyServices.h"
#include "RigidBodyServices.h"
class Pane;class Select;class InputBox;
#include "Orbiter.h"
extern Orbiter* g_pOrbiter;
extern Pane* g_pane;extern Select* g_select;extern InputBox* g_input;extern HELPCONTEXT DefHelpContext;
extern TimeData td;extern PlanetarySystem* g_psys;extern Vessel* g_focusobj;
extern Camera* g_camera;
namespace orbiter::production {
inline Camera* CockpitCamera() {return g_camera;}
namespace CockpitMouse {
constexpr oapi::UInt LeftDown=WM_LBUTTONDOWN,RightDown=WM_RBUTTONDOWN,LeftUp=WM_LBUTTONUP,RightUp=WM_RBUTTONUP,Wheel=WM_MOUSEWHEEL;
}
inline oapi::SdkRectangle CockpitRectangle(int left,int top,int right,int bottom) {return _R(left,top,right,bottom);}
inline int CockpitScreenHeight() {return GetSystemMetrics(SM_CYSCREEN);}
inline TimeData& CockpitTime() {return td;}
inline PlanetarySystem* CockpitWorld() {return g_psys;}
inline Vessel* CockpitFocus() {return g_focusobj;}
inline Pane* ActiveCockpitPane() {return g_pane;}
inline Pane* CockpitPane() {return g_pane;}
inline Select* CockpitSelect() {return g_select;}
inline InputBox* CockpitInput() {return g_input;}
inline HELPCONTEXT& CockpitHelpContext() {return DefHelpContext;}
inline std::uint16_t CockpitHighWord(oapi::UInt32 value) {return HIWORD(value);}
inline std::uint16_t CockpitLowWord(oapi::UInt32 value) {return LOWORD(value);}
inline oapi::UInt32 CockpitColor(std::uint8_t r,std::uint8_t g,std::uint8_t b) {return RGB(r,g,b);}
inline Config* CockpitConfiguration() {return &GetCameraServices().Configuration();}
inline oapi::CockpitClient* CockpitGraphicsClient() {return g_pOrbiter->GetGraphicsClient();}
inline std::filesystem::path CockpitConfigPath(const char* name) {return g_pOrbiter->ConfigPath(name);}
inline bool CockpitReleaseSurface(SURFHANDLE surface) {return g_pOrbiter->ReleaseSurface(surface);}
inline oapi::UInt32 CockpitDeviceColour(std::uint8_t r,std::uint8_t g,std::uint8_t b) {return g_pOrbiter->GetDeviceColour(r,g,b);}
inline bool CockpitFillSurface(SURFHANDLE surface,oapi::UInt32 color) {return g_pOrbiter->FillSurface(surface,color);}
inline bool CockpitBlt(SURFHANDLE target,oapi::UInt32 x,oapi::UInt32 y,SURFHANDLE source,oapi::UInt32 flags=0) {return g_pOrbiter->Blt(target,x,y,source,flags);}
inline bool CockpitBlt(SURFHANDLE target,oapi::UInt32 x,oapi::UInt32 y,SURFHANDLE source,oapi::UInt32 sx,oapi::UInt32 sy,oapi::UInt32 width,oapi::UInt32 height,oapi::UInt32 flags=0) {return g_pOrbiter->Blt(target,x,y,source,sx,sy,width,height,flags);}
}
#endif''',services,'Windows cockpit service adapter identities')
    equal('''#ifndef ORBITER_PRODUCTION_COCKPIT_NATIVE_SUPPORT_H
#define ORBITER_PRODUCTION_COCKPIT_NATIVE_SUPPORT_H
#include "RigidBodyServices.h"
#include "CockpitServices.h"
#include "OrbiterScalar.h"
#include "OrbiterGeometry.h"
#include "FlightKeys.h"
#include "ConfigFile.h"
#include "Config.h"
#include "Text.h"
#include <algorithm>
inline double normangle(double angle) {double a=fmod(angle,PI2);return a>=PI?a-PI2:a< -PI?a+PI2:a;}
inline double posangle(double angle) {return orbiter::math::PositiveAngle(angle,PI2);}
#define TRACENEW orbiter::production::GetRigidBodyServices().TraceAllocation(__FILE__,__LINE__);
#endif''',raw('Src/Orbiter/Production/CockpitNativeSupport.h'),'Native instrument math, text and allocation bindings')
    header=windows(raw('Src/Orbiter/Production/CockpitGraphics.h'))
    equal('''#ifndef ORBITER_PRODUCTION_COCKPIT_GRAPHICS_H
#define ORBITER_PRODUCTION_COCKPIT_GRAPHICS_H
#include "GraphicsAPI.h"
namespace oapi {using CockpitClient=GraphicsClient;}
#endif''',header,'Windows cockpit graphics type identity')
    legacy_source=subprocess.check_output(['git','-C',str(ROOT),'show',BASE+':Src/Orbiter/OrbiterAPI.cpp']).decode('cp1252').replace('\r\n','\n')
    delegates=[]
    for signature in ('void oapiRegisterMFD (int mfd, const MFDSPEC &spec)',
                      'void oapiRegisterPanelBackground (HBITMAP hBmp, DWORD flag, DWORD ck)',
                      'void oapiRegisterPanelArea (int id, const RECT &pos, int draw_event, int mouse_event, int bkmode)'):
        start=legacy_source.index(signature);end=legacy_source.index('\n}',start)+2
        body=legacy_source[start:end]
        for before,after in [('g_pane','orbiter::production::CockpitPane()'),('HBITMAP','SURFHANDLE'),('DWORD','oapi::UInt32'),('RECT','oapi::SdkRectangle')]:body=body.replace(before,after)
        delegates.append(body)
    actual=raw('Src/Orbiter/Production/NativeLegacyPanelSdk.cpp')
    actual=actual[actual.index('void oapiRegisterMFD'):]
    equal('\n\n'.join(delegates)+'\n',actual,'Original legacy MFD/background/area SDK delegates with actual native surface ownership')
    for name in FILES:
        path='Src/Orbiter/'+name
        import re
        view=windows(raw(path))
        if name.endswith('.cpp') and re.search(r'orbiter::production::Cockpit\w+\s*\(',view):
            if '#include "Production/CockpitServices.h"' not in view:
                raise ValueError('Windows cockpit implementation lacks its explicit service include: '+name)
        original=subprocess.check_output(['git','-C',str(ROOT),'show',BASE+':'+path]).decode('cp1252').replace('\r\n','\n')
        current=view.replace('oapi::CockpitClient','oapi::GraphicsClient')
        if name in ('Panel.h','Panel.cpp'):
            # The SDK coordinate is original Windows LONG and explicit native int32.
            current=current.replace('oapi::SdkCoordinate','LONG')
            current=current.replace('LONG srcX, LONG srcY, LONG &tgtX, LONG &tgtY',
                                    'long srcX, long srcY, long &tgtX, long &tgtY')
            current=current.replace('srcX = (LONG)(srcX*scale)','srcX = (long)(srcX*scale)')
            current=current.replace('srcY = (LONG)(srcY*scale)','srcY = (long)(srcY*scale)')
        if name=='Panel2D.h':
            observation='\t// Read-only engine observation; no panel state or SDK layout changes.\n\tvoid GetOrigin(double &x, double &y) const { x = x0; y = y0; }\n'
            if current.count(observation)!=1:raise ValueError('Panel origin observation changed')
            current=current.replace(observation,'',1)
        # Only the original known Elements call sites receive explicit time.
        current=current.replace('new Elements(orbiter::production::CockpitTime().MJD_ref)','new Elements()')
        import re
        pattern=re.compile(r'\b(?:shpel2?|tgtel|el2)->(?:Setup|Set|Reset|Update)\s*\(')
        for match in reversed(list(pattern.finditer(current))):
            start=match.end()-1;depth=1;end=start+1
            while depth:
                if current[end]=='(':depth+=1
                elif current[end]==')':depth-=1
                end+=1
            argument='orbiter::production::CockpitTime().SimT1' if '->Update' in match.group(0) else 'orbiter::production::CockpitTime().MJD_ref'
            suffix=', '+argument
            if not current[:end-1].endswith(suffix):raise ValueError('Instrument Elements lacks its explicit original time input: '+name)
            current=current[:end-1-len(suffix)]+current[end-1:]
        for service,application in [('CockpitCamera()','g_camera'),('CockpitTime()','td'),('CockpitWorld()','g_psys'),('CockpitFocus()','g_focusobj'),('CockpitPane()','g_pane'),('CockpitSelect()','g_select'),('CockpitInput()','g_input'),('CockpitHelpContext()','DefHelpContext')]:
            current=current.replace('orbiter::production::'+service,application)
        current=current.replace('orbiter::production::CockpitConfiguration()','g_pOrbiter->Cfg()')
        current=current.replace('#include "Production/CockpitServices.h"','').replace('#include "Production/CockpitProjection.h"','')
        for key,value in [('WM_LBUTTONDOWN','LeftDown'),('WM_RBUTTONDOWN','RightDown'),('WM_LBUTTONUP','LeftUp'),('WM_RBUTTONUP','RightUp'),('WM_MOUSEWHEEL','Wheel')]:current=current.replace('orbiter::production::CockpitMouse::'+value,key)
        for service,application in [('CockpitColor','RGB'),('CockpitGraphicsClient','g_pOrbiter->GetGraphicsClient'),('CockpitReleaseSurface','g_pOrbiter->ReleaseSurface'),('CockpitDeviceColour','g_pOrbiter->GetDeviceColour'),('CockpitFillSurface','g_pOrbiter->FillSurface'),('CockpitBlt','g_pOrbiter->Blt'),('CockpitConfigPath','g_pOrbiter->ConfigPath'),('ComparePrefix','_strnicmp'),('CompareText','_stricmp'),('CockpitHighWord','HIWORD'),('CockpitLowWord','LOWORD'),('CockpitRectangle','_R')]:
            current=current.replace('orbiter::production::'+service,application)
        for a,b in [('orbiter::production::CockpitPoint','D3DVECTOR'),('std::uint16_t','WORD'),('std::uint8_t','BYTE'),('oapi::UInt32','DWORD'),('std::intptr_t','INT_PTR'),('oapi::SdkDrawContext','HDC'),('oapi::SdkFont','HFONT'),('oapi::SdkPoint','POINT'),('oapi::UInt','UINT'),('oapi::SdkRectangle','RECT')]:current=current.replace(a,b)
        if name in ('Mfd.h','hud.h'):current=current.replace('#include "Production/CockpitGraphics.h"','#include "GraphicsAPI.h"')
        else:current=current.replace('#include "Production/CockpitGraphics.h"','')
        if name=='Mfd.h':current=current.replace('class Pane;','class Pane;\nclass oapi::GraphicsClient;',1)
        if name=='VectorMap.h':current=current.replace('explicit DRAWDATA(double reference_mjd):focusel(reference_mjd),tgtvel(reference_mjd) {}','',1)
        if name=='VectorMap.cpp':
            # LSan attributes 24 leaked font/pen/brush allocations to the map.
            # Its existing release routine had no caller. Only pair allocation
            # with that original release routine at destruction.
            repair='\tCloseGDIResources();\n'
            if current.count(repair)!=1:raise ValueError('Map resource destruction differs')
            current=current.replace(repair,'',1)
            current=current.replace(':drawdata(td.MJD_ref)','')
            current=current.replace('drawdata.focusel.Set (*g_focusobj->Els(), td.MJD_ref)','drawdata.focusel.Set (*g_focusobj->Els())')
            current=current.replace('orbiter::production::CockpitScreenHeight()','GetSystemMetrics(SM_CYSCREEN)')
        if name=='MfdHsi.cpp':current=current.replace('static const int arrowseg','static const INT arrowseg').replace('static const int narrowseg','static const INT narrowseg')
        if name=='MfdAlign.cpp':current=current.replace('saveprm = {0,0,0,false,0.0,0.0}','saveprm = {0,0,0,0.0,0.0,false}')
        if name=='MfdTransfer.cpp':current=restore_transfer_finite_indicators(restore_transfer_rotation_lifetime(restore_transfer_initialization(current)))
        if name=='Mfd.cpp':
            current=current.replace('(long long)id + 1','(int64_t)id + 1').replace('#include <memory>','')
            # The scenario loader owns the instrument through ReadParams, including exceptions.
            owned='std::unique_ptr<Instrument> owner(instr);\n\tif (owner && owner->ReadParams(ifs)) return owner.release();\n\treturn nullptr;'
            start=original.index('if (instr) {\n\t\tif (!instr->ReadParams')
            end=original.index('\n}',start)
            if current.count(owned)!=1:raise ValueError('Scenario MFD ownership changed')
            current=current.replace(owned,original[start:end])
        if name=='Pane.cpp':
            for initialization in ('mfd[i].prm      = {};','mfd[id].prm.flag     = 0;'):
                if current.count(initialization)!=1:raise ValueError('MFD off-state initialization changed')
                current=current.replace(initialization,'',1)
        if name=='hud.cpp':current=restore_heading_marker_lifetime(current,original)
        current=restore_geometry(name,current,original)
        equal(original.replace('COLORREF','DWORD'),current.replace('COLORREF','DWORD'),'Original cockpit calculations, declarations and call order: '+name)
    print('Original Pane, HUD, MFD and panel algorithms conserved; Windows graphics pointer types unchanged')
if __name__=='__main__':verify()
