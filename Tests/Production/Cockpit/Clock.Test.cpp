// Licensed under the MIT License
#include "Production/CockpitSystemClock.h"
#include "TimeData.h"
#include <iostream>
#include <limits>
namespace {
void require(bool value,const char* message){if(!value)throw std::runtime_error(message);}
}
int main(){
    orbiter::production::CockpitSystemClock invalid;
    for(double elapsed:{0.,-1.,std::numeric_limits<double>::infinity(),std::numeric_limits<double>::quiet_NaN()}) {
        bool rejected=false;try{invalid.Step(elapsed);}catch(const std::invalid_argument&){rejected=true;}
        require(rejected,"Invalid elapsed time was accepted");
    }
    for(int i=0;i<3;i++)require(invalid.Step(.25)==.01,"Invalid input consumed a startup tick");
    require(invalid.Step(.25)==.1 && invalid.Step(.05)==.05,"Elapsed-time cap changed");
    orbiter::production::CockpitSystemClock clock;TimeData time;time.Reset(51982.5);time.SetFixedStep(.25);
    for(int tick=0;tick<60;tick++) {
        const double systemStep=clock.Step(.25);
        require(systemStep==(tick<3?.01:.1),"Original startup/system-time schedule differs");
        time.BeginStep(systemStep,true);time.EndStep(true);
        require(time.SimT0==(tick+1)*.25,"System-time policy changed the production physics step");
    }
    time.BeginStep(clock.Step(.05),false);time.EndStep(false);
    require(time.SimT0==15.,"Paused UI time advanced simulation time");
    time.SetWarp(10.);time.BeginStep(clock.Step(.05),true);time.EndStep(true);
    require(time.SimT0==17.5,"System clock changed original fixed-step time acceleration");
    std::cout<<"Original startup/system-time cap, fixed physics step, pause and warp verified\n";
}
