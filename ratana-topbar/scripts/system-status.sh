#!/usr/bin/env bash
# ============================================================
# Ratana Top Bar — System Status Diagnostic Helper
# ============================================================

echo "=== Ratana Top Bar System Status ==="
echo "Compositor: ${XDG_CURRENT_DESKTOP:-Unknown} ($SWAYSOCK)"
echo "Waybar: $(waybar --version 2>/dev/null || echo 'Not found')"
echo "Audio (pamixer): $(pamixer --get-volume 2>/dev/null || echo 'N/A')%"
echo "Brightness: $(brightnessctl get 2>/dev/null || echo 'N/A')"
echo "Power Profile: $(cat /sys/firmware/acpi/platform_profile 2>/dev/null || echo 'N/A')"
echo "Active Workspaces: $(swaymsg -t get_workspaces 2>/dev/null | grep -o '"num":[0-9]*' | tr '\n' ' ')"
echo "====================================="
