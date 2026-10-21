import QtQuick
import "../services"
import "../themes"

Rectangle {
    id: root

    // Only visible when an active secondary accessory exists
    visible: opacity > 0.01
    opacity: IslandBridge.accessoryVisible ? 1.0 : 0.0
    scale: IslandBridge.accessoryVisible ? 1.0 : 0.6

    Behavior on opacity {
        NumberAnimation { duration: IslandBridge.reducedMotion ? 0 : 250; easing.type: Easing.OutQuad }
    }
    Behavior on scale {
        NumberAnimation { duration: IslandBridge.reducedMotion ? 0 : 280; easing.type: Easing.OutBack }
    }

    width: 38
    height: 38
    radius: 19

    // iOS Dynamic Island Styling: Deep OLED Black / Glass with Subtle Border
    color: Theme.capsuleBackground || "#000000"
    border.color: hoverHandler.hovered ? Qt.rgba(1, 1, 1, 0.35) : (Theme.capsuleBorder || Qt.rgba(1, 1, 1, 0.14))
    border.width: 1

    // Content: Icon + Audio Waveform Indicator
    Item {
        anchors.fill: parent

        // Audio Waveform bars if accessory is Music/Audio
        Row {
            anchors.centerIn: parent
            spacing: 2
            visible: (IslandBridge.accessoryIcon === "󰎆" || IslandBridge.accessoryLabel === "Music")

            Repeater {
                model: 3

                delegate: Rectangle {
                    required property int index
                    width: 3
                    radius: 1.5
                    color: Theme.accentRed || "#ff3b30"
                    anchors.verticalCenter: parent.verticalCenter

                    SequentialAnimation on height {
                        loops: Animation.Infinite
                        running: root.visible && (IslandBridge.accessoryIcon === "󰎆" || IslandBridge.accessoryLabel === "Music") && !IslandBridge.reducedMotion
                        NumberAnimation { from: 6; to: (index === 1 ? 16 : 10); duration: 350 + index * 100; easing.type: Easing.InOutQuad }
                        NumberAnimation { from: (index === 1 ? 16 : 10); to: 6; duration: 350 + index * 100; easing.type: Easing.InOutQuad }
                    }
                }
            }
        }

        // Standard Icon (Nerd Font Glyph) for other accessories (Bluetooth, Minimized App, Wi-Fi)
        Text {
            anchors.centerIn: parent
            visible: !(IslandBridge.accessoryIcon === "󰎆" || IslandBridge.accessoryLabel === "Music")
            text: IslandBridge.accessoryIcon || "󰖲"
            color: hoverHandler.hovered ? Theme.accentCyan : Theme.accent
            font.pixelSize: 15
        }
    }

    HoverHandler { id: hoverHandler }

    TapHandler {
        onTapped: {
            if (IslandBridge.accessoryIcon === "󰎆" || IslandBridge.accessoryLabel === "Music") {
                IslandBridge.toggleExpanded();
            } else if (IslandBridge.accessoryIcon === "󰂱" || IslandBridge.accessoryIcon === "󰋋" || IslandBridge.accessoryLabel === "BT") {
                IslandBridge.toggleBluetoothView();
            } else if (IslandBridge.accessoryIcon.indexOf("󰤨") !== -1 || IslandBridge.accessoryLabel === "WiFi") {
                IslandBridge.toggleWifiView();
            } else if (IslandBridge.minimizedWindows && IslandBridge.minimizedWindows.length > 0) {
                // Restore minimized window
                var idx = Math.max(0, Math.min(IslandBridge.selectedMinimizedIndex, IslandBridge.minimizedWindows.length - 1));
                var targetWin = IslandBridge.minimizedWindows[idx];
                if (targetWin) {
                    IslandBridge.restoreWindow(targetWin.id);
                }
            }
        }
    }
}
