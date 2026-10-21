cmake_minimum_required(VERSION 3.20)
project(ratana-island C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

add_compile_options(-Wall -Wextra -Wpedantic -Wno-unused-parameter)

find_package(PkgConfig REQUIRED)
pkg_check_modules(GTK4 REQUIRED gtk4)
pkg_check_modules(LAYER_SHELL REQUIRED gtk4-layer-shell-0)
pkg_check_modules(GLIB REQUIRED glib-2.0 gio-2.0 gobject-2.0)
pkg_check_modules(JSON_GLIB REQUIRED json-glib-1.0)
pkg_check_modules(PULSE REQUIRED libpulse libpulse-mainloop-glib)
pkg_check_modules(UPOWER REQUIRED upower-glib)
pkg_check_modules(CAIRO REQUIRED cairo)
pkg_check_modules(PANGO REQUIRED pango)

include_directories(
    ${CMAKE_CURRENT_SOURCE_DIR}/src
    ${GTK4_INCLUDE_DIRS}
    ${LAYER_SHELL_INCLUDE_DIRS}
    ${GLIB_INCLUDE_DIRS}
    ${JSON_GLIB_INCLUDE_DIRS}
    ${PULSE_INCLUDE_DIRS}
    ${UPOWER_INCLUDE_DIRS}
    ${CAIRO_INCLUDE_DIRS}
    ${PANGO_INCLUDE_DIRS}
)

set(SOURCES
    src/main.c
    src/settings.c
    src/animation.c
    src/state_manager.c
    src/media.c
    src/sway_ipc.c
    src/notifications.c
    src/system_status.c
    src/island_window.c
    src/settings_window.c
)

add_executable(ratana-island ${SOURCES})

target_link_libraries(ratana-island PRIVATE
    ${GTK4_LIBRARIES}
    ${LAYER_SHELL_LIBRARIES}
    ${GLIB_LIBRARIES}
    ${JSON_GLIB_LIBRARIES}
    ${PULSE_LIBRARIES}
    ${UPOWER_LIBRARIES}
    ${CAIRO_LIBRARIES}
    ${PANGO_LIBRARIES}
    m
)

# Testing
enable_testing()

add_executable(test_state
    tests/test_state.c
    src/state_manager.c
)
target_link_libraries(test_state PRIVATE ${GLIB_LIBRARIES})
add_test(NAME test_state COMMAND test_state)

add_executable(test_config
    tests/test_config.c
    src/settings.c
)
target_link_libraries(test_config PRIVATE ${GLIB_LIBRARIES})
add_test(NAME test_config COMMAND test_config)

add_executable(test_animation
    tests/test_animation.c
    src/animation.c
)
target_link_libraries(test_animation PRIVATE ${GTK4_LIBRARIES} ${GLIB_LIBRARIES} m)
add_test(NAME test_animation COMMAND test_animation)

add_executable(test_media_track
    tests/test_media_track.c
    src/media.c
)
target_link_libraries(test_media_track PRIVATE ${GLIB_LIBRARIES})
add_test(NAME test_media_track COMMAND test_media_track)

add_executable(test_notifications_unit
    tests/test_notifications_unit.c
    src/notifications.c
)
target_link_libraries(test_notifications_unit PRIVATE ${GLIB_LIBRARIES})
add_test(NAME test_notifications_unit COMMAND test_notifications_unit)

add_executable(test_ipc_robustness
    tests/test_ipc_robustness.c
)
target_link_libraries(test_ipc_robustness PRIVATE ${GLIB_LIBRARIES} ${JSON_GLIB_LIBRARIES})
add_test(NAME test_ipc_robustness COMMAND test_ipc_robustness)

# Installation
include(GNUInstallDirs)
install(TARGETS ratana-island DESTINATION ${CMAKE_INSTALL_BINDIR})
install(DIRECTORY config/ DESTINATION ${CMAKE_INSTALL_DATADIR}/ratana-island)
install(FILES systemd/ratana-island.service DESTINATION lib/systemd/user OPTIONAL)
