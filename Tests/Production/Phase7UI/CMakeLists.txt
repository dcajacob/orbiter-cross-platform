cmake_minimum_required(VERSION 3.24)
project(WindowsPhase7 LANGUAGES CXX)
if(NOT WIN32 OR NOT MSVC)
  message(FATAL_ERROR "This fixture requires the Windows Orbiter application and MSVC")
endif()
add_library(Phase7Driver SHARED Driver.cpp)
target_compile_features(Phase7Driver PRIVATE cxx_std_17)
target_compile_definitions(Phase7Driver PRIVATE NOMINMAX
  "IMGUI_USER_CONFIG=\"${ORBITER_SOURCE_ROOT}/Extern/imgui/imconfig.h\"")
target_include_directories(Phase7Driver PRIVATE
  "${ORBITER_TEST_RUNTIME}/Orbitersdk/include" "${ORBITER_TEST_RUNTIME}/Orbitersdk/XRSound"
  "${ORBITER_SOURCE_ROOT}/Tests/Production" "${ORBITER_SOURCE_ROOT}/Src/Plugin")
target_link_libraries(Phase7Driver PRIVATE
  "${ORBITER_TEST_RUNTIME}/Orbitersdk/lib/Orbiter.lib"
  "${ORBITER_TEST_RUNTIME}/Orbitersdk/lib/Orbitersdk.lib"
  "${ORBITER_TEST_RUNTIME}/Orbitersdk/XRSound/XRSound.lib")
set_target_properties(Phase7Driver PROPERTIES RUNTIME_OUTPUT_DIRECTORY "${ORBITER_TEST_RUNTIME}/Modules/Plugin")
include(FetchContent)
FetchContent_Declare(ui_headers
  URL "https://codeload.github.com/ocornut/imgui/zip/3912b3d9a9c1b3f17431aebafd86d2f40ee6e59c"
  URL_HASH SHA256=943c3c8f6ef87c2616ff5545d4c50d941f29f20d23d783a8ff2f46c8a3bcfdf6
  DOWNLOAD_EXTRACT_TIMESTAMP TRUE SOURCE_SUBDIR no-build)
FetchContent_MakeAvailable(ui_headers)
target_include_directories(Phase7Driver PRIVATE "${ui_headers_SOURCE_DIR}")
