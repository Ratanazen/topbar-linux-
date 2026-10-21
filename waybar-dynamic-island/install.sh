#!/usr/bin/env bash
# =============================================================================
# RATANA DYNAMIC ISLAND — AUTOMATED INSTALLER & ENVIRONMENT VALIDATOR
# =============================================================================
# Supports Arch Linux, Debian/Ubuntu, and Fedora.
# Dual frontend options: Waybar Lite, Quickshell Pro, or Both (default).
# =============================================================================

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}====================================================${NC}"
echo -e "${BLUE}   🏝️  Ratana Dynamic Island V2 — Installer         ${NC}"
echo -e "${BLUE}====================================================${NC}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WAYBAR_CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/waybar"
WAYBAR_SCRIPTS_DIR="$WAYBAR_CONFIG_DIR/scripts"
SYSTEMD_USER_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
LOCAL_BIN="$HOME/.local/bin"
RATANA_CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/ratana-island"

MODE_UPDATE=false
RUN_DOCTOR=false
FRONTEND_CHOICE="both" # "waybar", "quickshell", "both"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --update)
            MODE_UPDATE=true
            shift
            ;;
        --waybar-only)
            FRONTEND_CHOICE="waybar"
            shift
            ;;
        --quickshell-only)
            FRONTEND_CHOICE="quickshell"
            shift
            ;;
        --health|--doctor)
            RUN_DOCTOR=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --waybar-only      Deploy Waybar Lite edition (skips Quickshell overlay)"
            echo "  --quickshell-only  Deploy Quickshell Pro edition (standalone Wayland overlay)"
            echo "  --update           Update core, scripts, and Quickshell components, preserving config.ini"
            echo "  --doctor           Run dependency audit and system health verification"
            echo "  -h, --help         Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use $0 --help for available options."
            exit 1
            ;;
    esac
done

# -----------------------------------------------------------------------------
# 1. DETECT LINUX DISTRIBUTION & PACKAGE MANAGER
# -----------------------------------------------------------------------------
PKG_MANAGER=""
INSTALL_CMD=""

if command -v pacman &>/dev/null; then
    PKG_MANAGER="arch"
    INSTALL_CMD="sudo pacman -S --needed --noconfirm"
    PKG_DEPS="python playerctl libpulse brightnessctl upower ttf-jetbrains-mono-nerd bluez bluez-utils"
elif command -v apt-get &>/dev/null; then
    PKG_MANAGER="debian"
    INSTALL_CMD="sudo apt-get install -y"
    PKG_DEPS="python3 playerctl pulseaudio-utils brightnessctl upower fonts-jetbrains-mono bluez"
elif command -v dnf &>/dev/null; then
    PKG_MANAGER="fedora"
    INSTALL_CMD="sudo dnf install -y"
    PKG_DEPS="python3 playerctl pulseaudio-utils brightnessctl upower jetbrains-mono-fonts bluez"
else
    echo -e "${YELLOW}[!] Warning: Unknown distribution package manager. Manual dependency check required.${NC}"
fi

# -----------------------------------------------------------------------------
# 2. CHECK CORE DEPENDENCIES
# -----------------------------------------------------------------------------
echo -e "\n${BLUE}[*] Checking required system binaries...${NC}"

MISSING_DEPS=()
for bin in python3 playerctl pactl brightnessctl upower dbus-monitor bluetoothctl; do
    if command -v "$bin" &>/dev/null; then
        echo -e "  [✓] $bin found"
    else
        echo -e "  ${YELLOW}[!] $bin missing (optional/recommended)${NC}"
        MISSING_DEPS+=("$bin")
    fi
done

# Check Quickshell if requested
if [ "$FRONTEND_CHOICE" != "waybar" ]; then
    if command -v quickshell &>/dev/null; then
        QS_VER=$(quickshell --version 2>&1 | head -n 1 || echo "installed")
        echo -e "  [✓] quickshell found ($QS_VER)"
    else
        echo -e "  ${YELLOW}[!] quickshell missing. Quickshell Pro overlay requires quickshell.${NC}"
        echo -e "      On Arch Linux: yay -S quickshell-git"
    fi
