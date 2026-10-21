#!/bin/bash
# ~/.config/waybar/scripts/function_menu.sh
# Quick Functions Menu for Waybar using fuzzel

OPTIONS="󰚰 System Update (garuda-update)
󰖔 Toggle Dark / Light Mode
󰸉 Change Wallpaper
󰔎 Change Theme
🏝️ Dynamic Island: Control Center
🪔 Dynamic Island: Magic Lamp Style
󰌾 Lock Screen
󰤄 Sleep (Suspend)
󰈐 Fan: Quiet Mode
󰈐 Fan: Balanced Mode
󰈐 Fan: Performance Mode
󰄀 Screenshot Selection
󰹑 Screenshot Fullscreen
󰑓 Reload Sway, Waybar & Dynamic Island
󰂯 Bluetooth Settings
󰤨 Network Connections
󰕾 Audio & Volume (Pavucontrol)
󰐥 Power Options"

SELECTION=$(echo -e "$OPTIONS" | fuzzel --dmenu -l 18 -w 34 -p "⚡ Quick Functions: ")

case "$SELECTION" in
    *"System Update"*)
        kitty --title waybar_garuda-update -e garuda-update &
        ;;
    *"Toggle Dark / Light Mode"*)
        bash "$HOME/.config/waybar/scripts/toggle_dark_light.sh" --toggle &
        ;;
    *"Change Wallpaper"*)
        python3 "$HOME/.config/sway/scripts/wallpaper_manager_gui.py" &
        ;;
    *"Change Theme"*)
        python3 "$HOME/.config/sway/scripts/theme_manager.py" &
        ;;
    *"Control Center"*)
        island-ctl toggle &
        ;;
    *"Magic Lamp Style"*)
        island-ctl windows style lamp &
        notify-send -u low "Dynamic Island" "Animation style set to Magic Lamp 🪔"
        ;;
    *"Lock Screen"*)
        bash "$HOME/.config/sway/scripts/lock_screen.sh" &
        ;;
    *"Sleep (Suspend)"*)
        sync && bash "$HOME/.config/sway/scripts/lock_screen.sh" & sleep 0.5 && systemctl suspend
        ;;
    *"Fan: Quiet Mode"*)
        bash "$HOME/.config/waybar/scripts/fan_profile.sh" --set quiet
        ;;
    *"Fan: Balanced Mode"*)
        bash "$HOME/.config/waybar/scripts/fan_profile.sh" --set balanced
        ;;
    *"Fan: Performance Mode"*)
        bash "$HOME/.config/waybar/scripts/fan_profile.sh" --set performance
        ;;
    *"Screenshot Selection"*)
        sleep 0.2
        grim -g "$(slurp)" - | swappy -f -
        ;;
    *"Screenshot Fullscreen"*)
        sleep 0.2
        bash "$HOME/.config/sway/scripts/screenshot_display.sh" 2>/dev/null || grim - | swappy -f -
        ;;
    *"Reload Sway"*)
        swaymsg reload
        pkill waybar
        waybar &
        systemctl --user restart island.service
        pkill -f quickshell.real
        sleep 0.3
        quickshell -d -p "$HOME/.config/ratana-island/quickshell" &
        notify-send -u low "Desktop Reload" "Sway, Waybar & Dynamic Island reloaded successfully"
        ;;
    *"Bluetooth Settings"*)
        blueman-manager &
        ;;
    *"Network Connections"*)
        nm-connection-editor &
        ;;
    *"Audio & Volume"*)
        pavucontrol &
        ;;
    *"Power Options"*)
        bash "$HOME/.config/sway/scripts/power_menu.sh"
        ;;
esac
