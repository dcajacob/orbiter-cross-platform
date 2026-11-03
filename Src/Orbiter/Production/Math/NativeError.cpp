// Licensed under the MIT License
#include <cerrno>
#include <cfenv>
#include <cstdint>
#include <cstring>
#include <initializer_list>
#include <xmmintrin.h>
namespace {
int StandardFlags(unsigned flags) {
    int result=0;
    if(flags&1u)result|=FE_OVERFLOW;
    if(flags&2u)result|=FE_UNDERFLOW;
    if(flags&4u)result|=FE_DIVBYZERO;
    if(flags&8u)result|=FE_INVALID;
    if(flags&16u)result|=FE_INEXACT;
    return result;
}
double Special(double x) {
    std::uint64_t bits;std::memcpy(&bits,&x,sizeof(bits));
    if((bits&UINT64_C(0x7ff0000000000000))!=UINT64_C(0x7ff0000000000000))return x;
    const auto mantissa=bits&UINT64_C(0x000fffffffffffff);
    if(!mantissa) {
        bits=UINT64_C(0xfff8000000000000);errno=EDOM;std::feraiseexcept(FE_INVALID);
    } else {
        if(!(bits&UINT64_C(0x0008000000000000)))std::feraiseexcept(FE_INVALID);
        bits|=UINT64_C(0x0008000000000000);
    }
    std::memcpy(&x,&bits,sizeof(x));return x;
}
}
extern "C" {
void orbiter_math_set_status(std::uintptr_t flags) {
    // This vendor helper receives x86 status-word bits, unlike its error
    // requests' AMD_F_* bits. Preserve all rounding/exception-control bits.
    _mm_setcsr(_mm_getcsr() | (static_cast<unsigned>(flags)&0x3fu));
}
double orbiter_math_error(char*,int,unsigned long value,int,int flags,int error,double arg1,double arg2,int nargs) {
    static_assert(sizeof(unsigned long)==sizeof(double),"Native math requires LP64");
    auto raised=StandardFlags(static_cast<unsigned>(flags));
    bool nanInput=false;
    for(double arg:{arg1,nargs==2?arg2:0.}) {
        std::uint64_t bits;std::memcpy(&bits,&arg,sizeof(bits));
        const bool nan=(bits&UINT64_C(0x7ff0000000000000))==UINT64_C(0x7ff0000000000000) && (bits&UINT64_C(0x000fffffffffffff));
        nanInput|=nan;
        if(nan && !(bits&UINT64_C(0x0008000000000000)))raised|=FE_INVALID;
    }
    if(error && !nanInput)errno=error;
    if(raised)std::feraiseexcept(raised);
    double result;std::memcpy(&result,&value,sizeof(result));return result;
}
// The original x86-64 assembly passes this private helper its third argument in R8D.
__attribute__((ms_abi)) double _exp_special(double x,double y,unsigned code) {
    unsigned long bits;
    std::memcpy(&bits,&y,sizeof(bits));
    int flags=code==2 ? 16|2 : code==3 ? 16|1 : 0;
    return orbiter_math_error(nullptr,0,bits,0,flags,code==1 ? EDOM : ERANGE,x,0.,1);
}
double _cos_special(double x) {return Special(x);}
double _sin_special(double x) {return Special(x);}
}
