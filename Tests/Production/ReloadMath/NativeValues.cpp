// Licensed under the MIT License
// Typed primitive observations from the retained native math archive.
#include "Runtime.h"
#include <cfenv>
#include <cstdint>
#include <cstring>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <xmmintrin.h>
extern "C" {
double __wrap_asin(double) noexcept;
double __wrap_sin(double) noexcept;
double __wrap_cos(double) noexcept;
double __wrap_atan2(double,double) noexcept;
}
double Number(const std::string& text) {
    if(text.size()!=16)throw std::runtime_error("Exact binary64 input required");
    std::size_t consumed=0;auto bits=std::stoull(text,&consumed,16);
    if(consumed!=16)throw std::runtime_error("Invalid binary64 input");
    double value;std::memcpy(&value,&bits,sizeof(value));return value;
}
int main() {
    std::cout<<"{\"profile\":\""<<orbiter::production::ReferenceMathProfile()
        <<"\",\"rounding\":"<<std::fegetround()<<",\"mxcsr_control\":"<<(_mm_getcsr()&0xffc0u)<<"}\n";
    std::string line;std::getline(std::cin,line);
    if(line!="tag,function,x,y")return 1;
    std::cout<<line<<",result\n";unsigned count=0;
    while(std::getline(std::cin,line)) {
        std::istringstream in(line);std::string tag,fn,x,y;
        if(!std::getline(in,tag,',') || !std::getline(in,fn,',') || !std::getline(in,x,',') || in.eof())return 1;
        std::getline(in,y); // Unary functions have an intentionally empty final field.
        const double a=Number(x);double result;
        if(fn=="asin")result=__wrap_asin(a);
        else if(fn=="sin")result=__wrap_sin(a);
        else if(fn=="cos")result=__wrap_cos(a);
        else if(fn=="atan2")result=__wrap_atan2(a,Number(y));
        else return 1;
        std::uint64_t bits;std::memcpy(&bits,&result,sizeof(bits));
        std::cout<<tag<<','<<fn<<','<<x<<','<<y<<','<<std::hex<<std::setfill('0')<<std::setw(16)<<bits<<'\n';++count;
    }
    return std::cin.eof() && count && std::cout ? 0 : 1;
}
