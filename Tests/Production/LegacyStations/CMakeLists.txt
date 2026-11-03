cmake_minimum_required(VERSION 3.24)
project(OriginalLegacyStationObservation LANGUAGES CXX)
if(NOT WIN32 OR NOT MSVC)
  message(FATAL_ERROR "The original observer requires native Windows/MSVC")
endif()
set(ORBITER_TEST_RUNTIME "" CACHE PATH "Preserved original application and SDK")
get_filename_component(ORBITER_TEST_RUNTIME "${ORBITER_TEST_RUNTIME}" ABSOLUTE)
# Reuse the accepted read-only observer and its original public SDK fields.
add_library(ProductionCockpitDriver SHARED ../StockVessels/Driver.cpp)
target_compile_features(ProductionCockpitDriver PRIVATE cxx_std_17)
target_compile_definitions(ProductionCockpitDriver PRIVATE NOMINMAX)
target_include_directories(ProductionCockpitDriver PRIVATE
  "${ORBITER_TEST_RUNTIME}/Orbitersdk/include" ../StockVessels ..)
target_link_libraries(ProductionCockpitDriver PRIVATE
  "${ORBITER_TEST_RUNTIME}/Orbitersdk/lib/Orbiter.lib"
  "${ORBITER_TEST_RUNTIME}/Orbitersdk/lib/Orbitersdk.lib")
set_target_properties(ProductionCockpitDriver PROPERTIES
  RUNTIME_OUTPUT_DIRECTORY "${ORBITER_TEST_RUNTIME}/Modules/Plugin")
