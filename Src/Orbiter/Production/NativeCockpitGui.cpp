// Copyright (c) Martin Schweiger
// Licensed under the MIT License
// Native dialog services surrounding the original Select/InputBox algorithms.
#include "Select.h"
#include "Config.h"
#include "NativeCockpitUi.h"
#include <memory>
#include <fstream>
#include "CockpitGuiExports.h"
#include "NativeGraphics.h"
#include "imgui_internal.h"
#include <unordered_map>
#include <algorithm>
#include <vector>
#include <stdexcept>
using namespace orbiter::production;
namespace {
std::vector<ImGuiDialog*> moduleDialogs;
}

void oapiOpenDialog(ImGuiDialog *dialog) {
    if (std::find(moduleDialogs.begin(), moduleDialogs.end(), dialog) == moduleDialogs.end())
        moduleDialogs.push_back(dialog);
    dialog->Activate();
}

void oapiCloseDialog(ImGuiDialog *dialog) {
    moduleDialogs.erase(std::remove(moduleDialogs.begin(), moduleDialogs.end(), dialog), moduleDialogs.end());
}

ImGuiDialog::~ImGuiDialog() {
    oapiCloseDialog(this);
    auto& context=GetNativeRenderContext();
    if(context.cockpitSelect==this)context.cockpitSelect=nullptr;
    if(context.cockpitInput==this)context.cockpitInput=nullptr;
}
bool ImGuiDialog::HandleHelpButton() {
    if(helpfile.empty())return false;
    if(ImGui::Button("Help"))throw std::runtime_error("Native compiled-help viewer is unavailable");
    return true;
}
void ImGuiDialog::Display() {
    ImGui::SetNextWindowSize(ImVec2(defaultSize.width,defaultSize.height),ImGuiCond_FirstUseEver);
    if(ImGui::Begin(name.c_str(),&active)){HandleHelpButton();OnDraw();}
    ImGui::End();if(!active)OnClose();
}
void ImGuiDialog::Activate() {active=true;ImGui::SetWindowFocus(name.c_str());}
namespace ImGui {
	struct FadingState
	{
		enum State { Closed, Opening, Open } state = Closed;
		float animstate = 0.0f;
	};
	static std::unordered_map<ImGuiID, FadingState> g_popupStates;

	// A popup that will fade-in when open (making it fade-out is too tricky)
	ORBITER_PRODUCTION_API bool BeginAnimatedPopup(const char* name, float duration)
	{
		ImGuiContext& g = *GImGui;
		ImGuiID id = g.CurrentWindow->GetID(name);
		FadingState& S = g_popupStates[id];

		if (ImGui::IsPopupOpen(name) && S.state == FadingState::Closed)	{
			S.state = FadingState::Opening;
			S.animstate = 0.0f;
		}

		if (S.state == FadingState::Opening) {
			S.animstate += ImGui::GetIO().DeltaTime;
			if (S.animstate >= duration)
				S.state = FadingState::Open;
		}

		float x = ImClamp(S.animstate / duration, 0.0f, 1.0f);
		float alpha = x * x * (3.0f - 2.0f * x);

		ImGui::PushStyleVar(ImGuiStyleVar_Alpha, alpha);

		if (!ImGui::BeginPopup(name)) {
			ImGui::PopStyleVar();
			S.state = FadingState::Closed;
			return false;
		}

		return true;
	}

	ORBITER_PRODUCTION_API void EndAnimatedPopup()
	{
		ImGui::PopStyleVar();
		ImGui::EndPopup();
	}

}

