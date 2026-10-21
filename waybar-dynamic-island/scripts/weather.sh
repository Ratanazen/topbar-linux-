#!/usr/bin/env bash
# ============================================================
# Ratana Top Bar — Weather Script
# Non-blocking, cached weather fetcher for Waybar
# ============================================================

CACHE_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/waybar"
CACHE_FILE="$CACHE_DIR/weather.cache"
TTL=1800 # 30 minutes in seconds

mkdir -p "$CACHE_DIR"

# Check if cache is still valid
now=$(date +%s)
if [[ -f "$CACHE_FILE" ]]; then
    last_mod=$(stat -c %Y "$CACHE_FILE" 2>/dev/null || echo 0)
    age=$((now - last_mod))
    if [[ $age -lt $TTL ]]; then
        cat "$CACHE_FILE"
        exit 0
    fi
fi

# Fetch new weather data with 3s timeout
raw=$(curl -s --max-time 3 "wttr.in/?format=%c+%t" 2>/dev/null | tr -d '\n' | sed 's/+//g')

if [[ -n "$raw" && "$raw" != *"Unknown"* && "$raw" != *"error"* ]]; then
    # Format clean output
    json_output=$(cat <<EOF
{"text":"$raw","tooltip":"Weather: $raw (Updated every 30m)","class":"weather"}
EOF
)
    echo "$json_output" > "$CACHE_FILE"
    echo "$json_output"
else
    # Return previous cache if available, or quiet fallback
    if [[ -f "$CACHE_FILE" ]]; then
        cat "$CACHE_FILE"
    else
        echo '{"text":"","tooltip":"Weather unavailable (Offline)","class":"offline"}'
    fi
fi
