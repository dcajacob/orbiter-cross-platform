// Licensed under the MIT License
#include "Production/Random.h"
#include <cstdlib>
#include <iostream>
#include <stdexcept>
#include <thread>
using namespace orbiter::production;
void require(bool value,const char* message){if(!value)throw std::runtime_error(message);}
int main() {
    try {
        // Independent Windows CRT oracle: this same test executes its original
        // std::rand adapter on MSVC, as well as the native engine generator.
        const int expected[]={41,18467,6334,26500,19169,15724,11478,29358,26962,24464};
        require(RandomMaximum==32767,"Original runtime random range changed");
        SeedRandom(1);
        for(int value:expected)require(RandomInteger()==value,"Original runtime seeded sequence differs");
        SeedRandom(1);require(RandomInteger()==41,"Random seed did not reset");
        int worker=0;
        std::thread thread([&]{SeedRandom(1);worker=RandomInteger();});thread.join();
        require(worker==41 && RandomInteger()==18467,"Simulation random streams leaked across threads");
#ifndef _WIN32
        SeedRandom(1);require(RandomInteger()==41,"Initial private random draw differs");
        std::srand(98765);for(int i=0;i<10000;++i)(void)std::rand();
        require(RandomInteger()==18467,"Foreign libraries consumed the simulation random stream");
#endif
        std::cout<<"Original runtime sequence, reset, thread ownership and native isolation passed\n";
        return 0;
    } catch(const std::exception& error){std::cerr<<error.what()<<'\n';return 1;}
}
