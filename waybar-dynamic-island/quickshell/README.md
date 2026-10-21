# Ratana Dynamic Island — Quickshell Pro Edition
### Standalone macOS Tahoe-Inspired Wayland Dynamic Island Overlay

A native Wayland animated Dynamic Island overlay for **Arch Linux** running **Sway/SwayFX**, **Hyprland**, and compatible wlroots compositors, built with **Quickshell** (Qt 6 / QML).

---

## 1. Overview & Architecture

The **Quickshell Pro Edition** delivers authentic Apple Dynamic Island morphological capsule transitions on the Linux desktop:
- **Continuous Geometry Morphing**: Real spring-based transitions for capsule `width`, `height`, and `radius` using QML `Behavior` and spring / cubic easing physics.
- **Wayland Layer Shell (`WlrLayer.Top`)**: Anchored top-center on the active monitor, rendering above tiling and floating application windows.
- **Input Region Pass-Through Mask**: Clicks outside the active capsule pass directly through to windows below (`mask: Region { item: capsule }`), maintaining normal desktop interactivity.
- **Single Source of Truth**: Connects directly to the modular Python backend (`island-daemon.py`) over `$XDG_RUNTIME_DIR/ratana-island.sock` using high-speed Unix socket JSON streaming. Zero duplicate backend logic.
- **Instant Dismissal**: Dismiss expanded views, settings, or transient banners instantly via the `Escape` key or by clicking anywhere outside the capsule.

```
                          ┌────────────────────────┐
                          │   island-daemon.py     │
                          │   + core/ package      │
                          └───────────┬────────────┘
                                      │ Unix Socket (JSON Streaming)
                                      ▼
                        ┌───────────────────────────┐
                        │   Quickshell Pro Layer    │
                        │ - shell.qml (LayerShell)  │
                        │ - IslandCapsule.qml       │
                        │ - IslandContent.qml       │
                        │ - 14 Visual State Views   │
                        │ - IslandBridge Singleton  │
                        └───────────────────────────┘
```

---

## 2. Component Structure

```text
quickshell/
├── shell.qml                   # ShellRoot entry point, LayerShell, Variants
├── README.md                   # This documentation
├── themes/
│   ├── qmldir                  # QML singleton module definition
│   └── Theme.qml               # Theme color tokens (macos-black, catppuccin, glass, minimal)
├── services/
│   ├── qmldir                  # QML singleton module definition
│   └── IslandBridge.qml        # Unix socket connection, IPC commands, state model
└── components/
    ├── IslandCapsule.qml       # Morphological capsule with spring easing & Esc handler
    ├── IslandContent.qml       # State-driven cross-fading router for all 14 visual states
    ├── CompactView.qml         # Minimal pill showing origin keyboard script and clock
    ├── ExpandedView.qml        # Expanded card for media, sliders, or timers
    ├── EventView.qml           # Generic transient banner for clipboard, network, system
    ├── BluetoothView.qml       # Real BlueZ device status, battery %, and connection pulse
    ├── MediaView.qml           # MPRIS album art, track title, and playback controls
    ├── NotificationView.qml    # High-priority alert banner with dismiss action
    ├── RecordingView.qml       # Pulsing red recording dot & process status
    ├── VolumeView.qml          # Smooth volume slider with speaker icon & mute toggle
    ├── BrightnessView.qml      # Backlight slider with sun icon
    ├── TimerView.qml           # Countdown timer & Pomodoro status with stop button
    ├── QuickActions.qml        # macOS Tahoe 6-button quick controls grid
    └── Settings.qml            # Theme selector, motion toggle, and DND controls
```

---

## 3. The 14 Visual States & Morphing Dimensions

| State | Capsule Size (W × H) | Corner Radius | Description |
| :--- | :---: | :---: | :--- |
| `idle` | 130 × 32 px | 16 px | Compact pill with time and keyboard script |
| `hover` | 150 × 34 px | 17 px | Gentle expansion under pointer cursor |
| `media` | 230 × 34 px | 17 px | Active track and playback indicator |
| `bluetooth` | 220 × 34 px | 17 px | BlueZ connection pulse or device battery % |
| `volume` | 200 × 34 px | 17 px | Audio level and block progress indicator |
| `brightness` | 200 × 34 px | 17 px | Backlight slider display |
| `network` | 200 × 34 px | 17 px | Network connection banner |
| `battery` | 210 × 34 px | 17 px | Low battery warning (<15%) or charging state |
| `recording` | 190 × 34 px | 17 px | Red pulsing recording indicator |
| `notification` | 280 × 40 px | 20 px | Desktop notification banner |
| `timer` / `pomodoro` | 180 × 34 px | 17 px | Live countdown timer |
| `quick_actions` | 300 × 180 px | 24 px | 6-button quick settings grid |
| `expanded` | 340 × 140 px | 24 px | Full interactive media player / slider card |
| `settings` | 300 × 200 px | 24 px | System settings and theme customizer |

---

## 4. Mouse & Keyboard Interactions

| Input | Target State | Action |
| :--- | :--- | :--- |
| **Left Click** | `idle` | Opens Quick Actions menu |
| **Left Click** | `media` | Expands capsule to full media controls card |
| **Left Click** | `timer` / `pomodoro`| Expands capsule to timer controls |
| **Left Click** | `notification` | Dismisses the current notification |
| **Right Click** | Any | Toggles Quick Actions menu |
| **Middle Click** | Any | Toggles Media Play/Pause |
| **Scroll Wheel Up/Down**| Any | Adjusts master audio volume |
| **Escape Key (`Esc`)** | `expanded`, `quick_actions`, `settings` | Closes expanded views back to compact state |

---

## 5. Controlling the Overlay via CLI (`island-ctl`)

```bash
# Frontend Management
island-ctl frontend status            # Check status of Quickshell and Waybar
island-ctl frontend set quickshell    # Select Quickshell Pro as default
island-ctl frontend start quickshell  # Launch Quickshell overlay in background
island-ctl frontend stop quickshell   # Terminate running Quickshell instance

# Motion Control
island-ctl motion reduced             # Instant geometry transitions (accessibility)
island-ctl motion normal              # Smooth spring physics animations

# Interactive Views
island-ctl menu                       # Trigger Quick Actions grid
island-ctl settings                   # Open Settings panel
island-ctl dismiss                    # Dismiss transient banners
```

---

## 6. Autostart Configuration

### For Sway / SwayFX (`~/.config/sway/config`)

```sway
# Launch Quickshell Dynamic Island overlay on login
exec_always --no-startup-id island-ctl frontend start quickshell
```

### Manual Testing

Test the Quickshell overlay directly from the source directory:
```bash
quickshell -p quickshell/shell.qml
```
