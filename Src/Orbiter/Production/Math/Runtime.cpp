// Licensed under the MIT License
#include "Runtime.h"
extern "C" {
int __use_fma3_lib=0;
double aw_exp(double);double aw_sin(double);double aw_cos(double);double aw_atan2(double,double);
double orbiter_asin_fma(double);double orbiter_asin_sse2(double);
}
namespace {
bool Fma() noexcept {
    static const bool selected=[] {
        __builtin_cpu_init();
#if ORBITER_MATH_FORCE_SSE2
        const bool available=false;
#else
        const bool available=__builtin_cpu_supports("avx") && __builtin_cpu_supports("fma");
#endif
        __use_fma3_lib=available?1:0;
        return available;
    }();
    return selected;
}
}
extern "C" {
// The vendor SSE2 polynomial turns sin(-0) into +0. Preserve the native C99
// signed-zero contract at the binding, without modifying the vendor source.
double orbiter_math_sin_value(double x) noexcept {return x==0.?x:aw_sin(x);}
// Linker wrapping applies only to targets using this internal numerical SDK.
// Ordinary process/libc/OpenGL symbols are never replaced or intercepted.
double __wrap_sin(double x) noexcept {Fma();return orbiter_math_sin_value(x);}
double __wrap_exp(double x) noexcept {Fma();return aw_exp(x);}
double __wrap_cos(double x) noexcept {Fma();return aw_cos(x);}
double __wrap_asin(double x) noexcept {return Fma()?orbiter_asin_fma(x):orbiter_asin_sse2(x);}
double __wrap_atan2(double y,double x) noexcept {Fma();return aw_atan2(y,x);}
void __wrap_sincos(double x,double* s,double* c) noexcept {Fma();*s=orbiter_math_sin_value(x);*c=aw_cos(x);}
}
namespace orbiter::production {
// The original Windows Release runtime rounds the equatorial latitude with
// the SSE2 polynomial even when its CRT FMA3 switch is enabled (run 41560881876).
double ReferenceLatitudeAsin(double x) noexcept {
#if ORBITER_MATH_RELEASE_LATITUDE
    return orbiter_asin_sse2(x);
#else
    return __wrap_asin(x);
#endif
}
const char* ReferenceMathProfile() noexcept {return Fma()?"amd-6121d02-fma3":"amd-6121d02-sse2";}
}
