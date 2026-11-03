# Copyright (c) Martin Schweiger
# Licensed under the MIT License

add_executable(meshc meshc.cpp)
target_compile_features(meshc PRIVATE cxx_std_17)
if(WIN32)
    target_sources(meshc PRIVATE Mesh.cpp)
    target_include_directories(meshc PRIVATE "${ORBITER_SOURCE_DIR}")
else()
    target_link_libraries(meshc PRIVATE orbiter_production_boundary)
endif()

set_target_properties(meshc
	PROPERTIES
	FOLDER Tools
)

if(NOT ORBITER_INSTALL_SDK_DIR)
    set(ORBITER_INSTALL_SDK_DIR Orbitersdk)
endif()
install(TARGETS meshc
	DESTINATION ${ORBITER_INSTALL_SDK_DIR}/Utils
)
