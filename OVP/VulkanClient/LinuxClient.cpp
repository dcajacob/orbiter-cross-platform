// Licensed under the MIT License
#include "OrbiterScene.h"
#include "OrbiterNativeBuild.h"
#include "Production/ModuleBootstrap.h"
#include "Production/FlightKeys.h"
#include "Production/NativeAbi.h"
#include "Production/NativeParticle.h"
#include "Config.h"

#include <algorithm>
#include <cstdio>
#include <iostream>

namespace orbiter::vulkan {
namespace {

using namespace production;

constexpr struct {
    SDL_Scancode scan;
    unsigned key;
} flightKeys[] = {
    {SDL_SCANCODE_SPACE, OAPI_KEY_SPACE}, {SDL_SCANCODE_P, OAPI_KEY_P},
    {SDL_SCANCODE_LCTRL, OAPI_KEY_LCONTROL}, {SDL_SCANCODE_RCTRL, OAPI_KEY_RCONTROL},
    {SDL_SCANCODE_LSHIFT, OAPI_KEY_LSHIFT}, {SDL_SCANCODE_RSHIFT, OAPI_KEY_RSHIFT},
    {SDL_SCANCODE_LALT, OAPI_KEY_LALT}, {SDL_SCANCODE_RALT, OAPI_KEY_RALT},
    {SDL_SCANCODE_KP_PLUS, OAPI_KEY_ADD}, {SDL_SCANCODE_KP_MINUS, OAPI_KEY_SUBTRACT},
    {SDL_SCANCODE_KP_MULTIPLY, OAPI_KEY_MULTIPLY}, {SDL_SCANCODE_KP_DIVIDE, OAPI_KEY_DIVIDE},
    {SDL_SCANCODE_KP_0, OAPI_KEY_NUMPAD0}, {SDL_SCANCODE_KP_PERIOD, OAPI_KEY_DECIMAL},
    {SDL_SCANCODE_KP_1, OAPI_KEY_NUMPAD1}, {SDL_SCANCODE_KP_2, OAPI_KEY_NUMPAD2},
    {SDL_SCANCODE_KP_3, OAPI_KEY_NUMPAD3}, {SDL_SCANCODE_KP_4, OAPI_KEY_NUMPAD4},
    {SDL_SCANCODE_KP_5, OAPI_KEY_NUMPAD5}, {SDL_SCANCODE_KP_6, OAPI_KEY_NUMPAD6},
    {SDL_SCANCODE_KP_7, OAPI_KEY_NUMPAD7}, {SDL_SCANCODE_KP_8, OAPI_KEY_NUMPAD8},
    {SDL_SCANCODE_KP_9, OAPI_KEY_NUMPAD9},
    {SDL_SCANCODE_COMMA, OAPI_KEY_COMMA}, {SDL_SCANCODE_PERIOD, OAPI_KEY_PERIOD},
    {SDL_SCANCODE_G, OAPI_KEY_G}, {SDL_SCANCODE_F, OAPI_KEY_F}, {SDL_SCANCODE_S, OAPI_KEY_S},
    {SDL_SCANCODE_F3, OAPI_KEY_F3}, {SDL_SCANCODE_F5, OAPI_KEY_F5}, {SDL_SCANCODE_INSERT, OAPI_KEY_INSERT},
    {SDL_SCANCODE_DELETE, OAPI_KEY_DELETE},
    {SDL_SCANCODE_LEFT, OAPI_KEY_LEFT}, {SDL_SCANCODE_RIGHT, OAPI_KEY_RIGHT},
    {SDL_SCANCODE_UP, OAPI_KEY_UP}, {SDL_SCANCODE_DOWN, OAPI_KEY_DOWN},
    {SDL_SCANCODE_PAGEUP, OAPI_KEY_PRIOR}, {SDL_SCANCODE_PAGEDOWN, OAPI_KEY_NEXT}
};

class FontResource final : public oapi::Font {
public:
    FontResource(int height, bool prop, const char* face, FontStyle style, int orientation)
        : Font(height, prop, face, style, orientation) {}
};

class PenResource final : public oapi::Pen {
public:
    PenResource(int style, int width, oapi::UInt32 color) : Pen(style, width, color) {}
};

class BrushResource final : public oapi::Brush {
public:
    explicit BrushResource(oapi::UInt32 color) : Brush(color) {}
};

class Client final : public NativeGraphics {
public:
    ~Client() override { Close(); }

