// Licensed under the MIT License.
#include "Production/RecordedAttitude.h"
#include <algorithm>
#include <array>
#include <cmath>
#include <cstring>
#include <fstream>
#include <iostream>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

void Euler2Quaternion(double*,Quaternion&,int);
namespace {
void require(bool value,const char* message){if(!value)throw std::runtime_error(message);}
bool finite(const Quaternion& q){return std::isfinite(q.qvx)&&std::isfinite(q.qvy)&&std::isfinite(q.qvz)&&std::isfinite(q.qs);}
double distance(const Quaternion& a,const Quaternion& b){
    double direct=0,opposite=0;
    for(auto pair:{std::pair<double,double>{a.qvx,b.qvx},{a.qvy,b.qvy},{a.qvz,b.qvz},{a.qs,b.qs}}){
        direct+=(pair.first-pair.second)*(pair.first-pair.second);
        opposite+=(pair.first+pair.second)*(pair.first+pair.second);
    }
    return 4*std::asin(.5*std::sqrt((std::min)(direct,opposite)));
}
}
int main(int argc,char** argv){
    try {
        require(argc==2,"Unchanged original GL-01.att path required");
        // Actual endpoint values observed in both frozen Windows SSE2 and the
        // native production library at the failed recording segment.
        Quaternion a(-0.20705975295440079,-0.707331128182206,
            0.6758748997950339,0.0014330574344375848);
        Quaternion b(-0.20575859225389001,-0.70733535298824113,
            0.6762746414472951,1.1333992937104704e-06),original,repaired;
        const double u=(307540.40009604016-307540.3857392)/(307540.4680605-307540.3857392);
        original.interp(a,b,u);require(!finite(original),"Actual original Moon failure was not reproduced");
        orbiter::production::InterpolateRecordedAttitude(repaired,a,b,u);
        require(finite(repaired)&&std::abs(repaired.norm2()-1)<1e-12,"Moon recovery is not a unit rotation");
        // Independent 85-digit decimal matrix/Euler conversion and spherical
        // interpolation, evaluated at the exact binary64 recording operands.
        const Quaternion oracle(-0.20683275767584022,-0.7073316140694368,
            0.6759443747973376,0.0011833300338211358);
        const double error=distance(repaired,oracle);
        require(error<=1e-8,"Recovered recording rotation exceeds the existing angular budget");
        std::ifstream stream(argv[1]);require(bool(stream),"Original attitude recording missing");
        std::vector<Quaternion> samples;std::string line;int frame=0;
        while(std::getline(stream,line)){
            if(line.compare(0,4,"FRM ")==0){frame=line.find("HORIZON")!=std::string::npos?1:0;continue;}
            std::istringstream fields(line);double t,angles[3];
            if(fields>>t>>angles[0]>>angles[1]>>angles[2]){Quaternion q;Euler2Quaternion(angles,q,frame);samples.push_back(q);}
        }
        require(samples.size()>2500,"Complete original Moon attitude stream required");
        unsigned unchanged=0,recovered=0;
        for(std::size_t i=1;i<samples.size();++i)for(double fraction:{0.0,.125,u,.25,.5,.75,.875,1.0}){
            Quaternion oldValue,newValue;oldValue.interp(samples[i-1],samples[i],fraction);
            orbiter::production::InterpolateRecordedAttitude(newValue,samples[i-1],samples[i],fraction);
            require(finite(newValue)&&std::abs(newValue.norm2()-1)<1e-12,"Recorded pair is still invalid");
            if(finite(oldValue)){
                require(std::memcmp(&oldValue,&newValue,sizeof(Quaternion))==0,"Finite original interpolation bits changed");++unchanged;
            }else ++recovered;
        }
        require(unchanged>10000,"Original finite recording cases required");
        for(double sign:{1.0,-1.0}){
            Quaternion x(0,0,0,1+2e-8),y(0,0,0,sign*(1+3e-8)),q;
            orbiter::production::InterpolateRecordedAttitude(q,x,y,.5);
            require(finite(q)&&q.qs==1&&q.norm2()==1,"Rounded coincident/antipodal unit-dot limit failed");
        }
        for(Quaternion invalid:{Quaternion(0,0,0,0),Quaternion(std::numeric_limits<double>::quiet_NaN(),0,0,1),Quaternion(std::numeric_limits<double>::infinity(),0,0,1)}){
            Quaternion q;orbiter::production::InterpolateRecordedAttitude(q,invalid,invalid,.5);
            require(!finite(q),"Invalid non-Euler input was silently repaired");
        }
        std::cout<<"{\"status\":\"passed\",\"finite_original_results_bit_identical\":"<<unchanged
                 <<",\"original_nonfinite_results_recovered\":"<<recovered
                 <<",\"original_recording_samples\":"<<samples.size()
                 <<",\"independent_rotation_error_rad\":"<<error<<"}\n";
        return 0;
    }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
