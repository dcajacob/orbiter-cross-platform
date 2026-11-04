cmake_minimum_required(VERSION 3.24)
project(RepairedOriginalWindowsModules LANGUAGES C CXX RC)
if(NOT WIN32 OR NOT MSVC)
  message(FATAL_ERROR "This explicit original-runtime variant requires native Windows/MSVC")
endif()
foreach(name ORBITER_TEST_RUNTIME ORBITER_REPAIRED_SOURCES ORBITER_REPAIRED_OBSERVER)
  if(NOT IS_ABSOLUTE "${${name}}")
    message(FATAL_ERROR "${name} must name the fresh absolute build input")
  endif()
endforeach()
get_filename_component(repo "${CMAKE_CURRENT_SOURCE_DIR}/../../.." ABSOLUTE)
set(atlantis "${ORBITER_REPAIRED_SOURCES}/Src/Vessel/Atlantis")
set(dragonfly "${ORBITER_REPAIRED_SOURCES}/Src/Vessel/Dragonfly")
set(sdk "${ORBITER_TEST_RUNTIME}/Orbitersdk")
function(module_defaults target)
  target_compile_features(${target} PRIVATE cxx_std_17)
  target_compile_options(${target} PRIVATE /Zi)
  target_compile_definitions(${target} PRIVATE NOMINMAX)
  target_link_options(${target} PRIVATE /DEBUG)
  target_include_directories(${target} PRIVATE "${sdk}/include")
  target_link_libraries(${target} PRIVATE "${sdk}/lib/Orbiter.lib" "${sdk}/lib/Orbitersdk.lib")
  set_target_properties(${target} PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${ORBITER_TEST_RUNTIME}/Modules"
    PDB_OUTPUT_DIRECTORY "${ORBITER_TEST_RUNTIME}/Modules")
endfunction()
# Build the unchanged SRB solely to obtain its genuine MSVC import library.
# Its DLL is retained as build evidence and must never replace the original SRB.
add_library(RepairedSrbImport SHARED "${atlantis}/Atlantis_SRB/Atlantis_SRB.cpp")
module_defaults(RepairedSrbImport)
target_include_directories(RepairedSrbImport PRIVATE "${atlantis}/Atlantis")
set_target_properties(RepairedSrbImport PROPERTIES OUTPUT_NAME Atlantis_SRB
  RUNTIME_OUTPUT_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/import-only"
  PDB_OUTPUT_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/import-only"
  ARCHIVE_OUTPUT_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/import-only")
add_library(Atlantis_Tank SHARED "${atlantis}/Atlantis_Tank/Atlantis_Tank.cpp")
module_defaults(Atlantis_Tank)
target_include_directories(Atlantis_Tank PRIVATE "${atlantis}/Atlantis")
target_link_libraries(Atlantis_Tank PRIVATE RepairedSrbImport)
add_library(Dragonfly SHARED
  "${dragonfly}/Dragonfly.cpp" "${dragonfly}/Internal.cpp"
  "${dragonfly}/instruments.cpp" "${dragonfly}/Matrix.cpp"
  "${dragonfly}/quaternion.cpp" "${dragonfly}/vectors.cpp"
  "${dragonfly}/Hsystems.cpp" "${dragonfly}/Thermal.cpp"
  "${dragonfly}/Esystems.cpp" "${dragonfly}/panel.rc")
module_defaults(Dragonfly)
target_link_libraries(Dragonfly PRIVATE opengl32 glu32 gdi32 user32)
add_library(ProductionCockpitDriver SHARED "${ORBITER_REPAIRED_OBSERVER}")
module_defaults(ProductionCockpitDriver)
target_compile_definitions(ProductionCockpitDriver PRIVATE NOMINMAX)
target_include_directories(ProductionCockpitDriver PRIVATE
  "${repo}/Tests/Production/RemainingStock" "${repo}/Tests/Production")
set_target_properties(ProductionCockpitDriver PROPERTIES
  RUNTIME_OUTPUT_DIRECTORY "${ORBITER_TEST_RUNTIME}/Modules/Plugin"
  PDB_OUTPUT_DIRECTORY "${ORBITER_TEST_RUNTIME}/Modules/Plugin")
add_subdirectory("${repo}/OVP/OGLClient" "${CMAKE_CURRENT_BINARY_DIR}/client")
target_compile_options(OGLClient PRIVATE
  "$<$<COMPILE_LANGUAGE:CXX>:/FI${CMAKE_CURRENT_SOURCE_DIR}/PreservedSdkTypes.h>")
