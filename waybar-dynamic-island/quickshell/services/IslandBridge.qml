pragma Singleton
import Quickshell
import Quickshell.Io
import QtQuick
import "../themes"

QtObject {
    id: root

    // Socket Path
    readonly property string socketPath: {
        var runtime = Quickshell.env("XDG_RUNTIME_DIR");
        if (runtime && runtime.length > 0) {
            return runtime + "/ratana-island.sock";
        }
        return "/run/user/1000/ratana-island.sock";
    }

    // Active Daemon State Model
    property string activeState: "idle"
    property string visualState: "idle"
    property string title: ""
    property string subtitle: ""
    property string icon: "󰸗"
    property string iconPath: ""
    property real progressPct: 0.0
    property string progressBar: ""
    property int priority: 10
    property string source: "core"
    property bool reducedMotion: false
    property bool showFull: false
    property string themeName: "macos-black"

    // Media & Hardware Details
    property string artUrl: ""
    property string durationStr: ""
    property string positionStr: ""
    property string playerName: ""
    property string deviceMac: ""
    property var deviceBattery: null

    // Live System Metrics (CPU / RAM / Disk)
    property real systemCpu: 0.0
    property real systemMem: 0.0
    property real systemDiskUsed: 0.0
    property real systemDiskTotal: 0.0
    property real systemDiskPct: 0.0
    property string systemCpuName: "Ryzen 5"
    property bool panelOpen: false

    // Dock Configuration & State
    property bool dockEnabled: false
    property string dockPosition: "bottom"
    property int dockIconSize: 48
    property bool dockMagnification: true

    // Smart Share & Sway Windows State
    property var droppedFiles: []
    property var shareTargets: []
    property var runningWindows: []
    property var minimizedWindows: []
    property int selectedMinimizedIndex: 0
    property var focusedWindow: null
    readonly property var selectedMinimizedWindow: {
        if (!minimizedWindows || minimizedWindows.length === 0) return null;
        var idx = Math.max(0, Math.min(selectedMinimizedIndex, minimizedWindows.length - 1));
        return minimizedWindows[idx];
    }
    signal windowAnimationRequested(var animData)
    signal windowAbsorptionPulseRequested()

    // Layout, Positioning & Style Options
    property string capsulePosition: "top-center"
    property bool blurEnabled: true
    property string minimizeStyle: "macos-genie-inspired"
    property string minimizeTarget: "island"
    property string minimizedAppsVisibility: "auto"

    // UI Interactive Overrides
    property bool userExpanded: false
    property bool quickActionsOpen: false
    property bool settingsOpen: false
    property bool wifiOpen: false
    property bool bluetoothOpen: false
    property bool systemMenuOpen: false
    property bool audioPopoverOpen: false
    property bool batteryPopoverOpen: false
    property bool calendarPopoverOpen: false
    property bool controlCenterOpen: false

    // macOS Top Bar Configuration & State
    property bool topBarEnabled: true
    property int topBarHeight: 30
    property bool notchEnabled: false
    property int notchWidth: 160
    property real capsuleWidth: 180
    property bool micActive: false
    property var audioSinks: []

    // Active Window Name for Top Bar Left Menu
    readonly property string activeAppTitle: {
        if (focusedWindow) {
            if (focusedWindow.name && focusedWindow.name.length > 0) return focusedWindow.name;
            if (focusedWindow.app_id && focusedWindow.app_id.length > 0) return focusedWindow.app_id;
            if (focusedWindow.title && focusedWindow.title.length > 0) return focusedWindow.title;
        }
        return "Finder";
    }

    // Wi-Fi Interactive State
    property var wifiNetworks: []
    property bool wifiScanning: false
    property var wifiStatus: ({ "available": true, "enabled": true, "connected": false, "ssid": "", "signal": 0, "icon": "󰤮" })

    // Bluetooth Interactive State
    property var bluetoothDevices: []
    property bool bluetoothScanning: false
    property bool bluetoothPowered: true

    // Apple-style Dual Split Accessory Pill State
    property string accessoryIcon: ""
    property string accessoryLabel: ""
    property bool accessoryVisible: false

    // Compute effective visual state across all states
    function updateVisualState() {
        if (panelOpen || activeState === "panel_island") {
            visualState = "panel_island";
        } else if (wifiOpen || activeState === "wifi_manager") {
            visualState = "wifi_manager";
        } else if (bluetoothOpen || activeState === "bluetooth_manager") {
            visualState = "bluetooth_manager";
        } else if (settingsOpen || activeState === "settings") {
            visualState = "settings";
        } else if (quickActionsOpen || activeState === "quickActions" || activeState === "quick_actions" || activeState === "quick_settings") {
            visualState = "quickActions";
        } else if (activeState === "drag_active" || activeState === "drag_enter") {
            visualState = "dragActive";
        } else if (activeState === "share_picker") {
            visualState = "sharePicker";
        } else if (activeState === "minimized_apps") {
            visualState = "minimized_apps";
        } else if (activeState === "minimized" || activeState === "restoring" || activeState === "minimize_detected" || activeState === "minimize_animating" || activeState === "restore_detected" || activeState === "restore_animating") {
            visualState = "windowAnimation";
        } else if (activeState === "media_expanded") {
            visualState = "mediaExpanded";
        } else if (userExpanded && (activeState === "media" || activeState === "idle")) {
            visualState = "mediaExpanded";
        } else if (userExpanded) {
            visualState = "expanded";
        } else if (activeState === "media") {
            visualState = "mediaCompact";
        } else if (activeState === "bluetooth") {
            visualState = "bluetooth";
        } else {
            visualState = activeState;
        }
    }

    onActiveStateChanged: {
        updateVisualState();
        if (activeState === "wifi_manager") {
            scanWifi();
        } else if (activeState === "bluetooth_manager") {
            scanBluetooth();
        }
    }
    onUserExpandedChanged: updateVisualState()
    onQuickActionsOpenChanged: updateVisualState()
    onSettingsOpenChanged: updateVisualState()
    onWifiOpenChanged: updateVisualState()
    onBluetoothOpenChanged: updateVisualState()

    // Socket Connection
    property var socket: Socket {
        id: daemonSocket
        path: root.socketPath
        connected: true

        onConnectedChanged: {
            if (connected) {
                write("stream\n");
            }
        }

        parser: SplitParser {
            splitMarker: "\n"
            onRead: data => {
                if (!data || data.trim().length === 0) return;
                try {
                    var msg = JSON.parse(data.trim());
                    if (msg.ui_action !== undefined) {
                        if (msg.ui_action === "calendar") root.toggleCalendarPopover();
                        else if (msg.ui_action === "audio") root.toggleAudioPopover();
                        else if (msg.ui_action === "battery") root.toggleBatteryPopover();
                        else if (msg.ui_action === "system_menu") root.toggleSystemMenu();
                        else if (msg.ui_action === "control_center") root.toggleControlCenter();
                        else if (msg.ui_action === "wifi") root.toggleWifiView();
                        else if (msg.ui_action === "bluetooth") root.toggleBluetoothView();
                        else if (msg.ui_action === "dismiss") root.dismiss();
                        else if (msg.ui_action === "hide_bar") root.topBarEnabled = false;
                        else if (msg.ui_action === "show_bar") root.topBarEnabled = true;
                        else if (msg.ui_action === "toggle_bar") root.topBarEnabled = !root.topBarEnabled;
                    }
                    if (msg.state !== undefined) {
                        var nextState = msg.state || "idle";
                        if (root.activeState !== nextState) root.activeState = nextState;
                        if (root.title !== (msg.title || "")) root.title = msg.title || "";
                        if (root.subtitle !== (msg.subtitle || "")) root.subtitle = msg.subtitle || "";
                        if (root.icon !== (msg.icon || "󰸗")) root.icon = msg.icon || "󰸗";
                        if (msg.icon_path !== undefined && root.iconPath !== (msg.icon_path || "")) root.iconPath = msg.icon_path || "";
                        var nextProg = msg.progress_pct !== undefined ? Number(msg.progress_pct) : 0.0;
                        if (Math.abs(root.progressPct - nextProg) > 0.01) root.progressPct = nextProg;
                        if (root.progressBar !== (msg.progress_bar || "")) root.progressBar = msg.progress_bar || "";
                        var nextPrio = msg.priority !== undefined ? parseInt(msg.priority) : 10;
                        if (root.priority !== nextPrio) root.priority = nextPrio;
                        if (root.source !== (msg.source || "core")) root.source = msg.source || "core";
                        var nextMotion = Boolean(msg.reduced_motion);
                        if (root.reducedMotion !== nextMotion) root.reducedMotion = nextMotion;
                        if (msg.show_full !== undefined && root.showFull !== Boolean(msg.show_full)) {
                            root.showFull = Boolean(msg.show_full);
                        }
                        if (msg.theme && msg.theme !== root.themeName) {
                            root.themeName = msg.theme;
                            Theme.currentTheme = msg.theme;
                        }

                        // Rich payload fields
                        if (msg.art_url !== undefined && root.artUrl !== (msg.art_url || "")) root.artUrl = msg.art_url || "";
                        if (msg.duration_str !== undefined && root.durationStr !== (msg.duration_str || "")) root.durationStr = msg.duration_str || "";
                        if (msg.position_str !== undefined && root.positionStr !== (msg.position_str || "")) root.positionStr = msg.position_str || "";
                        if (msg.player_name !== undefined && root.playerName !== (msg.player_name || "")) root.playerName = msg.player_name || "";
                        if (msg.device_mac !== undefined && root.deviceMac !== (msg.device_mac || "")) root.deviceMac = msg.device_mac || "";
                        if (msg.device_battery !== undefined && root.deviceBattery !== msg.device_battery) root.deviceBattery = msg.device_battery;
                        if (msg.system_cpu !== undefined) {
                            var nCpu = Number(msg.system_cpu);
                            if (Math.abs(root.systemCpu - nCpu) >= 1.0) root.systemCpu = nCpu;
                        }
                        if (msg.system_mem !== undefined) {
                            var nMem = Number(msg.system_mem);
                            if (Math.abs(root.systemMem - nMem) >= 0.5) root.systemMem = nMem;
                        }
                        if (msg.system_disk_used !== undefined) {
                            root.systemDiskUsed = Number(msg.system_disk_used);
                        }
                        if (msg.system_disk_total !== undefined) {
                            root.systemDiskTotal = Number(msg.system_disk_total);
                        }
                        if (msg.system_disk_pct !== undefined) {
                            root.systemDiskPct = Number(msg.system_disk_pct);
                        }
                        if (msg.system_cpu_name !== undefined && msg.system_cpu_name.length > 0) {
                            root.systemCpuName = msg.system_cpu_name;
                        }
                        if (msg.dock_enabled !== undefined && root.dockEnabled !== Boolean(msg.dock_enabled)) {
                            root.dockEnabled = Boolean(msg.dock_enabled);
                        }
                        if (msg.dock_position !== undefined && root.dockPosition !== msg.dock_position) {
                            root.dockPosition = msg.dock_position;
                        }
                        if (msg.dropped_files !== undefined) {
                            root.droppedFiles = msg.dropped_files || [];
                        }
                        if (msg.capsule_position !== undefined && root.capsulePosition !== msg.capsule_position) {
                            root.capsulePosition = msg.capsule_position;
                        }
                        if (msg.blur_enabled !== undefined && root.blurEnabled !== Boolean(msg.blur_enabled)) {
                            root.blurEnabled = Boolean(msg.blur_enabled);
                        }
                        if (msg.minimize_style !== undefined && root.minimizeStyle !== msg.minimize_style) {
                            root.minimizeStyle = msg.minimize_style;
                        }
                        if (msg.minimize_target !== undefined && root.minimizeTarget !== msg.minimize_target) {
                            root.minimizeTarget = msg.minimize_target;
                        }
                        if (msg.minimized_apps_visibility !== undefined && root.minimizedAppsVisibility !== msg.minimized_apps_visibility) {
                            root.minimizedAppsVisibility = msg.minimized_apps_visibility;
                        }
                        if (msg.window_anim !== undefined) {
                            root.windowAnimationRequested(msg.window_anim);
                        }
                        if (msg.running_windows !== undefined) {
                            var newWins = msg.running_windows || [];
                            if (JSON.stringify(root.runningWindows) !== JSON.stringify(newWins)) {
                                root.runningWindows = newWins;
                                var minList = [];
                                for (var wIdx = 0; wIdx < newWins.length; wIdx++) {
                                    if (newWins[wIdx].minimized) {
                                        minList.push(newWins[wIdx]);
                                    }
                                }
                                root.minimizedWindows = minList;
                            }
                        }
                        if (msg.selected_minimized_index !== undefined) {
                            root.selectedMinimizedIndex = parseInt(msg.selected_minimized_index) || 0;
                        }
                        if (msg.focused_window !== undefined) {
                            root.focusedWindow = msg.focused_window;
                        }
                        if (msg.accessory_icon !== undefined) {
                            root.accessoryIcon = msg.accessory_icon || "";
                        }
                        if (msg.accessory_label !== undefined) {
                            root.accessoryLabel = msg.accessory_label || "";
                        }
                        if (msg.accessory_visible !== undefined) {
                            root.accessoryVisible = Boolean(msg.accessory_visible);
                        }
                        if (msg.mic_active !== undefined) {
                            root.micActive = Boolean(msg.mic_active);
                        }
                        if (msg.audio_sinks !== undefined) {
                            root.audioSinks = msg.audio_sinks || [];
                        }
                        if (msg.notch_enabled !== undefined) {
                            root.notchEnabled = Boolean(msg.notch_enabled);
                        }
                        if (msg.notch_width !== undefined) {
                            root.notchWidth = parseInt(msg.notch_width) || 160;
                        }
                        if (msg.topbar_height !== undefined) {
                            root.topBarHeight = parseInt(msg.topbar_height) || 30;
                        }
                        if (msg.topbar_enabled !== undefined) {
                            root.topBarEnabled = Boolean(msg.topbar_enabled);
                        }
                    }
                } catch (e) {
                    // Ignore transient malformed chunks
                }
            }
        }
    }

    // Auto-reconnect watchdog
    property var reconnectTimer: Timer {
        interval: 1500
        repeat: true
        running: !daemonSocket.connected
        onTriggered: {
            daemonSocket.connected = true;
        }
    }

    // Action Helpers
    function sendCommand(action, params) {
        var cmd = ["/home/reny/.local/bin/island-ctl", action];
        if (params && params.length > 0) {
            cmd = cmd.concat(params);
        }
        var p = appLauncherComponent.createObject(root, { command: cmd });
        if (p) p.running = true;
    }

    function toggleMedia() { sendCommand("media", ["toggle"]); }
    function nextMedia() { sendCommand("media", ["next"]); }
    function prevMedia() { sendCommand("media", ["prev"]); }
    function volumeUp() { sendCommand("volume", ["up"]); }
    function volumeDown() { sendCommand("volume", ["down"]); }
    function volumeMute() { sendCommand("volume", ["mute"]); }
    function brightnessUp() { sendCommand("brightness", ["up"]); }
    function brightnessDown() { sendCommand("brightness", ["down"]); }
    function dndToggle() { sendCommand("dnd", ["toggle"]); }
    function stopTimer() { sendCommand("timer", ["stop"]); }
    function toggleDock() { sendCommand("dock", ["toggle"]); }
    function togglePanelIsland() { sendCommand("panel_island", []); }

    // Smart Share Actions
    function inspectFiles(urls) {
        if (!urls || urls.length === 0) return;
        var p = appLauncherComponent.createObject(root, {
            command: ["island-ctl", "share", "inspect"].concat(urls)
        });
        if (p) p.running = true;
    }

    function executeShare(targetId) {
        if (!targetId) return;
        var p = appLauncherComponent.createObject(root, {
            command: ["island-ctl", "share", "execute", targetId]
        });
        if (p) p.running = true;
    }

    function cancelShare() {
        var p = appLauncherComponent.createObject(root, {
            command: ["island-ctl", "share", "cancel"]
        });
        if (p) p.running = true;
    }

    // Sway Window Management Actions
    function minimizeWindow(conId) {
        var p = appLauncherComponent.createObject(root, {
            command: ["island-ctl", "windows", "minimize", "" + conId]
        });
        if (p) p.running = true;
    }

    property var activeRestoringIds: ({})
    property real lastRestoreClickMs: 0

    function restoreWindow(conId) {
        if (!conId) return;
        var now = Date.now();
        if (now - lastRestoreClickMs < 350) {
            return; // Debounce rapid repeated clicks
        }
        if (activeRestoringIds[conId]) {
            return; // Already restoring
        }
        lastRestoreClickMs = now;
        activeRestoringIds[conId] = true;

        var p = appLauncherComponent.createObject(root, {
            command: ["island-ctl", "windows", "restore", "" + conId]
        });
        if (p) p.running = true;
    }

    function notifyRestoreFinished(conId) {
        if (conId && activeRestoringIds[conId]) {
            delete activeRestoringIds[conId];
        }
        sendCommand("window_restore_finished", ["" + (conId || 0)]);
    }

    function nextMinimizedWindow() {
        sendCommand("windows", ["next"]);
    }

    function prevMinimizedWindow() {
        sendCommand("windows", ["prev"]);
    }

    function selectMinimizedIndex(idx) {
        sendCommand("windows", ["select", "" + idx]);
    }

    function triggerAbsorptionPulse() {
        root.windowAbsorptionPulseRequested();
    }

    function restoreSelectedWindow() {
        if (selectedMinimizedWindow && selectedMinimizedWindow.id) {
            restoreWindow(selectedMinimizedWindow.id);
        } else {
            sendCommand("windows", ["restore"]);
        }
    }

    function toggleWindow(conId) {
        var p = appLauncherComponent.createObject(root, {
            command: ["island-ctl", "windows", "toggle", "" + conId]
        });
        if (p) p.running = true;
    }

    function toggleApp(keyword, fallback) {
        var p = appLauncherComponent.createObject(root, {
            command: ["island-ctl", "windows", "toggle-app", keyword, fallback || keyword]
        });
        if (p) p.running = true;
    }

    // Safe application launcher: executes specific binary without arbitrary shell interpolation
    function launchApp(appBinary) {
        if (!appBinary || appBinary.length === 0) return;
        var launcher = appLauncherComponent.createObject(root, { command: [appBinary] });
        if (launcher) {
            launcher.running = true;
        }
    }

    property Component appLauncherComponent: Component {
        Process {
            id: p
            onExited: destroy()
        }
    }

    function closeAllPopovers() {
        wifiOpen = false;
        bluetoothOpen = false;
        settingsOpen = false;
        quickActionsOpen = false;
        systemMenuOpen = false;
        audioPopoverOpen = false;
        batteryPopoverOpen = false;
        calendarPopoverOpen = false;
        controlCenterOpen = false;
        userExpanded = false;
    }

    function dismiss() {
        if (systemMenuOpen || audioPopoverOpen || batteryPopoverOpen || calendarPopoverOpen || controlCenterOpen || wifiOpen || bluetoothOpen) {
            systemMenuOpen = false;
            audioPopoverOpen = false;
            batteryPopoverOpen = false;
            calendarPopoverOpen = false;
            controlCenterOpen = false;
            wifiOpen = false;
            bluetoothOpen = false;
            return;
        }
        if (wifiOpen) {
            wifiOpen = false;
        } else if (bluetoothOpen) {
            bluetoothOpen = false;
        } else if (activeState === "share_picker") {
            cancelShare();
        } else if (settingsOpen) {
            settingsOpen = false;
        } else if (quickActionsOpen || activeState === "quickActions" || activeState === "quick_actions") {
            quickActionsOpen = false;
            sendCommand("dismiss");
        } else if (userExpanded) {
            userExpanded = false;
        } else {
            sendCommand("dismiss");
        }
    }

    function toggleSystemMenu() {
        var next = !systemMenuOpen;
        closeAllPopovers();
        systemMenuOpen = next;
    }

    function toggleAudioPopover() {
        var next = !audioPopoverOpen;
        closeAllPopovers();
        audioPopoverOpen = next;
        if (next) fetchAudioSinks();
    }

    function toggleBatteryPopover() {
        var next = !batteryPopoverOpen;
        closeAllPopovers();
        batteryPopoverOpen = next;
    }

    function toggleCalendarPopover() {
        var next = !calendarPopoverOpen;
        closeAllPopovers();
        calendarPopoverOpen = next;
    }

    function toggleControlCenter() {
        var next = !controlCenterOpen;
        closeAllPopovers();
        controlCenterOpen = next;
    }

    function toggleQuickActions() {
        var next = !(quickActionsOpen || activeState === "quickActions" || activeState === "quick_actions");
        closeAllPopovers();
        if (next) {
            quickActionsOpen = true;
            sendCommand("quick-actions");
        } else {
            quickActionsOpen = false;
            sendCommand("dismiss");
        }
    }

    function toggleSettings() {
        var next = !settingsOpen;
        closeAllPopovers();
        settingsOpen = next;
    }


    function toggleExpanded() {
        wifiOpen = false;
        bluetoothOpen = false;
        settingsOpen = false;
        quickActionsOpen = false;
        userExpanded = !userExpanded;
    }

    function setTheme(name) {
        sendCommand("theme", ["set", name]);
    }

    // Wallpaper & Desktop Theme Management
    function openWallpaperManager() {
        var p = appLauncherComponent.createObject(root, {
            command: ["python3", "/home/reny/.config/sway/scripts/wallpaper_manager_gui.py"]
        });
        if (p) p.running = true;
        dismiss();
    }

    function nextWallpaper() {
        var p = appLauncherComponent.createObject(root, {
            command: ["python3", "/home/reny/.config/sway/scripts/wallpaper_manager_gui.py", "--next"]
        });
        if (p) p.running = true;
        sendCommand("wallpaper", ["next"]);
    }

    function prevWallpaper() {
        var p = appLauncherComponent.createObject(root, {
            command: ["python3", "/home/reny/.config/sway/scripts/wallpaper_manager_gui.py", "--prev"]
        });
        if (p) p.running = true;
        sendCommand("wallpaper", ["prev"]);
    }

    function randomWallpaper() {
        var p = appLauncherComponent.createObject(root, {
            command: ["python3", "/home/reny/.config/sway/scripts/wallpaper_manager_gui.py", "--random"]
        });
        if (p) p.running = true;
        sendCommand("wallpaper", ["random"]);
    }

    function setWallpaper(path) {
        var p = appLauncherComponent.createObject(root, {
            command: ["python3", "/home/reny/.config/sway/scripts/wallpaper_manager_gui.py", "--set", path]
        });
        if (p) p.running = true;
        sendCommand("wallpaper", ["set", path]);
    }

    function openThemeManager() {
        var p = appLauncherComponent.createObject(root, {
            command: ["python3", "/home/reny/.config/sway/scripts/theme_manager.py"]
        });
        if (p) p.running = true;
        dismiss();
    }

    function nextSystemTheme() {
        sendCommand("system-theme", ["next"]);
    }

    function prevSystemTheme() {
        sendCommand("system-theme", ["prev"]);
    }

    function setSystemTheme(themeId) {
        sendCommand("system-theme", ["set", themeId]);
    }

    function openSettings() {
        wifiOpen = false;
        bluetoothOpen = false;
        quickActionsOpen = false;
        userExpanded = false;
        settingsOpen = true;
    }

    function closeSettings() {
        settingsOpen = false;
    }

    function setSetting(key, val) {
        sendCommand("settings", ["set", key, String(val)]);
    }

    function resetSettings() {
        sendCommand("settings", ["reset"]);
    }

    // Wi-Fi Interactive Actions
    function openWifi() {
        settingsOpen = false;
        quickActionsOpen = false;
        bluetoothOpen = false;
        wifiOpen = true;
        scanWifi();
    }

    function closeWifi() {
        wifiOpen = false;
    }

    function toggleWifiView() {
        if (wifiOpen) closeWifi(); else openWifi();
    }

    function scanWifi() {
        wifiScanning = true;
        wifiScanProcess.running = true;
    }

    function connectWifi(ssid, password) {
        if (!ssid) return;
        var p = appLauncherComponent.createObject(root, {
            command: ["island-ctl", "wifi", "connect", ssid, password || ""]
        });
        if (p) p.running = true;
        wifiRefreshTimer.restart();
    }

    function disconnectWifi() {
        var p = appLauncherComponent.createObject(root, {
            command: ["island-ctl", "wifi", "disconnect"]
        });
        if (p) p.running = true;
        wifiRefreshTimer.restart();
    }

    function toggleWifi(on) {
        var p = appLauncherComponent.createObject(root, {
            command: ["island-ctl", "wifi", "toggle"]
        });
        if (p) p.running = true;
        wifiRefreshTimer.restart();
    }

    property var wifiScanProcess: Process {
        command: ["python3", "-c", "import socket, json; s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM); s.connect('/run/user/1000/ratana-island.sock'); s.sendall(b'{\"command\":\"wifi_scan\"}\\n'); print(s.recv(32768).decode())"]
        stdout: SplitParser {
            splitMarker: "\n"
            onRead: data => {
                root.wifiScanning = false;
                if (!data || data.trim().length === 0) return;
                try {
                    var res = JSON.parse(data.trim());
                    if (res.networks) root.wifiNetworks = res.networks;
                    if (res.wifi) root.wifiStatus = res.wifi;
                } catch (e) {}
            }
        }
    }

    property var wifiRefreshTimer: Timer {
        interval: 1500
        repeat: false
        onTriggered: scanWifi()
    }

    // Bluetooth Interactive Actions
    function openBluetooth() {
        settingsOpen = false;
        quickActionsOpen = false;
        wifiOpen = false;
        bluetoothOpen = true;
        scanBluetooth();
    }

    function closeBluetooth() {
        bluetoothOpen = false;
    }

    function toggleBluetoothView() {
        if (bluetoothOpen) closeBluetooth(); else openBluetooth();
    }

    function scanBluetooth() {
        bluetoothScanning = true;
        bluetoothScanProcess.running = true;
    }

    function connectBluetooth(mac) {
        if (!mac) return;
        var p = appLauncherComponent.createObject(root, {
            command: ["island-ctl", "bluetooth", "connect", mac]
        });
        if (p) p.running = true;
        btRefreshTimer.restart();
    }

    function disconnectBluetooth(mac) {
        var p = appLauncherComponent.createObject(root, {
            command: ["island-ctl", "bluetooth", "disconnect", mac || ""]
        });
        if (p) p.running = true;
        btRefreshTimer.restart();
    }

    function toggleBluetooth(on) {
        var p = appLauncherComponent.createObject(root, {
            command: ["island-ctl", "bluetooth", "toggle"]
        });
        if (p) p.running = true;
        btRefreshTimer.restart();
    }

    property var bluetoothScanProcess: Process {
        command: ["python3", "-c", "import socket, json; s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM); s.connect('/run/user/1000/ratana-island.sock'); s.sendall(b'{\"command\":\"bluetooth_devices\"}\\n'); print(s.recv(16384).decode())"]
        stdout: SplitParser {
            splitMarker: "\n"
            onRead: data => {
                root.bluetoothScanning = false;
                if (!data || data.trim().length === 0) return;
                try {
                    var res = JSON.parse(data.trim());
                    var paired = res.paired || [];
                    var conn = res.connected || [];
                    var merged = [];
                    var macs = {};
                    for (var i = 0; i < conn.length; i++) {
                        conn[i].connected = true;
                        merged.push(conn[i]);
                        macs[conn[i].mac] = true;
                    }
                    for (var j = 0; j < paired.length; j++) {
                        if (!macs[paired[j].mac]) {
                            paired[j].connected = false;
                            merged.push(paired[j]);
                        }
                    }
                    root.bluetoothDevices = merged;
                    if (res.adapter_powered !== undefined) {
                        root.bluetoothPowered = Boolean(res.adapter_powered);
                    }
                } catch (e) {}
            }
        }
    }

    property var btRefreshTimer: Timer {
        interval: 1500
        repeat: false
        onTriggered: scanBluetooth()
    }

    // Audio Output Sinks Interactive State
    property var audioSinksProcess: Process {
        command: ["python3", "-c", "import socket, json; s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM); s.connect('/run/user/1000/ratana-island.sock'); s.sendall(b'{\"command\":\"audio_sinks\"}\\n'); print(s.recv(16384).decode())"]
        stdout: SplitParser {
            splitMarker: "\n"
            onRead: data => {
                if (!data || data.trim().length === 0) return;
                try {
                    var res = JSON.parse(data.trim());
                    if (res.sinks) root.audioSinks = res.sinks;
                } catch (e) {}
            }
        }
    }

    function fetchAudioSinks() {
        audioSinksProcess.running = true;
    }

    function setAudioSink(sinkId) {
        if (!sinkId) return;
        var p = appLauncherComponent.createObject(root, {
            command: ["island-ctl", "audio-sink", "set", String(sinkId)]
        });
        if (p) p.running = true;
        audioSinkRefreshTimer.restart();
    }

    property var audioSinkRefreshTimer: Timer {
        interval: 600
        repeat: false
        onTriggered: fetchAudioSinks()
    }
}

