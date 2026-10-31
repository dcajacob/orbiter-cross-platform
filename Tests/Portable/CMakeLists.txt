cmake_minimum_required(VERSION 3.19)
project(OrbiterPortableCore LANGUAGES CXX)
enable_testing()
add_executable(vecmat_portability Vecmat.Portability.cpp ../../Src/Orbiter/Vecmat.cpp)
target_include_directories(vecmat_portability PRIVATE ../../Src/Orbiter)
target_compile_features(vecmat_portability PRIVATE cxx_std_17)
add_test(NAME Vecmat.Portability COMMAND vecmat_portability)

# Reuse the upstream suite and its pinned test dependency, without the Windows app.
option(ORBITER_PORTABLE_COLLISION_TESTS "Build existing collision regression suite" OFF)
if(ORBITER_PORTABLE_COLLISION_TESTS)
    include(FetchContent)
    FetchContent_Declare(Catch2
        GIT_REPOSITORY https://github.com/catchorg/Catch2.git
        GIT_TAG b9853b4b356b83bb580c746c3a1f11101f9af54f) # v3.0.0-preview3
    FetchContent_MakeAvailable(Catch2)
    if(CMAKE_SYSTEM_NAME STREQUAL "Linux")
        # This upstream-pinned preview predates glibc's dynamic MINSIGSTKSZ.
        # Disable only Catch2's optional crash handler, not test assertions.
        target_compile_definitions(Catch2 PUBLIC CATCH_CONFIG_NO_POSIX_SIGNALS)
    endif()
    if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
        # The pinned preview relies on a transitive cstdint include that newer
        # standard libraries no longer provide. Keep this workaround test-only.
        target_compile_options(Catch2 PRIVATE -include cstdint)
    endif()
    add_executable(collision_portability ../Collision.CollisionCore.cpp
        ../../Src/Orbiter/CollisionCore.cpp ../../Src/Orbiter/Vecmat.cpp)
    target_include_directories(collision_portability PRIVATE
        ../../Src/Orbiter ../../Orbitersdk/include)
    target_compile_features(collision_portability PRIVATE cxx_std_17)
    target_link_libraries(collision_portability PRIVATE Catch2::Catch2WithMain)
    add_test(NAME Collision.Portability COMMAND collision_portability)
    set_tests_properties(Collision.Portability PROPERTIES TIMEOUT 30)
endif()

add_executable(vector_layout Vector.Layout.cpp)
target_include_directories(vector_layout PRIVATE ../../Orbitersdk/include)
target_compile_features(vector_layout PRIVATE cxx_std_17)
add_test(NAME Vector.Layout COMMAND vector_layout)

add_executable(physics_trace_test PhysicsTrace.Test.cpp)
target_include_directories(physics_trace_test PRIVATE ../../Src/Orbiter)
target_compile_features(physics_trace_test PRIVATE cxx_std_17)
add_test(NAME PhysicsTrace.IO COMMAND physics_trace_test "${CMAKE_CURRENT_BINARY_DIR}")

find_package(Python3 3.8 REQUIRED COMPONENTS Interpreter)
add_test(NAME PhysicsTrace.Validation
    COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/test_trace_tools.py")
set_tests_properties(PhysicsTrace.IO PhysicsTrace.Validation PROPERTIES TIMEOUT 30)
