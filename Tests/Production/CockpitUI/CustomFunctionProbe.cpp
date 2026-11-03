// Licensed under the MIT License
// Test-only module: register through the public SDK and let the real Function
// dialog invoke callbacks. No callback is invoked by this observation wrapper.
#include "Production/NativeGraphics.h"
#include "NativeVesselAPI.h"
#include "Production/NativeInterpreterSdk.h"
#include <dlfcn.h>
#include <cstdlib>
#include <fstream>
#include <stdexcept>
#include <vector>
using namespace orbiter::production;
namespace {
OBJHANDLE owner=nullptr;
int first=-1,second=-1,replacement=-1,cleanup=-1;
int firstContext=17,secondContext=29;
bool simple=false;
void require(bool value,const char* message) {if(!value)throw std::runtime_error(message);}
void event(const char* value) {std::ofstream(GetNativeRenderContext().evidence/"custom-function-events.txt",std::ios::app)<<value<<'\n';}
void forbidden(void*) {throw std::runtime_error("Removed or unselected custom function was invoked");}
void firstCallback(void* context) {
    require(context==&firstContext && *static_cast<int*>(context)==17,"First custom function context differs");
    require(oapiUnregisterCustomCmd(first) && !oapiUnregisterCustomCmd(first),"Self-unregistration failed");
    char label[]="Transient",description[]="Reallocation exercise";
    std::vector<int> transient;
    for(int i=0;i<64;++i)transient.push_back(oapiRegisterCustomCmd(label,description,forbidden,nullptr));
    for(int id:transient)require(oapiUnregisterCustomCmd(id),"Transient registration was lost");
    char name[]="Replacement";
    replacement=oapiRegisterCustomCmd(name,description,forbidden,nullptr);
    event("first:context:self-unregister:reallocate:replace");
    if(std::getenv("ORBITER_TEST_HELP_FAILURE")) {
        HELPCONTEXT help{};help.helpfile=const_cast<char*>("html/missing-help-probe.chm");
        require(!oapiOpenHelp(&help) && !oapiOpenHelp(&help),"Missing help book did not fail through the SDK");
    }
}
void secondCallback(void* context) {
    require(context==&secondContext && *static_cast<int*>(context)==29,"Second custom function context differs");
    require(oapiUnregisterCustomCmd(replacement),"Replacement command was lost");
    require(oapiUnregisterCustomCmd(second),"Second self-unregistration failed");
    require(!oapiUnregisterCustomCmd(-1),"Unknown custom function was removed");
    char name[]="Cleanup sentinel",description[]="Released when the module visual is destroyed";
    cleanup=oapiRegisterCustomCmd(name,description,forbidden,nullptr);
    event("second:context:remove-other:self-unregister");
}
void setup() {
    simple=std::getenv("ORBITER_TEST_SIMPLE_FUNCTION")!=nullptr;
    if(simple) {
        char label[]="SDK function",description[]="Public SDK callback";
        first=oapiRegisterCustomCmd(label,description,[](void*){event("invoked");},nullptr);
        event("registered");return;
    }
    char label[]="SDK Function",description[]="SDK callback with owned label and description";
    first=oapiRegisterCustomCmd(label,description,firstCallback,&firstContext);
    second=oapiRegisterCustomCmd(label,description,secondCallback,&secondContext);
    require(first!=second,"Duplicate labels did not receive unique IDs");
    // The registration API must not retain the caller's temporary strings.
    label[0]='X';description[0]='X';
    event("registered:duplicate-labels");
}
}
void orbiter::production::RenderRegisterVisual(OBJHANDLE object,VISHANDLE visual) {
    auto original=reinterpret_cast<decltype(&RenderRegisterVisual)>(dlsym(RTLD_NEXT,"_ZN7orbiter10production20RenderRegisterVisualEPvS1_"));
    require(original,"Native renderer registration missing");original(object,visual);
    if(!owner && oapiGetObjectType(object)==OBJTP_VESSEL) {owner=object;setup();}
}
void orbiter::production::RenderUnregisterVisual(OBJHANDLE object) {
    auto original=reinterpret_cast<decltype(&RenderUnregisterVisual)>(dlsym(RTLD_NEXT,"_ZN7orbiter10production22RenderUnregisterVisualEPv"));
    require(original,"Native renderer unregistration missing");
    if(object==owner) {
        oapiUnregisterCustomCmd(first);oapiUnregisterCustomCmd(second);
        if(replacement>=0)oapiUnregisterCustomCmd(replacement);
        if(cleanup>=0)require(oapiUnregisterCustomCmd(cleanup),"Live function not removed at module teardown");
        event(simple ? "unregistered" : "unregistered:teardown");owner=nullptr;
    }
    original(object);
}
