// Copyright (c) Martin Schweiger
// Licensed under the MIT License
// Native dialog services surrounding the original Select/InputBox algorithms.
#define IMGUI_DEFINE_MATH_OPERATORS
#include "Select.h"
#include "DlgFocus.h"
#include "IconsFontAwesome6.h"
#include "NativeInterpreterSdk.h"
#include "NativeHelp.h"
#include "Config.h"
#include "Pane.h"
#include "Panel2D.h"
#include "Camera.h"
#include "Keymap.h"
#include "Vessel.h"
#include "TimeData.h"
#include "Mfd.h"
#include "NativeCockpitUi.h"
#include <memory>
#include <chrono>
#include <fstream>
#include "CockpitGuiExports.h"
#include "NativeGraphics.h"
#include "imgui_internal.h"
#include <unordered_map>
#include <algorithm>
#include <vector>
#include <stdexcept>
using namespace orbiter::production;
#define ORBITER_NOTIFICATION_EXPORT ORBITER_PRODUCTION_API
#include "GuiNotifications.inc"
#undef ORBITER_NOTIFICATION_EXPORT
namespace {
std::vector<ImGuiDialog*> moduleDialogs;
ImFont *uiFonts[4]{};
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
    HELPCONTEXT help{};
    help.helpfile=const_cast<char*>(helpfile.c_str());
    help.topic=helptopic.empty() ? nullptr : const_cast<char*>(helptopic.c_str());
    if(ImGui::MenuButton(ICON_FA_CIRCLE_QUESTION,"Help"))oapiOpenHelp(&help);
    return true;
}
void ImGuiDialog::Display() {
    ImGui::SetNextWindowSize(ImVec2(defaultSize.width,defaultSize.height),ImGuiCond_FirstUseEver);
    if(ImGui::Begin(name.c_str(),&active)){HandleHelpButton();OnDraw();}
    ImGui::End();if(!active)OnClose();
}
void ImGuiDialog::Activate() {active=true;ImGui::SetWindowFocus(name.c_str());}
namespace ImGui {
#define ORBITER_WIDGET_EXPORT ORBITER_PRODUCTION_API
#include "GuiOptionControls.inc"
#undef ORBITER_WIDGET_EXPORT
    ORBITER_PRODUCTION_API ImTextureID GetImTextureID(SURFHANDLE surf) {
        auto* graphics=GetNativeRenderContext().graphics;
        return graphics && surf ? graphics->GuiTextureId(surf) : 0;
    }
#define ORBITER_MENU_EXPORT ORBITER_PRODUCTION_API
#include "GuiMenuButton.inc"
#undef ORBITER_MENU_EXPORT
    ORBITER_PRODUCTION_API bool ImageButton(const char* id,SURFHANDLE surf,const ImVec2& size,const ImVec2& uv0,const ImVec2& uv1,const ImVec4& bg,const ImVec4& tint) {
        return ImageButton(id,GetImTextureID(surf),size,uv0,uv1,bg,tint);
    }
    ORBITER_PRODUCTION_API void PushFont(ImGuiFont font,float scale) {
        const auto index=static_cast<unsigned>(font);
        ImGui::PushFont(uiFonts[index<4 ? index : 0],ImGui::GetStyle().FontSizeBase*scale);
    }
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

#define ORBITER_WIDGET_EXPORT ORBITER_PRODUCTION_API
#include "GuiAnimatedControls.inc"
#undef ORBITER_WIDGET_EXPORT
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
std::unique_ptr<DlgFocus> focusDialog;
std::unique_ptr<InputBox> inputBox;
std::ofstream uiEvidence;
std::ofstream uiFrames;
std::ofstream menuWindows;
std::ofstream optionsState;
std::ofstream panelLayout;
std::ofstream cameraLayout;
ImGuiID replayClockHook=0;
float replayClockStep=0;
std::ofstream replayClockTrace;
}

