// Licensed under the MIT License
// Test-only ABI and independent MPFR oracle. Not installed or linked to Orbiter.
#include "Runtime.h"
#include <mpfr.h>
#include <cerrno>
#include <cfenv>
#include <cstdint>
#include <cstring>
#include <cstdlib>
#include <dlfcn.h>
extern "C" {
extern int __use_fma3_lib;
double aw_sin(double);double aw_cos(double);double aw_atan2(double,double);
double orbiter_math_sin_value(double);
double orbiter_asin_fma(double);double orbiter_asin_sse2(double);
double __wrap_sin(double);double __wrap_cos(double);double __wrap_asin(double);double __wrap_atan2(double,double);
}
namespace {int mode=-1;}
extern "C" {
const char* probe_profile() {return orbiter::production::ReferenceMathProfile();}
int probe_fma_available() {__builtin_cpu_init();return __builtin_cpu_supports("avx") && __builtin_cpu_supports("fma");}
void probe_mode(int value) {
    if(value<0 || value>1 || (value && !probe_fma_available()))std::abort();
    mode=value;__use_fma3_lib=value;
}
double probe_value(int function,double x,double y) {
    if(mode==-1) {
        switch(function) {
        case 0:return __wrap_sin(x);case 1:return __wrap_cos(x);
        case 2:return __wrap_asin(x);case 3:return __wrap_atan2(x,y);
        }
    } else {
        switch(function) {
        case 0:return orbiter_math_sin_value(x);case 1:return aw_cos(x);
        case 2:return mode?orbiter_asin_fma(x):orbiter_asin_sse2(x);case 3:return aw_atan2(x,y);
        }
    }
    std::abort();
}
double probe_bits(int function,std::uint64_t x,std::uint64_t y) {
    double a,b;std::memcpy(&a,&x,sizeof(a));std::memcpy(&b,&y,sizeof(b));return probe_value(function,a,b);
}
void probe_clear() {errno=0;std::feclearexcept(FE_ALL_EXCEPT);}
int probe_errno() {return errno;}
int probe_invalid() {return std::fetestexcept(FE_INVALID)!=0;}
const char* oracle_version() {return mpfr_get_version();}
const char* oracle_module() {Dl_info info{};if(!dladdr(reinterpret_cast<void*>(mpfr_get_version),&info))std::abort();return info.dli_fname;}
double oracle_value(int function,double x,double y,unsigned precision) {
    mpfr_t a,b,out;mpfr_init2(a,precision);mpfr_init2(b,precision);mpfr_init2(out,precision);
    mpfr_set_d(a,x,MPFR_RNDN);mpfr_set_d(b,y,MPFR_RNDN);
    switch(function) {
    case 0:mpfr_sin(out,a,MPFR_RNDN);break;
    case 1:mpfr_cos(out,a,MPFR_RNDN);break;
    case 2:mpfr_asin(out,a,MPFR_RNDN);break;
    case 3:mpfr_atan2(out,a,b,MPFR_RNDN);break;
    default:std::abort();
    }
    const auto value=mpfr_get_d(out,MPFR_RNDN);
    mpfr_clear(a);mpfr_clear(b);mpfr_clear(out);return value;
}
}
