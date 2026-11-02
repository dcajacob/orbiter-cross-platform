cmake_minimum_required(VERSION 3.24)
project(ProductionBehaviorDriverIteration LANGUAGES CXX)
if(NOT WIN32 OR NOT MSVC)
  message(FATAL_ERROR "Production behavior iteration requires native Windows MSVC")
endif()
set(ORBITER_TEST_RUNTIME "" CACHE PATH "Verified source-built application and SDK")
get_filename_component(ORBITER_TEST_RUNTIME "${ORBITER_TEST_RUNTIME}" ABSOLUTE)
foreach(name Orbiter.exe Orbitersdk/lib/Orbiter.lib Orbitersdk/lib/Orbitersdk.lib test-runtime.json)
  if(NOT EXISTS "${ORBITER_TEST_RUNTIME}/${name}")
    message(FATAL_ERROR "Incomplete source-built runtime: ${name}")
  endif()
endforeach()
add_library(ProductionBehaviorDriver SHARED ../BehaviorDriver.cpp)
target_compile_features(ProductionBehaviorDriver PRIVATE cxx_std_17)
target_include_directories(ProductionBehaviorDriver PRIVATE "${ORBITER_TEST_RUNTIME}/Orbitersdk/include")
target_link_libraries(ProductionBehaviorDriver PRIVATE
  "${ORBITER_TEST_RUNTIME}/Orbitersdk/lib/Orbiter.lib"
  "${ORBITER_TEST_RUNTIME}/Orbitersdk/lib/Orbitersdk.lib")
set_target_properties(ProductionBehaviorDriver PROPERTIES
  RUNTIME_OUTPUT_DIRECTORY "${ORBITER_TEST_RUNTIME}/Modules/Plugin")
add_library(ProductionGroundMathDriver SHARED ../GroundFlight/MathObserve.cpp)
target_compile_features(ProductionGroundMathDriver PRIVATE cxx_std_17)
target_compile_definitions(ProductionGroundMathDriver PRIVATE NOMINMAX)
target_include_directories(ProductionGroundMathDriver PRIVATE "${ORBITER_TEST_RUNTIME}/Orbitersdk/include")
target_link_libraries(ProductionGroundMathDriver PRIVATE
  "${ORBITER_TEST_RUNTIME}/Orbitersdk/lib/Orbiter.lib"
  "${ORBITER_TEST_RUNTIME}/Orbitersdk/lib/Orbitersdk.lib")
set_target_properties(ProductionGroundMathDriver PROPERTIES
  RUNTIME_OUTPUT_DIRECTORY "${ORBITER_TEST_RUNTIME}/Modules/Plugin")
set(ORBITER_FROZEN_SOURCE "" CACHE PATH "Matching verified frozen source for internal read-only diagnostics")
if(ORBITER_FROZEN_SOURCE)
  if(NOT EXISTS "${ORBITER_FROZEN_SOURCE}/Src/Orbiter/Vessel.h")
    message(FATAL_ERROR "Internal contact observation requires the matching frozen headers")
  endif()
  target_compile_definitions(ProductionGroundMathDriver PRIVATE ORBITER_INTERNAL_CONTACT_OBSERVATION)
  target_include_directories(ProductionGroundMathDriver PRIVATE "${ORBITER_FROZEN_SOURCE}/Src/Orbiter" "$ENV{DXSDK_DIR}/Include")
endif()
add_library(ProductionGroundMathDispatch SHARED ../GroundFlight/MathDispatch.cpp)
target_compile_features(ProductionGroundMathDispatch PRIVATE cxx_std_17)
target_compile_definitions(ProductionGroundMathDispatch PRIVATE NOMINMAX)
target_include_directories(ProductionGroundMathDispatch PRIVATE "${ORBITER_TEST_RUNTIME}/Orbitersdk/include")
target_link_libraries(ProductionGroundMathDispatch PRIVATE
  "${ORBITER_TEST_RUNTIME}/Orbitersdk/lib/Orbiter.lib"
  "${ORBITER_TEST_RUNTIME}/Orbitersdk/lib/Orbitersdk.lib")
set_target_properties(ProductionGroundMathDispatch PROPERTIES
  RUNTIME_OUTPUT_DIRECTORY "${ORBITER_TEST_RUNTIME}/Modules/Plugin")
