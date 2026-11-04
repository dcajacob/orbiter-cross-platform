# Internal integration candidate. The accepted external-view target remains the
# default until cockpit runtime comparisons have passed.
include(FetchContent)
set(ORBITER_NATIVE_UI_ARCHIVE "" CACHE FILEPATH "Verified pinned ImGui archive (offline builds)")
file(READ "${CMAKE_CURRENT_LIST_DIR}/../../../OVP/OGLClient/dependencies.lock.json" _ui_lock)
string(JSON _ui_hash GET "${_ui_lock}" imgui sha256)
string(JSON _ui_url GET "${_ui_lock}" imgui url)
if(ORBITER_NATIVE_UI_ARCHIVE)
    set(_ui_url "${ORBITER_NATIVE_UI_ARCHIVE}")
endif()
FetchContent_Declare(native_imgui URL "${_ui_url}" URL_HASH "SHA256=${_ui_hash}" DOWNLOAD_EXTRACT_TIMESTAMP TRUE SOURCE_SUBDIR no-build)
FetchContent_MakeAvailable(native_imgui)
set(ORBITER_NATIVE_PLOT_ARCHIVE "" CACHE FILEPATH "Verified original ImPlot archive (offline builds)")
string(JSON _plot_hash GET "${_ui_lock}" implot sha256)
string(JSON _plot_url GET "${_ui_lock}" implot url)
if(ORBITER_NATIVE_PLOT_ARCHIVE)
    set(_plot_url "${ORBITER_NATIVE_PLOT_ARCHIVE}")
endif()
FetchContent_Declare(native_implot URL "${_plot_url}" URL_HASH "SHA256=${_plot_hash}"
    DOWNLOAD_EXTRACT_TIMESTAMP TRUE SOURCE_SUBDIR no-build)
FetchContent_MakeAvailable(native_implot)
target_sources(orbiter_production_vessels PRIVATE
    NativeAnnotations.cpp NativeScript.cpp NativeInterpreterSdk.cpp NativeHelp.cpp NativeCockpitProjection.cpp NativeCockpitMfd.cpp NativeCockpitGui.cpp NativeCameraMouse.cpp ../MenuInfoBar.cpp ../DlgFocus.cpp ../DlgMenuCfg.cpp ../DlgTacc.cpp ../DlgCamera.cpp ../DlgInfo.cpp ../DlgMap.cpp ../DlgOptions.cpp ../DlgFunction.cpp ../DlgRecorder.cpp ../PlaybackEd.cpp NativeCockpitCommands.cpp NativeCockpitVessel.cpp ../CockpitSdk.cpp ../Astro.cpp
    ../Pane.cpp ../hud.cpp ../Defpanel.cpp ../Panel2D.cpp ../VCockpit.cpp ../Select.cpp
    ../Mfd.cpp ../MfdUser.cpp ../VectorMap.cpp ../MfdOrbit.cpp ../MfdSurface.cpp ../MfdMap.cpp ../MfdHsi.cpp
    ../MfdLanding.cpp ../MfdDocking.cpp ../MfdAlign.cpp ../MfdSync.cpp ../MfdTransfer.cpp ../MfdComms.cpp
    "${native_imgui_SOURCE_DIR}/imgui.cpp" "${native_imgui_SOURCE_DIR}/imgui_draw.cpp"
    "${native_imgui_SOURCE_DIR}/imgui_tables.cpp" "${native_imgui_SOURCE_DIR}/imgui_widgets.cpp"
    "${native_implot_SOURCE_DIR}/implot.cpp" "${native_implot_SOURCE_DIR}/implot_items.cpp")
target_include_directories(orbiter_production_vessels PRIVATE "${native_imgui_SOURCE_DIR}" "${native_implot_SOURCE_DIR}")
target_compile_definitions(orbiter_production_vessels PUBLIC ORBITER_NATIVE_COCKPIT)
file(MAKE_DIRECTORY "${PROJECT_BINARY_DIR}/NativeModules/Licenses")
configure_file("${native_implot_SOURCE_DIR}/LICENSE" "${PROJECT_BINARY_DIR}/NativeModules/Licenses/implot-LICENSE.txt" COPYONLY)

# Stock DG sources refer to meshc-generated group IDs in all four meshes.
add_subdirectory("${CMAKE_CURRENT_LIST_DIR}/../../../Utils/meshc" "${PROJECT_BINARY_DIR}/meshc-native")
set(_dg_mesh_root "${CMAKE_CURRENT_LIST_DIR}/../../Vessel/DeltaGlider/Meshes")
set(_dg_header_dir "${PROJECT_BINARY_DIR}/native-dg-include")
file(MAKE_DIRECTORY "${_dg_header_dir}")
function(native_dg_mesh_header mesh suffix header)
    add_custom_command(OUTPUT "${_dg_header_dir}/${header}"
        COMMAND meshc /I "${_dg_mesh_root}/${mesh}" /P "${suffix}" /O "${_dg_header_dir}/${header}"
        DEPENDS meshc "${_dg_mesh_root}/${mesh}" VERBATIM)
