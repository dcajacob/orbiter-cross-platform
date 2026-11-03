# Copyright (c) Martin Schweiger
# Licensed under the MIT License
cmake_minimum_required(VERSION 3.24)
project(OrbiterNativeLua LANGUAGES C CXX)
if(NOT CMAKE_SYSTEM_NAME STREQUAL "Linux")
    message(FATAL_ERROR "Use the original application build for Windows Lua modules")
endif()
get_filename_component(ORBITER_SOURCE_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../../../.." ABSOLUTE)
include(FetchContent)
set(ORBITER_NATIVE_LUA_ARCHIVE "" CACHE FILEPATH "Offline archive for the pinned original Lua 5.1 revision")
file(READ "${ORBITER_SOURCE_ROOT}/Tests/Production/dependencies.lock.json" dependencies)
string(JSON lua_commit GET "${dependencies}" dependencies lua commit)
set(lua_url "https://codeload.github.com/lua/lua/zip/${lua_commit}")
if(ORBITER_NATIVE_LUA_ARCHIVE)
    set(lua_url "${ORBITER_NATIVE_LUA_ARCHIVE}")
endif()
FetchContent_Declare(original_lua_source URL "${lua_url}"
    URL_HASH SHA256=18fdf2dd3756c0941d227c0eae0cf1f972b350d0ca7fce0052db9920eb06280b
    DOWNLOAD_EXTRACT_TIMESTAMP TRUE SOURCE_SUBDIR no-build)
FetchContent_MakeAvailable(original_lua_source)
file(SHA256 "${original_lua_source_SOURCE_DIR}/lua.h" header_hash)
string(JSON expected_header GET "${dependencies}" dependencies lua notice_sha256)
if(NOT header_hash STREQUAL expected_header)
    message(FATAL_ERROR "Lua source header differs from the original dependency lock")
endif()
# Use the same library sources and exclusions as the Windows application.
set(FETCHCONTENT_SOURCE_DIR_LUA "${original_lua_source_SOURCE_DIR}")
set(ORBITER_BINARY_ROOT_DIR "${PROJECT_BINARY_DIR}")
set(ORBITER_INSTALL_ROOT_DIR .)
set(ORBITER_INSTALL_SDK_DIR Orbitersdk)
add_subdirectory("${ORBITER_SOURCE_ROOT}/Extern/Lua" lua-build)
foreach(target lua lua-exe)
    target_compile_definitions(${target} PRIVATE LUA_USE_POSIX LUA_USE_DLOPEN)
    target_link_libraries(${target} PRIVATE ${CMAKE_DL_LIBS})
endforeach()
file(GLOB headers "${original_lua_source_SOURCE_DIR}/*.h")
file(COPY ${headers} DESTINATION "${PROJECT_BINARY_DIR}/sdk/include/lua")
target_include_directories(lua INTERFACE "${PROJECT_BINARY_DIR}/sdk/include")

# The original documentation generator uses LuaFileSystem and Penlight.
# Keep this build tool separate from the simulator's Lua module search path.
add_library(native_doc_lfs MODULE "${ORBITER_SOURCE_ROOT}/Extern/luafilesystem/src/lfs.c")
target_link_libraries(native_doc_lfs PRIVATE lua)
set_target_properties(native_doc_lfs PROPERTIES PREFIX "" OUTPUT_NAME lfs
    LIBRARY_OUTPUT_DIRECTORY "${PROJECT_BINARY_DIR}/doc-tools")

find_package(Threads REQUIRED)
add_library(native_lua_inline_worker OBJECT
    ../LuaInterpreter/InterpreterExecution.cpp ../LuaInline/InlineEnvironment.cpp)
target_compile_features(native_lua_inline_worker PRIVATE cxx_std_17)
target_include_directories(native_lua_inline_worker PRIVATE
    "${CMAKE_CURRENT_SOURCE_DIR}/../LuaInterpreter" "${ORBITER_SOURCE_ROOT}/Orbitersdk/include")
target_link_libraries(native_lua_inline_worker PRIVATE lua Threads::Threads)
set_target_properties(native_lua_inline_worker PROPERTIES POSITION_INDEPENDENT_CODE ON)

add_library(native_lua_vessel_bindings OBJECT ../LuaInterpreter/lua_vessel_mtd.cpp)
target_compile_features(native_lua_vessel_bindings PRIVATE cxx_std_17)
target_include_directories(native_lua_vessel_bindings PRIVATE
    "${ORBITER_SOURCE_ROOT}/Orbitersdk/include" "${ORBITER_SOURCE_ROOT}/Src/Orbiter")
target_link_libraries(native_lua_vessel_bindings PRIVATE lua)
set_target_properties(native_lua_vessel_bindings PROPERTIES POSITION_INDEPENDENT_CODE ON)

add_library(native_lua_script_files STATIC ScriptFiles.cpp)
target_compile_features(native_lua_script_files PUBLIC cxx_std_17)
target_include_directories(native_lua_script_files PUBLIC "${CMAKE_CURRENT_SOURCE_DIR}" "${ORBITER_SOURCE_ROOT}/Src/Orbiter")
target_link_libraries(native_lua_script_files PUBLIC lua)
set_target_properties(native_lua_script_files PROPERTIES POSITION_INDEPENDENT_CODE ON)

add_library(native_dg_lua_bindings OBJECT "${ORBITER_SOURCE_ROOT}/Src/Vessel/DeltaGlider/DGLua.cpp")
target_compile_features(native_dg_lua_bindings PRIVATE cxx_std_17)
target_include_directories(native_dg_lua_bindings PRIVATE
    "${ORBITER_SOURCE_ROOT}/Orbitersdk/include" "${ORBITER_SOURCE_ROOT}/Src/Orbiter")
target_link_libraries(native_dg_lua_bindings PRIVATE lua)
set_target_properties(native_dg_lua_bindings PROPERTIES POSITION_INDEPENDENT_CODE ON)

include(CTest)
if(BUILD_TESTING)
    add_executable(interpreter_handoff_check "${ORBITER_SOURCE_ROOT}/Tests/Production/NativeLua/ExecutionHandoff.Test.cpp")
    target_compile_features(interpreter_handoff_check PRIVATE cxx_std_17)
    target_include_directories(interpreter_handoff_check PRIVATE
        "${CMAKE_CURRENT_SOURCE_DIR}/../LuaInterpreter" "${ORBITER_SOURCE_ROOT}/Orbitersdk/include")
    target_link_libraries(interpreter_handoff_check PRIVATE lua Threads::Threads)
    add_test(NAME native_lua_thread_handoff COMMAND interpreter_handoff_check)
    set_tests_properties(native_lua_thread_handoff PROPERTIES TIMEOUT 30)

    add_executable(lua_script_files_check "${ORBITER_SOURCE_ROOT}/Tests/Production/NativeLua/ScriptFiles.Test.cpp"
        "${ORBITER_SOURCE_ROOT}/Src/Orbiter/Production/ResourceResolver.cpp")
    target_link_libraries(lua_script_files_check PRIVATE native_lua_script_files)
    set(fixture "${PROJECT_BINARY_DIR}/script-file-test")
    file(MAKE_DIRECTORY "${fixture}/assets/Script/DG")
    configure_file("${ORBITER_SOURCE_ROOT}/Src/Vessel/DeltaGlider/Script/aap.lua" "${fixture}/assets/Script/DG/aap.lua" COPYONLY)
    configure_file("${ORBITER_SOURCE_ROOT}/Script/oapi_init.lua" "${fixture}/assets/Script/oapi_init.lua" COPYONLY)
    configure_file("${ORBITER_SOURCE_ROOT}/Script/strict.lua" "${fixture}/assets/Script/strict.lua" COPYONLY)
    file(WRITE "${fixture}/assets/Script/DG/returns.lua" "return 'first', 2\n")
    file(WRITE "${fixture}/user.lua" "user_script_loaded = true\n")
    add_test(NAME native_lua_stock_script_paths COMMAND lua_script_files_check "${fixture}/assets")
    set_tests_properties(native_lua_stock_script_paths PROPERTIES WORKING_DIRECTORY "${fixture}")

endif()
