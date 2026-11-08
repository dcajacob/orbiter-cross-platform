cmake_minimum_required(VERSION 3.24)
project(OrbiterExistingNativeCoreUnits LANGUAGES CXX)
include(CTest)
set(ORBITER_ENGINE_BUILD "" CACHE PATH "Explicit source-bound native SDK build")
set(ORBITER_ENGINE_SOURCE "" CACHE PATH "Owning source for that SDK")
set(ORBITER_CATCH_SOURCE "" CACHE PATH "Offline original pinned Catch2 checkout")
if(NOT CMAKE_SYSTEM_NAME STREQUAL "Linux")
    message(FATAL_ERROR "Windows runs the existing application test targets")
endif()
foreach(required IN ITEMS
    "${ORBITER_ENGINE_BUILD}/liborbiter_production_boundary.so"
    "${ORBITER_ENGINE_BUILD}/liborbiter_production_vessels.so"
    "${ORBITER_ENGINE_BUILD}/NativeModules/Plugin/LuaInterpreter.so"
    "${ORBITER_ENGINE_BUILD}/native-lua/liblua.so"
    "${ORBITER_ENGINE_SOURCE}/Tests/Lua.Interpreter.cpp"
    "${ORBITER_ENGINE_SOURCE}/Tests/Collision.CollisionCore.cpp"
    "${ORBITER_CATCH_SOURCE}/CMakeLists.txt")
    if(NOT EXISTS "${required}")
        message(FATAL_ERROR "Required retained SDK, upstream test or offline Catch input missing: ${required}")
    endif()
endforeach()
file(READ "${ORBITER_ENGINE_SOURCE}/Tests/Production/dependencies.lock.json" dependencies)
string(JSON catch_commit GET "${dependencies}" dependencies Catch2 commit)
execute_process(COMMAND git -C "${ORBITER_CATCH_SOURCE}" rev-parse HEAD
    RESULT_VARIABLE git_result OUTPUT_VARIABLE actual_catch OUTPUT_STRIP_TRAILING_WHITESPACE)
if(NOT git_result EQUAL 0 OR NOT actual_catch STREQUAL catch_commit)
    message(FATAL_ERROR "Offline Catch checkout differs from the existing dependency lock")
endif()
execute_process(COMMAND git -C "${ORBITER_CATCH_SOURCE}" diff --exit-code HEAD
    RESULT_VARIABLE dirty_catch OUTPUT_QUIET)
if(NOT dirty_catch EQUAL 0)
    message(FATAL_ERROR "Offline Catch tracked source differs from its pinned commit")
endif()
add_subdirectory("${ORBITER_CATCH_SOURCE}" catch2 EXCLUDE_FROM_ALL)
target_compile_definitions(Catch2 PUBLIC CATCH_CONFIG_NO_POSIX_SIGNALS)
target_compile_options(Catch2 PRIVATE -include cstdint)
foreach(name IN ITEMS boundary vessels lua interpreter)
    add_library(unit_${name} SHARED IMPORTED)
endforeach()
set_target_properties(unit_boundary PROPERTIES IMPORTED_LOCATION "${ORBITER_ENGINE_BUILD}/liborbiter_production_boundary.so")
set_target_properties(unit_vessels PROPERTIES IMPORTED_LOCATION "${ORBITER_ENGINE_BUILD}/liborbiter_production_vessels.so")
set_target_properties(unit_lua PROPERTIES IMPORTED_LOCATION "${ORBITER_ENGINE_BUILD}/native-lua/liblua.so")
set_target_properties(unit_interpreter PROPERTIES IMPORTED_LOCATION "${ORBITER_ENGINE_BUILD}/NativeModules/Plugin/LuaInterpreter.so")
add_executable(existing_lua_unit NativeLuaUnitMain.cpp "${ORBITER_ENGINE_SOURCE}/Tests/Lua.Interpreter.cpp")
target_include_directories(existing_lua_unit PRIVATE
    "${ORBITER_ENGINE_SOURCE}/Src/Orbiter" "${ORBITER_ENGINE_SOURCE}/Orbitersdk/include"
    "${ORBITER_ENGINE_SOURCE}/Src/Module/LuaScript/LuaInterpreter"
    "${ORBITER_ENGINE_BUILD}/native-sdk" "${ORBITER_ENGINE_BUILD}/native-lua/sdk/include")
target_compile_features(existing_lua_unit PRIVATE cxx_std_17)
target_link_libraries(existing_lua_unit PRIVATE Catch2::Catch2 unit_interpreter unit_lua unit_vessels unit_boundary)
set(fixture "${CMAKE_CURRENT_BINARY_DIR}/assets")
file(MAKE_DIRECTORY "${fixture}/Script")
foreach(script IN ITEMS oapi_init.lua strict.lua)
    configure_file("${ORBITER_ENGINE_SOURCE}/Script/${script}" "${fixture}/Script/${script}" COPYONLY)
endforeach()
add_test(NAME Lua.Interpreter COMMAND existing_lua_unit "${fixture}")
add_executable(existing_collision_unit "${ORBITER_ENGINE_SOURCE}/Tests/Collision.CollisionCore.cpp"
    "${ORBITER_ENGINE_SOURCE}/Src/Orbiter/CollisionCore.cpp")
target_include_directories(existing_collision_unit PRIVATE
    "${ORBITER_ENGINE_SOURCE}/Src/Orbiter" "${ORBITER_ENGINE_SOURCE}/Orbitersdk/include")
target_compile_features(existing_collision_unit PRIVATE cxx_std_17)
target_link_libraries(existing_collision_unit PRIVATE Catch2::Catch2WithMain unit_boundary)
add_test(NAME Collision.CollisionCore COMMAND existing_collision_unit)
set_tests_properties(Lua.Interpreter Collision.CollisionCore PROPERTIES TIMEOUT 30)
