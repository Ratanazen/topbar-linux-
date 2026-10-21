#!/bin/bash
# Waybar Fan & Performance Profile Script

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

    # 1. Try direct write (works if udev/tmpfiles permission is set)
    if [[ -w "$PROFILE_FILE" ]] && echo "$target" > "$PROFILE_FILE" 2>/dev/null; then
        return 0
    fi
    if [[ -w "$ASUS_FILE" ]] && echo "$asus_val" > "$ASUS_FILE" 2>/dev/null; then
        return 0
    fi

    # 2. Try passwordless sudo if permitted
    if sudo -n sh -c "echo '$target' > '$PROFILE_FILE' 2>/dev/null || echo '$asus_val' > '$ASUS_FILE' 2>/dev/null" 2>/dev/null; then
        return 0
    fi

    # 3. Fallback to polkit graphical prompt (pkexec)
    if command -v pkexec >/dev/null 2>&1; then
        if pkexec sh -c "echo '$target' > '$PROFILE_FILE' 2>/dev/null || echo '$asus_val' > '$ASUS_FILE' 2>/dev/null"; then
            return 0
        fi
    fi

    return 1
}

case "$1" in
    --set)
        NEXT="$2"
        if [[ -n "$NEXT" ]]; then
            if set_profile "$NEXT"; then
                notify-send -u low -i preferences-system-power "Fan Profile: ${NEXT^}" "Switched to ${NEXT^} mode"
            else
                notify-send -u critical -i dialog-error "Fan Profile" "Could not change fan profile (Permission denied)"
            fi
            pkill -RTMIN+8 waybar 2>/dev/null
        fi
        ;;
    --toggle|--next)
        CURRENT=$(get_profile)
        case "$CURRENT" in
            quiet) NEXT="balanced" ;;
            balanced) NEXT="performance" ;;
            performance) NEXT="quiet" ;;
            *) NEXT="balanced" ;;
        esac

        if set_profile "$NEXT"; then
            case "$NEXT" in
                quiet)
                    notify-send -u low -i preferences-system-power "Fan Profile: Quiet" "Switched to Silent / Quiet mode"
                    ;;
                balanced)
                    notify-send -u low -i preferences-system-power "Fan Profile: Balanced" "Switched to Standard / Balanced mode"
                    ;;
                performance)
                    notify-send -u normal -i preferences-system-power "Fan Profile: Performance" "Switched to Turbo / Performance mode"
                    ;;
            esac
        else
            notify-send -u critical -i dialog-error "Fan Profile" "Could not change fan profile (Permission denied)"
        fi
        # Signal Waybar to refresh module immediately
        pkill -RTMIN+8 waybar 2>/dev/null
        ;;
    *)
        CURRENT=$(get_profile)
        case "$CURRENT" in
            quiet)
                printf '{"text":"󰈐 Quiet","tooltip":"Fan Profile: Quiet (Silent)\\nClick to switch to Balanced","class":"quiet"}\n'
                ;;
            balanced)
                printf '{"text":"󰈐 Balanced","tooltip":"Fan Profile: Balanced (Standard)\\nClick to switch to Performance","class":"balanced"}\n'
                ;;
            performance)
                printf '{"text":"󰈐 Performance","tooltip":"Fan Profile: Performance (Turbo)\\nClick to switch to Quiet","class":"performance"}\n'
                ;;
            *)
                printf '{"text":"󰈐 Auto","tooltip":"Fan Profile: %s\\nClick to toggle","class":"auto"}\n' "$CURRENT"
                ;;
        esac
        ;;
esac
