// Licensed under the MIT License
// Original instrument declarations must compile with real native SDK types.
#include "Mfd.h"
#include "MfdOrbit.h"
#include "MfdSurface.h"
#include "MfdMap.h"
#include "MfdHsi.h"
#include "MfdLanding.h"
#include "MfdDocking.h"
#include "MfdAlign.h"
#include "MfdSync.h"
#include "MfdTransfer.h"
#include "MfdComms.h"
#include <type_traits>
#include <iostream>
static_assert(std::is_abstract_v<Instrument>);
static_assert(std::is_base_of_v<ImGuiDialog,Select>);
template<class... T>constexpr bool stock_modes=(std::is_base_of_v<Instrument,T> && ...);
static_assert(stock_modes<Instrument_Orbit,Instrument_Surface,Instrument_Map,Instrument_HSI,
    Instrument_Landing,Instrument_Docking,Instrument_OPlaneAlign,Instrument_OSync,Instrument_Transfer,Instrument_Comms>);
static_assert(std::is_same_v<decltype(Instrument::Spec{}.flag),oapi::UInt32>);
using InstrumentFactory=Instrument*(*)(int,Pane*,std::intptr_t,const Instrument::Spec&,Vessel*,bool);
static_assert(std::is_same_v<decltype(static_cast<InstrumentFactory>(&Instrument::Create)),InstrumentFactory>);
int main(){std::cout<<"Original instrument declarations compile with platform SDK types; runtime integration remains separate\n";}