    void Open() override
    {
        Require(SDL_InitSubSystem(SDL_INIT_VIDEO), "Initialize Vulkan window");
        initialized_ = true;
        const auto& config = GetNativeRenderContext().configuration->CfgDevPrm;
        SDL_WindowFlags flags = SDL_WINDOW_VULKAN | SDL_WINDOW_RESIZABLE;
        if (config.bFullscreen) flags |= SDL_WINDOW_FULLSCREEN | SDL_WINDOW_HIGH_PIXEL_DENSITY;
        window_ = SDL_CreateWindow("Orbiter [Vulkan]", config.WinW, config.WinH, flags);
        Require(window_ != nullptr, "Open Vulkan window");
        SDL_GetWindowSizeInPixels(window_, &width_, &height_);
        scene_.Open(window_, [](OBJHANDLE base) {
            OrbiterScene::BaseGeometry geometry;
            oapi::UInt32 surfaceCount = 0, buildingCount = 0;
            geometry.tileCount = RenderBaseTiles(base, &geometry.tiles);
            RenderBaseStructures(base, &geometry.surfaces, &surfaceCount, &geometry.buildings, &buildingCount);
            geometry.surfaceCount = surfaceCount;
            geometry.buildingCount = buildingCount;
            return geometry;
        }, GetNativeRenderContext().configuration->CfgVisualPrm.bShadows);
        capturePending_ = !GetNativeRenderContext().evidence.empty();
    }

    RenderInput Poll() override
    {
        RenderInput input;
        // SDL pointer positions use window coordinates. Orbiter picks in framebuffer pixels.
        const float density = SDL_GetWindowPixelDensity(window_);
        const auto mouse = [&](RenderMouseAction action, float x, float y, double wheel = 0) {
            input.mouse.push_back({action, int(x * density), int(y * density), wheel});
        };
        SDL_Event event;
        while (SDL_PollEvent(&event)) {
            switch (event.type) {
            case SDL_EVENT_QUIT:
            case SDL_EVENT_WINDOW_CLOSE_REQUESTED:
                input.close = true;
                break;
            case SDL_EVENT_KEY_DOWN:
            case SDL_EVENT_KEY_UP: {
                const bool down = event.type == SDL_EVENT_KEY_DOWN;
                if (down && event.key.scancode == SDL_SCANCODE_ESCAPE) input.close = true;
                if (!event.key.repeat) {
                    for (const auto& key : flightKeys) {
                        if (key.scan == event.key.scancode) {
                            input.flight.events.push_back({key.key, down});
                            break;
                        }
                    }
                }
                break;
            }
            case SDL_EVENT_WINDOW_FOCUS_LOST:
                input.mouse.push_back({RenderMouseAction::RightUp, 0, 0, 0});
                break;
            case SDL_EVENT_MOUSE_MOTION:
                mouse(RenderMouseAction::Move, event.motion.x, event.motion.y);
                break;
            case SDL_EVENT_MOUSE_BUTTON_DOWN:
            case SDL_EVENT_MOUSE_BUTTON_UP: {
                if (event.button.button != SDL_BUTTON_LEFT && event.button.button != SDL_BUTTON_RIGHT) break;
                const bool down = event.type == SDL_EVENT_MOUSE_BUTTON_DOWN;
                const bool left = event.button.button == SDL_BUTTON_LEFT;
                const auto action = left ? (down ? RenderMouseAction::LeftDown : RenderMouseAction::LeftUp)
                    : (down ? RenderMouseAction::RightDown : RenderMouseAction::RightUp);
                mouse(action, event.button.x, event.button.y);
                break;
            }
            case SDL_EVENT_MOUSE_WHEEL:
                mouse(RenderMouseAction::Wheel, event.wheel.mouse_x, event.wheel.mouse_y, event.wheel.y);
                break;
            default:
                break;
            }
        }
        if (SDL_GetKeyboardFocus() == window_) {
            const auto* pressed = SDL_GetKeyboardState(nullptr);
            for (const auto& key : flightKeys) input.flight.keys[key.key] = pressed[key.scan] ? char(0x80) : 0;
        }
        SDL_GetWindowSizeInPixels(window_, &input.width, &input.height);
        return input;
    }

