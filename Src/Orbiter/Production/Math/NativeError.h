// Licensed under the MIT License
#ifndef ORBITER_NATIVE_MATH_ERROR_H
#define ORBITER_NATIVE_MATH_ERROR_H
#include <stdint.h>
#include <emmintrin.h>
// Private identifiers, used only to carry a vendor error request into the
// native errno/fenv binding. They are not exported SDK or Windows ABI values.
enum {OP_ASIN=1,OP_ATAN2=2};
#define _DOMAIN 1
#define _handle_error orbiter_math_error
#define _handle_errorf orbiter_math_errorf
#define _set_statfp orbiter_math_set_status
#endif
