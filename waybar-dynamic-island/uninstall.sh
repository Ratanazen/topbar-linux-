#!/usr/bin/env bash
# =============================================================================
# RATANA DYNAMIC ISLAND — UNINSTALLER
# =============================================================================
# Cleanly terminates running instances, disables systemd user units,
# removes installed binaries and scripts, and optionally purges configuration.
# =============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

WAYBAR_CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/waybar"
WAYBAR_SCRIPTS_DIR="$WAYBAR_CONFIG_DIR/scripts"
SYSTEMD_USER_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
LOCAL_BIN="$HOME/.local/bin"
RATANA_CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/ratana-island"
RUNTIME_SOCKET="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/ratana-island.sock"

PURGE_CONFIG=false
RESTORE_BACKUP=false
INTERACTIVE=true

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --purge)
            PURGE_CONFIG=true
            INTERACTIVE=false
            shift
            ;;
        --keep-config)
            PURGE_CONFIG=false
            INTERACTIVE=false
            shift
            ;;
        --restore-backup)
            RESTORE_BACKUP=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --purge           Completely remove all configuration and user data (~/.config/ratana-island)"
            echo "  --keep-config     Retain configuration directory while removing binaries, services, and core code"
            echo "  --restore-backup  Restore config.ini.bak to config.ini if a previous backup exists"
            echo "  -h, --help        Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown argument: $1"
            echo "Use $0 --help for options."
            exit 1
            ;;
    esac
done

echo -e "${BLUE}====================================================${NC}"
echo -e "${BLUE}   [x] Ratana Dynamic Island — Uninstaller          ${NC}"
echo -e "${BLUE}====================================================${NC}"

# 1. Stop active services and processes
echo -e "\n${BLUE}[*] Stopping running Ratana Island processes...${NC}"

if systemctl --user is-active --quiet island.service 2>/dev/null; then
    echo -e "  [-] Stopping systemd user service island.service..."
    systemctl --user stop island.service 2>/dev/null || true
fi

if systemctl --user is-enabled --quiet island.service 2>/dev/null; then
    echo -e "  [-] Disabling systemd user service island.service..."
    systemctl --user disable island.service 2>/dev/null || true
fi

# Kill any rogue daemon or quickshell overlay processes
pkill -f "island-daemon.py" 2>/dev/null || true
pkill -f "quickshell.*ratana" 2>/dev/null || true

# Remove runtime socket
if [ -S "$RUNTIME_SOCKET" ]; then
    rm -f "$RUNTIME_SOCKET"
    echo -e "  [✓] Removed runtime socket $RUNTIME_SOCKET"
fi

# 2. Remove systemd service file
if [ -f "$SYSTEMD_USER_DIR/island.service" ]; then
    rm -f "$SYSTEMD_USER_DIR/island.service"
    systemctl --user daemon-reload 2>/dev/null || true
    echo -e "  [✓] Removed $SYSTEMD_USER_DIR/island.service"
fi

# 3. Remove binaries, scripts, and deployed core modules
echo -e "\n${BLUE}[*] Removing installed executables, scripts, and modules...${NC}"

if [ -L "$LOCAL_BIN/island-ctl" ] || [ -f "$LOCAL_BIN/island-ctl" ]; then
    rm -f "$LOCAL_BIN/island-ctl"
    echo -e "  [✓] Removed $LOCAL_BIN/island-ctl"
fi

if [ -f "$WAYBAR_SCRIPTS_DIR/island-daemon.py" ]; then
    rm -f "$WAYBAR_SCRIPTS_DIR/island-daemon.py"
    echo -e "  [✓] Removed $WAYBAR_SCRIPTS_DIR/island-daemon.py"
fi

if [ -f "$WAYBAR_SCRIPTS_DIR/island-ctl" ]; then
    rm -f "$WAYBAR_SCRIPTS_DIR/island-ctl"
    echo -e "  [✓] Removed $WAYBAR_SCRIPTS_DIR/island-ctl"
fi

if [ -d "$WAYBAR_CONFIG_DIR/core" ]; then
    rm -rf "$WAYBAR_CONFIG_DIR/core"
    echo -e "  [✓] Removed $WAYBAR_CONFIG_DIR/core"
fi

# 4. Handle configuration directory and backups
if [ -d "$RATANA_CONFIG_DIR" ]; then
    if [ "$INTERACTIVE" = true ]; then
        if [ -f "$RATANA_CONFIG_DIR/config.ini.bak" ]; then
            echo -e "\n${YELLOW}[?] Found backup configuration at: $RATANA_CONFIG_DIR/config.ini.bak${NC}"
            read -rp "Would you like to restore config.ini.bak before finishing? [y/N]: " restore_choice
            case "$restore_choice" in
                [Yy]* ) RESTORE_BACKUP=true;;
            esac
        fi

        echo -e "\n${YELLOW}[?] Found configuration directory at: $RATANA_CONFIG_DIR${NC}"
        read -rp "Do you want to permanently purge configuration and user data? [y/N]: " choice
        case "$choice" in
            [Yy]* ) PURGE_CONFIG=true;;
            * ) PURGE_CONFIG=false;;
        esac
    fi

    if [ "$PURGE_CONFIG" = true ]; then
        rm -rf "$RATANA_CONFIG_DIR"
        echo -e "  ${RED}[✓] Purged configuration directory: $RATANA_CONFIG_DIR${NC}"
    else
        # Remove installed application code but preserve user configuration files
        if [ -d "$RATANA_CONFIG_DIR/core" ]; then
            rm -rf "$RATANA_CONFIG_DIR/core"
            echo -e "  [✓] Removed $RATANA_CONFIG_DIR/core"
        fi
        if [ -d "$RATANA_CONFIG_DIR/quickshell" ]; then
            rm -rf "$RATANA_CONFIG_DIR/quickshell"
            echo -e "  [✓] Removed $RATANA_CONFIG_DIR/quickshell"
        fi

        if [ "$RESTORE_BACKUP" = true ] && [ -f "$RATANA_CONFIG_DIR/config.ini.bak" ]; then
            cp "$RATANA_CONFIG_DIR/config.ini.bak" "$RATANA_CONFIG_DIR/config.ini"
            echo -e "  ${GREEN}[✓] Restored config.ini from config.ini.bak${NC}"
        fi

        echo -e "  ${GREEN}[✓] Retained user configuration directory: $RATANA_CONFIG_DIR${NC}"
    fi
fi

# 5. Instructions for cleaning Waybar configs
echo -e "\n${GREEN}====================================================${NC}"
echo -e "${GREEN}   [✓] Ratana Dynamic Island Successfully Removed!  ${NC}"
echo -e "${GREEN}====================================================${NC}"
echo -e "Optional cleanup steps:"
echo -e "1. Remove 'custom/island' from modules-center in: ${BLUE}$WAYBAR_CONFIG_DIR/config.jsonc${NC}"
echo -e "2. Remove '#custom-island' CSS rules from: ${BLUE}$WAYBAR_CONFIG_DIR/style.css${NC}"
echo -e "3. Reload Waybar: ${GREEN}killall -SIGUSR2 waybar${NC}\n"