endfunction()
native_dg_mesh_header(deltaglider.msh - meshres.h)
native_dg_mesh_header(deltaglider_vc.msh _VC meshres_vc.h)
native_dg_mesh_header(dg_2dpanel0.msh _P0 meshres_p0.h)
native_dg_mesh_header(dg_2dpanel1.msh _P1 meshres_p1.h)
add_custom_target(native_dg_mesh_resources DEPENDS
    "${_dg_header_dir}/meshres.h" "${_dg_header_dir}/meshres_vc.h"
    "${_dg_header_dir}/meshres_p0.h" "${_dg_header_dir}/meshres_p1.h")

# These are the panel elements and subsystem base used by the stock vessel.
set(_dg_source "${CMAKE_CURRENT_LIST_DIR}/../../Vessel/DeltaGlider")
add_library(native_dg_instruments STATIC
    "${_dg_source}/../Common/Instrument.cpp"
    "${_dg_source}/DGSwitches.cpp" "${_dg_source}/FuelMfd.cpp" "${_dg_source}/Horizon.cpp"
    "${_dg_source}/InstrAoa.cpp" "${_dg_source}/InstrHsi.cpp"
    "${_dg_source}/InstrVs.cpp" "${_dg_source}/MomentInd.cpp")
target_include_directories(native_dg_instruments PRIVATE "${_dg_header_dir}")
target_link_libraries(native_dg_instruments PRIVATE orbiter_production_vessels)
set_target_properties(native_dg_instruments PROPERTIES POSITION_INDEPENDENT_CODE ON)
add_dependencies(native_dg_instruments native_dg_mesh_resources)

# Compiled into the stock vessel once its main module and interpreter are linked.
add_library(native_dg_subsystems STATIC
    "${_dg_source}/AAPSubsys.cpp"
    "${_dg_source}/AerodynSubsys.cpp"
    "${_dg_source}/AvionicsSubsys.cpp"
    "${_dg_source}/DockingSubsys.cpp"
    "${_dg_source}/FailureSubsys.cpp"
    "${_dg_source}/GearSubsys.cpp"
    "${_dg_source}/HoverSubsys.cpp"
    "${_dg_source}/HudCtrl.cpp"
    "${_dg_source}/LightSubsys.cpp"
    "${_dg_source}/MainRetroSubsys.cpp"
    "${_dg_source}/MfdSubsys.cpp"
    "${_dg_source}/PressureSubsys.cpp"
    "${_dg_source}/RcsSubsys.cpp"
    "${_dg_source}/ScramSubsys.cpp"
    "${_dg_source}/ThermalSubsys.cpp"
)
target_include_directories(native_dg_subsystems PRIVATE "${_dg_header_dir}")
target_link_libraries(native_dg_subsystems PRIVATE native_dg_instruments orbiter_production_vessels)
set_target_properties(native_dg_subsystems PROPERTIES POSITION_INDEPENDENT_CODE ON)
add_dependencies(native_dg_subsystems native_dg_mesh_resources)

add_library(native_dg_vessel OBJECT "${_dg_source}/DeltaGlider.cpp")
target_include_directories(native_dg_vessel PRIVATE "${_dg_header_dir}" "${native_imgui_SOURCE_DIR}")
target_link_libraries(native_dg_vessel PRIVATE native_dg_subsystems orbiter_production_vessels)
set_target_properties(native_dg_vessel PROPERTIES POSITION_INDEPENDENT_CODE ON)
add_dependencies(native_dg_vessel native_dg_mesh_resources)

add_subdirectory("${CMAKE_CURRENT_LIST_DIR}/../../Module/LuaScript/Native" "${PROJECT_BINARY_DIR}/native-lua")
add_library(native_deltaglider MODULE
    $<TARGET_OBJECTS:native_dg_vessel> $<TARGET_OBJECTS:native_dg_lua_bindings>)
target_link_libraries(native_deltaglider PRIVATE native_dg_subsystems native_lua_script_files lua orbiter_production_vessels)
target_link_options(native_deltaglider PRIVATE -Wl,--no-undefined)
set_target_properties(native_deltaglider PROPERTIES PREFIX "" OUTPUT_NAME DeltaGlider
    LIBRARY_OUTPUT_DIRECTORY "${PROJECT_BINARY_DIR}/NativeModules/Vessel")

