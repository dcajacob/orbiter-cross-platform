# The classic Launchpad version is its YYMMDD build stamp.
function(orbiter_configure_about)
    string(TIMESTAMP DATE "%d %b %Y")
    string(TIMESTAMP VERSION "%y%m%d")
    configure_file("${CMAKE_CURRENT_FUNCTION_LIST_DIR}/../Src/Orbiter/about.hpp.in"
        "${CMAKE_CURRENT_BINARY_DIR}/about.hpp" @ONLY)
    if(ARGC GREATER 0)
        file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/classic-build.version" "${VERSION}\n")
        add_custom_command(TARGET ${ARGV0} POST_BUILD
            COMMAND "${CMAKE_COMMAND}" -E copy_if_different
                "${CMAKE_CURRENT_BINARY_DIR}/classic-build.version" "$<TARGET_FILE:${ARGV0}>.version"
            VERBATIM)
    endif()
endfunction()
