# Internal Linux x86-64 math profile matching the original Windows runtime.
if(CMAKE_SOURCE_DIR STREQUAL CMAKE_CURRENT_SOURCE_DIR)
    cmake_minimum_required(VERSION 3.19)
    project(OrbiterReferenceMath LANGUAGES C CXX ASM)
    include(CTest)
endif()
enable_language(C ASM)
find_package(Python3 REQUIRED COMPONENTS Interpreter)
if(NOT CMAKE_SYSTEM_PROCESSOR MATCHES "^(x86_64|AMD64|amd64)$" OR NOT CMAKE_C_COMPILER_ID STREQUAL "GNU")
    message(FATAL_ERROR "The production reference math backend currently requires GCC on Linux x86-64")
endif()
option(ORBITER_MATH_FORCE_SSE2 "Qualify the baseline CPU math path even on FMA3 hardware" OFF)
# The parent SDK records these dependencies too. Normalize before registering
# them so Ninja receives one spelling per file in its regeneration rule.
get_filename_component(_math_upstream "${CMAKE_CURRENT_LIST_DIR}/../../../../Extern/ReferenceMath" ABSOLUTE)
set(_math_generated "${CMAKE_CURRENT_BINARY_DIR}/generated")
execute_process(COMMAND "${Python3_EXECUTABLE}" -B "${CMAKE_CURRENT_LIST_DIR}/prepare.py"
    --source "${_math_upstream}" --output "${_math_generated}" COMMAND_ERROR_IS_FATAL ANY)
file(GLOB_RECURSE ORBITER_REFERENCE_MATH_INPUTS CONFIGURE_DEPENDS LIST_DIRECTORIES FALSE
    "${CMAKE_CURRENT_LIST_DIR}/*" "${_math_upstream}/*")
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS ${ORBITER_REFERENCE_MATH_INPUTS})
add_library(orbiter_reference_math STATIC Runtime.cpp NativeError.cpp
    "${_math_generated}/cos.s" "${_math_generated}/sin.s"
    "${_math_generated}/remainder_piby2_forAsm.s" "${_math_generated}/remainder_piby2_forFMA3.s"
    "${_math_generated}/Lsincos_array.s" "${_math_generated}/L2_by_pi_bits.s"
    "${_math_generated}/exp.s" "${_math_generated}/two_to_jby64_table.s" "${_math_generated}/two_to_jby64_head_tail_table.s"
    "${_math_generated}/atan2.c" "${_math_generated}/asin_fma.c" "${_math_generated}/asin_sse2.c")
set_target_properties(orbiter_reference_math PROPERTIES POSITION_INDEPENDENT_CODE ON
    C_VISIBILITY_PRESET hidden CXX_VISIBILITY_PRESET hidden)
target_compile_features(orbiter_reference_math PRIVATE cxx_std_17)
target_compile_definitions(orbiter_reference_math PRIVATE ORBITER_MATH_FORCE_SSE2=$<BOOL:${ORBITER_MATH_FORCE_SSE2}>
    ORBITER_MATH_RELEASE_LATITUDE=$<CONFIG:Release>)
target_include_directories(orbiter_reference_math PRIVATE "${CMAKE_CURRENT_LIST_DIR}" "${_math_generated}")
set_source_files_properties("${_math_generated}/asin_fma.c" PROPERTIES COMPILE_OPTIONS "-O2;-fno-builtin;-mfma;-ffp-contract=fast")
set_source_files_properties("${_math_generated}/asin_sse2.c" "${_math_generated}/atan2.c" PROPERTIES COMPILE_OPTIONS "-O2;-fno-builtin;-mno-avx;-mno-fma;-ffp-contract=off")
target_link_options(orbiter_reference_math INTERFACE
    -Wl,--wrap=sin -Wl,--wrap=cos -Wl,--wrap=asin -Wl,--wrap=atan2 -Wl,--wrap=sincos)
target_link_libraries(orbiter_reference_math INTERFACE m)
get_target_property(_math_sources orbiter_reference_math SOURCES)
foreach(_math_source IN LISTS _math_sources)
    get_filename_component(_math_absolute "${_math_source}" ABSOLUTE BASE_DIR "${CMAKE_CURRENT_SOURCE_DIR}")
    list(APPEND ORBITER_REFERENCE_MATH_INPUTS "${_math_absolute}")
endforeach()
list(REMOVE_DUPLICATES ORBITER_REFERENCE_MATH_INPUTS)
if(NOT CMAKE_SOURCE_DIR STREQUAL CMAKE_CURRENT_SOURCE_DIR)
    set(ORBITER_REFERENCE_MATH_INPUTS "${ORBITER_REFERENCE_MATH_INPUTS}" PARENT_SCOPE)
endif()
if(BUILD_TESTING)
    find_path(MPFR_INCLUDE_DIR mpfr.h REQUIRED)
    find_library(MPFR_LIBRARY NAMES mpfr REQUIRED)
    add_library(reference_math_probe MODULE "${CMAKE_CURRENT_LIST_DIR}/../../../../Tests/Production/Math/Probe.cpp")
    target_compile_definitions(reference_math_probe PRIVATE ORBITER_MATH_RELEASE_LATITUDE=$<CONFIG:Release>)
    target_include_directories(reference_math_probe PRIVATE "${CMAKE_CURRENT_LIST_DIR}" "${MPFR_INCLUDE_DIR}")
    target_link_libraries(reference_math_probe PRIVATE orbiter_reference_math "${MPFR_LIBRARY}" ${CMAKE_DL_LIBS})
    add_test(NAME Production.ReferenceMath COMMAND "${Python3_EXECUTABLE}" -B
        "${CMAKE_CURRENT_LIST_DIR}/../../../../Tests/Production/Math/verify.py"
        --probe $<TARGET_FILE:reference_math_probe> --output "${CMAKE_CURRENT_BINARY_DIR}/math-verification.json")
    set_tests_properties(Production.ReferenceMath PROPERTIES TIMEOUT 120)
endif()
