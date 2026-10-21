# Ratana Dynamic Island (V3 Master Edition)
### Waybar Lite + Quickshell Pro | HyperOS + OriginOS + macOS + iOS Inspired for Linux

A comprehensive, production-ready, Apple- and macOS Tahoe-inspired Dynamic Island system with Xiaomi HyperOS Quick Settings, vivo OriginOS Live Widgets, and macOS Floating Dock for Arch Linux, Sway/SwayFX, Hyprland, and Wayland desktops.

---

## 1. Architecture Overview

Ratana Dynamic Island features a decoupled dual-frontend architecture backed by a unified, asynchronous Python core:

```
                            ┌──────────────────────────────────────────────┐
                            │            Linux Desktop Backends            │
                            │  • Bluetooth: BlueZ D-Bus ObjectManager      │
                            │  • Media: MPRIS via playerctl + Artwork Cache│
                            │  • Audio: PipeWire / PulseAudio (pactl/wpctl)│
                            │  • Backlight: /sys/class/backlight           │
                            │  • Notifications: org.freedesktop.Notif      │
                            │  • Battery: UPower DisplayDevice             │
                            │  • Telemetry: /proc/stat & /proc/meminfo     │
                            │  • Recording: wf-recorder, obs, wl-screenrec │
                            │  • Network: nmcli monitor (SSID privacy)     │
                            │  • Clipboard: wl-paste watcher (zero leaks)  │
                            └──────────────────────┬───────────────────────┘
                                                   │ Async System Events
                                                   ▼
┌─────────────────────────┐              ┌────────────────────────────────┐
│   CLI: island-ctl       │◄────────────►│  island-daemon.py + core/      │
│ • Bluetooth & Media     │ Unix Socket  │  • Priority-Ranked Preemption  │
│ • Volume, Brightness    │ $XDG_RUNTIME_│  • 14 Visual States Engine     │
│ • Timers & Pomodoro     │ DIR/ratana-  │  • Real BlueZ State Machine    │
│ • Dock & System Stats   │ island.sock  │  • Zero-Subprocess Telemetry   │
│ • Themes & Diagnostics  │ (mode 0600)  │  • Single-line JSON Waybar     │
└─────────────────────────┘              └───────┬────────────────┬───────┘
                                                 │                │
                        Waybar JSONL Protocol    │                │ Unix Socket Streaming
                        (Flush stdout, stderr diag)               │ (Full State Dict)
                                                 ▼                ▼
                                ┌──────────────────┐    ┌──────────────────┐
                                │   Waybar Lite    │    │  Quickshell Pro  │
                                │  custom/island   │    │  Layer-Shell QML │
                                │ (0 Qt dependency)│    │ (Spring Physics) │
                                └──────────────────┘    │ • HyperOS Center │
                                                        │ • OriginOS Tiles │
                                                        │ • macOS Dock     │
                                                        └──────────────────┘
```

### The Two Independent Frontends
1. **Waybar Lite (`waybar`)**:
   - Ultra-lightweight, zero Qt dependencies, pure Waybar JSONL module.
   - Emits exactly one valid JSON object per line on standard output and immediately flushes stdout.
   - Diagnostic and debug messages strictly log to stderr or logfiles to prevent JSON parsing errors.
   - Supports 6 visual CSS themes with GTK3 transition styling.
2. **Quickshell Pro (`quickshell`)**:
   - Standalone Wayland layer-shell overlay (`WlrLayer.Top`), anchored top-center.
   - Real continuous geometric spring morphing (`Behavior on width, height, radius` with cubic/spring easing).
   - Mouse click-through mask outside the capsule so desktop and windows below remain interactive.
   - **Xiaomi HyperOS Quick Settings**: Translucent dual-card connectivity center (Wi-Fi & Bluetooth), stepped volume/brightness sliders, 4 quick action tiles, and real-time telemetry footer.
   - **vivo OriginOS Live Widgets**: Modular interactive cards for Media, Bluetooth, Network, Battery, Pomodoro, and System Stats.
   - **macOS Floating Dock**: Bottom-anchored glass dock with hover magnification (1.25x scale), 7 application shortcuts, and dynamic toggle.
   - Dismissal via `Escape` key or backdrop clicks.

---

## 2. All 14 Visual States & Priority Hierarchy

