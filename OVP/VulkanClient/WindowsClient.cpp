// Licensed under the MIT License
#define ORBITER_MODULE
#include "CockpitSketchpad.h"
#include "imgui.h"

#include <cstdio>
#include <exception>

namespace orbiter::vulkan {
namespace {

class Client final : public oapi::GraphicsClient {
public:
    explicit Client(HINSTANCE instance) : GraphicsClient(instance) {}
    ~Client() override { CloseVulkan(); }

    HWND clbkCreateRenderWindow() override
    {
        try {
            auto* video = GetVideoData();
            video->fullscreen = false;
            window_ = GraphicsClient::clbkCreateRenderWindow();
            Require(window_ != nullptr, "Open Orbiter Vulkan window");

            const auto style = GetWindowLongPtr(window_, GWL_STYLE);
            const auto extendedStyle = GetWindowLongPtr(window_, GWL_EXSTYLE);
            RECT bounds{0, 0, LONG(video->winw), LONG(video->winh)};
            AdjustWindowRectEx(&bounds, DWORD(style), GetMenu(window_) != nullptr, DWORD(extendedStyle));
            SetWindowPos(window_, nullptr, 0, 0, bounds.right - bounds.left, bounds.bottom - bounds.top,
                SWP_NOMOVE | SWP_NOZORDER | SWP_NOACTIVATE);

            Require(SDL_InitSubSystem(SDL_INIT_VIDEO), "Initialize SDL Vulkan video");
            sdlInitialized_ = true;
            auto props = SDL_CreateProperties();
            Require(props != 0, "Create SDL window properties");
            const bool configured = SDL_SetPointerProperty(props, SDL_PROP_WINDOW_CREATE_WIN32_HWND_POINTER, window_) &&
                SDL_SetBooleanProperty(props, SDL_PROP_WINDOW_CREATE_VULKAN_BOOLEAN, true);
            if (configured) wrapped_ = SDL_CreateWindowWithProperties(props);
            SDL_DestroyProperties(props);
            Require(wrapped_ != nullptr, "Wrap Orbiter window for Vulkan");
            scene_.SetPilotRegistration([this](OBJHANDLE h,VISHANDLE v) {
                if (v) RegisterVisObject(h,v); else UnregisterVisObject(h);
            });
            scene_.Open(wrapped_, [this](OBJHANDLE base) {
                OrbiterScene::BaseGeometry geometry;
                DWORD surfaceCount = 0, buildingCount = 0;
                geometry.tileCount = GetBaseTileList(base, &geometry.tiles);
                GetBaseStructures(base, &geometry.surfaces, &surfaceCount, &geometry.buildings, &buildingCount);
                geometry.surfaceCount = surfaceCount;
                geometry.buildingCount = buildingCount;
                return geometry;
            }, *static_cast<const bool*>(GetConfigParam(CFGPRM_OBJECTSHADOWS)));
            Log("Runway33: native Vulkan swapchain initialized");
            return window_;
        } catch (const std::exception& failure) {
            Log(failure.what());
            clbkDestroyRenderWindow(false);
            return nullptr;
        }
    }

    void clbkDeleteVessel(OBJHANDLE handle) override { scene_.RemoveVessel(handle); }

