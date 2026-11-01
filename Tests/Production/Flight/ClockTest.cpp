// Licensed under the MIT License
#include "Production/FlightClock.h"
#include <iostream>
#include <stdexcept>
using orbiter::production::FlightClock;
int main() {
    try {
        for(int fps:{24,30,60,144,240}) {
            FlightClock clock(1./60);int ticks=0;
            for(int frame=0;frame<fps*10;++frame) {clock.Add(1./fps);while(clock.Tick())++ticks;}
            if(ticks!=600)throw std::runtime_error("Physics count depends on render rate");
        }
        FlightClock clock(.25);clock.Add(100);for(int i=0;i<400;++i)if(!clock.Tick())throw std::runtime_error("Backlog discarded");
        if(clock.Tick())throw std::runtime_error("Clock created time");
        for(double invalid:{-1.,0.}) {bool rejected=false;try{FlightClock bad(invalid);}catch(const std::invalid_argument&){rejected=true;}if(!rejected)throw std::runtime_error("Invalid quantum accepted");}
        std::cout<<"Fixed ticks independent of rendering; backlog conserved\n";
    } catch(const std::exception& e) {std::cerr<<e.what()<<'\n';return 1;}
}
