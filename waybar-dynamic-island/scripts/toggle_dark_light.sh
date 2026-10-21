#!/usr/bin/env bash
# ============================================================
# Ratana Top Bar — Dark / Light Mode Toggle Script
# ============================================================

set -e

get_current_mode() {
    local scheme
    scheme=$(gsettings get org.gnome.desktop.interface color-scheme 2>/dev/null | tr -d "'" || true)
    if [ "$scheme" = "prefer-light" ]; then
        echo "light"
    else
        echo "dark"
    fi
}

CURRENT_MODE=$(get_current_mode)

if [ "$1" = "--toggle" ] || [ "$1" = "-t" ] || [ "$1" = "--next" ]; then
    THEME_MGR="$HOME/.config/sway/scripts/theme_manager.py"
    if [ -f "$THEME_MGR" ]; then
        python3 "$THEME_MGR" --toggle
    fi
    pkill -RTMIN+10 waybar 2>/dev/null || true
    pkill -SIGUSR2 waybar 2>/dev/null || true

    NEW_MODE=$(get_current_mode)
    if [ "$NEW_MODE" = "light" ]; then
        notify-send -u low -i "weather-clear" "Light Mode Active" "Switched to macOS Light theme" 2>/dev/null || true
    else
        notify-send -u low -i "weather-clear-night" "Dark Mode Active" "Switched to macOS Dark theme" 2>/dev/null || true
    fi
    exit 0
fi

# Waybar JSON output
if [ "$CURRENT_MODE" = "light" ]; then
    echo '{"text":"󰖙","alt":"light","tooltip":"☀️ Light Mode Active\\nClick: Switch to Dark Mode","class":"light"}'
else
    echo '{"text":"󰖔","alt":"dark","tooltip":"🌙 Dark Mode Active\\nClick: Switch to Light Mode","class":"dark"}'
fi
