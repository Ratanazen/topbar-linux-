# Ratana Top Bar — macOS-Inspired Floating Top Bar for Sway/SwayFX

A production-grade, macOS-inspired Linux top bar for **Waybar**, tailored specifically for **Sway and SwayFX** on Arch Linux / Garuda Linux. Built to replicate the minimalist floating glass aesthetic of the reference design ([V23.png](file:///home/reny/.config/waybar/V23.png)).

---

## Architecture & Layout

The panel is structured into three visually separated floating capsules with a translucent glass background, rounded borders, and subtle drop shadows:

```
+------------------------------------------------------------------------------------------------------------------------+
| [      0 ]  [ 1  2  3  4  5 ]           [ 👻 cbonsai --screensave ~ ]           [ < 󰖔   󰤨  17%  01% 󰂄 28% 󰾅 Balanced 🌦️ 29°C  08:37 Sun ] |
+------------------------------------------------------------------------------------------------------------------------+
  <---- Zone A: Left Capsules ---->             <-- Zone B: Center Title -->             <--------- Zone C: Right Status Capsule --------->
```

### Zone A — Left Floating Capsules
1. **Settings & Status Capsule (`#left1`)**:
   - `custom/omarchy`: Application menu / Settings (``), click opens Fuzzel, right-click opens nwg-drawer.
   - `idle_inhibitor`: Eye visibility icon (`` / ``), toggles system sleep prevention.
   - `custom/update`: Pending update icon with package counter (``), click launches `garuda-update`.
2. **Workspaces Capsule (`#workspaces`)**:
   - Workspaces 1 through 5.
   - Active / focused workspace is highlighted with a distinct rounded pill background (`#c8c0a8` warm light tan / gold) with dark text.
   - Inactive workspaces are rendered with subtle opacity.
   - Supports smooth switching via native Sway IPC.

### Zone B — Center Floating Title Capsule
- **Window Title (`.modules-center` / `#window`)**:
  - Floating pill centered horizontally on the output.
  - Automatically displays application glyphs (`󰈹` Firefox, `󰨞` VS Code, `󰄛` Terminal, `` Spotify, `` Chrome, `👻` cbonsai/screensaver).
  - Truncated with ellipsis at 55 characters to maintain symmetry.
  - Full Unicode and Khmer script support (`Noto Sans Khmer`).

### Zone C — Right Floating Status Capsule
- **System Information (`.modules-right`)**:
  - `group/tray-expander`: Collapsible tray drawer with chevron `<`.
  - `custom/darkmode`: Moon/sun toggle button (`󰖔` / `󰖙`) synchronized with desktop theme manager.
  - `bluetooth`: Bluetooth connection state and manager launcher (``).
  - `pulseaudio`: Audio volume, mute indicator, scroll-to-adjust, click for `pavucontrol`.
  - `network`: Wi-Fi signal glyph with tooltip bandwidth and connection editor.
  - `memory`: Real-time RAM utilization percentage (` 17%`).
  - `cpu`: Real-time CPU utilization percentage (` 01%`).
  - `battery`: Real-time battery percentage with capacity and charging glyphs (`󰂄 28%`).
  - `custom/power-profile`: Reads real ACPI platform profile (`/sys/firmware/acpi/platform_profile`), click cycles `Quiet`, `Balanced`, `Performance`.
  - `custom/weather`: Weather icon and temperature from `wttr.in`, 30-minute disk cache, fails silently when offline.
  - `clock`: Clock and date (` 08:37 Sun`), click opens interactive calendar.

---

## Installation & Deployment

### Quick Install
To install with automated backup of your current Waybar configuration:

```bash
cd ratana-topbar
./install.sh
```

The installer:
1. Runs automated tests verifying syntax and script responses.
2. Backups your existing configuration to `~/.config/waybar_backup_<timestamp>/`.
3. Installs the new `config.jsonc`, `style.css`, and helper scripts.
4. Signals Waybar to reload seamlessly (`pkill -SIGUSR2 waybar`).

### Instant Rollback / Uninstall
To restore your previous configuration at any time:

```bash
cd ratana-topbar
./uninstall.sh
```

---

## Testing

Run the automated test suite:

```bash
./tests/test_scripts.sh
```

This verifies:
- `config.jsonc` valid JSON formatting.
- `style.css` stylesheet presence and line count.
- `power-profile.sh` JSON output compliance.
- `toggle_dark_light.sh` JSON output compliance.
- `weather.sh` JSON output compliance and offline fallback.
