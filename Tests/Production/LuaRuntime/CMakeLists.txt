cmake_minimum_required(VERSION 3.24)
project(ProductionLuaObservation LANGUAGES CXX)
if(NOT WIN32 OR NOT MSVC)
  message(FATAL_ERROR "The reference driver requires native Windows/MSVC")
endif()
set(ORBITER_TEST_RUNTIME "" CACHE PATH "Frozen source-built application/SDK")
get_filename_component(ORBITER_TEST_RUNTIME "${ORBITER_TEST_RUNTIME}" ABSOLUTE)
# GetSurfParam is an inline internal accessor. Its layout must be taken from
# the exact archived application running the observer, for each configuration.
file(READ "${ORBITER_TEST_RUNTIME}/test-runtime.json" _runtime_manifest)
string(JSON _source_commit GET "${_runtime_manifest}" source_commit)
if(NOT _source_commit STREQUAL "f725194209634f7fd5d1d44d426cfa9b5e303e37")
    message(FATAL_ERROR "The Lua original surface diagnostic requires the pinned cockpit runtime")
endif()
find_package(Git REQUIRED)
set(_frozen "${CMAKE_CURRENT_BINARY_DIR}/original-headers")
file(MAKE_DIRECTORY "${_frozen}")
execute_process(COMMAND "${GIT_EXECUTABLE}" -C "${CMAKE_CURRENT_LIST_DIR}/../../.." archive
    --output "${_frozen}/headers.tar" "${_source_commit}" -- "Src/Orbiter"
    COMMAND_ERROR_IS_FATAL ANY)
file(ARCHIVE_EXTRACT INPUT "${_frozen}/headers.tar" DESTINATION "${_frozen}")
add_library(ProductionCockpitDriver SHARED Driver.cpp)
target_include_directories(ProductionCockpitDriver PRIVATE "${_frozen}/Src/Orbiter")
target_compile_features(ProductionCockpitDriver PRIVATE cxx_std_17)
target_compile_definitions(ProductionCockpitDriver PRIVATE NOMINMAX)
target_include_directories(ProductionCockpitDriver PRIVATE "${ORBITER_TEST_RUNTIME}/Orbitersdk/include" ..)
target_link_libraries(ProductionCockpitDriver PRIVATE
  "${ORBITER_TEST_RUNTIME}/Orbitersdk/lib/Orbiter.lib"
  "${ORBITER_TEST_RUNTIME}/Orbitersdk/lib/Orbitersdk.lib")
set_target_properties(ProductionCockpitDriver PROPERTIES RUNTIME_OUTPUT_DIRECTORY "${ORBITER_TEST_RUNTIME}/Modules/Plugin")
