// Licensed under the MIT License
#pragma once

#include <filesystem>

#ifdef __linux__
#include <array>
#include <cerrno>
#include <chrono>
#include <string_view>
#include <linux/input.h>
#include <fcntl.h>
#include <sys/ioctl.h>
#include <unistd.h>
#endif

namespace orbiter::production {

// The VelocityOne in PC mode sends the crosshair touchpad click on a separate
// USB mouse interface. Read only that interface, keeping regular mice separate.
class VelocityOneTouchpad {
public:
    enum class Access { Unavailable, Denied, Ready };
    struct State {
        Access access = Access::Unavailable;
        bool pressed = false; // Also reports a complete tap between polls
        bool down = false;
    };

    VelocityOneTouchpad() = default;
    ~VelocityOneTouchpad() { Reset(); }
    VelocityOneTouchpad(const VelocityOneTouchpad&) = delete;
    VelocityOneTouchpad& operator=(const VelocityOneTouchpad&) = delete;

#ifdef __linux__
    void Reset()
    {
        if (fd >= 0)
            close(fd);
        fd = -1;
        access = Access::Unavailable;
        retry = {};
        down = false;
        dropped = false;
        armed = false;
    }

    State Poll(bool grab = false, const std::filesystem::path& devices = "/dev/input/by-id")
    {
        const auto now = std::chrono::steady_clock::now();
        if (fd < 0 && now >= retry) {
            Connect(devices, grab);
            retry = now + std::chrono::seconds(1);
        }
        State result{access};
        if (fd < 0)
            return result;

        std::array<input_event, 32> events{};
        for (;;) {
            const auto size = read(fd, events.data(), sizeof events);
            if (size < 0 && errno == EINTR)
                continue;
            if (size < 0 && errno == EAGAIN)
                break;
            if (size <= 0) {
                Reset();
                return {};
            }
            for (unsigned i = 0; i < static_cast<std::size_t>(size) / sizeof(input_event); ++i) {
                const auto& event = events[i];
                if (event.type == EV_SYN && event.code == SYN_DROPPED) {
                    dropped = true;
                    result.pressed = false;
                } else if (dropped) {
                    if (event.type == EV_SYN && event.code == SYN_REPORT && !Resync()) {
                        Reset();
                        return {};
                    }
                } else if (event.type == EV_KEY && event.code == BTN_LEFT) {
                    if (event.value == 0) {
                        down = false;
                        armed = true;
                    } else if (event.value == 1) {
                        result.pressed |= armed && !down;
                        down = true;
                    }
                }
            }
        }
        result.down = armed && down && !dropped;
        return result;
    }

private:
    bool Resync()
    {
        std::array<unsigned char, KEY_MAX / 8 + 1> keys{};
        if (ioctl(fd, EVIOCGKEY(keys.size()), keys.data()) < 0)
            return false;
        down = keys[BTN_LEFT / 8] & (1u << (BTN_LEFT % 8));
        armed = !down;
        dropped = false;
        return true;
    }

    void Connect(const std::filesystem::path& devices, bool grab)
    {
        access = Access::Unavailable;
        constexpr std::string_view prefix = "usb-Turtle_Beach_VelocityOne_Flightstick_";
        constexpr std::string_view suffix = "-if01-event-mouse";
        std::error_code error;
        std::filesystem::path match;
        for (auto entry = std::filesystem::directory_iterator(devices, error);
             !error && entry != std::filesystem::directory_iterator(); entry.increment(error)) {
            const auto name = entry->path().filename().string();
            if (name.size() >= prefix.size() + suffix.size() && name.compare(0, prefix.size(), prefix) == 0
                && name.compare(name.size() - suffix.size(), suffix.size(), suffix) == 0) {
                if (!match.empty())
                    return;
                match = entry->path();
            }
        }
        if (error || match.empty())
            return;
        fd = open(match.c_str(), O_RDONLY | O_NONBLOCK | O_CLOEXEC);
        if (fd < 0) {
            if (errno == EACCES)
                access = Access::Denied;
            return;
        }
        input_id id{};
        if (ioctl(fd, EVIOCGID, &id) < 0 || id.bustype != BUS_USB || id.vendor != 0x10f5
            || id.product != 0x7055 || (grab && ioctl(fd, EVIOCGRAB, 1) < 0) || !Resync()) {
            Reset();
            return;
        }
        access = Access::Ready;
    }

    int fd = -1;
    Access access = Access::Unavailable;
    std::chrono::steady_clock::time_point retry{};
    bool down = false;
    bool dropped = false;
    bool armed = false;
#else
    // This separate hardware interface is exposed through Linux evdev.
    void Reset() {}
    State Poll(bool) { return {}; }
#endif
};

}