namespace orbiter::production {
void HandleCockpitSystemKeys(const Keymap& keymap,char* kstate,bool& g_bForceUpdate) {
    const auto& context=GetNativeRenderContext();
    auto* g_camera=context.camera;
    auto* g_pane=context.cockpitPane;
    auto& td=*context.time;
    auto IncFOV=[&](double dfov) {
#include "CockpitFovInput.inc"
    };
    using std::min;
    using std::max;
#include "CockpitSystemInput.inc"
}
void OpenCockpitFocusDialog() {
    if (!focusDialog) focusDialog=std::make_unique<DlgFocus>();
    oapiOpenDialog(focusDialog.get());
}
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
        if(std::filesystem::is_regular_file(context.evidence/"panel-picking.enabled")) {
            panelLayout.open(context.evidence/"panel-layout.csv");
            panelLayout.precision(17);
            panelLayout<<"tick,mode,panel_id,scale,x,y\n";
        }
        if(std::filesystem::is_regular_file(context.evidence/"vc-picking.enabled")) {
            cameraLayout.open(context.evidence/"cockpit-camera.csv");
            cameraLayout.precision(17);
            cameraLayout<<"tick,mode,internal,distance,phi,theta,aperture,x,y,z,m11,m12,m13,m21,m22,m23,m31,m32,m33,mouse_rotation\n";
        }
        const auto& fonts = context.configuration->CfgFontPrm;
        auto load = [&](const char* file, const ImFontConfig* options = nullptr) {
            auto path = context.programFiles->Resolve(file).string();
            auto *font=io.Fonts->AddFontFromFileTTF(path.c_str(), fonts.ImGui_FontSize, options);
            if (!font)
                throw std::runtime_error("Cannot load original cockpit font: " + path);
            return font;
        };
        uiFonts[static_cast<unsigned>(ImGuiFont::DEFAULT)]=load(fonts.ImGui_DefaultFontFile);
        ImFontConfig icons;
        icons.MergeMode = true;
        icons.PixelSnapH = true;
        // AddFontFromFileTTF allocates its input buffer. The atlas must own it
        // so destroying the GUI releases it instead of cloning and leaking it.
        icons.FontDataOwnedByAtlas = true;
        load("Fonts/fa-solid-900.ttf", &icons);
        uiFonts[static_cast<unsigned>(ImGuiFont::CONSOLE)]=load(fonts.ImGui_ConsoleFontFile);
        uiFonts[static_cast<unsigned>(ImGuiFont::MONO)]=load(fonts.ImGui_MonospacedFontFile);
        uiFonts[static_cast<unsigned>(ImGuiFont::MANUSCRIPT)]=load(fonts.ImGui_ManuscriptFontFile);
        if(std::filesystem::is_regular_file(context.evidence/"menu-evidence.enabled")) {
            menuWindows.open(context.evidence/"menu-windows.csv");
            menuWindows<<"frame,name,x,y,width,height\n";
            optionsState.open(context.evidence/"options-state.csv");
            optionsState<<"frame,refresh,size,panel_scale,limited_fuel,mouse_focus,joystick,deadzone,saturation,ignore_throttle,throttle_axis,rudder_axis,mfd_width,mfd_height\n";
        }
        CreateCockpitInfoBars();
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
    focusDialog.reset();
    DestroyCockpitInfoBars();
    moduleDialogs.clear();
    notifications.clear();
    if(replayClockHook) {
        ImGui::RemoveContextHook(ImGui::GetCurrentContext(),replayClockHook);
        replayClockHook=0;
    }
    if(menuWindows.is_open())menuWindows.close();
    if(optionsState.is_open())optionsState.close();
    if(panelLayout.is_open())panelLayout.close();
    if(cameraLayout.is_open())cameraLayout.close();
    if(uiEvidence.is_open())uiEvidence.close();
    if(uiFrames.is_open())uiFrames.close();
    if(replayClockTrace.is_open())replayClockTrace.close();
    inputBox.reset();
    selection.reset();
    ImGui::g_stackHeaders.clear();
    ImGui::g_headerStates.clear();
    ImGui::g_popupStates.clear();
    if (ImGui::GetCurrentContext()) ImGui::DestroyContext();
}
void BeginCockpitGuiFrame() {
    for(const auto& failure:PollNativeHelp())oapiAddNotification(OAPINOTIF_ERROR,"Orbiter Help",failure.c_str());
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
    RenderNotifications();
    ImGui::EndFrame();
    if(menuWindows.is_open()) {
        for(auto* window:GImGui->Windows) {
            if(!window->Active || window->Hidden || window->Flags & ImGuiWindowFlags_ChildWindow)continue;
            menuWindows<<ImGui::GetFrameCount()<<','<<window->Name<<','<<window->Pos.x<<','<<window->Pos.y
                <<','<<window->Size.x<<','<<window->Size.y<<'\n';
        }
        menuWindows.flush();
    }
    if(optionsState.is_open()) {
        const auto& cfg=*context.configuration;
        oapi::UInt32 width=0,height=0;
        auto* instrument=context.cockpitPane ? context.cockpitPane->MFD(0) : nullptr;
        if(instrument && instrument->Texture())context.graphics->clbkGetSurfaceSize(instrument->Texture(),&width,&height);
        optionsState<<ImGui::GetFrameCount()<<','<<cfg.CfgLogicPrm.InstrUpdDT<<','<<cfg.CfgLogicPrm.MFDSize
            <<','<<cfg.CfgLogicPrm.PanelScale<<','<<cfg.CfgLogicPrm.bLimitedFuel<<','<<cfg.CfgUIPrm.MouseFocusMode
            <<','<<cfg.CfgJoystickPrm.Joy_idx<<','<<cfg.CfgJoystickPrm.Deadzone<<','<<cfg.CfgJoystickPrm.ThrottleSaturation
            <<','<<cfg.CfgJoystickPrm.bThrottleIgnore<<','<<context.joystickThrottleAxis<<','<<context.joystickTwistAxis
            <<','<<width<<','<<height<<'\n';
        optionsState.flush();
    }
    if(uiFrames.is_open()){uiFrames<<ImGui::GetFrameCount()<<'\n';uiFrames.flush();}
}
void ObserveCockpitGui(unsigned tick) {
    if(cameraLayout.is_open()) {
        const auto& context=GetNativeRenderContext();
        const auto& camera=*context.camera;
        const auto& vessel=*context.focus;
        const Vector position=tmul(vessel.GRot(),camera.GPos()-vessel.GPos());
        const Matrix rotation=transp(vessel.GRot())*camera.GRot();
        cameraLayout<<tick<<','<<context.cockpitPane->GetPanelMode()<<','<<camera.IsInternal()<<','<<camera.Distance()<<','<<camera.Phi()<<','<<camera.Theta()<<','<<camera.Aperture();
        for(double value:{position.x,position.y,position.z})cameraLayout<<','<<value;
        for(double value:rotation.data)cameraLayout<<','<<value;
        cameraLayout<<','<<context.cameraRotating;
        cameraLayout<<'\n';cameraLayout.flush();
    }
    if(panelLayout.is_open()) {
        auto* pane=GetNativeRenderContext().cockpitPane;
        auto* panel=pane ? pane->GetPanel2D() : nullptr;
        if(panel) {
            double x=0,y=0;panel->GetOrigin(x,y);
            panelLayout<<tick<<','<<pane->GetPanelMode()<<','<<panel->GetId()<<','<<panel->GetActiveScale()<<','<<x<<','<<y<<'\n';
            panelLayout.flush();
        }
    }
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