# Compile the original Shuttle-A vessel, instruments, Lua bindings and payload.
# Both factories use the same checked native SDK ABI as the stock DG module.
set(_shuttle_a_source "${CMAKE_CURRENT_LIST_DIR}/../../Vessel/ShuttleA")
set(_shuttle_a_header_dir "${PROJECT_BINARY_DIR}/native-shuttle-a-include")
file(MAKE_DIRECTORY "${_shuttle_a_header_dir}")
add_custom_command(OUTPUT "${_shuttle_a_header_dir}/meshres.h"
    COMMAND meshc /I "${_shuttle_a_source}/Meshes/ShuttleA.msh" /P - /O "${_shuttle_a_header_dir}/meshres.h"
    DEPENDS meshc "${_shuttle_a_source}/Meshes/ShuttleA.msh" VERBATIM)
add_library(native_shuttle_a MODULE
    "${_shuttle_a_header_dir}/meshres.h"
    "${_shuttle_a_source}/adiball.cpp" "${_shuttle_a_source}/adictrl.cpp"
    "${_shuttle_a_source}/airlockswitch.cpp" "${_shuttle_a_source}/attref.cpp"
    "${_shuttle_a_source}/auxpodctrl.cpp" "${_shuttle_a_source}/dockcvrswitch.cpp"
    "${_shuttle_a_source}/gearswitch.cpp" "${_shuttle_a_source}/hudbutton.cpp"
    "${_shuttle_a_source}/InstrVs.cpp" "${_shuttle_a_source}/mfdbutton.cpp"
    "${_shuttle_a_source}/navbutton.cpp" "${_shuttle_a_source}/needlepair.cpp"
    "${_shuttle_a_source}/paneltext.cpp" "${_shuttle_a_source}/payloadctrl.cpp"
    "${_shuttle_a_source}/rcsswitch.cpp" "${_shuttle_a_source}/ShuttleA.cpp"
    "${_shuttle_a_source}/ShuttleALua.cpp" "${_shuttle_a_source}/sliderpair.cpp"
    "${_shuttle_a_source}/switches.cpp" "${_shuttle_a_source}/../Common/Instrument.cpp")
target_include_directories(native_shuttle_a PRIVATE "${_shuttle_a_header_dir}")
target_link_libraries(native_shuttle_a PRIVATE lua orbiter_production_vessels)
target_link_options(native_shuttle_a PRIVATE -Wl,--no-undefined)
set_target_properties(native_shuttle_a PROPERTIES PREFIX "" OUTPUT_NAME ShuttleA
    LIBRARY_OUTPUT_DIRECTORY "${PROJECT_BINARY_DIR}/NativeModules/Vessel")

add_library(native_shuttle_a_payload MODULE "${_shuttle_a_source}/ShuttleA_PL/ShuttleA_pl.cpp")
target_link_libraries(native_shuttle_a_payload PRIVATE orbiter_production_vessels)
target_link_options(native_shuttle_a_payload PRIVATE -Wl,--no-undefined)
set_target_properties(native_shuttle_a_payload PROPERTIES PREFIX "" OUTPUT_NAME ShuttleA_PL
    LIBRARY_OUTPUT_DIRECTORY "${PROJECT_BINARY_DIR}/NativeModules/Vessel")

# Preserve the original Atlantis -> external tank -> booster C++ dependency
# chain; each vessel still enters through the checked native SDK factory.
set(_atlantis_source "${CMAKE_CURRENT_LIST_DIR}/../../Vessel/Atlantis")
set(_atlantis_header_dir "${PROJECT_BINARY_DIR}/native-atlantis-include")
file(MAKE_DIRECTORY "${_atlantis_header_dir}" "${_atlantis_header_dir}/srb")
add_custom_command(OUTPUT "${_atlantis_header_dir}/meshres.h"
    COMMAND meshc /I "${_atlantis_source}/Atlantis/Meshes/Atlantis.msh" /P - /O "${_atlantis_header_dir}/meshres.h"
    DEPENDS meshc "${_atlantis_source}/Atlantis/Meshes/Atlantis.msh" VERBATIM)
add_custom_command(OUTPUT "${_atlantis_header_dir}/meshres_vc.h"
    COMMAND meshc /I "${_atlantis_source}/Atlantis/Meshes/AtlantisVC.msh" /P _VC /O "${_atlantis_header_dir}/meshres_vc.h"
    DEPENDS meshc "${_atlantis_source}/Atlantis/Meshes/AtlantisVC.msh" VERBATIM)
add_custom_command(OUTPUT "${_atlantis_header_dir}/srb/meshres.h"
    COMMAND meshc /I "${_atlantis_source}/Atlantis_SRB/Meshes/Atlantis_SRB.msh" /P - /O "${_atlantis_header_dir}/srb/meshres.h"
    DEPENDS meshc "${_atlantis_source}/Atlantis_SRB/Meshes/Atlantis_SRB.msh" VERBATIM)
