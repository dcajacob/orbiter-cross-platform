cmake_minimum_required(VERSION 3.19)
project(OrbiterArchiveReference LANGUAGES C CXX)
if(NOT WIN32)
    message(FATAL_ERROR "Original production archive capture requires native Windows")
endif()
include(FetchContent)
set(CMAKE_POLICY_VERSION_MINIMUM 3.5)
set(SKIP_INSTALL_ALL ON)
FetchContent_Declare(zlib
    GIT_REPOSITORY https://github.com/madler/zlib.git
    GIT_TAG cacf7f1d4e3d44d871b605da3b647f07d718623f) # Original application zlib 1.2.11
FetchContent_MakeAvailable(zlib)
add_executable(production_archive_observer Observe.cpp ../../../Src/Orbiter/ZTreeMgr.cpp)
target_compile_features(production_archive_observer PRIVATE cxx_std_17)
target_compile_definitions(production_archive_observer PRIVATE NOGRAPHICS DIRECTINPUT_VERSION=0x0800 NOMINMAX)
target_include_directories(production_archive_observer PRIVATE ../../../Src/Orbiter ../../../Orbitersdk/include
    "${zlib_SOURCE_DIR}" "${zlib_BINARY_DIR}")
target_link_libraries(production_archive_observer PRIVATE zlibstatic)