namespace {
static void ApplyGlowTheme(const ImVec4& accent)
{
    ImGuiStyle& style = ImGui::GetStyle();
    ImVec4* colors = style.Colors;

    // Base backgrounds
    const ImVec4 bgDark   = ImVec4(0.02f, 0.03f, 0.05f, 1.0f);
    const ImVec4 bgMed    = ImVec4(0.07f, 0.08f, 0.12f, 1.0f);

    // Glow layers
    ImVec4 glowSoft   = ImVec4(accent.x, accent.y, accent.z, 0.20f);
    ImVec4 glowMedium = ImVec4(accent.x, accent.y, accent.z, 0.35f);
    ImVec4 glowStrong = ImVec4(accent.x * 1.2f, accent.y * 1.2f, accent.z * 1.2f, 1.0f);
    ImVec4 title = ImVec4(accent.x * 0.2f, accent.y * 0.2f, accent.z * 0.2f, 1.0f);
    ImVec4 titleActive = ImVec4(accent.x * 0.35f, accent.y * 0.35f, accent.z * 0.35f, 1.0f);

    // Neon text: bright foreground + soft glow shadow
    colors[ImGuiCol_Text]         = ImVec4(1, 1, 1, 1);
    colors[ImGuiCol_TextDisabled] = ImVec4(0.4f, 0.4f, 0.44f, 1);

    // Window backgrounds
    colors[ImGuiCol_WindowBg] = bgDark;
    colors[ImGuiCol_ChildBg]  = bgDark;
    colors[ImGuiCol_PopupBg]  = bgMed;

    // Glow-ish borders
    colors[ImGuiCol_Border]       = glowMedium;
    colors[ImGuiCol_BorderShadow] = ImVec4(0,0,0,0);

    // Frames (inputs, checkboxes, sliders)
    colors[ImGuiCol_FrameBg]        = bgMed;
    colors[ImGuiCol_FrameBgHovered] = glowSoft;
    colors[ImGuiCol_FrameBgActive]  = glowMedium;

    // Buttons
    colors[ImGuiCol_Button]        = glowSoft;
    colors[ImGuiCol_ButtonHovered] = glowMedium;
    colors[ImGuiCol_ButtonActive]  = glowStrong;

    // Headers (collapsing header, tree node)
    colors[ImGuiCol_Header]        = glowSoft;
    colors[ImGuiCol_HeaderHovered] = glowMedium;
    colors[ImGuiCol_HeaderActive]  = glowStrong;

    // Checkmark & sliders use bright neon
    colors[ImGuiCol_CheckMark]       = glowStrong;
    colors[ImGuiCol_SliderGrab]      = glowMedium;
    colors[ImGuiCol_SliderGrabActive]= glowStrong;

    // Scrollbar
    colors[ImGuiCol_ScrollbarBg]          = bgDark;
    colors[ImGuiCol_ScrollbarGrab]        = glowSoft;
    colors[ImGuiCol_ScrollbarGrabHovered] = glowMedium;
    colors[ImGuiCol_ScrollbarGrabActive]  = glowStrong;

    // Separators: bright neon lines
    colors[ImGuiCol_Separator]        = glowMedium;
    colors[ImGuiCol_SeparatorHovered] = glowStrong;
    colors[ImGuiCol_SeparatorActive]  = glowStrong;

    // Title bar
    colors[ImGuiCol_TitleBg]          = title;
    colors[ImGuiCol_TitleBgActive]    = titleActive;
    colors[ImGuiCol_TitleBgCollapsed] = bgDark;

    // Resize grip
    colors[ImGuiCol_ResizeGrip]        = glowSoft;
    colors[ImGuiCol_ResizeGripHovered] = glowMedium;
    colors[ImGuiCol_ResizeGripActive]  = glowStrong;

    // Tabs
    colors[ImGuiCol_Tab]                = glowSoft;
    colors[ImGuiCol_TabHovered]         = glowMedium;
    colors[ImGuiCol_TabActive]          = glowMedium;
    colors[ImGuiCol_TabUnfocused]       = ImVec4(glowSoft.x, glowSoft.y, glowSoft.z, 0.5f);
    colors[ImGuiCol_TabUnfocusedActive] = glowMedium;

    style.FrameRounding = 6;
    style.GrabRounding  = 4;
    style.WindowRounding = 4;

    style.FrameBorderSize = 1.0f;
    style.ChildBorderSize = 1.0f;
    style.WindowBorderSize = 1.0f;
}

static void ImGuiSetStyle()
{
    ImVec4 green = ImVec4(0.0f, 1.0f, 0.0f, 1.0f);
    ApplyGlowTheme(green);

    ImGuiStyle& style = ImGui::GetStyle();
    style.WindowMenuButtonPosition = ImGuiDir_Right;

    style.Colors[ImGuiCol_Separator] = style.Colors[ImGuiCol_Button];
}


std::unique_ptr<Select> selection;
std::unique_ptr<InputBox> inputBox;
std::ofstream uiEvidence;
std::ofstream uiFrames;
ImGuiID replayClockHook=0;
float replayClockStep=0;
std::ofstream replayClockTrace;
}