    void Resize(int width, int height) override { width_ = width; height_ = height; }
    void PostCreation() override {}
    void Render() override
    {
        if (!loaded_) {
            char path[4096] = {};
            if (!RenderTexturePath("Earth", path, true))
                throw std::runtime_error("Cannot locate the stock Earth texture directory");
            scene_.OpenWorld(std::filesystem::path(path) / "Archive" / "Surf.tree");
            loaded_ = true;
        }
    }

    bool Present() override
    {
        const auto& context = GetNativeRenderContext();
        if (capturePending_ && oapiGetSimTime() >= context.captureTime) {
            scene_.CaptureFrame(context.evidence / "vulkan-frame.bmp");
            capturePending_ = false;
        }
        return scene_.Present(unsigned(width_), unsigned(height_));
    }
    void CloseSession() override
    {
        for (auto& stream : particles_) stream->Detach();
        scene_.CloseWorld();
        loaded_ = false;
    }
    void Close() override
    {
        scene_.Close();
        if (window_) SDL_DestroyWindow(window_);
        window_ = nullptr;
        if (initialized_) SDL_QuitSubSystem(SDL_INIT_VIDEO);
        initialized_ = false;
    }

    SURFHANDLE LoadTextureResource(const char* name, oapi::UInt32) override { return LoadSurface(name); }
    SURFHANDLE clbkLoadSurface(const char* name, oapi::UInt32, bool) override { return LoadSurface(name); }
    bool ReleaseTextureResource(SURFHANDLE handle) override { return scene_.Release(handle); }
    const void* GetConfigParam(oapi::UInt32 type) const override { return RenderConfig(type); }
    const std::vector<LABELLIST>& GetCelestialMarkers() const override { return RenderCelestialMarkers(); }
    void clbkGetViewportSize(oapi::UInt32* width, oapi::UInt32* height) const override
    { *width = oapi::UInt32(width_); *height = oapi::UInt32(height_); }

    SURFHANDLE clbkCreateSurfaceEx(oapi::UInt32 width, oapi::UInt32 height, oapi::UInt32) override
    { return scene_.Create(width, height); }
    SURFHANDLE clbkCreateTexture(oapi::UInt32 width, oapi::UInt32 height) override
    { return scene_.Create(width, height); }
    SURFHANDLE CreateSurfaceResource(int width, int height) override
    { return width > 0 && height > 0 ? scene_.Create(unsigned(width), unsigned(height)) : nullptr; }

    bool clbkGetSurfaceSize(SURFHANDLE handle, oapi::UInt32* width, oapi::UInt32* height) override
    { return scene_.Size(handle, *width, *height); }
    void clbkIncrSurfaceRef(SURFHANDLE handle) override { scene_.Retain(handle); }
    bool clbkReleaseSurface(SURFHANDLE handle) override { return scene_.Release(handle); }

    bool clbkBlt(SURFHANDLE target, oapi::UInt32 x, oapi::UInt32 y, SURFHANDLE source, oapi::UInt32) const override
    {
        unsigned width, height;
        return scene_.Size(source, width, height) && scene_.Blit(target, x, y, source, 0, 0, width, height);
    }

    bool clbkBlt(SURFHANDLE target, oapi::UInt32 x, oapi::UInt32 y, SURFHANDLE source,
        oapi::UInt32 sx, oapi::UInt32 sy, oapi::UInt32 width, oapi::UInt32 height, oapi::UInt32) const override
    { return scene_.Blit(target, x, y, source, sx, sy, width, height); }

