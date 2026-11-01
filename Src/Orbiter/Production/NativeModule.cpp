// Licensed under the MIT License
#include "NativeModule.h"
#include "NativeAbi.h"
#include <stdexcept>
#include <cstring>
#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#else
#include <dlfcn.h>
#endif
namespace orbiter::production {
const char* NativeModule::SdkBuild() noexcept { return ORBITER_NATIVE_SDK_BUILD; }
const char* NativeModule::CppAbi() noexcept { return ORBITER_NATIVE_CPP_ABI; }
namespace {
void require(bool value, const std::string& message) { if (!value) throw std::runtime_error(message); }
}
NativeModule::NativeModule(const std::filesystem::path& path, uint32_t kind, void* context)
{
    require(path.is_absolute(), "Native module requires an absolute library path: "+path.string());
    require(kind>=ORBITER_NATIVE_VESSEL && kind<=ORBITER_NATIVE_GRAPHICS, "Unknown native module kind");
#ifdef _WIN32
    library=LoadLibraryExW(path.c_str(),nullptr,LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR|LOAD_LIBRARY_SEARCH_DEFAULT_DIRS);
    if (!library) {
        const auto error=GetLastError();
        throw std::runtime_error("Cannot load native module "+path.string()+" (Windows error "+std::to_string(error)+")");
    }
#else
    library=dlopen(path.c_str(),RTLD_NOW|RTLD_LOCAL);
    if (!library) { const char* error=dlerror();throw std::runtime_error("Cannot load native module "+path.string()+": "+(error?error:"unknown loader error")); }
#endif
    try {
        auto query=reinterpret_cast<OrbiterNativeQueryFunction>(Symbol("OrbiterNativeQuery"));
        descriptor=query(ORBITER_NATIVE_BOOTSTRAP_VERSION);
        require(descriptor!=nullptr,"Native module rejected bootstrap ABI: "+path.string());
        require(descriptor->struct_size==sizeof(OrbiterNativeModuleDescriptor),"Native module descriptor size mismatch");
        require(descriptor->abi_version==ORBITER_NATIVE_BOOTSTRAP_VERSION,"Native module bootstrap version mismatch");
        require(descriptor->pointer_bytes==sizeof(void*),"Native module architecture mismatch");
        require(descriptor->kind==kind,"Native module kind mismatch");
        require(descriptor->name && *descriptor->name,"Native module has no identity");
        require(descriptor->sdk_build && std::strcmp(descriptor->sdk_build,SdkBuild())==0,"Native module SDK build mismatch");
        require(descriptor->cpp_abi && std::strcmp(descriptor->cpp_abi,CppAbi())==0,"Native module C++ toolchain/ABI mismatch");
        require(descriptor->initialize && descriptor->shutdown,"Native module lifecycle entry is missing");
        info={descriptor->name,descriptor->sdk_build,descriptor->cpp_abi,descriptor->kind};
        host={sizeof(OrbiterNativeHost),ORBITER_NATIVE_BOOTSTRAP_VERSION,SdkBuild(),CppAbi(),context};
        char error[512]{};
        const int result=descriptor->initialize(&host,&instance,error,sizeof(error));
        error[sizeof(error)-1]='\0';
        require(result==0 && instance!=nullptr,"Native module initialization failed: "+info.name+(error[0]?": "+std::string(error):""));
    } catch (...) { Close();throw; }
}
NativeModule::~NativeModule() { Close(); }
void NativeModule::Close() noexcept
{
    if (instance) { descriptor->shutdown(instance);instance=nullptr; }
    descriptor=nullptr;
    if (library) {
#ifdef _WIN32
        FreeLibrary(static_cast<HMODULE>(library));
#else
        dlclose(library);
#endif
        library=nullptr;
    }
}
void* NativeModule::Symbol(const char* name) const
{
    require(library && name && *name,"Native module symbol query has no library or name");
#ifdef _WIN32
    auto result=reinterpret_cast<void*>(GetProcAddress(static_cast<HMODULE>(library),name));
    require(result!=nullptr,"Missing native module entry: "+std::string(name));
#else
    dlerror();
    auto result=dlsym(library,name);
    const char* error=dlerror();
    require(!error && result,"Missing native module entry: "+std::string(name)+(error?": "+std::string(error):""));
#endif
    return result;
}
}