namespace orbiter::production {
void CreateCockpitGui() {
    if (ImGui::GetCurrentContext()) throw std::logic_error("A cockpit GUI context already exists");
    IMGUI_CHECKVERSION();
    ImGui::CreateContext();
    try {
        auto& context = GetNativeRenderContext();
        auto& io = ImGui::GetIO();
        io.ConfigFlags |= ImGuiConfigFlags_NavEnableKeyboard;
        // The native client owns one render window, matching the reference client.
        io.IniFilename = nullptr;
        ImGuiSetStyle();
        const auto& fonts = context.configuration->CfgFontPrm;
        auto load = [&](const char* file, const ImFontConfig* options = nullptr) {
            auto path = context.programFiles->Resolve(file).string();
            if (!io.Fonts->AddFontFromFileTTF(path.c_str(), fonts.ImGui_FontSize, options))
                throw std::runtime_error("Cannot load original cockpit font: " + path);
        };
        load(fonts.ImGui_DefaultFontFile);
        ImFontConfig icons;
        icons.MergeMode = true;
        icons.PixelSnapH = true;
        // AddFontFromFileTTF allocates its input buffer. The atlas must own it
        // so destroying the GUI releases it instead of cloning and leaking it.
        icons.FontDataOwnedByAtlas = true;
        load("Fonts/fa-solid-900.ttf", &icons);
        load(fonts.ImGui_ConsoleFontFile);
        load(fonts.ImGui_MonospacedFontFile);
        load(fonts.ImGui_ManuscriptFontFile);
        selection = std::make_unique<Select>();
        inputBox = std::make_unique<InputBox>();
        context.cockpitSelect = selection.get();
        context.cockpitInput = inputBox.get();
        if (std::filesystem::is_regular_file(context.evidence/"ui-evidence.enabled")) {
            uiEvidence.open(context.evidence/"ui-state.csv");
            uiFrames.open(context.evidence/"ui-frames.csv");
            uiEvidence << "tick,popup_hex,x,y,width,height,capture_mouse,capture_keyboard\n";
        }
    } catch (...) {
        DestroyCockpitGui();
        throw;
    }
}
void SetCockpitReplayClock(float seconds) {
    if(!ImGui::GetCurrentContext() || seconds<=0 || replayClockHook)
        throw std::logic_error("Invalid cockpit replay clock setup");
    replayClockStep=seconds;
    ImGuiContextHook hook;
    hook.Type=ImGuiContextHookType_NewFramePre;
    hook.Callback=[](ImGuiContext* context,ImGuiContextHook*) {
        context->IO.DeltaTime=replayClockStep;
        if(replayClockTrace.is_open())replayClockTrace<<context->FrameCount<<','<<context->IO.DeltaTime<<'\n';
    };
    replayClockHook=ImGui::AddContextHook(ImGui::GetCurrentContext(),&hook);
    const auto& evidence=GetNativeRenderContext().evidence;
    if(!evidence.empty()) {
        replayClockTrace.exceptions(std::ios::badbit|std::ios::failbit);
        replayClockTrace.open(evidence/"ui-clock-trace.csv");replayClockTrace<<"frame,delta\n";
        std::ofstream record(evidence/"ui-clock.json");record.exceptions(std::ios::badbit|std::ios::failbit);
        record<<"{\"seconds_per_frame\":"<<seconds<<",\"scope\":\"test-only ImGui frame clock\"}\n";
    }
}
void DestroyCockpitGui() {
    moduleDialogs.clear();
    if(replayClockHook) {
        ImGui::RemoveContextHook(ImGui::GetCurrentContext(),replayClockHook);
        replayClockHook=0;
    }
    if(uiEvidence.is_open())uiEvidence.close();
    if(uiFrames.is_open())uiFrames.close();
    if(replayClockTrace.is_open())replayClockTrace.close();
    inputBox.reset();
    selection.reset();
    ImGui::g_popupStates.clear();
    if (ImGui::GetCurrentContext()) ImGui::DestroyContext();
}
void BeginCockpitGuiFrame() {
    ImGui::NewFrame();
    const auto& context = GetNativeRenderContext();
    if (context.configuration->CfgUIPrm.MouseFocusMode != 0 && !ImGui::GetIO().WantCaptureMouse)
        ImGui::SetWindowFocus(static_cast<const char*>(nullptr));
    if (selection->IsActive()) selection->Display();
    if (inputBox->IsActive()) inputBox->Display();
    // A dialog may close or destroy another dialog during its draw callback.
    const auto pending = moduleDialogs;
    for (auto *dialog : pending) {
        if (std::find(moduleDialogs.begin(), moduleDialogs.end(), dialog) != moduleDialogs.end() && dialog->IsActive())
            dialog->Display();
    }
    ImGui::EndFrame();
    if(uiFrames.is_open()){uiFrames<<ImGui::GetFrameCount()<<'\n';uiFrames.flush();}
}
void ObserveCockpitGui(unsigned tick) {
    if(!uiEvidence.is_open())return;
    const auto& io=ImGui::GetIO();
    bool found=false;
    for(auto* window:GImGui->Windows) {
        if(!window->Active || window->Hidden || !(window->Flags & ImGuiWindowFlags_Popup))continue;
        found=true;
        uiEvidence<<tick<<',';
        static const char hex[]="0123456789abcdef";
        for(const unsigned char* p=reinterpret_cast<const unsigned char*>(window->Name);*p;++p)
            uiEvidence<<hex[*p>>4]<<hex[*p&15];
        uiEvidence<<','<<window->Pos.x<<','<<window->Pos.y<<','<<window->Size.x<<','<<window->Size.y
            <<','<<io.WantCaptureMouse<<','<<io.WantCaptureKeyboard<<'\n';
    }
    if(!found)uiEvidence<<tick<<",,0,0,0,0,"<<io.WantCaptureMouse<<','<<io.WantCaptureKeyboard<<'\n';
    uiEvidence.flush();
}
bool CockpitGuiCapturesKeyboard() {
    if (!ImGui::GetCurrentContext()) return false;
    const auto& io = ImGui::GetIO();
    return (selection && selection->IsActive()) || (inputBox && inputBox->IsActive()) ||
        (io.WantCaptureKeyboard && (GetNativeRenderContext().configuration->CfgUIPrm.MouseFocusMode == 0 || io.WantCaptureMouse));
}
bool CockpitGuiCapturesMouse() {
    return ImGui::GetCurrentContext() && ImGui::GetIO().WantCaptureMouse;
}
}

void oapiOpenInputBox(char* title,bool (*callback)(void*,char*,void*),char* buffer,int length,void* data) {
    auto* input=GetNativeRenderContext().cockpitInput;
    if(!input)throw std::logic_error("Native input dialog is not initialized");
    input->Open(title,buffer,length,reinterpret_cast<InputBox::Callbk>(callback),data);
}
void oapiOpenInputBoxEx(const char* title,bool (*enter)(void*,char*,void*),bool (*cancel)(void*,char*,void*),char* buffer,int length,void* data,oapi::UInt32 flags) {
    auto* input=GetNativeRenderContext().cockpitInput;
    if(!input)throw std::logic_error("Native input dialog is not initialized");
    input->OpenEx(title,buffer,length,reinterpret_cast<InputBox::Callbk>(enter),reinterpret_cast<InputBox::Callbk>(cancel),data,flags);
}
