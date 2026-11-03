// Licensed under the MIT License
#include "Interpreter.h"
#include <atomic>
#include <stdexcept>
#include <thread>
#include <type_traits>

static_assert(std::is_same_v<decltype(&Interpreter::WaitExec), void (Interpreter::*)(oapi::UInt32)>);

int main()
{
    ExecutionHandoff handoff;
    std::atomic<bool> checkedInitialOwnership{};
    int frame = 0;
    std::thread worker([&] {
        try {
            handoff.Wait(0);
            std::terminate();
        } catch (const std::runtime_error &) {
            checkedInitialOwnership = true;
        }
        for (int i = 1; i <= 10000; ++i) {
            handoff.Wait(UINT32_MAX);
            if (frame != i - 1) std::terminate();
            frame = i;
            handoff.Release();
        }
    });
    while (!checkedInitialOwnership) std::this_thread::yield();
    // A synchronous chunk nested in its caller must retain the outer turn.
    handoff.Wait(0);
    handoff.Release();
    for (int i = 1; i <= 10000; ++i) {
        handoff.Release();
        handoff.Wait(UINT32_MAX);
        if (frame != i) std::terminate();
    }
    worker.join();
}
