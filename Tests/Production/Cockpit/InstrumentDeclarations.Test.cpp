// Licensed under the MIT License
// Original instrument declarations must compile with real native SDK types.
#include "Mfd.h"
#include <type_traits>
#include <iostream>
static_assert(std::is_abstract_v<Instrument>);
static_assert(std::is_base_of_v<ImGuiDialog,Select>);
static_assert(std::is_same_v<decltype(Instrument::Spec{}.flag),oapi::UInt32>);
using InstrumentFactory=Instrument*(*)(int,Pane*,std::intptr_t,const Instrument::Spec&,Vessel*,bool);
static_assert(std::is_same_v<decltype(static_cast<InstrumentFactory>(&Instrument::Create)),InstrumentFactory>);
int main(){std::cout<<"Original instrument declarations compile with platform SDK types; runtime integration remains separate\n";}
