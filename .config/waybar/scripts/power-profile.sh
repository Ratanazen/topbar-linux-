#!/usr/bin/env bash
# ============================================================
# Ratana Top Bar — Power & Fan Profile Script
# Real ACPI platform profile integration for Waybar
# ============================================================

PROFILE_FILE="/sys/firmware/acpi/platform_profile"
ASUS_FILE="/sys/devices/platform/asus-nb-wmi/throttle_thermal_policy"

get_profile() {
    if [[ -r "$PROFILE_FILE" ]]; then
        cat "$PROFILE_FILE" 2>/dev/null
    elif [[ -r "$ASUS_FILE" ]]; then
        case $(cat "$ASUS_FILE" 2>/dev/null) in
            0) echo "balanced" ;;
            1) echo "performance" ;;
            2) echo "quiet" ;;
            *) echo "balanced" ;;
        esac
    elif command -v powerprofilesctl >/dev/null 2>&1; then
        powerprofilesctl get 2>/dev/null || echo "balanced"
    else
        echo "balanced"
    fi
}

set_profile() {
    local target="$1"
    local asus_val=0
    case "$target" in
        quiet) asus_val=2 ;;
        balanced) asus_val=0 ;;
        performance) asus_val=1 ;;
    esac

    # 1. Direct sysfs write if writable
    if [[ -w "$PROFILE_FILE" ]] && echo "$target" > "$PROFILE_FILE" 2>/dev/null; then
        return 0
    fi
    if [[ -w "$ASUS_FILE" ]] && echo "$asus_val" > "$ASUS_FILE" 2>/dev/null; then
        return 0
    fi

    # 2. powerprofilesctl if available
    if command -v powerprofilesctl >/dev/null 2>&1; then
        if powerprofilesctl set "$target" 2>/dev/null; then
            return 0
        fi
    fi

    # 3. pkexec fallback
    if command -v pkexec >/dev/null 2>&1; then
        if pkexec sh -c "echo '$target' > '$PROFILE_FILE' 2>/dev/null || echo '$asus_val' > '$ASUS_FILE' 2>/dev/null"; then
            return 0
        fi
    fi

    return 1
}

# Handle switching
if [[ "$1" == "--next" || "$1" == "--toggle" ]]; then
    CURRENT=$(get_profile)
    case "$CURRENT" in
        quiet) NEXT="balanced" ;;
        balanced) NEXT="performance" ;;
        performance) NEXT="quiet" ;;
        *) NEXT="balanced" ;;
    esac

    if set_profile "$NEXT"; then
        notify-send -u low -i preferences-system-power "Power Profile: ${NEXT^}" "Switched to ${NEXT^} mode" 2>/dev/null
        pkill -RTMIN+8 waybar 2>/dev/null || true
    fi
    exit 0
fi

# Default: Output JSON for Waybar
CURRENT=$(get_profile)
CAPITALIZED="${CURRENT^}"

ICON="󰾆"
case "$CURRENT" in
    quiet) ICON="󰾆" ;;
    balanced) ICON="󰾅" ;;
    performance) ICON="󰓅" ;;
esac

printf '{"text":"%s %s","tooltip":"Power Profile: %s\\nClick to cycle (Quiet -> Balanced -> Performance)","class":"%s"}\n' "$ICON" "$CAPITALIZED" "$CAPITALIZED" "$CURRENT"
