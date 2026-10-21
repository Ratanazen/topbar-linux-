#!/bin/bash

# Prefer Chromium-based browsers for YouTube, then Firefox, then anything else
PLAYER="--player=brave,chromium,chrome,firefox,%any"

status=$(playerctl $PLAYER status 2>/dev/null)

if [[ -z "$status" || "$status" == "Stopped" ]]; then
    # Nothing is playing or player is stopped
    jq -n -c '{"text": "", "tooltip": "", "class": "stopped"}'
    exit 0
fi

# Get metadata using playerctl
artist=$(playerctl $PLAYER metadata artist 2>/dev/null)
title=$(playerctl $PLAYER metadata title 2>/dev/null)
album=$(playerctl $PLAYER metadata album 2>/dev/null)
player_name=$(playerctl $PLAYER metadata --format '{{playerName}}' 2>/dev/null)

# Clean up YouTube titles if needed (Optional Bash parsing)
if [[ "$player_name" == "brave" || "$player_name" == "chromium" || "$player_name" == "chrome" || "$player_name" == "firefox" ]]; then
    # Strip (Official Video) etc if present
    title=$(echo "$title" | sed -E 's/\(.*\)//g' | sed -E 's/\[.*\]//g' | xargs)
    if [[ -z "$artist" || "$artist" == "YouTube" ]]; then
        if [[ "$title" == *"-"* ]]; then
            artist=$(echo "$title" | awk -F'-' '{print $1}' | xargs)
            title=$(echo "$title" | awk -F'-' '{print $2}' | xargs)
        fi
    fi
fi

# Set icon and class based on status
if [[ "$status" == "Playing" ]]; then
    icon="󰐊"
    class="playing"
elif [[ "$status" == "Paused" ]]; then
    icon="󰏤"
    class="paused"
else
    icon="󰓛"
    class="stopped"
    jq -n -c '{"text": "", "tooltip": "", "class": "stopped"}'
    exit 0
fi

if [[ -z "$title" ]]; then
    jq -n -c '{"text": "", "tooltip": "", "class": "stopped"}'
    exit 0
fi

# Format text
if [[ -n "$artist" ]]; then
    text="$icon 󰎆 $artist - $title"
else
    text="$icon 󰎆 $title"
fi

# Truncate text (max 40 chars)
if [[ ${#text} -gt 40 ]]; then
    text="${text:0:37}..."
fi

# Prepare tooltip
tooltip="Player: ${player_name}\nStatus: ${status}"
if [[ -n "$album" ]]; then
    tooltip="${tooltip}\nAlbum: ${album}"
fi

# Output JSON for Waybar safely using jq
jq -n -c --arg text "$text" --arg tooltip "$(echo -e "$tooltip")" --arg class "$class" '{"text": $text, "tooltip": $tooltip, "class": $class}'
