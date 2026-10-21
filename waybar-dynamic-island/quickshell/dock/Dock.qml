import QtQuick
import Quickshell
import Quickshell.Wayland
import "../services"
import "../themes"

PanelWindow {
    id: dockWindow

    required property var screenTarget
    screen: screenTarget

    WlrLayershell.layer: WlrLayer.Top
    WlrLayershell.namespace: "ratana-dock"
    WlrLayershell.keyboardFocus: WlrKeyboardFocus.None
    WlrLayershell.exclusionMode: ExclusionMode.Ignore
    exclusionMode: ExclusionMode.Ignore

    // Bottom anchored floating dock
    anchors.bottom: true
    anchors.left: true
    anchors.right: true

    implicitHeight: 76
    color: "transparent"
    visible: IslandBridge.dockEnabled

    // Input hit test: pass clicks outside the dock container through to desktop
    mask: Region {
        item: dockContainer
    }

    // Dock Floating Glass Container
    Rectangle {
        id: dockContainer
        anchors.bottom: parent.bottom
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottomMargin: 10

        width: dockRow.implicitWidth + 24
        height: 56
        radius: 20

        color: Theme.background
        border.color: Theme.border
        border.width: 1

        // Smooth geometry behavior
        Behavior on width {
            NumberAnimation { duration: IslandBridge.reducedMotion ? 0 : 200; easing.type: Easing.OutQuad }
        }

        Row {
            id: dockRow
            anchors.centerIn: parent
            spacing: 12

            // 1. Terminal (Kitty / Foot / Alacritty)
            DockItem {
                iconText: "󰄛"
                tooltipText: "Terminal"
                iconColor: Theme.accent
                appKeyword: "kitty|foot|alacritty|terminal|wezterm|ghostty"
                launchBinary: "kitty"
            }

            // 2. Web Browser (Brave / Firefox / Chrome / Zen)
            DockItem {
                iconText: ""
                tooltipText: "Browser"
                iconColor: Theme.accentCyan
                appKeyword: "brave|firefox|chrome|chromium|zen"
                launchBinary: "brave-browser"
            }

            // 3. File Manager (Thunar / Dolphin / Nautilus)
            DockItem {
                iconText: "󰉋"
                tooltipText: "Files"
                iconColor: Theme.accentYellow
                appKeyword: "thunar|dolphin|nautilus|pcmanfm"
                launchBinary: "thunar"
            }

            // 4. Code Editor (VSCode / Codium / Neovim)
            DockItem {
                iconText: "󰨞"
                tooltipText: "Code Editor"
                iconColor: Theme.accent
                appKeyword: "code|codium|vscodium|nvim"
                launchBinary: "code"
            }

            // Separator Pill
            Rectangle {
                width: 1
                height: 24
                radius: 1
                color: Qt.rgba(1, 1, 1, 0.15)
                anchors.verticalCenter: parent.verticalCenter
            }

            // 5. Media Player / Spotify
            DockItem {
                iconText: "󰓇"
                tooltipText: IslandBridge.title ? "Now Playing: " + IslandBridge.title : "Music Player"
                iconColor: Theme.accentGreen
                appKeyword: "spotify|rhythmbox|cider"
                launchBinary: "spotify"
                onActivated: {
                    var w = getRunningInfo();
                    if (w) {
                        IslandBridge.toggleWindow(w.id);
                    } else if (IslandBridge.activeState === "media") {
                        IslandBridge.toggleExpanded();
                    } else {
                        IslandBridge.toggleMedia();
                    }
                }
            }

            // 6. Control Center (Dynamic Island)
            DockItem {
                iconText: "🏝️"
                tooltipText: "Dynamic Island Controls"
                iconColor: Theme.textPrimary
                onActivated: IslandBridge.toggleQuickActions()
            }

            // 7. System Settings
            DockItem {
                iconText: "⚙"
                tooltipText: "Settings"
                iconColor: Theme.textSecondary
                onActivated: IslandBridge.toggleSettings()
            }
        }
    }

    // Component definition for reusable dock icons with magnification and running dots
    component DockItem: Item {
        id: itemRoot
        property string iconText: "󰄛"
        property string tooltipText: ""
        property color iconColor: Theme.textPrimary
        property string appKeyword: ""
        property string launchBinary: ""
        signal activated()

        function getRunningInfo() {
            if (!IslandBridge.dockEnabled || !appKeyword || !IslandBridge.runningWindows) return null;
            var keywords = appKeyword.toLowerCase().split("|");
            for (var i = 0; i < IslandBridge.runningWindows.length; i++) {
                var w = IslandBridge.runningWindows[i];
                var appId = (w.app_id || "").toLowerCase();
                var name = (w.name || "").toLowerCase();
                for (var k = 0; k < keywords.length; k++) {
                    if (appId.indexOf(keywords[k]) !== -1 || name.indexOf(keywords[k]) !== -1) {
                        return w;
                    }
                }
            }
            return null;
        }

        width: 40
        height: 44

        Rectangle {
            id: iconBg
            anchors.top: parent.top
            anchors.horizontalCenter: parent.horizontalCenter
            width: 38
            height: 38
            radius: 12
            color: itemHover.hovered ? Qt.rgba(1, 1, 1, 0.18) : Qt.rgba(1, 1, 1, 0.06)
            border.color: itemHover.hovered ? Qt.rgba(1, 1, 1, 0.25) : Qt.rgba(1, 1, 1, 0.08)
            border.width: 1

            // Magnification effect
            scale: (itemHover.hovered && IslandBridge.dockMagnification && !IslandBridge.reducedMotion) ? 1.25 : 1.0

            Behavior on scale {
                NumberAnimation { duration: 150; easing.type: Easing.OutQuad }
            }

            Text {
                anchors.centerIn: parent
                text: itemRoot.iconText
                color: itemRoot.iconColor
                font.pixelSize: 18
            }

            HoverHandler { id: itemHover }
            TapHandler {
                onTapped: {
                    var w = itemRoot.getRunningInfo();
                    if (itemRoot.appKeyword && w) {
                        IslandBridge.toggleWindow(w.id);
                    } else if (itemRoot.launchBinary) {
                        IslandBridge.launchApp(itemRoot.launchBinary);
                    } else {
                        itemRoot.activated();
                    }
                }
            }

            // Tooltip preview banner above icon on hover
            Rectangle {
                visible: itemHover.hovered && itemRoot.tooltipText.length > 0
                anchors.bottom: parent.top
                anchors.bottomMargin: 8
                anchors.horizontalCenter: parent.horizontalCenter
                width: tooltipLabel.implicitWidth + 14
                height: 22
                radius: 6
                color: Qt.rgba(0, 0, 0, 0.85)
                border.color: Qt.rgba(1, 1, 1, 0.15)
                border.width: 1
                z: 100

                Text {
                    id: tooltipLabel
                    anchors.centerIn: parent
                    text: itemRoot.tooltipText
                    color: "#ffffff"
                    font.pixelSize: 10
                    font.bold: true
                }
            }
        }

        // Running Application Indicator Dot (macOS style)
        Rectangle {
            id: runningDot
            visible: itemRoot.getRunningInfo() !== null
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 1
            anchors.horizontalCenter: parent.horizontalCenter
            width: 4
            height: 4
            radius: 2
            color: {
                var w = itemRoot.getRunningInfo();
                if (w && w.focused) return Theme.accent;
                if (w && w.minimized) return Theme.accentYellow;
                return Qt.rgba(1, 1, 1, 0.6);
            }
        }
    }
}
