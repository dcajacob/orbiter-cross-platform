cmake_minimum_required(VERSION 3.24)
project(ProductionStockLuaExitObservation LANGUAGES CXX)
if(NOT WIN32 OR NOT MSVC)
    message(FATAL_ERROR "The original exit observer requires native Windows/MSVC")
endif()
set(ORBITER_TEST_RUNTIME "" CACHE PATH "Preserved original application and SDK")
get_filename_component(ORBITER_TEST_RUNTIME "${ORBITER_TEST_RUNTIME}" ABSOLUTE)
add_library(ProductionCockpitDriver SHARED Driver.cpp)
target_compile_features(ProductionCockpitDriver PRIVATE cxx_std_17)
target_compile_definitions(ProductionCockpitDriver PRIVATE NOMINMAX)
target_include_directories(ProductionCockpitDriver PRIVATE
    "${ORBITER_TEST_RUNTIME}/Orbitersdk/include" ../..)
target_link_libraries(ProductionCockpitDriver PRIVATE
    "${ORBITER_TEST_RUNTIME}/Orbitersdk/lib/Orbiter.lib"
    "${ORBITER_TEST_RUNTIME}/Orbitersdk/lib/Orbitersdk.lib" opengl32)
set_target_properties(ProductionCockpitDriver PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${ORBITER_TEST_RUNTIME}/Modules/Plugin")
