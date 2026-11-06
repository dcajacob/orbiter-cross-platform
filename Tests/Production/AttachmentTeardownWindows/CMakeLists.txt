cmake_minimum_required(VERSION 3.24)
project(CurrentWindowsPausedAttachmentLifetime LANGUAGES CXX)
if(NOT WIN32 OR NOT MSVC)
  message(FATAL_ERROR "This current application regression requires Windows/MSVC")
endif()
set(ORBITER_TEST_RUNTIME "" CACHE PATH "Exact current application/SDK")
set(ORBITER_SOURCE_ROOT "" CACHE PATH "Exact owning application source")
add_library(ProductionAttachmentTeardownDriver SHARED Driver.cpp)
target_compile_features(ProductionAttachmentTeardownDriver PRIVATE cxx_std_17)
target_compile_definitions(ProductionAttachmentTeardownDriver PRIVATE NOMINMAX WIN32_LEAN_AND_MEAN)
target_include_directories(ProductionAttachmentTeardownDriver PRIVATE
  "${ORBITER_TEST_RUNTIME}/Orbitersdk/include" "${ORBITER_SOURCE_ROOT}/Tests/Production")
target_link_libraries(ProductionAttachmentTeardownDriver PRIVATE user32
  "${ORBITER_TEST_RUNTIME}/Orbitersdk/lib/Orbiter.lib"
  "${ORBITER_TEST_RUNTIME}/Orbitersdk/lib/Orbitersdk.lib")
set_target_properties(ProductionAttachmentTeardownDriver PROPERTIES
  RUNTIME_OUTPUT_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/bin")