fi

# Check Python version >= 3.11
if command -v python3 &>/dev/null; then
    PY_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    PY_MAJOR=$(echo "$PY_VER" | cut -d. -f1)
    PY_MINOR=$(echo "$PY_VER" | cut -d. -f2)
    if [ "$PY_MAJOR" -ge 3 ] && [ "$PY_MINOR" -ge 11 ]; then
        echo -e "  [✓] Python $PY_VER detected (>= 3.11 ok)"
    else
        echo -e "  ${RED}[✗] Python $PY_VER detected. Python 3.11+ is recommended.${NC}"
    fi
fi

if [ ${#MISSING_DEPS[@]} -gt 0 ]; then
    echo -e "\n${YELLOW}[!] Optional missing dependencies: ${MISSING_DEPS[*]}${NC}"
    if [ -n "$PKG_MANAGER" ]; then
        echo -e "You can install them via: ${GREEN}$INSTALL_CMD $PKG_DEPS${NC}"
    fi
fi

if [ "$RUN_DOCTOR" = true ]; then
    echo -e "\n${BLUE}[*] Executing Island Doctor diagnostics...${NC}"
    if [ -f "$LOCAL_BIN/island-ctl" ]; then
        "$LOCAL_BIN/island-ctl" doctor || true
    elif [ -f "$SCRIPT_DIR/scripts/island-ctl" ]; then
        "$SCRIPT_DIR/scripts/island-ctl" doctor || true
    fi
    exit 0
fi

# -----------------------------------------------------------------------------
# 3. INSTALL SCRIPTS, SHARED CORE, AND BINARIES
# -----------------------------------------------------------------------------
echo -e "\n${BLUE}[*] Deploying scripts and shared core to $WAYBAR_CONFIG_DIR ...${NC}"
mkdir -p "$WAYBAR_SCRIPTS_DIR"
mkdir -p "$LOCAL_BIN"
mkdir -p "$RATANA_CONFIG_DIR"

cp "$SCRIPT_DIR/scripts/island-daemon.py" "$WAYBAR_SCRIPTS_DIR/island-daemon.py"
cp "$SCRIPT_DIR/scripts/island-ctl" "$WAYBAR_SCRIPTS_DIR/island-ctl"

chmod +x "$WAYBAR_SCRIPTS_DIR/island-daemon.py"
chmod +x "$WAYBAR_SCRIPTS_DIR/island-ctl"

# Also deploy scripts to ~/.config/ratana-island/scripts for unified installation
mkdir -p "$RATANA_CONFIG_DIR/scripts"
cp "$SCRIPT_DIR/scripts/island-daemon.py" "$RATANA_CONFIG_DIR/scripts/island-daemon.py"
cp "$SCRIPT_DIR/scripts/island-ctl" "$RATANA_CONFIG_DIR/scripts/island-ctl"
chmod +x "$RATANA_CONFIG_DIR/scripts/island-daemon.py"
chmod +x "$RATANA_CONFIG_DIR/scripts/island-ctl"

# Deploy shared core to both ~/.config/ratana-island/core and waybar config dir
if [ -d "$SCRIPT_DIR/core" ]; then
    mkdir -p "$RATANA_CONFIG_DIR/core"
    mkdir -p "$WAYBAR_CONFIG_DIR/core"
    cp -r "$SCRIPT_DIR/core/"* "$RATANA_CONFIG_DIR/core/"
    cp -r "$SCRIPT_DIR/core/"* "$WAYBAR_CONFIG_DIR/core/"
    echo -e "  [✓] Deployed modular shared core"
fi

# Create symlink in ~/.local/bin for easy CLI access
ln -sf "$RATANA_CONFIG_DIR/scripts/island-ctl" "$LOCAL_BIN/island-ctl"
echo -e "  [✓] Symlinked $LOCAL_BIN/island-ctl"

# -----------------------------------------------------------------------------
# 4. DEPLOY CONFIGURATION, QUICKSHELL PRO, AND SYSTEMD SERVICE
# -----------------------------------------------------------------------------
echo -e "\n${BLUE}[*] Setting up configuration at $RATANA_CONFIG_DIR ...${NC}"
if [ -f "$RATANA_CONFIG_DIR/config.ini" ]; then
    cp "$RATANA_CONFIG_DIR/config.ini" "$RATANA_CONFIG_DIR/config.ini.bak"
    echo -e "  [✓] Backed up existing config to $RATANA_CONFIG_DIR/config.ini.bak"
else
    cp "$SCRIPT_DIR/config.ini" "$RATANA_CONFIG_DIR/config.ini"
    echo -e "  [✓] Created default config.ini at $RATANA_CONFIG_DIR/config.ini"
fi

# Quickshell Pro installation
if [ "$FRONTEND_CHOICE" != "waybar" ] && [ -d "$SCRIPT_DIR/quickshell" ]; then
    echo -e "\n${BLUE}[*] Deploying Quickshell Pro Edition to $RATANA_CONFIG_DIR/quickshell ...${NC}"
    mkdir -p "$RATANA_CONFIG_DIR/quickshell"
    cp -r "$SCRIPT_DIR/quickshell/"* "$RATANA_CONFIG_DIR/quickshell/"
    echo -e "  [✓] Quickshell Pro QML components installed"
fi

echo -e "\n${BLUE}[*] Configuring systemd user service...${NC}"
mkdir -p "$SYSTEMD_USER_DIR"
cp "$SCRIPT_DIR/island.service" "$SYSTEMD_USER_DIR/island.service"
systemctl --user daemon-reload 2>/dev/null || true
echo -e "  [✓] Copied island.service to $SYSTEMD_USER_DIR"

# -----------------------------------------------------------------------------
# 5. INTEGRATION INSTRUCTIONS
# -----------------------------------------------------------------------------
echo -e "\n${GREEN}====================================================${NC}"
echo -e "${GREEN}   ✅ Installation Completed Successfully!          ${NC}"
echo -e "${GREEN}====================================================${NC}"

if [ "$FRONTEND_CHOICE" != "quickshell" ]; then
    echo -e "🔹 ${BLUE}Waybar Lite Edition Setup:${NC}"
    echo -e "   1. Add 'custom/island' to 'modules-center' in: $WAYBAR_CONFIG_DIR/config.jsonc"
    echo -e "   2. Append $SCRIPT_DIR/style.css to: $WAYBAR_CONFIG_DIR/style.css"
    echo -e "   3. Reload Waybar: ${GREEN}killall -SIGUSR2 waybar${NC}"
    echo -e ""
fi

if [ "$FRONTEND_CHOICE" != "waybar" ]; then
    echo -e "🔹 ${BLUE}Quickshell Pro Edition Setup (Standalone Overlay):${NC}"
    echo -e "   1. Set frontend:   ${GREEN}island-ctl frontend quickshell${NC}"
    echo -e "   2. Launch overlay: ${GREEN}island-ctl frontend start quickshell${NC}"
    echo -e "   3. Autostart in ~/.config/sway/config:"
    echo -e "      ${YELLOW}exec_always --no-startup-id island-ctl frontend start quickshell${NC}"
    echo -e ""
fi

echo -e "🔹 ${BLUE}Useful CLI Commands:${NC}"
echo -e "   ${GREEN}island-ctl status${NC}                # System diagnostics"
echo -e "   ${GREEN}island-ctl bluetooth status${NC}      # Real Bluetooth state"
echo -e "   ${GREEN}island-ctl bluetooth scan${NC}        # Discover devices"
echo -e "   ${GREEN}island-ctl volume mute${NC}           # Toggle audio mute"
echo -e "   ${GREEN}island-ctl brightness up${NC}         # Increase backlight"
echo -e "   ${GREEN}island-ctl pomodoro start${NC}        # 25m Focus Session"
echo -e "   ${GREEN}island-ctl menu${NC}                  # Quick Actions"
echo -e ""
