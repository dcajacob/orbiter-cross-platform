// Licensed under the MIT License
#ifndef ORBITER_NATIVE_VESSEL_FACTORY_H
#define ORBITER_NATIVE_VESSEL_FACTORY_H
#include "NativeVesselModule.h"
#include "NativeAbi.h"
#include <cstdio>
#include <memory>
#include <stdexcept>
namespace orbiter::native {
template<VESSEL* (*Create)(OBJHANDLE,int),void (*Destroy)(VESSEL*)>
struct VesselFactory {
    static void release(VesselInstance* instance) noexcept
    {if(instance->vessel) {Destroy(instance->vessel);instance->vessel=nullptr;}}
    static int ORBITER_NATIVE_CALL initialize(const OrbiterNativeHost* host,void** result,char* error,std::uint32_t capacity) noexcept
    {
        try {
            if(!host || host->struct_size!=sizeof(*host) || !host->context || !result)
                throw std::runtime_error("Missing native vessel initialization context");
            const auto& context=*static_cast<const VesselInit*>(host->context);
            if(context.size!=sizeof(context) || !context.vessel)
                throw std::runtime_error("Invalid native vessel initialization context");
            auto instance=std::make_unique<VesselInstance>();
            instance->size=sizeof(VesselInstance);instance->release=release;
            instance->vessel=Create(context.vessel,context.flightmodel);
            if(!instance->vessel) throw std::runtime_error("Native vessel factory returned no interface");
            *result=instance.release();return 0;
        } catch(const std::exception& e) {std::snprintf(error,capacity,"%s",e.what());return 1;}
        catch(...) {std::snprintf(error,capacity,"Unexpected native vessel initialization failure");return 1;}
    }
    static void ORBITER_NATIVE_CALL shutdown(void* value) noexcept
    {auto* instance=static_cast<VesselInstance*>(value);release(instance);delete instance;}
};
}
#endif
