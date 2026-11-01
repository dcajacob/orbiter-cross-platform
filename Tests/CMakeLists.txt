Include(FetchContent)
add_subdirectory(Production/Boundary)

# Test-only control/observation plugin; never installed as a stock module.
option(ORBITER_PRODUCTION_REFERENCE_CAPTURE "Build production Windows reference driver" OFF)
if(WIN32 AND ORBITER_PRODUCTION_REFERENCE_CAPTURE)
    # Observe the actual, still unmodified Pines source before porting it.
    add_executable(production_gravity_observer Production/Gravity/Observe.cpp
        "${PROJECT_SOURCE_DIR}/Src/Orbiter/PinesGrav.cpp")
    target_include_directories(production_gravity_observer PRIVATE $<TARGET_PROPERTY:Orbiter,INCLUDE_DIRECTORIES>)
    target_compile_definitions(production_gravity_observer PRIVATE NOGRAPHICS DIRECTINPUT_VERSION=0x0800)
    target_link_libraries(production_gravity_observer PRIVATE orbiter_production_boundary)
    set_target_properties(production_gravity_observer PROPERTIES
        OUTPUT_NAME production-gravity-observer RUNTIME_OUTPUT_DIRECTORY "${ORBITER_BINARY_ROOT_DIR}")
    orbiter_stage_core_runtime(production_gravity_observer)
    target_sources(${OrbiterTgt} PRIVATE Production/ApplicationObservation.cpp)
    target_include_directories(${OrbiterTgt} PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/Production")
    target_compile_definitions(${OrbiterTgt} PRIVATE ORBITER_PRODUCTION_OBSERVATION=1)
    add_library(ProductionReferenceDriver SHARED Production/ReferenceDriver.cpp)
    target_include_directories(ProductionReferenceDriver PRIVATE ${ORBITER_SOURCE_SDK_INCLUDE_DIR})
    target_link_libraries(ProductionReferenceDriver PRIVATE ${ORBITER_LIB} ${ORBITER_SDK_LIB})
    add_dependencies(ProductionReferenceDriver ${OrbiterTgt} Orbitersdk)
    set_target_properties(ProductionReferenceDriver PROPERTIES
        RUNTIME_OUTPUT_DIRECTORY "${ORBITER_BINARY_ROOT_DIR}/Modules/Plugin")
    add_library(ProductionBehaviorDriver SHARED Production/BehaviorDriver.cpp)
    target_include_directories(ProductionBehaviorDriver PRIVATE ${ORBITER_SOURCE_SDK_INCLUDE_DIR})
    target_link_libraries(ProductionBehaviorDriver PRIVATE ${ORBITER_LIB} ${ORBITER_SDK_LIB})
    add_dependencies(ProductionBehaviorDriver ${OrbiterTgt} Orbitersdk)
    set_target_properties(ProductionBehaviorDriver PROPERTIES
        RUNTIME_OUTPUT_DIRECTORY "${ORBITER_BINARY_ROOT_DIR}/Modules/Plugin")
endif()

# Only for pre-refactor Windows reference capture. Not part of the SDK or app
# installation, and never needed by the future native headless runner.
option(ORBITER_PORTABLE_REFERENCE_CAPTURE "Build stationary-primary reference fixture" OFF)
if(WIN32 AND ORBITER_PORTABLE_REFERENCE_CAPTURE)
    add_library(PortableFixedPrimary SHARED Portable/Windows/FixedPrimary.cpp)
    target_include_directories(PortableFixedPrimary PRIVATE ${ORBITER_SOURCE_SDK_INCLUDE_DIR})
    target_link_libraries(PortableFixedPrimary PRIVATE ${ORBITER_LIB} ${ORBITER_SDK_LIB})
    add_dependencies(PortableFixedPrimary ${OrbiterTgt} Orbitersdk)
    set_target_properties(PortableFixedPrimary PROPERTIES
        RUNTIME_OUTPUT_DIRECTORY "${ORBITER_BINARY_ROOT_DIR}/Modules/Celbody")
endif()

FetchContent_Declare(
  Catch2
  GIT_REPOSITORY https://github.com/catchorg/Catch2.git
  GIT_TAG        v3.0.0-preview3
)

FetchContent_MakeAvailable(Catch2)

# Utility function
function(add_test_file test_name)
	add_executable(${test_name} "${test_name}.cpp")

	set_target_properties( ${test_name} PROPERTIES RUNTIME_OUTPUT_DIRECTORY "${ORBITER_BINARY_ROOT_DIR}" )

	target_include_directories(${test_name}
		PRIVATE ${ORBITER_SOURCE_SDK_INCLUDE_DIR}
		PRIVATE ${MODULE_COMMON_DIR}
		PRIVATE ${ORBITER_SOURCE_ROOT_DIR}/Src/Module/LuaScript/LuaInterpreter
	)

	target_link_libraries(${test_name}
		${ORBITER_LIB}
		${ORBITER_SDK_LIB}
		lua::lib
		LuaInterpreter
		Catch2::Catch2WithMain
	)

	add_dependencies(${test_name}
		${OrbiterTgt}
		Orbitersdk
		LuaInterpreter
	)

	add_test( 
		NAME ${test_name} 
		COMMAND $<TARGET_FILE:${test_name}>
		WORKING_DIRECTORY ${ORBITER_BINARY_ROOT_DIR}
	)
	set_tests_properties(${test_name} PROPERTIES TIMEOUT 30)
endfunction()

# Utility function for self-contained tests that only need a few core source
# files (listed after the test name) and neither the Orbiter library nor Lua
function(add_core_test_file test_name)
	add_executable(${test_name} "${test_name}.cpp" ${ARGN})

	set_target_properties( ${test_name} PROPERTIES RUNTIME_OUTPUT_DIRECTORY "${ORBITER_BINARY_ROOT_DIR}" )

	target_include_directories(${test_name}
		PRIVATE ${ORBITER_SOURCE_SDK_INCLUDE_DIR}
		PRIVATE ${ORBITER_SOURCE_ROOT_DIR}/Src/Orbiter
	)

	target_link_libraries(${test_name} Catch2::Catch2WithMain)

	add_test(
		NAME ${test_name}
		COMMAND $<TARGET_FILE:${test_name}>
		WORKING_DIRECTORY ${ORBITER_BINARY_ROOT_DIR}
	)
	set_tests_properties(${test_name} PROPERTIES TIMEOUT 30)
endfunction()

# Register unit tests
add_test_file(Lua.Interpreter)
add_core_test_file(Collision.CollisionCore
	${ORBITER_SOURCE_ROOT_DIR}/Src/Orbiter/CollisionCore.cpp
	${ORBITER_SOURCE_ROOT_DIR}/Src/Orbiter/Vecmat.cpp
)

if (BUILD_ORBITER_SERVER)

	# Sanity check for scenario tests
	add_test(
		NAME "Scenario.SanityCheck"
		COMMAND $<TARGET_FILE:Orbiter_server> "--scenariox=${CMAKE_SOURCE_DIR}/Scenarios/Delta-glider/Smack!.scn" "--maxframes=60"
		WORKING_DIRECTORY ${ORBITER_BINARY_ROOT_DIR}
	)
	set_tests_properties(Scenario.SanityCheck PROPERTIES TIMEOUT 60)

	# Register scenario tests
	file(GLOB TestScenarios "${CMAKE_SOURCE_DIR}/Scenarios/Tests/*.scn")
	foreach(Scenario ${TestScenarios})
		get_filename_component(test_name ${Scenario} NAME_WE)
		add_test(
			NAME "Scenario.${test_name}"
			COMMAND $<TARGET_FILE:Orbiter_server> "--scenariox=${Scenario}"
			WORKING_DIRECTORY ${ORBITER_BINARY_ROOT_DIR}
		)
		set_tests_properties(Scenario.${test_name} PROPERTIES TIMEOUT 60)
	endforeach()

endif()