    bool clbkFillSurface(SURFHANDLE handle, oapi::UInt32 color) const override
    {
        unsigned width, height;
        return scene_.Size(handle, width, height) && scene_.Fill(handle, 0, 0, width, height, color);
    }
    bool clbkFillSurface(SURFHANDLE handle, oapi::UInt32 x, oapi::UInt32 y, oapi::UInt32 width,
        oapi::UInt32 height, oapi::UInt32 color) const override
    { return scene_.Fill(handle, x, y, width, height, color); }

    oapi::UInt32 clbkGetDeviceColour(std::uint8_t r, std::uint8_t g, std::uint8_t b) override
    { return std::uint32_t(r) | (std::uint32_t(g) << 8) | (std::uint32_t(b) << 16); }

    int DesktopHeight() const override
    {
        const auto* mode = SDL_GetCurrentDisplayMode(SDL_GetDisplayForWindow(window_));
        return mode ? mode->h : height_;
    }
    oapi::SdkPoint CursorPosition() const override
    {
        float x = 0, y = 0;
        SDL_GetMouseState(&x, &y);
        return {int(x), int(y)};
    }
    void SetCursorPosition(oapi::SdkPoint point) override
    { SDL_WarpMouseInWindow(window_, float(point.x), float(point.y)); }
    void SetCameraRotation(bool active) override
    { SDL_SetWindowMouseGrab(window_, active); }

    oapi::Font* CreateFontResource(int height, bool prop, const char* face, FontStyle style, int orientation) override
    { return new FontResource(height, prop, face, style, orientation); }
    void ReleaseFontResource(oapi::Font* font) override { delete font; }
    oapi::Pen* CreatePenResource(int style, int width, oapi::UInt32 color) override
    { return new PenResource(style, width, color); }
    void ReleasePenResource(oapi::Pen* pen) override { delete pen; }
    oapi::Brush* CreateBrushResource(oapi::UInt32 color) override { return new BrushResource(color); }
    void ReleaseBrushResource(oapi::Brush* brush) override { delete brush; }

