cmake_minimum_required(VERSION 3.24)
project(ProductionRendererSurfaceProbe LANGUAGES CXX)
if(WIN32)
  message(FATAL_ERROR "This probe exercises the native Linux renderer adapter")
endif()
find_package(OpenGL REQUIRED)
set(ORBITER_ENGINE_BUILD "" CACHE PATH "Matching production engine build")
get_filename_component(ORBITER_ENGINE_BUILD "${ORBITER_ENGINE_BUILD}" ABSOLUTE)
get_filename_component(ORBITER_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../../../.." ABSOLUTE)
add_library(native_engine SHARED IMPORTED)
set_target_properties(native_engine PROPERTIES IMPORTED_LOCATION "${ORBITER_ENGINE_BUILD}/liborbiter_production_vessels.so")
add_library(native_boundary SHARED IMPORTED)
set_target_properties(native_boundary PROPERTIES IMPORTED_LOCATION "${ORBITER_ENGINE_BUILD}/liborbiter_production_boundary.so")
add_executable(renderer-probe Probe.cpp)
target_compile_features(renderer-probe PRIVATE cxx_std_17)
target_compile_definitions(renderer-probe PRIVATE ORBITER_PRODUCTION_SHARED ORBITER_NATIVE_BUILD_CONFIGURATION="${CMAKE_BUILD_TYPE}")
target_include_directories(renderer-probe PRIVATE "${ORBITER_ROOT}" "${ORBITER_ROOT}/Src/Orbiter" "${ORBITER_ROOT}/Orbitersdk/include" "${ORBITER_ENGINE_BUILD}/native-sdk")
target_link_libraries(renderer-probe PRIVATE native_engine native_boundary OpenGL::GL)
add_executable(cockpit-sdk-layout ../SdkLayout.Test.cpp)
target_compile_features(cockpit-sdk-layout PRIVATE cxx_std_17)
target_include_directories(cockpit-sdk-layout PRIVATE "${ORBITER_ROOT}/Orbitersdk/include")
add_executable(instrument-declarations ../InstrumentDeclarations.Test.cpp)
target_compile_features(instrument-declarations PRIVATE cxx_std_17)
target_include_directories(instrument-declarations PRIVATE "${ORBITER_ROOT}/Src/Orbiter" "${ORBITER_ROOT}/Orbitersdk/include")
add_executable(mfd-orbit-geometry ../OrbitGeometry.Test.cpp)
target_compile_features(mfd-orbit-geometry PRIVATE cxx_std_17)
target_include_directories(mfd-orbit-geometry PRIVATE "${ORBITER_ROOT}/Src/Orbiter" "${ORBITER_ROOT}/Orbitersdk/include")
target_link_libraries(mfd-orbit-geometry PRIVATE native_boundary)
# Compile the actual ten stock modes. Object compilation is a portability gate;
# no native Pane/instrument lifecycle is claimed until the runtime is linked.
add_library(stock-instrument-objects OBJECT ../../../../Src/Orbiter/Mfd.cpp ../../../../Src/Orbiter/VectorMap.cpp
    ../../../../Src/Orbiter/MfdOrbit.cpp ../../../../Src/Orbiter/MfdSurface.cpp
    ../../../../Src/Orbiter/MfdMap.cpp ../../../../Src/Orbiter/MfdHsi.cpp
    ../../../../Src/Orbiter/MfdLanding.cpp ../../../../Src/Orbiter/MfdDocking.cpp
    ../../../../Src/Orbiter/MfdAlign.cpp ../../../../Src/Orbiter/MfdSync.cpp
    ../../../../Src/Orbiter/MfdTransfer.cpp ../../../../Src/Orbiter/MfdComms.cpp)
target_compile_features(stock-instrument-objects PRIVATE cxx_std_17)
target_include_directories(stock-instrument-objects PRIVATE "${ORBITER_ROOT}/Src/Orbiter" "${ORBITER_ROOT}/Orbitersdk/include")
