# Ratana Dynamic Island (Native C)

A polished, native C11 desktop application providing an Apple macOS Tahoe / iPhone-inspired Dynamic Island for Sway and SwayFX on Wayland (Arch Linux / Garuda Linux).

---

## Key Features

- **Native C11 & GTK4**: Pure C application with ultra-low memory (~25MB) and near-zero CPU usage (<0.5%).
- **Wayland Layer Shell**: Centered at the top of the monitor using `gtk4-layer-shell` on the `OVERLAY` layer, floating smoothly above Waybar without pushing windows down (`exclusive_zone = 0`).
- **Waybar Preserved 100%**: Coexists seamlessly with your existing Waybar setup. The input hit area is strictly confined to the island pill itself, allowing mouse clicks to pass through to Waybar modules to the left, right, and beneath.
- **Apple Dynamic Island Media Card**: Reproduces authentic Apple expanded player proportions:
  - **Row 1**: Rounded album art container (52x52px) with async caching + Bold title + Muted artist + Live coral-orange animated equalizer waveform (`#ff6036`).
  - **Row 2**: Elapsed time label + thick solid progress slider + remaining/total duration.
  - **Row 3**: 5-item playback controls (Shuffle, Previous, Play/Pause, Next, Output / Player Cycle).
- **Intelligent Media Sanitization**:
  - Automatically cleans YouTube notification badge counts (e.g. `(904) `) and trailing ` - YouTube`.
  - Automatically extracts `Artist - Song` from video titles when browser metadata lacks artist tags.
  - Automatically fetches YouTube video thumbnails when `mpris:artUrl` is omitted.
  - Prioritizes active playing media players (`plasma-browser-integration`, Spotify, mpv) over bare browser tabs.
- **Dedicated GTK4 Preferences Dialog**:
  - Launch with `ratana-island --settings` or by **Right-Clicking** the island capsule.
  - Configure top margin, compact/expanded dimensions, animation durations, reduced motion, themes, privacy mode, and systemd autostart.
- **Hardware-Synchronized Animations (60 FPS)**: Driven by GTK4 frame-clock tick callbacks with cubic easing curves (`ANIM_EASE_OUT_CUBIC`) interpolating width, height, corner radius, and opacity.
- **Sway IPC Workspace Integration**: Subscribes directly to Sway's IPC Unix socket (`$SWAYSOCK`) to display animated workspace switch transitions without spawning subprocesses.
- **Freedesktop Notifications**: Displays incoming notifications with privacy mode support.
- **System Status (Volume & Battery)**: Real-time PulseAudio sink monitoring via `libpulse-mainloop-glib` and UPower battery status.

---

## Build & Test

### Dependencies

```bash
sudo pacman -S --needed \
  base-devel cmake pkgconf git curl \
  gtk4 gtk4-layer-shell glib2 json-glib \
  libpulse upower wayland wayland-protocols
```

### Compile & Run Tests

```bash
cd ratana-island
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel
ctest --test-dir build --output-on-failure
```

### Installation

Install binary and assets to `~/.local`:

```bash
cmake --install build --prefix ~/.local
cp -u config/* ~/.config/ratana-island/
```

---

## Usage & IPC Controls

Start the background daemon:

```bash
~/.local/bin/ratana-island &
```

Control or query the running island via CLI IPC flags:

```bash
ratana-island --toggle    # Toggle between compact pill and expanded media card
ratana-island --expand    # Expand media card
ratana-island --compact   # Collapse to compact pill
ratana-island --settings  # Open the GTK4 Preferences / Settings Dialog
ratana-island --quit      # Cleanly stop daemon and release all D-Bus/socket handles
```

Mouse interactions:
- **Left-Click**: Toggle expanded card / collapse to pill.
- **Right-Click**: Open Preferences / Settings window.
- **Output Button (5th button)**: Cycle through connected MPRIS media players.

---

## Autostart

### Option 1: Sway Configuration (Recommended)

Add to `~/.config/sway/config`:

```sway
exec_always --no-startup-id ~/.local/bin/ratana-island
```

Optional Sway keybinding to toggle the island:
```sway
bindsym $mod+i exec ~/.local/bin/ratana-island --toggle
```

### Option 2: Systemd User Service

Enable and start via systemd (or toggle via GUI Settings):

```bash
mkdir -p ~/.config/systemd/user
cp systemd/ratana-island.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now ratana-island.service
```

---

## Configuration

Configuration is located at `~/.config/ratana-island/config.ini`:

```ini
[General]
theme=mac_obsidian
low_power_mode=false
privacy_mode=false

[Dimensions]
top_margin=4
collapsed_width=190
collapsed_height=32
expanded_width=380
expanded_height=165
corner_radius_collapsed=16
corner_radius_expanded=36

[Animation]
duration_ms=240
reduced_motion=false

[Integrations]
enable_media=true
enable_sway=true
enable_notifications=true
enable_system_status=true
```

Custom CSS styling can be tuned in `~/.config/ratana-island/style.css`.

---

## Uninstallation

To cleanly remove Ratana Dynamic Island:

```bash
# 1. Stop and disable systemd service (if enabled)
systemctl --user stop ratana-island.service 2>/dev/null
systemctl --user disable ratana-island.service 2>/dev/null
rm -f ~/.config/systemd/user/ratana-island.service

# 2. Terminate any running process
killall ratana-island 2>/dev/null

# 3. Remove installed binaries and configurations
rm -f ~/.local/bin/ratana-island
rm -rf ~/.local/share/ratana-island
rm -rf ~/.config/ratana-island
rm -rf ~/.cache/ratana-island
```