    // These callbacks belong to the full interactive UI, instruments, and
    // vessel effects. This client provides only the external scenario view.
    void InitGui() override {}
    void NewGuiFrame() override {}
    void RenderGui() override {}
    void ShutdownGui() override {}
    void ReplayGuiInput(const std::string&, int, int, const std::string&) override {}
    void Status(const std::string&) override
    {
        if (SDL_GetTicks() < nextTitle_) return;
        nextTitle_ = SDL_GetTicks() + 250;
        SDL_SetWindowTitle(window_, scene_.FlightTitle().c_str());
    }
    void NewVessel(OBJHANDLE) override {}
    void DeleteVessel(OBJHANDLE handle) override { scene_.RemoveVessel(handle); }
    void StoreMesh(MESHHANDLE, const char*) override {}
    void VisualEvent(OBJHANDLE, VISHANDLE, oapi::UInt32, std::uintptr_t) override {}
    std::vector<NativeJoystickDevice> Joysticks() const override { return {}; }
    bool clbkSetSurfaceColourKey(SURFHANDLE, oapi::UInt32) override { return false; }
    std::unique_ptr<NativeGraphicsContext> SaveGraphicsContext() override { return {}; }
    std::unique_ptr<NativeGraphicsContext> ActivateMainGraphicsContext() override { return {}; }
    std::unique_ptr<NativeInstrumentTarget> CreateInstrumentTarget(int, int) override { return {}; }
    bool UploadSurfacePixels(SURFHANDLE, int, int, const std::vector<std::uint8_t>&) override { return false; }
    bool clbkGetRenderParam(oapi::UInt32, oapi::UInt32*) const override { return false; }
    bool clbkScaleBlt(SURFHANDLE, oapi::UInt32, oapi::UInt32, oapi::UInt32, oapi::UInt32, SURFHANDLE,
        oapi::UInt32, oapi::UInt32, oapi::UInt32, oapi::UInt32, oapi::UInt32) const override { return false; }
    void clbkRender2DPanel(SURFHANDLE*, MESHHANDLE, MATRIX3*, bool) override {}
    void clbkRender2DPanel(SURFHANDLE*, MESHHANDLE, MATRIX3*, float, bool) override {}
    std::uint64_t GuiTextureId(SURFHANDLE) override { return 0; }
    oapi::Sketchpad* AcquireSketchpad(SURFHANDLE) override { return nullptr; }
    oapi::Sketchpad* AcquireRasterSketchpad(SURFHANDLE) override { return nullptr; }
    void ReleaseSketchpadResource(oapi::Sketchpad*) override {}
    int MeshGroup(DEVMESHHANDLE, oapi::UInt32, GROUPREQUESTSPEC*) override { return -2; }
    MESHHANDLE clbkGetMesh(VISHANDLE, oapi::UInt) override { return nullptr; }
    int EditMeshGroup(DEVMESHHANDLE, int, GROUPEDITSPEC*) override { return -2; }
    bool SetMeshTexture(DEVMESHHANDLE, int, SURFHANDLE) override { return false; }
    bool clbkSaveSurfaceToImage(SURFHANDLE, const char*, oapi::ImageFileFormat, float) override { return false; }
    bool SetMeshProperty(DEVMESHHANDLE, int, int) override { return false; }
    int SetMeshMaterial(DEVMESHHANDLE, int, const MATERIAL*) override { return 2; }
    oapi::ParticleStream* Exhaust(PARTICLESTREAMSPEC* spec, OBJHANDLE object, const double* level,
        const VECTOR3* pos, const VECTOR3* dir) override
    {
        auto* stream = CreateParticle(spec);
        stream->Attach(object, pos, dir, level);
        return stream;
    }
    oapi::ParticleStream* Exhaust(PARTICLESTREAMSPEC* spec, OBJHANDLE object, const double* level,
        const VECTOR3& pos, const VECTOR3& dir) override
    {
        auto* stream = CreateParticle(spec);
        stream->Attach(object, pos, dir, level);
        return stream;
    }
    oapi::ParticleStream* Reentry(PARTICLESTREAMSPEC* spec, OBJHANDLE) override
    { return CreateParticle(spec); }

private:
    oapi::ParticleStream* CreateParticle(PARTICLESTREAMSPEC* spec)
    {
        particles_.push_back(std::make_unique<oapi::ParticleStream>(this, spec));
        return particles_.back().get();
    }
    std::vector<std::unique_ptr<oapi::ParticleStream>> particles_;
    SURFHANDLE LoadSurface(const char* name)
    {
        char path[4096] = {};
        if (!name || !RenderTexturePath(name, path, false)) return nullptr;
        try {
            return scene_.Load(path);
        } catch (const std::exception& error) {
            std::clog << "Runway33 texture: " << error.what() << '\n';
            return nullptr;
        }
    }
    mutable OrbiterScene scene_;
    SDL_Window* window_ = nullptr;
    int width_ = 0;
    int height_ = 0;
    bool initialized_ = false;
    bool loaded_ = false;
    bool capturePending_ = false;
    Uint64 nextTitle_ = 0;
};

int ORBITER_NATIVE_CALL Initialize(const OrbiterNativeHost*, void** instance, char* error, uint32_t capacity) noexcept
{
    try {
        *instance = static_cast<NativeGraphics*>(new Client);
        return 0;
    } catch (const std::exception& failure) {
        if (capacity) std::snprintf(error, capacity, "%s", failure.what());
        return 1;
    }
}

void ORBITER_NATIVE_CALL Shutdown(void* instance) noexcept
{
    delete static_cast<NativeGraphics*>(instance);
}

const OrbiterNativeModuleDescriptor descriptor{
    sizeof(descriptor), ORBITER_NATIVE_BOOTSTRAP_VERSION, sizeof(void*),
    ORBITER_NATIVE_GRAPHICS, "Runway 33 Vulkan client", ORBITER_NATIVE_SDK_BUILD,
    ORBITER_NATIVE_CPP_ABI, Initialize, Shutdown
};

} // namespace
} // namespace orbiter::vulkan

extern "C" ORBITER_NATIVE_EXPORT const OrbiterNativeModuleDescriptor*
ORBITER_NATIVE_CALL OrbiterNativeQuery(uint32_t version) noexcept
{
    return version == ORBITER_NATIVE_BOOTSTRAP_VERSION ? &orbiter::vulkan::descriptor : nullptr;
}
