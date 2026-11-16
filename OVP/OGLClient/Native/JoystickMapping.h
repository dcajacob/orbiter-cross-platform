// Licensed under the MIT License
#pragma once

#include <GLFW/glfw3.h>
#include "Production/FlightKeys.h"
#include "Production/NativeJoystick.h"
#include "Keymap.h"
#include <array>
#include <filesystem>
#include <fstream>
#include <optional>
#include <string>

namespace orbiter::production {

inline constexpr std::array<unsigned, 12> JoystickFunctionKeys{
    OAPI_KEY_F1, OAPI_KEY_F2, OAPI_KEY_F3, OAPI_KEY_F4, OAPI_KEY_F5, OAPI_KEY_F6,
    OAPI_KEY_F7, OAPI_KEY_F8, OAPI_KEY_F9, OAPI_KEY_F10, OAPI_KEY_F11, OAPI_KEY_F12
};

inline constexpr unsigned JoystickShortcutModifiers = KMOD_SHIFT | KMOD_CTRL | KMOD_ALT;

// A pair of modifier bits denotes either side, just as in Orbiter's keymap.
inline std::array<unsigned, 3> JoystickModifierKeys(unsigned shortcut)
{
    const auto side = [shortcut](unsigned mask, unsigned right, unsigned leftKey, unsigned rightKey) {
        const unsigned value = shortcut & mask;
        return value == 0 ? 0 : value == right ? rightKey : leftKey;
    };
    return {side(KMOD_SHIFT, KMOD_RSHIFT, OAPI_KEY_LSHIFT, OAPI_KEY_RSHIFT),
            side(KMOD_CTRL, KMOD_RCTRL, OAPI_KEY_LCONTROL, OAPI_KEY_RCONTROL),
            side(KMOD_ALT, KMOD_RALT, OAPI_KEY_LALT, OAPI_KEY_RALT)};
}

inline bool IsJoystickShortcut(unsigned value)
{
    const auto base = value & 255;
    return value == (value & (255u | JoystickShortcutModifiers)) && base
        && base != OAPI_KEY_LSHIFT && base != OAPI_KEY_RSHIFT
        && base != OAPI_KEY_LCONTROL && base != OAPI_KEY_RCONTROL
        && base != OAPI_KEY_LALT && base != OAPI_KEY_RALT;
}

struct JoystickMapping {
    enum CameraControl : unsigned { LookWithH1 = 1, LookWithH2 = 2, LookWithBoth = 3 };
    static constexpr int VelocityOneH2Click = 18; // GLFW index for the physical B19 button

    std::string guid;
    int slot = -1;
    std::array<int, 4> axes{0, 1, 2, -1}; // roll, pitch, yaw, throttle
    unsigned reversed = 0;
    int alternate = -1;
    std::array<unsigned, 256> buttonKeys{}; // Orbiter key code and modifiers, or 0
    unsigned touchpadKey = 0;
    std::optional<unsigned> cameraControls;

    unsigned CameraControls() const
    {
        return IsVelocityOnePcMode(guid) ? cameraControls.value_or(LookWithBoth) : 0;
    }

    bool UsesH2Recenter(int button) const
    {
        return button == VelocityOneH2Click && (CameraControls() & LookWithH2)
            && !buttonKeys[button] && alternate != button;
    }

    unsigned H1LookDirections(unsigned hat, int firstHatButton) const
    {
        constexpr std::array<unsigned, 4> directions{GLFW_HAT_UP, GLFW_HAT_RIGHT, GLFW_HAT_DOWN, GLFW_HAT_LEFT};
        if (!(CameraControls() & LookWithH1) || firstHatButton < 0 ||
            firstHatButton + int(directions.size()) > int(buttonKeys.size()))
            return 0;
        for (unsigned i = 0; i < directions.size(); ++i)
            if (buttonKeys[firstHatButton + i] || alternate == firstHatButton + int(i))
                hat &= ~directions[i];
        return hat;
    }

    bool IsReversed(unsigned control) const { return reversed & (1u << control); }

    static std::filesystem::path Path(const std::filesystem::path& config)
    {
        auto path = config;
        path += ".joystick";
        return path;
    }

