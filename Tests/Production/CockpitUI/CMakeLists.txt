cmake_minimum_required(VERSION 3.24)
project(ProductionCockpitUIObservation LANGUAGES CXX)
if(NOT WIN32 OR NOT MSVC)
  message(FATAL_ERROR "The reference driver requires native Windows/MSVC")
endif()
set(ORBITER_TEST_RUNTIME "" CACHE PATH "Frozen source-built application/SDK")
get_filename_component(ORBITER_TEST_RUNTIME "${ORBITER_TEST_RUNTIME}" ABSOLUTE)
add_library(ProductionCockpitDriver SHARED Driver.cpp)
target_compile_features(ProductionCockpitDriver PRIVATE cxx_std_17)
target_compile_definitions(ProductionCockpitDriver PRIVATE NOMINMAX)
target_include_directories(ProductionCockpitDriver PRIVATE "${ORBITER_TEST_RUNTIME}/Orbitersdk/include" ..)
target_link_libraries(ProductionCockpitDriver PRIVATE
  "${ORBITER_TEST_RUNTIME}/Orbitersdk/lib/Orbiter.lib"
  "${ORBITER_TEST_RUNTIME}/Orbitersdk/lib/Orbitersdk.lib")
set_target_properties(ProductionCockpitDriver PROPERTIES RUNTIME_OUTPUT_DIRECTORY "${ORBITER_TEST_RUNTIME}/Modules/Plugin")

# Read-only inspection uses the exact original ImGui layout. Implementation is
# linked from the preserved SDK, which imports the application's shared context.
include(FetchContent)
FetchContent_Declare(ui_headers
  URL "https://codeload.github.com/ocornut/imgui/zip/3912b3d9a9c1b3f17431aebafd86d2f40ee6e59c"
  URL_HASH SHA256=943c3c8f6ef87c2616ff5545d4c50d941f29f20d23d783a8ff2f46c8a3bcfdf6
  DOWNLOAD_EXTRACT_TIMESTAMP TRUE SOURCE_SUBDIR no-build)
FetchContent_MakeAvailable(ui_headers)
target_include_directories(ProductionCockpitDriver PRIVATE "${ui_headers_SOURCE_DIR}")
target_compile_definitions(ProductionCockpitDriver PRIVATE
  "IMGUI_USER_CONFIG=\"${CMAKE_CURRENT_SOURCE_DIR}/../../../Extern/imgui/imconfig.h\"")
