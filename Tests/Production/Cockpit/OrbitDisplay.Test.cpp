// Licensed under the MIT License.
// Link with the matching native production boundary and ASan/UBSan runtimes.
#include "Production/OrbitAnomalyDisplay.h"
#include <array>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <iostream>
#include <limits>
#include <stdexcept>
using orbiter::production::OrbitDisplayTrueAnomaly;
using orbiter::production::OrbitDisplayTrueLongitude;
namespace {
void require(bool ok,const char* message){if(!ok)throw std::runtime_error(message);}
bool same(double a,double b){return std::memcmp(&a,&b,sizeof(a))==0;}
void landed(Elements& e){
 // Actual complete-scene landed PB at t=3.25s: normalized acos input is -1-1ULP.
 e.Setup(1250.0,5.97369890113e24,51982.5,51982.5);
 e.Calculate(Vector(1028564.7983398438,4580514.641579036,-4307150.337720871),
             Vector(421.02629977096876,-29.871762398708398,68.77512110340103),3.25);
 require(std::isnan(e.TrueAnm()) && std::isnan(e.TrueLng()),"Actual roundoff fixture did not reproduce");
}
}
int main(){
 Elements e(51982.5);landed(e);
 std::array<unsigned char,sizeof(Elements)> before{};std::memcpy(before.data(),&e,sizeof(e));
 const double anomaly=OrbitDisplayTrueAnomaly(e),longitude=OrbitDisplayTrueLongitude(e);
 char tra[64],trl[64];std::snprintf(tra,sizeof(tra),"%.2f",Deg(anomaly));std::snprintf(trl,sizeof(trl),"%.2f",Deg(longitude));
 require(std::strcmp(tra,"180.00")==0 && std::strcmp(trl,"280.98")==0,"Displayed original finite anomalies differ");
 require(std::memcmp(before.data(),&e,sizeof(e))==0,"Display mutated physical Elements state");
 Elements nonroundoff(51982.5);landed(nonroundoff);nonroundoff.e*=0.5;
 require(same(nonroundoff.TrueAnm(),OrbitDisplayTrueAnomaly(nonroundoff)),"Large invalid argument was recovered");
 Elements hyperbolic(51982.5);landed(hyperbolic);hyperbolic.e=1.5;
 require(same(hyperbolic.TrueAnm(),OrbitDisplayTrueAnomaly(hyperbolic)),"Hyperbolic invalid argument was recovered");
 Elements invalid(51982.5);landed(invalid);invalid.a=std::numeric_limits<double>::quiet_NaN();
 require(same(invalid.TrueAnm(),OrbitDisplayTrueAnomaly(invalid)),"Nonfinite input was recovered");
 Elements valid(51982.5);valid.Setup(1250.0,5.97369890113e24,51982.5,51982.5);
 valid.Calculate(Vector(7e6,0,0),Vector(0,0,7500),0);
 require(std::isfinite(valid.TrueAnm()) && same(valid.TrueAnm(),OrbitDisplayTrueAnomaly(valid)) && same(valid.TrueLng(),OrbitDisplayTrueLongitude(valid)),"Finite display bits changed");
 std::cout<<"Orbit display roundoff regression and three invalid-input controls passed\n";
}