    static std::optional<JoystickMapping> Read(const std::filesystem::path& config)
    {
        std::ifstream input(Path(config));
        JoystickMapping mapping;
        std::string header, extra;
        if (!(input >> header >> mapping.guid >> mapping.slot)
            || (header != "orbiter-joystick-v1" && header != "orbiter-joystick-v2"
                && header != "orbiter-joystick-v3" && header != "orbiter-joystick-v4"
                && header != "orbiter-joystick-v5")
            || mapping.guid.size() != 32 || mapping.guid.find_first_not_of("0123456789abcdef") != std::string::npos
            || mapping.slot < GLFW_JOYSTICK_1 || mapping.slot > GLFW_JOYSTICK_LAST)
            return {};
        for (auto& axis : mapping.axes)
            if (!(input >> axis) || axis < -1 || axis > 255)
                return {};
        if (!(input >> mapping.reversed >> mapping.alternate) || mapping.reversed > 15
            || mapping.alternate < -1 || mapping.alternate > 255)
            return {};
        if (header != "orbiter-joystick-v1") {
            int count = 0;
            if (!(input >> count) || count < 0 || count > int(mapping.buttonKeys.size()))
                return {};
            for (int i = 0; i < count; ++i) {
                int button;
                unsigned key;
                if (!(input >> button >> key) || button < 0 || button >= int(mapping.buttonKeys.size())
                    || mapping.buttonKeys[button])
                    return {};
                if (header == "orbiter-joystick-v2") {
                    if (key == 0 || key > JoystickFunctionKeys.size())
                        return {};
                    key = JoystickFunctionKeys[key - 1];
                }
                if (!IsJoystickShortcut(key))
                    return {};
                mapping.buttonKeys[button] = key;
            }
        }
        if (header == "orbiter-joystick-v4" || header == "orbiter-joystick-v5") {
            if (!(input >> mapping.touchpadKey) ||
                (mapping.touchpadKey ? !IsJoystickShortcut(mapping.touchpadKey) : header == "orbiter-joystick-v4"))
                return {};
        }
        if (header == "orbiter-joystick-v5") {
            unsigned controls;
            if (!(input >> controls) || controls > LookWithBoth)
                return {};
            mapping.cameraControls = controls;
        }
        if (input >> extra)
            return {};
        return mapping;
    }

    void Write(std::ostream& stream) const
    {
        int count = 0;
        for (auto key : buttonKeys)
            count += key != 0;
        const char* version = cameraControls ? "orbiter-joystick-v5" : touchpadKey ? "orbiter-joystick-v4"
            : count ? "orbiter-joystick-v3" : "orbiter-joystick-v1";
        stream << version << '\n'
               << guid << ' ' << slot << '\n';
        for (const auto axis : axes)
            stream << axis << ' ';
        stream << reversed << ' ' << alternate << '\n';
        if (count || touchpadKey || cameraControls) {
            stream << count << '\n';
            for (unsigned i = 0; i < buttonKeys.size(); ++i)
                if (buttonKeys[i])
                    stream << i << ' ' << buttonKeys[i] << '\n';
        }
        if (touchpadKey || cameraControls)
            stream << touchpadKey << '\n';
        if (cameraControls)
            stream << *cameraControls << '\n';
    }

    int ConnectedSlot() const
    {
        int match = -1;
        for (int id = GLFW_JOYSTICK_1; id <= GLFW_JOYSTICK_LAST; ++id) {
            const auto* deviceGuid = glfwGetJoystickGUID(id);
            if (!deviceGuid || guid != deviceGuid)
                continue;
            if (id == slot)
                return id;
            match = match == -1 ? id : GLFW_JOYSTICK_LAST + 1;
        }
        return match <= GLFW_JOYSTICK_LAST ? match : -1;
    }

    std::array<float, 4> Samples(const float* values, int count) const
    {
        std::array<float, 4> samples{0, 0, 0, 1}; // throttle idle is +1 after inversion
        for (unsigned i = 0; i < axes.size(); ++i)
            if (values && axes[i] >= 0 && axes[i] < count)
                samples[i] = IsReversed(i) ? -values[axes[i]] : values[axes[i]];
        return samples;
    }
};

}
