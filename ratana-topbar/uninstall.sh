#!/usr/bin/env bash
# ============================================================
# Ratana Top Bar — Rollback & Uninstaller
# ============================================================

set -e

TARGET_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/waybar"
LAST_BACKUP_FILE="$TARGET_DIR/.last_backup"

echo "=== Uninstalling Ratana Top Bar ==="

if [[ -f "$LAST_BACKUP_FILE" ]]; then
    BACKUP_PATH=$(cat "$LAST_BACKUP_FILE")
    if [[ -d "$BACKUP_PATH" ]]; then
        echo "-> Restoring previous configuration from: $BACKUP_PATH"
        cp -r "$BACKUP_PATH/"* "$TARGET_DIR/"
        echo "-> Configuration restored successfully."
    else
        echo "-> Warning: Backup path $BACKUP_PATH does not exist."
    fi
else
    # Find most recent backup directory
    LATEST_BACKUP=$(ls -td "${TARGET_DIR}_backup_"* 2>/dev/null | head -n 1)
    if [[ -n "$LATEST_BACKUP" && -d "$LATEST_BACKUP" ]]; then
        echo "-> Found most recent backup at: $LATEST_BACKUP"
        cp -r "$LATEST_BACKUP/"* "$TARGET_DIR/"
        echo "-> Restored from $LATEST_BACKUP."
    else
        echo "-> No previous backup found. Reverting to default configuration."
    fi
fi

# Reload Waybar
if pgrep -x waybar >/dev/null; then
    pkill -SIGUSR2 waybar 2>/dev/null || true
    swaymsg reload 2>/dev/null || true
fi

echo "=== Ratana Top Bar Uninstalled ==="
