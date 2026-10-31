if(NOT TARGET orbiter_production_boundary)
    add_subdirectory("${CMAKE_CURRENT_SOURCE_DIR}/../../../Src/Orbiter/Production" production-boundary)
endif()
add_executable(production_boundary_test Boundary.Test.cpp)
target_link_libraries(production_boundary_test PRIVATE orbiter_production_boundary)
# Windows locates shared dependencies beside the executable, not via an RPATH.
add_custom_command(TARGET production_boundary_test POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_if_different $<TARGET_FILE:orbiter_production_boundary>
        $<TARGET_FILE_DIR:production_boundary_test>)
add_test(NAME Production.SessionBoundary COMMAND production_boundary_test session)
add_test(NAME Production.ResourceBoundary COMMAND production_boundary_test resources "${CMAKE_CURRENT_BINARY_DIR}")
add_test(NAME Production.MeshBoundary COMMAND production_boundary_test meshes "${CMAKE_CURRENT_SOURCE_DIR}/../../../Meshes")
add_test(NAME Production.BodyBoundary COMMAND production_boundary_test bodies "${CMAKE_CURRENT_BINARY_DIR}")
set_tests_properties(Production.SessionBoundary Production.ResourceBoundary Production.MeshBoundary Production.BodyBoundary
    PROPERTIES TIMEOUT 30)