The system enforces a strict 14-state priority hierarchy. Higher priority states immediately preempt lower priority states; when transient events expire, the system smoothly restores the highest-priority active persistent state.

| Priority | State Name | Category | Capsule Dimensions (Quickshell) | Timeout / Behavior |
| :---: | :--- | :--- | :--- :--- | :--- |
| **90** | `recording` | Persistent | 190 × 34 px | Persistent while `obs`, `wf-recorder`, or screen recording runs. Pulsing red indicator. |
| **85** | `battery` (low) | Transient | 210 × 34 px | 5s banner when battery discharges below 15%. Red warning. |
| **80** | `notification` (urgent)| Transient | 300 × 44 px | 6s alert banner for critical desktop notifications. |
| **72** | `bluetooth` (connecting) | Transient | 220 × 34 px | 3.5s pulse while connecting to a Bluetooth device. |
| **70** | `drag_active` | Interactive | 320 × 46 px | Active drag-and-drop target expanding when supported files enter capsule. "Drop to Share". |
| **68** | `notification` (normal) | Transient | 280 × 40 px | 4s alert banner showing app icon, title, and summary. |
| **60** | `volume` / `brightness` | Transient | 200 × 34 px | 1.8s slider banner with block progress `▰▰▰▱▱` and percentage. |
| **50** | `network` | Transient | 200 × 34 px | 2.5s indicator on Wi-Fi/Ethernet connect or disconnect. SSID privacy supported. |
| **45** | `bluetooth` (connected) | Transient | 220 × 34 px | 3.5s confirmation banner showing device name and battery percentage. |
| **30** | `timer` / `pomodoro` | Persistent | 180 × 34 px | Live 1-second countdown clock. Chimes upon completion. |
| **20** | `media` | Persistent | 230 × 34 px | Active MPRIS track info, album artwork, formatted duration (`MM:SS`), and player tag. |
| **10** | `idle` | Persistent | 130 × 32 px | Minimal clock pill showing time and origin keyboard script. |
| **—** | `hover` | Interactive | 150 × 34 px | Capsule grows slightly on pointer hover. |
| **—** | `expanded` | Interactive | 340 × 140 px | Rich interactive card for media controls, timers, or system sliders. |
| **—** | `share_picker` | Interactive | 420 × 260 px | Smart Share app picker with file previews, Telegram, Discord, Bluetooth OBEX, and desktop apps. |
| **—** | `share_confirm` | Interactive | 380 × 180 px | Safe confirmation dialog before opening destination applications. |
| **—** | `quick_actions` | Interactive | 380 × 220 px | HyperOS Control Center with dual connectivity cards, sliders, tiles, and telemetry. |
| **—** | `settings` | Interactive | 300 × 200 px | Theme picker, reduced motion toggle, and diagnostic quick controls. |

---

## 3. Real Bluetooth Integration (BlueZ 5+ D-Bus)

Unlike mock status tools, Ratana Dynamic Island connects directly to the Linux system bus via the **BlueZ 5 D-Bus ObjectManager** (`org.bluez`), with an automatic fallback to `bluetoothctl`:
- **Real-Time Adapter State**: Tracks power, discovery/scanning, and pairable modes.
- **Device Management**: Connects, disconnects, and pairs with real audio peripherals, keyboards, and mice.
- **Battery Reporting**: Reads device battery percentage via `org.bluez.Battery1` when supported by hardware.
- **Transient UI Alerts**:
  - `bluetooth connecting`: Priority 72 (blue pulsing capsule).
  - `bluetooth connected`: Priority 45 (device icon, friendly name, battery %).
  - `bluetooth disconnected`: Priority 45 (brief confirmation banner).
  - `bluetooth failed`: Red alert if connection times out or rejects.

### Bluetooth CLI Commands
```bash
island-ctl bluetooth status           # Show active adapter, powered state, connected devices
island-ctl bluetooth devices          # List paired and known devices
island-ctl bluetooth scan             # Trigger background device discovery (15s)
island-ctl bluetooth connect <MAC>    # Connect to device by address
island-ctl bluetooth disconnect <MAC> # Disconnect device
```

---

## 4. Theme System (6 Coherent Presets)