    void clbkCloseSession(bool fast) override
    {
        scene_.CloseWorld();
        loaded_ = false;
        GraphicsClient::clbkCloseSession(fast);
    }
    void clbkDestroyRenderWindow(bool fast) override
    {
        CloseVulkan();
        GraphicsClient::clbkDestroyRenderWindow(fast);
        window_ = nullptr;
    }
    void clbkRenderScene() override
    {
        scene_.BeginPanelFrame();
        if (!loaded_ && !failed_) {
            try {
                char path[MAX_PATH] = {};
                if (!PlanetTexturePath("Earth", path))
                    throw std::runtime_error("Cannot locate the stock Earth texture directory");
                scene_.OpenWorld(std::filesystem::path(path) / "Archive" / "Surf.tree");
                if (const char* capture = SDL_getenv("ORBITER_VULKAN_CAPTURE_FRAME"); capture && *capture)
                    scene_.CaptureFrame(capture);
                loaded_ = true;
            } catch (const std::exception& failure) {
                failed_ = true;
                Log(failure.what());
                PostMessage(window_, WM_CLOSE, 0, 0);
            }
        }
        if (loaded_ && oapiCameraInternal()) Render2DOverlay();
    }
    bool clbkDisplayFrame() override
    {
        if (failed_ || !wrapped_) return false;
        DWORD width = 0, height = 0;
        clbkGetViewportSize(&width, &height);
        try {
            const bool shown = scene_.Present(unsigned(width), unsigned(height), PilotDisplays(loaded_,
                [this](const VCHUDSPEC** h) { return GetVCHUDSurface(h); },
                [this](int i, const VCMFDSPEC** m) { return GetVCMFDSurface(i,m); }));
            Require(shown, "Present Vulkan frame");
            if (SDL_GetTicks() >= nextTitle_) {
                nextTitle_ = SDL_GetTicks() + 250;
                SetWindowTextA(window_, scene_.FlightTitle().c_str());
            }
            return shown;
        } catch (const std::exception& failure) {
            failed_ = true;
            Log(failure.what());
            PostMessage(window_, WM_CLOSE, 0, 0);
            return false;
        }
    }

    bool clbkFullscreenMode() const override { return false; }
    void clbkGetViewportSize(DWORD* width, DWORD* height) const override
    {
        RECT rect{};
        if (window_) GetClientRect(window_, &rect);
        *width = DWORD(rect.right - rect.left);
        *height = DWORD(rect.bottom - rect.top);
    }
    bool clbkGetRenderParam(DWORD param, DWORD* value) const override
    {
        if (param != RP_COLOURDEPTH) return false;
        *value = 32;
        return true;
    }

    // Orbiter owns the ImGui context. Cockpit instruments render separately
    // through the panel and Sketchpad callbacks.
    void clbkImGuiInit() override
    {
        auto& io = ImGui::GetIO();
        io.ConfigFlags &= ~ImGuiConfigFlags_ViewportsEnable;
        io.Fonts->Build();
    }
    void clbkImGuiNewFrame() override {}
    void clbkImGuiRenderDrawData() override { ImGui::Render(); }
    void clbkImGuiShutdown() override {}
    uint64_t clbkImGuiSurfaceTexture(SURFHANDLE) override { return 0; }

    void clbkRender2DPanel(SURFHANDLE* surfaces, MESHHANDLE mesh, MATRIX3* tx, bool additive) override
    { clbkRender2DPanel(surfaces, mesh, tx, 1.0f, additive); }
    void clbkRender2DPanel(SURFHANDLE* surfaces, MESHHANDLE mesh, MATRIX3* tx, float alpha, bool additive) override
    { scene_.Panel(surfaces, mesh, *tx, alpha, additive, [this](int i) { return GetMFDSurface(i); }); }
    MESHHANDLE clbkGetMesh(VISHANDLE v,UINT i) override { return scene_.DeviceMesh(v,i); }
    int clbkGetMeshGroup(DEVMESHHANDLE m,DWORD i,GROUPREQUESTSPEC* s) override { return scene_.ReadGroup(m,i,s); }
    int clbkEditMeshGroup(DEVMESHHANDLE m,DWORD i,GROUPEDITSPEC* s) override { return scene_.EditGroup(m,i,s); }
    bool clbkSetMeshTexture(DEVMESHHANDLE m,DWORD i,SURFHANDLE t) override { return scene_.SetTexture(m,i,t); }
    int clbkSetMeshMaterial(DEVMESHHANDLE m,DWORD i,const MATERIAL* s) override { return scene_.SetMaterial(m,i,s); }
    oapi::Font* clbkCreateFont(int height, bool prop, const char* face, FontStyle style, int angle) const override
    { return new CockpitFont(height, prop, face, style, angle); }
    void clbkReleaseFont(oapi::Font* font) const override { delete font; }
    oapi::Pen* clbkCreatePen(int style, int width, DWORD color) const override { return new CockpitPen(style,width,color); }
    void clbkReleasePen(oapi::Pen* pen) const override { delete pen; }
    oapi::Brush* clbkCreateBrush(DWORD color) const override { return new CockpitBrush(color); }
    void clbkReleaseBrush(oapi::Brush* brush) const override { delete brush; }
    oapi::Sketchpad* clbkGetSketchpad(SURFHANDLE s) override { return OpenCockpitSketchpad(scene_,s); }
    void clbkReleaseSketchpad(oapi::Sketchpad* pad) override { delete pad; }

