// Controlled preemption of the preserved two-mutex handoff, plus the native
// explicit-turn control. This is a protocol diagnostic, not simulator acceptance.
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include "../../../Src/Module/LuaScript/Native/ExecutionHandoff.h"
#include <array>
#include <atomic>
#include <cstdlib>
#include <cstdio>
#include <thread>

class OriginalHandoff {
    HANDLE execution=CreateMutex(nullptr,TRUE,nullptr);
    HANDLE waiting=CreateMutex(nullptr,FALSE,nullptr);
public:
    OriginalHandoff(){if(!execution || !waiting)std::abort();}
    ~OriginalHandoff(){CloseHandle(waiting);CloseHandle(execution);}
    void Wait(std::uint32_t timeout) {
        // Same operations/order as the preserved Interpreter::WaitExec.
        if(WaitForSingleObject(waiting,timeout)!=WAIT_OBJECT_0)std::abort();
        if(WaitForSingleObject(execution,timeout)!=WAIT_OBJECT_0)std::abort();
        if(!ReleaseMutex(waiting))std::abort();
    }
    void Release(){if(!ReleaseMutex(execution))std::abort();}
};

template<class Handoff>
std::array<unsigned,4> observe(bool original)
{
    Handoff handoff;
    std::atomic<unsigned> frame{0},completed{0};
    std::array<unsigned,4> observed{};
    std::thread worker([&] {
        handoff.Wait(UINT32_MAX);
        for(unsigned i=0;i<observed.size();++i) {
            observed[i]=frame.load();
            ++completed;
            handoff.Release();
            if(i+1<observed.size())handoff.Wait(UINT32_MAX);
        }
    });
    handoff.Release();
    // Model the simulator being descheduled between EndExec and WaitExec.
    // Give the original worker permission to finish all four yields first.
    // An explicit-turn handoff must keep it blocked after its first yield.
    const auto deadline=GetTickCount64()+2000;
    while(completed.load()<(original ? 4u : 1u)) {
        if(GetTickCount64()>deadline)std::abort();
        Sleep(1);
    }
    if(!original)Sleep(30);
    handoff.Wait(UINT32_MAX);
    for(unsigned i=1;i<observed.size();++i) {
        frame=i;
        handoff.Release();
        handoff.Wait(UINT32_MAX);
    }
    worker.join();
    return observed;
}

int main()
{
    const auto original=observe<OriginalHandoff>(true);
    const auto explicitTurn=observe<ExecutionHandoff>(false);
    std::printf("{\"purpose\":\"controlled handoff diagnostic, not simulator acceptance\","
        "\"original_frames\":[%u,%u,%u,%u],\"explicit_turn_frames\":[%u,%u,%u,%u]}\n",
        original[0],original[1],original[2],original[3],
        explicitTurn[0],explicitTurn[1],explicitTurn[2],explicitTurn[3]);
    return original==std::array<unsigned,4>{0,0,0,0} &&
           explicitTurn==std::array<unsigned,4>{0,1,2,3} ? 0 : 1;
}