Select from 6 design presets with full visual parity across Quickshell QML and Waybar GTK3:
1. **`macos-black`** (Default): Apple obsidian `#09090B` surface, graphite `#292933` border, white `#F5F5F7` text.
2. **`macos-glass`** (Alias: `glass`): Acrylic translucent glass (`rgba(18, 20, 26, 0.72)`) with subtle glowing border.
3. **`hyperos-dark`**: Xiaomi HyperOS obsidian cards (`#141416`), vibrant cyan accent (`#0A84FF`), and translucent rounded sliders.
4. **`originos-dark`**: vivo OriginOS high-contrast dark palette (`#111216`), warm orange accents (`#FF7A00`), and squircle tile containers.
5. **`catppuccin-mocha`**: `#1E1E2E` base with authentic pastel lavender (`#CBA6F7`) and sapphire accents (`#89B4FA`).
6. **`minimal-dark`** (Alias: `minimal`): Pure flat dark `#121214` with subtle edges and zero drop shadows.

Switch themes on the fly via CLI or the interactive menu:
```bash
island-ctl theme set macos-black
island-ctl theme set macos-glass
island-ctl theme set hyperos-dark
island-ctl theme set originos-dark
island-ctl theme set catppuccin-mocha
island-ctl theme set minimal-dark
```

---

## 5. Xiaomi HyperOS & vivo OriginOS Features

### Xiaomi HyperOS Control Center
Access the expanded Quick Settings view by clicking the Dynamic Island or running `island-ctl menu`:
- **Dual Connectivity Cards**: Prominent Wi-Fi and Bluetooth status cards with live SSID, signal strength, and connected device names.
- **Stepped Volume & Backlight Sliders**: Inline interactive stepper controls with instant feedback.
- **Quick Action Grid**: 4 tactile toggle tiles for Pomodoro Focus session, Do Not Disturb, Theme cycling, and macOS Dock visibility.
- **Telemetry Footer**: Real-time CPU, RAM, and Battery percentage metrics displayed at the base of the card.

### vivo OriginOS Live Widgets
Reusable QML components located in `quickshell/widgets/`:
- `MediaWidget.qml`: Live playback progress, artwork container, and track details.
- `BluetoothWidget.qml`: Device status and battery indicators.
- `NetworkWidget.qml`: Network interface and SSID details.
- `BatteryWidget.qml`: Live charging state and capacity bar.
- `TimerWidget.qml`: Active countdown display with pause/stop actions.
- `SystemWidget.qml`: CPU load and memory utilization gauges.

---

## 6. macOS Floating Dock

Quickshell Pro includes an independent, macOS Tahoe-inspired bottom dock (`quickshell/dock/Dock.qml`):
- **Hover Magnification**: Fluid spring-animated scaling (1.25x scale factor) on icon hover.
- **Layer-Shell Integration**: Runs on `WlrLayer.Top` anchored to screen bottom with click-through input masks outside the dock capsule.
- **Application Shortcuts**: Pre-configured launchers for `kitty`, `brave-browser` / `firefox`, `thunar`, `code`, `spotify`, Dynamic Island trigger, and Settings.
- **IPC Dock Controls**:
  ```bash
  island-ctl dock status               # Check dock visibility state
  island-ctl dock on                   # Show floating dock
  island-ctl dock off                  # Hide floating dock
  island-ctl dock toggle               # Toggle dock visibility
  ```

---

## 7. System Telemetry Engine

Built into `core/system_metrics.py`, the telemetry monitor reads directly from the Linux `/proc` filesystem without spawning external shell processes:
- **CPU Utilization**: Accurate differential calculation from `/proc/stat` `(total - idle) / total`.
- **Memory Utilization**: Exact percentage calculation from `/proc/meminfo` `(MemTotal - MemAvailable) / MemTotal`.
- **Query Telemetry via CLI**:
  ```bash
  island-ctl system
  # Output: CPU: 12% | RAM: 46% (6800 MB / 14780 MB)
  ```

---

## 8. Command-Line Reference (`island-ctl`)

