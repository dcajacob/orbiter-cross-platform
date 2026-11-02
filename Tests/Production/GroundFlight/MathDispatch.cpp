// Licensed under the MIT License
// Diagnostic Windows runtime variation only; never loaded by an acceptance run.
#define ORBITER_MODULE
#include "Orbitersdk.h"
#include <cmath>
#include <fstream>
#include <cstdlib>
namespace {int previous=0;}
DLLCLBK void InitModule(HINSTANCE) {
    previous=_get_FMA3_enable();const int selected=_set_FMA3_enable(0);
    std::ofstream out("math-dispatch.json",std::ios::binary);
    out<<"{\"diagnostic_only\":true,\"previous_fma3\":"<<previous
       <<",\"selected_fma3\":"<<selected<<"}\n";
    out.close();if(!out || selected!=0)std::exit(1);
}
DLLCLBK void ExitModule(HINSTANCE) {_set_FMA3_enable(previous);}
