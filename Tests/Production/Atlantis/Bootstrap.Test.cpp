// Licensed under the MIT License
// Load the real three SDK entries and their private implementation under ASan/UBSan.
#include "Production/NativeModule.h"
#include "Production/NativeAbi.h"
#include <dlfcn.h>
#include <cstring>
#include <filesystem>
#include <iostream>
#include <stdexcept>

void require(bool value,const char* message) {
    if(!value)throw std::runtime_error(message);
}

int main(int argc,char** argv) {
    try {
        require(argc==4,"Three actual Atlantis SDK module paths required");
        const char* names[]={"Stock Atlantis","Stock Atlantis external tank","Stock Atlantis solid rocket booster"};
        for(unsigned repeat=0;repeat<20;++repeat)for(int part=0;part<3;++part) {
            void* library=dlopen(argv[part+1],RTLD_NOW|RTLD_LOCAL);
            if(!library)throw std::runtime_error(dlerror());
            using Query=const OrbiterNativeModuleDescriptor* (ORBITER_NATIVE_CALL*)(std::uint32_t) noexcept;
            auto query=reinterpret_cast<Query>(dlsym(library,"OrbiterNativeQuery"));
            require(query && !query(0) && !query(ORBITER_NATIVE_BOOTSTRAP_VERSION+1),"SDK bootstrap version rejection differs");
            const auto* descriptor=query(ORBITER_NATIVE_BOOTSTRAP_VERSION);
            require(descriptor && descriptor->struct_size==sizeof(*descriptor) && descriptor->kind==ORBITER_NATIVE_VESSEL,
                    "Actual Atlantis SDK descriptor differs");
            require(!std::strcmp(descriptor->name,names[part]),"Actual Atlantis entry selected a different class");
            require(!std::strcmp(descriptor->sdk_build,orbiter::production::NativeModule::SdkBuild()) &&
                    !std::strcmp(descriptor->cpp_abi,orbiter::production::NativeModule::CppAbi()),"Actual Atlantis SDK/toolchain differs");
            Dl_info owner{};
            require(dladdr(descriptor,&owner) && owner.dli_fname &&
                    std::filesystem::path(owner.dli_fname).filename()=="liborbiter_native_atlantis.so",
                    "Actual Atlantis descriptor does not belong to its private implementation");
            void* instance=nullptr;char error[512]{};
            require(descriptor->initialize(nullptr,&instance,error,sizeof(error))!=0 && !instance && error[0],
                    "Actual Atlantis factory accepted a missing host");
            require(dlclose(library)==0,"Actual Atlantis SDK module close failed");
        }
        std::cout<<"Passed 60 real SDK library load/version/identity/missing-host/close cycles; no simulation admission\n";
        return 0;
    } catch(const std::exception& error) {
        std::cerr<<error.what()<<'\n';return 1;
    }
}
