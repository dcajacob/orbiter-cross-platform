// Read-only wall-clock/thread observations for the preserved Windows runtime.
// This does not acquire, release or inspect the interpreter's private mutexes.
#pragma once
#include <mutex>

namespace timing_probe {
inline void record(const char* source,const char* event,int frame,double seconds)
{
    static std::mutex mutex;
    std::lock_guard<std::mutex> lock(mutex);
    static std::ofstream file("lua-timing.csv");
    static const auto frequency=[] {
        LARGE_INTEGER value{};
        if(!QueryPerformanceFrequency(&value))std::abort();
        file.imbue(std::locale::classic());
        file<<"source,event,counter,frequency,thread,frame,seconds\n";
        return value.QuadPart;
    }();
    LARGE_INTEGER counter{};
    if(!QueryPerformanceCounter(&counter))std::abort();
    file<<source<<','<<event<<','<<counter.QuadPart<<','<<frequency<<','
        <<GetCurrentThreadId()<<','<<frame<<','<<std::setprecision(17)<<seconds<<'\n';
    file.flush();
    if(!file)std::abort();
}

inline int luaEvent(lua_State* state)
{
    static const auto string=reinterpret_cast<decltype(&lua_tolstring)>(
        GetProcAddress(GetModuleHandleA("lua.dll"),"lua_tolstring"));
    const auto* event=string ? string(state,1,nullptr) : nullptr;
    if(!event)std::abort();
    record("lua",event,-1,oapiGetSimTime());
    return 0;
}

inline void install(lua_State* state)
{
    const auto module=GetModuleHandleA("lua.dll");
    const auto closure=reinterpret_cast<decltype(&lua_pushcclosure)>(GetProcAddress(module,"lua_pushcclosure"));
    const auto field=reinterpret_cast<decltype(&lua_setfield)>(GetProcAddress(module,"lua_setfield"));
    if(!state || !closure || !field)std::abort();
    closure(state,luaEvent,0);
    field(state,LUA_GLOBALSINDEX,"_reference_timing");
}
}
