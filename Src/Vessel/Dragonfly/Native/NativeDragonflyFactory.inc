// Licensed under the MIT License. Compiled after the original module bodies.
namespace {
unsigned nativeDragonflyInstances=0;
VESSEL* CreateNativeDragonfly(OBJHANDLE object,int model) {
    if(!nativeDragonflyInstances){hDLL=dragonfly::drawing::ModuleResources();PANEL_DLLAtach();}
    try {
        VESSEL* result=ovcInit(object,model);++nativeDragonflyInstances;return result;
    } catch(...) {
        if(!nativeDragonflyInstances){PANEL_ReleaseGDIResources();dragonfly::drawing::ReleaseStockResources();}
        throw;
    }
}
void DestroyNativeDragonfly(VESSEL* vessel) {
    // Native contexts hold real selected drawing resources. Release the vessel
    // and its panels before the last instance's shared module drawing assets.
    delete static_cast<Dragonfly*>(vessel);
    if(!--nativeDragonflyInstances){PANEL_ReleaseGDIResources();dragonfly::drawing::ReleaseStockResources();}
}
}
#define ORBITER_NATIVE_STOCK_NAME "Dragonfly"
#define ORBITER_NATIVE_STOCK_CREATE CreateNativeDragonfly
#define ORBITER_NATIVE_STOCK_DESTROY DestroyNativeDragonfly
#include "../../NativeStockFactory.inc"