add_library(native_atlantis_srb SHARED "${_atlantis_header_dir}/srb/meshres.h"
    "${_atlantis_source}/Atlantis_SRB/Atlantis_SRB.cpp" "${_atlantis_source}/Common.cpp")
target_include_directories(native_atlantis_srb PRIVATE "${_atlantis_header_dir}/srb" "${_atlantis_source}/Atlantis")
target_link_libraries(native_atlantis_srb PRIVATE orbiter_production_vessels)
add_library(native_atlantis_tank SHARED "${_atlantis_source}/Atlantis_Tank/Atlantis_Tank.cpp")
target_include_directories(native_atlantis_tank PRIVATE "${_atlantis_source}/Atlantis")
target_link_libraries(native_atlantis_tank PRIVATE native_atlantis_srb orbiter_production_vessels)
add_library(native_atlantis MODULE "${_atlantis_header_dir}/meshres.h" "${_atlantis_header_dir}/meshres_vc.h"
    "${_atlantis_source}/Atlantis/Atlantis.cpp" "${_atlantis_source}/Atlantis/AscentAP.cpp"
    "${_atlantis_source}/Atlantis/PlBayOp.cpp" "${_atlantis_source}/Common.cpp")
target_include_directories(native_atlantis PRIVATE "${_atlantis_header_dir}" "${_atlantis_source}/Atlantis"
    "${native_imgui_SOURCE_DIR}" "${native_implot_SOURCE_DIR}")
target_link_libraries(native_atlantis PRIVATE native_atlantis_tank orbiter_production_vessels)
foreach(_atlantis_part IN ITEMS native_atlantis native_atlantis_tank native_atlantis_srb)
    target_link_options(${_atlantis_part} PRIVATE -Wl,--no-undefined)
    set_target_properties(${_atlantis_part} PROPERTIES PREFIX ""
        LIBRARY_OUTPUT_DIRECTORY "${PROJECT_BINARY_DIR}/NativeModules/Vessel" BUILD_RPATH_USE_ORIGIN TRUE)
endforeach()
set_target_properties(native_atlantis PROPERTIES OUTPUT_NAME Atlantis)
set_target_properties(native_atlantis_tank PROPERTIES OUTPUT_NAME Atlantis_Tank)
set_target_properties(native_atlantis_srb PROPERTIES OUTPUT_NAME Atlantis_SRB)

add_library(native_lua_inline_list OBJECT ../../Module/LuaScript/LuaInline/LuaInline.cpp)
target_include_directories(native_lua_inline_list PRIVATE "${CMAKE_CURRENT_LIST_DIR}/../../Module/LuaScript/LuaInterpreter")
target_link_libraries(native_lua_inline_list PRIVATE lua orbiter_production_vessels)
set_target_properties(native_lua_inline_list PROPERTIES POSITION_INDEPENDENT_CODE ON)

add_library(native_lua_interpreter_core OBJECT ../../Module/LuaScript/LuaInterpreter/Interpreter.cpp)
target_link_libraries(native_lua_interpreter_core PRIVATE lua orbiter_production_vessels)
set_target_properties(native_lua_interpreter_core PROPERTIES POSITION_INDEPENDENT_CODE ON)

target_link_libraries(orbiter_production_vessels PRIVATE ${_archive_zlib})
target_include_directories(orbiter_production_vessels PRIVATE ${_archive_zlib_includes})

add_library(native_lua_interpreter SHARED
    $<TARGET_OBJECTS:native_lua_interpreter_core> $<TARGET_OBJECTS:native_lua_vessel_bindings>
    ../../Module/LuaScript/LuaInterpreter/InterpreterExecution.cpp)
target_link_libraries(native_lua_interpreter PRIVATE native_lua_script_files native_lua_exit lua orbiter_production_vessels)
target_link_options(native_lua_interpreter PRIVATE -Wl,--no-undefined)
set_target_properties(native_lua_interpreter PROPERTIES PREFIX "" OUTPUT_NAME LuaInterpreter
    LIBRARY_OUTPUT_DIRECTORY "${PROJECT_BINARY_DIR}/NativeModules/Plugin")

add_library(native_lua_inline MODULE $<TARGET_OBJECTS:native_lua_inline_list>
    ../../Module/LuaScript/LuaInline/InlineEnvironment.cpp)
target_include_directories(native_lua_inline PRIVATE "${CMAKE_CURRENT_LIST_DIR}/../../Module/LuaScript/LuaInterpreter")
target_link_libraries(native_lua_inline PRIVATE native_lua_interpreter lua orbiter_production_vessels)
target_link_options(native_lua_inline PRIVATE -Wl,--no-undefined)
set_target_properties(native_lua_inline PROPERTIES PREFIX "" OUTPUT_NAME LuaInline
    LIBRARY_OUTPUT_DIRECTORY "${PROJECT_BINARY_DIR}/NativeModules/Plugin")
