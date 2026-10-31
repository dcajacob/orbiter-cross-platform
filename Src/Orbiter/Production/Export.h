// Licensed under the MIT License
#ifndef ORBITER_PRODUCTION_EXPORT_H
#define ORBITER_PRODUCTION_EXPORT_H
#if defined(_WIN32) && defined(ORBITER_PRODUCTION_SHARED)
# ifdef ORBITER_PRODUCTION_BUILD
#  define ORBITER_PRODUCTION_API __declspec(dllexport)
# else
#  define ORBITER_PRODUCTION_API __declspec(dllimport)
# endif
#else
# define ORBITER_PRODUCTION_API
#endif
#endif
