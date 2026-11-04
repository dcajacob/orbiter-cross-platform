cmake_minimum_required(VERSION 3.24)
project(ProductionWindowsSurfaceDC LANGUAGES CXX)
if(NOT WIN32 OR NOT MSVC)
  message(FATAL_ERROR "The real GDI surface test requires native Windows/MSVC")
endif()
set(ORBITER_TEST_RUNTIME "" CACHE PATH "Same-build production application and SDK")
get_filename_component(ORBITER_TEST_RUNTIME "${ORBITER_TEST_RUNTIME}" ABSOLUTE)
add_library(ProductionSurfaceDCDriver SHARED Driver.cpp)
target_compile_features(ProductionSurfaceDCDriver PRIVATE cxx_std_17)
target_compile_definitions(ProductionSurfaceDCDriver PRIVATE NOMINMAX WIN32_LEAN_AND_MEAN)
target_include_directories(ProductionSurfaceDCDriver PRIVATE "${ORBITER_TEST_RUNTIME}/Orbitersdk/include")
target_link_libraries(ProductionSurfaceDCDriver PRIVATE opengl32 gdi32 user32
  "${ORBITER_TEST_RUNTIME}/Orbitersdk/lib/Orbiter.lib"
  "${ORBITER_TEST_RUNTIME}/Orbitersdk/lib/Orbitersdk.lib")
set_target_properties(ProductionSurfaceDCDriver PROPERTIES
  RUNTIME_OUTPUT_DIRECTORY "${ORBITER_TEST_RUNTIME}/Modules/Plugin")
