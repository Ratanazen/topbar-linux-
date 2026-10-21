#!/usr/bin/env bash
# ============================================================
# Ratana Top Bar — Safe Non-Destructive Installer
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/waybar"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="${TARGET_DIR}_backup_${TIMESTAMP}"

echo "=== Installing Ratana Top Bar ==="

# 1. Run tests first
echo "-> Validating configurations before installing..."
"$SCRIPT_DIR/tests/test_scripts.sh"

# 2. Backup existing Waybar configuration
if [[ -d "$TARGET_DIR" ]]; then
    echo "-> Creating backup of existing Waybar config at: $BACKUP_DIR"
    cp -r "$TARGET_DIR" "$BACKUP_DIR"
    echo "$BACKUP_DIR" > "$TARGET_DIR/.last_backup"
else
    mkdir -p "$TARGET_DIR"
fi

# 3. Install scripts
mkdir -p "$TARGET_DIR/scripts"
cp "$SCRIPT_DIR/scripts/"*.sh "$TARGET_DIR/scripts/"
chmod +x "$TARGET_DIR/scripts/"*.sh

# 4. Install config and stylesheet
cp "$SCRIPT_DIR/config/waybar/config.jsonc" "$TARGET_DIR/config.jsonc"
cp "$SCRIPT_DIR/config/waybar/style.css" "$TARGET_DIR/style.css"

# Keep track of last backup path in target dir
echo "$BACKUP_DIR" > "$TARGET_DIR/.last_backup"

echo "-> Configuration files successfully deployed to: $TARGET_DIR"

# 5. Reload Waybar
echo "-> Reloading Waybar..."
if pgrep -x waybar >/dev/null; then
    # Try SIGUSR2 reload, or clean restart if needed
    pkill -SIGUSR2 waybar 2>/dev/null || true
    sleep 0.5
    # If not updated, restart swaybar
    swaymsg reload 2>/dev/null || true
fi

echo "=== Ratana Top Bar Installed Successfully ==="
echo "To restore previous configuration anytime, run: $SCRIPT_DIR/uninstall.sh"