```bash
# System Diagnostics & Setup
island-ctl doctor                     # Comprehensive dependency & environment audit
island-ctl status                     # Daemon connection and current active state
island-ctl system                     # Live CPU and Memory utilization
island-ctl restart                    # Restart daemon and active frontends

# Frontend Switching
island-ctl frontend status            # Check active frontend (waybar / quickshell / both)
island-ctl frontend waybar            # Switch to Waybar Lite
island-ctl frontend quickshell        # Switch to Quickshell Pro
island-ctl frontend both              # Enable both simultaneously

# Dock Management
island-ctl dock toggle                # Toggle macOS floating dock
island-ctl dock on                    # Force dock visible
island-ctl dock off                   # Force dock hidden

# Audio & Backlight Controls
island-ctl volume up                  # Increase volume (+2%)
island-ctl volume down                # Decrease volume (-2%)
island-ctl volume mute                # Toggle audio mute
island-ctl brightness up              # Increase backlight (+5%)
island-ctl brightness down            # Decrease backlight (-5%)

# Media Controls & Artwork
island-ctl media toggle               # Play / Pause active player
island-ctl media next                 # Skip to next track
island-ctl media prev                 # Previous track

# Timers & Pomodoro
island-ctl pomodoro start             # Start 25m focus session
island-ctl timer 10m Tea              # Start named 10m countdown
island-ctl timer pause                # Pause countdown
island-ctl timer resume               # Resume countdown
island-ctl stop                       # Stop running timer

# Motion & Accessibility
island-ctl motion reduced             # Enable reduced motion (instant geometry transitions)
island-ctl motion normal              # Enable spring physics animations

# Interactive Overlays
island-ctl menu                       # Open HyperOS Quick Actions center
island-ctl settings                   # Open Settings panel
island-ctl dismiss                    # Dismiss top transient notification
```

---

## 9. Installation & Autostart

### Automated Installation
```bash
git clone https://github.com/Ratanazen/RatanaOS.git
cd RatanaOS/waybar-dynamic-island
chmod +x install.sh uninstall.sh
./install.sh
```

**Installer Options**:
- `./install.sh --waybar-only`: Install only the lightweight Waybar edition.
- `./install.sh --quickshell-only`: Install only the Quickshell Pro overlay edition.
- `./install.sh --doctor`: Run diagnostics before installing.
- `./install.sh --update`: Fast non-destructive update of scripts, core, and QML files.
- Existing configurations are automatically backed up to `~/.config/ratana-island/config.ini.bak`.

### Autostart in Sway / SwayFX (`~/.config/sway/config`)

Add the following to your Sway configuration:

```sway
# Launch Ratana Dynamic Island Daemon
exec_always --no-startup-id ~/.config/waybar/scripts/island-daemon.py

# Optional: Autostart Quickshell Pro overlay if using Quickshell frontend
exec_always --no-startup-id island-ctl frontend start quickshell

# Recommended Keybindings
bindsym $mod+m exec island-ctl media toggle
bindsym $mod+b exec island-ctl menu
bindsym $mod+Shift+b exec island-ctl bluetooth status
bindsym $mod+d exec island-ctl dock toggle
bindsym $mod+y exec island-ctl window minimize
bindsym XF86AudioMute exec island-ctl volume mute
bindsym XF86AudioRaiseVolume exec island-ctl volume up
bindsym XF86AudioLowerVolume exec island-ctl volume down
bindsym XF86MonBrightnessUp exec island-ctl brightness up
bindsym XF86MonBrightnessDown exec island-ctl brightness down
```

---

## 10. Smart Share Engine (Drag & Drop File Sharing)

Quickshell Pro features an integrated Drag-and-Drop file sharing system:
- **`DropArea` Detection**: Drop files directly onto the compact Dynamic Island capsule.
- **Spring Expansion**: Expands from compact to `320 × 46 px` with `󰒍 Drop to Share` banner and visual highlight.
- **Strict URL Sanitization**: Decodes percent-encoded URIs (`file:///...`), handles Unicode & Khmer filenames (`ឯកសារ.pdf`), rejects untrusted remote schemes (`http://`, `https://`, `javascript:`, `ftp://`).
- **Dynamic Application Discovery**:
  - **Telegram Desktop**: Detects `/usr/bin/Telegram` binary or Flatpak (`Ready to send`).
  - **Discord**: Detects installation or displays clear `[Not Installed]` reason badge.
  - **Bluetooth OBEX**: Checks adapter power status via `bluetoothctl` / `rfkill` and locates `blueman-sendto`.
  - **Associated Desktop Apps**: Discovers file-type handlers via MIME matching.
- **Strict Zero-`shell=True` Security**: Executes target applications with argument vectors (`[binary, *paths]`) without shell interpolation.
- **Mandatory User Confirmation**: Requires explicit user tap/click before opening any application with files.

