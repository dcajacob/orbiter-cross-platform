// Licensed under the MIT License
namespace {
unsigned activeSolarSails=0;
VESSEL* CreateNativeSolarSail(OBJHANDLE object,int flightmodel) {
    try {
        if(activeSolarSails==0)InitSailResources();
        VESSEL* vessel=ovcInit(object,flightmodel);
        ++activeSolarSails;
        return vessel;
    } catch(...) {
        if(activeSolarSails==0)ReleaseSailResources();
        throw;
    }
}
void DestroyNativeSolarSail(VESSEL* vessel) {
    ovcExit(vessel);
    if(--activeSolarSails==0)ReleaseSailResources();
}
}
#define ORBITER_NATIVE_STOCK_NAME "Stock SolarSail"
#define ORBITER_NATIVE_STOCK_CREATE CreateNativeSolarSail
#define ORBITER_NATIVE_STOCK_DESTROY DestroyNativeSolarSail
#include "../NativeStockFactory.inc"
