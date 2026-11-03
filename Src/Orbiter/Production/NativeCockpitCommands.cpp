// Licensed under the MIT License
#include "NativeVesselAPI.h"
#include "NativeGraphics.h"

oapi::UInt32 oapiRegisterCustomCmd(char* label,char* description,CustomFunc callback,void* context) {
    return orbiter::production::GetNativeRenderContext().customCommands.Register(label,description,callback,context);
}
bool oapiUnregisterCustomCmd(int id) {
    return orbiter::production::GetNativeRenderContext().customCommands.Remove(id);
}
