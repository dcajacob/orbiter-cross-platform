// Licensed under the MIT License
#include "NativeScript.h"
#include "NativeGraphics.h"
#include <stdexcept>

using namespace orbiter::production;

NativeScriptApi& NativeScriptHost::Load()
{
    if (!library) {
        auto next = std::make_unique<NativeModule>(modules.Resolve("Plugin/LuaInline.so"), ORBITER_NATIVE_PLUGIN, this);
        auto *entry = static_cast<NativeScriptApi*>(next->Instance());
        if (entry->size != sizeof(*entry) || !entry->create || !entry->destroy || !entry->run ||
            !entry->execute || !entry->queue || !entry->state || !entry->postStep || !entry->deleteVessel || !entry->end)
            throw std::runtime_error("Incomplete native LuaInline interface");
        api = entry;
        library = std::move(next);
    }
    return *api;
}

void NativeScriptHost::LoadTerminalMfd()
{
    if (terminalLibrary) return;
    auto next = std::make_unique<NativeModule>(modules.Resolve("Plugin/LuaMFD.so"), ORBITER_NATIVE_PLUGIN, this);
    auto *entry = static_cast<NativeLuaMfdApi*>(next->Instance());
    if (entry->size != sizeof(*entry) || !entry->postStep || !entry->deleteVessel || !entry->end)
        throw std::runtime_error("Incomplete native LuaMFD interface");
    terminalApi = entry;
    terminalLibrary = std::move(next);
}

void NativeScriptHost::EndTerminalMfd()
{
    if (terminalApi) terminalApi->end();
    terminalApi = nullptr;
    terminalLibrary.reset();
}

void NativeScriptHost::PostStep(double simt, double simdt, double mjd)
{
    if (api) api->postStep(simt, simdt, mjd);
    if (terminalApi) terminalApi->postStep(simt, simdt, mjd);
}

void NativeScriptHost::DeleteVessel(OBJHANDLE vessel)
{
    if (api) api->deleteVessel(vessel);
    if (terminalApi) terminalApi->deleteVessel(vessel);
}

void NativeScriptHost::End()
{
    EndTerminalMfd();
    if (api) api->end();
    api = nullptr;
    library.reset();
}

namespace {
NativeScriptApi& interpreter()
{
    auto *scripts = GetNativeRenderContext().scripts;
    if (!scripts) throw std::logic_error("Native script host is not bound");
    return scripts->Load();
}
}

INTERPRETERHANDLE oapiCreateInterpreter() { return interpreter().create(); }
int oapiDelInterpreter(INTERPRETERHANDLE handle) { return interpreter().destroy(handle); }
bool oapiExecScriptCmd(INTERPRETERHANDLE handle, const char *cmd) { return interpreter().execute(handle, cmd); }
bool oapiAsyncScriptCmd(INTERPRETERHANDLE handle, const char *cmd) { return interpreter().queue(handle, cmd); }
lua_State *oapiGetLua(INTERPRETERHANDLE handle) { return interpreter().state(handle); }
