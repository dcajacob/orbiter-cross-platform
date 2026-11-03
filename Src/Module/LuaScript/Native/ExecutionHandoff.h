// Licensed under the MIT License
#pragma once
#include <chrono>
#include <condition_variable>
#include <cstdint>
#include <mutex>
#include <stdexcept>
#include <thread>

// LuaInline alternates a single interpreter worker with the simulator thread.
// The creator starts with execution permission. Nested calls (ProcessChunk)
// keep the permission until the outermost EndExec releases it.
class ExecutionHandoff {
public:
    void Wait(std::uint32_t timeout)
    {
        const auto caller = std::this_thread::get_id();
        std::unique_lock lock(mutex);
        auto ready = [&] { return hostTurn == (caller == simulator) && (!depth || owner == caller); };
        if (timeout == UINT32_MAX) {
            changed.wait(lock, ready);
        } else if (!changed.wait_for(lock, std::chrono::milliseconds(timeout), ready)) {
            throw std::runtime_error("Timed out waiting for Orbiter interpreter execution");
        }
        owner = caller;
        ++depth;
    }

    void Release()
    {
        std::lock_guard lock(mutex);
        if (!depth || owner != std::this_thread::get_id())
            throw std::logic_error("Interpreter execution released by a thread without permission");
        if (--depth == 0) {
            hostTurn = !hostTurn;
            changed.notify_all();
        }
    }

private:
    const std::thread::id simulator = std::this_thread::get_id();
    std::thread::id owner = simulator;
    std::mutex mutex;
    std::condition_variable changed;
    bool hostTurn = true;
    unsigned depth = 1;
};
