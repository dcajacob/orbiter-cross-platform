// Copyright (c) Martin Schweiger
// Licensed under the MIT License

// ======================================================================
// Flight recorder dialog
// ======================================================================

#include "DlgRecorder.h"
#ifdef _WIN32
#include "Orbiter.h"
#include "OrbiterAPI.h"
#else
#include "Production/NativeGraphics.h"
#include "Production/CockpitGuiExports.h"
#include "Production/NativeInterpreterSdk.h"
#include "Production/NativeCockpitUi.h"
#include "Production/VesselRecorderState.h"
#include "Production/VesselServices.h"
#include "Production/CameraServices.h"
#include "Config.h"
#endif
#include "imgui.h"
#include "imgui_extras.h"
#include "IconsFontAwesome6.h"

#ifdef _WIN32
extern Vessel *g_focusobj;
extern Orbiter *g_pOrbiter;
static int RecorderStatus() {return g_pOrbiter->RecorderStatus();}
static bool ToggleRecorder(const char*,bool force=false) {return g_pOrbiter->ToggleRecorder(force);}
static Config* RecorderConfig() {return g_pOrbiter->Cfg();}
static void StopPlayback() {g_pOrbiter->EndPlayback();}
static void RecordedWarp(double warp) {g_pOrbiter->SetWarpFactor(warp,true);}
static Vessel* RecorderFocus() {return g_focusobj;}
static void RecordedFocus(Vessel* v) {g_pOrbiter->SetFocusObject(v);}
static void OpenRecorderEditor() {g_pOrbiter->FRecorder_ToggleEditor();}
#else
using namespace orbiter::production;
static int RecorderStatus() {return GetNativeRenderContext().scriptApplication->RecorderStatus();}
static bool ToggleRecorder(const char* name,bool force=false) {return GetNativeRenderContext().scriptApplication->ToggleRecorder(name,force);}
static Config* RecorderConfig() {return GetNativeRenderContext().configuration;}
static void StopPlayback() {GetNativeRenderContext().scriptApplication->EndPlayback();}
static void RecordedWarp(double warp) {GetVesselServices().PlaybackWarp(warp,0);}
static Vessel* RecorderFocus() {return GetNativeRenderContext().focus;}
static void RecordedFocus(Vessel* v) {GetCameraServices().SetFocus(v);}
static void OpenRecorderEditor() {OpenCockpitPlaybackEditor();}
#endif

DlgRecorder::DlgRecorder() : ImGuiDialog(ICON_FA_FILM " Flight recorder/player", {329,354}) {
#ifndef _WIN32
    GetNativeRenderContext().optionsUsed=true;
#endif
	SetHelp("html/orbiter.chm", "/recorder.htm");
    strcpy(m_ScenarioFile, "test_record");
}

void DlgRecorder::OnDraw() {
    int status = RecorderStatus();
    static const char *statestr[3] = {"Status: Normal", "Status: Recording", "Status: Playing"};
    ImGui::TextUnformatted(statestr[status]);

    switch(status) {
        case 0: DrawNormalRecording(false); break;
        case 1: DrawNormalRecording(true); break;
        case 2: DrawPlaying(); break;
    }
}

void DlgRecorder::DrawNormalRecording(bool recording) {
    if(recording) {
        if(ImGui::Button("STOP")) {
            ToggleRecorder (m_ScenarioFile);
        }
    } else {
        if(ImGui::Button("REC")) {
            if(!ToggleRecorder (m_ScenarioFile))
                ImGui::OpenPopup("Warning");
        }
    }

    bool unused_open = true;
    if (ImGui::BeginPopupModal("Warning", &unused_open))
    {
        ImGui::TextUnformatted("A flight record under this name already exists!");
        if(ImGui::Button("Overwrite")) {
            ToggleRecorder (m_ScenarioFile,true);
            ImGui::CloseCurrentPopup();
        }
        ImGui::SameLine();
        if(ImGui::Button("Cancel")) {
            ImGui::CloseCurrentPopup();
        }
        ImGui::EndPopup();
    }

    ImGui::Separator();
    ImGui::InputText("Scenario", m_ScenarioFile, sizeof(m_ScenarioFile));
    if(ImGui::BeginAnimatedCollapsingHeader("Advanced")) {
        ImGui::Checkbox("Record Time Acceleration", &RecorderConfig()->CfgRecPlayPrm.bRecordWarp);
        ImGui::Checkbox("Record Focus Events", &RecorderConfig()->CfgRecPlayPrm.bRecordFocus);
        ImGui::BeginDisabled(recording);
        ImGui::Checkbox("Sampling in System Time Steps", &RecorderConfig()->CfgRecPlayPrm.bSysInterval);
        //char buf[20]="";
        //ImGui::InputText("sec. sampling", buf, 20);
        ImGui::Separator();
        ImGui::TextUnformatted("Attitude Data");
        ImGui::RadioButton("Ecliptic Frame###ef1", &RecorderConfig()->CfgRecPlayPrm.RecordAttFrame, 0);
        ImGui::RadioButton("Local Horizon Frame", &RecorderConfig()->CfgRecPlayPrm.RecordAttFrame, 1);

        ImGui::Separator();
        ImGui::TextUnformatted("Position / Velocity Data");
        ImGui::RadioButton("Ecliptic Frame###ef2", &RecorderConfig()->CfgRecPlayPrm.RecordPosFrame, 0);
        ImGui::RadioButton("Equatorial Frame", &RecorderConfig()->CfgRecPlayPrm.RecordPosFrame, 1);
        ImGui::EndDisabled();
        ImGui::EndAnimatedCollapsingHeader();
    }
}

void DlgRecorder::DrawPlaying() {
    if(ImGui::Button("STOP")) {
        StopPlayback();
    }
    ImGui::Separator();
    ImGui::TextUnformatted("Replay Options");
    ImGui::Checkbox("Show Inflight Notes", &RecorderConfig()->CfgRecPlayPrm.bShowNotes);
    if(ImGui::Checkbox("Play at Recording Speed", &RecorderConfig()->CfgRecPlayPrm.bReplayWarp)) {
		if (RecorderConfig()->CfgRecPlayPrm.bReplayWarp) {
			extern double RecordingSpeed;
			RecordedWarp(RecordingSpeed);
		}
    }
    if(ImGui::Checkbox("Use Recorded Camera Settings", &RecorderConfig()->CfgRecPlayPrm.bReplayCam)) {
		if (RecorderConfig()->CfgRecPlayPrm.bReplayCam) {
			// should set camera according to current playback status here!
		}
    }
    if(ImGui::Checkbox("Use Recorded Focus Events", &RecorderConfig()->CfgRecPlayPrm.bReplayFocus)) {
		if (RecorderConfig()->CfgRecPlayPrm.bReplayFocus) {
			extern Vessel *vfocus;
			if (vfocus && vfocus != RecorderFocus()) RecordedFocus(vfocus);
			// do we need to check if vfocus is valid?
		}
    }
    if(ImGui::Button("Editor")) {
        OpenRecorderEditor();
    }
}

void DlgRecorder::GetRecordName (char *str, int maxlen) const
{
	strncpy(str, m_ScenarioFile, maxlen);
}