    DWORD clbkGetDeviceColour(BYTE r, BYTE g, BYTE b) override { return RGB(r, g, b); }
    SURFHANDLE clbkLoadTexture(const char* name, DWORD) override { return LoadSurface(name); }
    SURFHANDLE clbkLoadSurface(const char* name, DWORD, bool path) override { return LoadSurface(name, path); }
    void clbkReleaseTexture(SURFHANDLE surface) override { scene_.Release(surface); }
    SURFHANDLE clbkCreateSurfaceEx(DWORD w, DWORD h, DWORD) override { return scene_.Create(w, h); }
    SURFHANDLE clbkCreateSurface(DWORD w, DWORD h, SURFHANDLE) override { return scene_.Create(w, h); }
    SURFHANDLE clbkCreateTexture(DWORD w, DWORD h) override { return scene_.Create(w, h); }
    void clbkIncrSurfaceRef(SURFHANDLE surface) override { scene_.Retain(surface); }
    bool clbkReleaseSurface(SURFHANDLE surface) override { return scene_.Release(surface); }
    bool clbkGetSurfaceSize(SURFHANDLE surface, DWORD* width, DWORD* height) override
    {
        unsigned w = 0, h = 0;
        if (!scene_.Size(surface, w, h)) return false;
        *width = w;
        *height = h;
        return true;
    }
    bool clbkFillSurface(SURFHANDLE surface, DWORD col) const override
    {
        unsigned width, height;
        return scene_.Size(surface, width, height) && scene_.Fill(surface, 0, 0, width, height, col);
    }
    bool clbkFillSurface(SURFHANDLE surface, DWORD x, DWORD y, DWORD w, DWORD h, DWORD col) const override
    { return scene_.Fill(surface, x, y, w, h, col); }
    bool clbkBlt(SURFHANDLE dst, DWORD x, DWORD y, SURFHANDLE src, DWORD) const override
    {
        unsigned width, height;
        return scene_.Size(src, width, height) && scene_.Blit(dst, x, y, src, 0, 0, width, height);
    }
    bool clbkBlt(SURFHANDLE dst, DWORD x, DWORD y, SURFHANDLE src, DWORD sx, DWORD sy, DWORD w, DWORD h, DWORD) const override
    { return scene_.Blit(dst, x, y, src, sx, sy, w, h); }

private:
    static void Log(const char* message)
    {
        oapiWriteLog(const_cast<char*>(message));
    }

    SURFHANDLE LoadSurface(const char* name, bool absolute = false)
    {
        if (!name) return nullptr;
        char resolved[MAX_PATH] = {};
        if (!absolute && !TexturePath(name, resolved)) return nullptr;
        try {
            return scene_.Load(absolute ? name : resolved);
        } catch (const std::exception& failure) {
            Log(failure.what());
            return nullptr;
        }
    }
    void CloseVulkan() noexcept
    {
        scene_.Close();
        if (wrapped_) SDL_DestroyWindow(wrapped_);
        if (sdlInitialized_) SDL_QuitSubSystem(SDL_INIT_VIDEO);
        wrapped_ = nullptr;
        sdlInitialized_ = false;
        loaded_ = false;
        failed_ = false;
    }

    mutable OrbiterScene scene_;
    HWND window_ = nullptr;
    SDL_Window* wrapped_ = nullptr;
    bool sdlInitialized_ = false;
    bool loaded_ = false;
    bool failed_ = false;
    Uint64 nextTitle_ = 0;
};

Client* client = nullptr;

} // namespace
} // namespace orbiter::vulkan

DLLCLBK void InitModule(HINSTANCE instance)
{
    using namespace orbiter::vulkan;
    client = new Client(instance);
    if (!oapiRegisterGraphicsClient(client)) {
        delete client;
        client = nullptr;
    }
}

DLLCLBK void ExitModule(HINSTANCE)
{
    using namespace orbiter::vulkan;
    if (client) oapiUnregisterGraphicsClient(client);
    delete client;
    client = nullptr;
}