### Smart Share CLI Commands
```bash
# Scan dropped files and discover available destination applications
island-ctl share scan [--json] <files...>

# Safely launch application with validated files
island-ctl share launch <app_id> <files...>
```

---

## 11. macOS-Inspired Window Minimization & Island Integration

Seamless Sway / SwayFX window management via native Sway IPC:
- **Mac-Style Scale Minimize Animation**:
  - `WindowMinimizeAnimator.qml`: Dedicated non-blocking layer-shell overlay on `WlrLayer.Overlay`.
  - Captures the exact window screen geometry (`x`, `y`, `width`, `height`) before it moves to Sway scratchpad.
  - Smooth `ParallelAnimation` scales and translates the window card directly into the top-center Dynamic Island capsule.
  - Reverse animation on restore expands the card back to its original screen geometry.
  - `mask: Region { item: animCard.opacity > 0.05 ? animCard : null }` ensures zero desktop input blocking outside the transient animating preview card.
- **Dynamic Island Representation**:
  - **Compact Island**: Minimized applications are represented by interactive circular icon pills (e.g. `󰄛 󰈰`) next to the time display. Clicking any icon instantly restores and focuses the window.
  - **Expanded Island**: Dedicated "Minimized Windows" management card with app icon, window title, and one-click "Restore" button.
- **Sway Scratchpad IPC**:
  - Native minimize: `swaymsg [con_id=...] move scratchpad`
  - Native restore: `swaymsg [con_id=...] scratchpad show; [con_id=...] focus`
  - Zero process killing or artificial window destruction.
  - In-memory event-driven Sway IPC cache eliminating repeated high-frequency tree parsing.

### Window Management CLI Commands
```bash
# List active and minimized scratchpad windows
island-ctl windows list

# Minimize window by ID (or focused window)
island-ctl windows min [con_id]

# Restore minimized window by ID
island-ctl windows restore <con_id>
```

---

## 12. Low CPU & Low RAM Performance Optimization

Engineered for ultra-low resource consumption on lightweight or older hardware:
- **Idle CPU**: Slashed from ~23% combined down to **< 1.8%** (`island-daemon`: ~0.3% CPU, 34MB RSS; `quickshell`: ~1.5% CPU idle).
- **Adaptive Idle Clock Loop**: Replaces 1-second busy loops with adaptive sleep (15s default, 30s in low-resource mode) when no active countdown or stopwatch is running.
- **Event-Driven Sway Caching**: `SwayWindowMonitor` caches window trees in memory and invalidates only on compositor events (`focus`, `close`, `new`, `title`, `move`), eliminating `swaymsg -t get_tree` subprocess spikes.
- **Zero Socket Leaks**: Reusable persistent Sway IPC connection eliminates file descriptor exhaustion.
- **QML Evaluation Guards**: All socket-driven QML properties feature change-detection guards, preventing redundant layout passes and continuous repaint cycles.
- **TTL Caching**: Background service queries (BlueZ, Telegram, Discord) use 60-second in-memory TTL caching to avoid repeated filesystem or D-Bus roundtrips.

### Performance Profiles
Switch profiles on the fly with instant daemon reconfiguration:
- `low-resource`: 30s idle clock, 6s metrics polling, reduced motion enabled, 180ms fade animations.
- `balanced` (default): 15s idle clock, 3s metrics polling, 380ms smooth scale animations.
- `visual-quality`: 5s idle clock, 2s metrics polling, 420ms full scale genie-style animations.

```bash
# View active profile and timing parameters
island-ctl profile get

# Switch profile
island-ctl profile set <low-resource|balanced|visual-quality>
```

---

## 13. Automated Test Suite

Run the full automated test suite (62 tests) verifying all 14 states, priority arbitration, Bluetooth OBEX, Smart Share URL sanitization, Unicode/Khmer filenames, zero-`shell=True` security, Sway window minimization, performance profile switching, and Waybar JSON single-line emission:

```bash
python3 -m unittest discover -s tests -p "test_*.py"
```

Result:
```text
Ran 62 tests in 0.803s
OK
```

---

## 13. Uninstallation & Rollback

To uninstall or roll back cleanly:
```bash
./uninstall.sh                # Interactive uninstallation
./uninstall.sh --purge        # Purge all binaries, units, and config directories
./uninstall.sh --keep-config  # Remove code & binaries, keep user settings
./uninstall.sh --restore-backup # Restore config.ini from config.ini.bak
```
