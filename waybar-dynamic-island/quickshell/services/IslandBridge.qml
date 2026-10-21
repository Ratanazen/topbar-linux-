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

    // Live System Metrics (CPU / RAM)
    property real systemCpu: 0.0
    property real systemMem: 0.0

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
    signal windowAnimationRequested(var animData)

    // Layout, Positioning & Style Options
    property string capsulePosition: "top-center"
    property bool blurEnabled: true
    property string minimizeStyle: "scale"
    property string minimizeTarget: "island"
    property string minimizedAppsVisibility: "auto"

    // UI Interactive Overrides
    property bool userExpanded: false
    property bool quickActionsOpen: false
    property bool settingsOpen: false

    // Compute effective visual state across all states
    function updateVisualState() {
        if (settingsOpen) {
            visualState = "settings";
        } else if (quickActionsOpen) {
            visualState = "quickActions";
        } else if (activeState === "drag_active" || activeState === "drag_enter") {
            visualState = "dragActive";
        } else if (activeState === "share_picker") {
            visualState = "sharePicker";
        } else if (activeState === "minimized_apps") {
            visualState = "minimized_apps";
        } else if (activeState === "minimized" || activeState === "restoring" || activeState === "minimize_detected" || activeState === "minimize_animating" || activeState === "restore_detected" || activeState === "restore_animating") {
            visualState = "windowAnimation";
        } else if (activeState === "quick_settings") {
            visualState = "quickActions";
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

    onActiveStateChanged: updateVisualState()
    onUserExpandedChanged: updateVisualState()
    onQuickActionsOpenChanged: updateVisualState()
    onSettingsOpenChanged: updateVisualState()

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
                    if (msg.state !== undefined) {
                        var nextState = msg.state || "idle";
                        if (root.activeState !== nextState) root.activeState = nextState;
                        if (root.title !== (msg.title || "")) root.title = msg.title || "";
                        if (root.subtitle !== (msg.subtitle || "")) root.subtitle = msg.subtitle || "";
                        if (root.icon !== (msg.icon || "󰸗")) root.icon = msg.icon || "󰸗";
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
        var cmd = ["island-ctl", action];
        if (params && params.length > 0) {
            cmd = cmd.concat(params);
        }
        cmdProcess.command = cmd;
        cmdProcess.running = true;
    }

    property var cmdProcess: Process {
        id: cmdProc
        command: ["island-ctl", "status"]
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

    function restoreWindow(conId) {
        var p = appLauncherComponent.createObject(root, {
            command: ["island-ctl", "windows", "restore", "" + conId]
        });
        if (p) p.running = true;
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

    function dismiss() {
        if (activeState === "share_picker") {
            cancelShare();
        } else if (settingsOpen) {
            settingsOpen = false;
        } else if (quickActionsOpen) {
            quickActionsOpen = false;
        } else if (userExpanded) {
            userExpanded = false;
        } else {
            sendCommand("dismiss");
        }
    }

    function toggleQuickActions() {
        settingsOpen = false;
        userExpanded = false;
        quickActionsOpen = !quickActionsOpen;
    }

    function toggleSettings() {
        quickActionsOpen = false;
        userExpanded = false;
        settingsOpen = !settingsOpen;
    }

    function toggleExpanded() {
        settingsOpen = false;
        quickActionsOpen = false;
        userExpanded = !userExpanded;
    }

    function setTheme(name) {
        sendCommand("theme", ["set", name]);
    }
}
