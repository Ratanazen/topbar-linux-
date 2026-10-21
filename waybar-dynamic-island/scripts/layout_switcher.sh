#!/bin/bash
# ~/.config/waybar/scripts/layout_switcher.sh
# Khmer & English keyboard layout indicator and switcher for Waybar

if [[ "$1" == "--next" || "$1" == "--toggle" ]]; then
    swaymsg input type:keyboard xkb_switch_layout next 2>/dev/null
    pkill -RTMIN+9 waybar 2>/dev/null
    exit 0
fi

python3 - << 'EOF'
import subprocess, json, sys

try:
    res = subprocess.check_output(["swaymsg", "-t", "get_inputs"], timeout=1)
    inputs = json.loads(res.decode())
    is_khmer = False
    for dev in inputs:
        if dev.get("type") == "keyboard":
            name = dev.get("xkb_active_layout_name", "")
            if "Khmer" in name or "Cambodia" in name or "kh" in name.lower():
                is_khmer = True
                break
    if is_khmer:
        print('{"text":" ខ្មែរ","tooltip":"Keyboard: Khmer (NiDA Unicode)\\nClick or press Alt+Shift to switch to English","class":"khmer"}')
    else:
        print('{"text":" EN","tooltip":"Keyboard: English (US)\\nClick or press Alt+Shift to switch to Khmer","class":"us"}')
except Exception:
    print('{"text":" EN","tooltip":"Keyboard Layout","class":"us"}')
EOF
