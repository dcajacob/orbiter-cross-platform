cmake_minimum_required(VERSION 3.19)
project(ProductionElevationObservation LANGUAGES CXX)
if(NOT WIN32 OR NOT MSVC)
    message(FATAL_ERROR "Original elevation capture requires native Windows Orbiter")
endif()
set(ORBITER_TEST_RUNTIME "" CACHE PATH "Verified original Windows application and SDK")
add_library(ProductionElevationObserver SHARED Observe.cpp)
target_compile_features(ProductionElevationObserver PRIVATE cxx_std_17)
target_compile_definitions(ProductionElevationObserver PRIVATE NOMINMAX)
target_include_directories(ProductionElevationObserver PRIVATE "${ORBITER_TEST_RUNTIME}/Orbitersdk/include")
target_link_libraries(ProductionElevationObserver PRIVATE "${ORBITER_TEST_RUNTIME}/Orbitersdk/lib/Orbiter.lib"
    "${ORBITER_TEST_RUNTIME}/Orbitersdk/lib/Orbitersdk.lib")
set_target_properties(ProductionElevationObserver PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${ORBITER_TEST_RUNTIME}/Modules/Plugin")
