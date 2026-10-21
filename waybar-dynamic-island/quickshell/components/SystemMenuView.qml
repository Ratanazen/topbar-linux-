import QtQuick
import "../services"
import "../themes"

Rectangle {
    id: root
    width: 230
    height: menuCol.implicitHeight + 16
    radius: 12
    color: Theme.background
    border.color: Theme.border
    border.width: 1

    Column {
        id: menuCol
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: 8
        spacing: 2

        // About This PC
        MenuItem {
            iconGlyph: ""
            iconColor: "#ffffff"
            label: "About This PC"
            shortcut: ""
            onTriggered: {
                IslandBridge.dismiss();
                IslandBridge.sendCommand("event", ["--title", "System Info", "--message", "Arch Linux SwayFX • Ratana Shell", "--duration", "4"]);
            }
        }

        // System Settings
        MenuItem {
            iconGlyph: "󰒓"
            iconColor: "#0a84ff"
            label: "System Settings..."
            shortcut: "⌘,"
            onTriggered: {
                IslandBridge.dismiss();
                IslandBridge.openSettings();
            }
        }

        // App Store
        MenuItem {
            iconGlyph: "󰀻"
            iconColor: "#007AFF"
            label: "App Store..."
            shortcut: ""
            onTriggered: {
                IslandBridge.dismiss();
                IslandBridge.launchApp("pamac-manager");
            }
        }

        MenuSeparator {}

        // Force Quit
        MenuItem {
            iconGlyph: "󰅖"
            iconColor: "#ff453a"
            label: "Force Quit..."
            shortcut: "⌥⌘⎋"
            onTriggered: {
                IslandBridge.dismiss();
                IslandBridge.launchApp("xkill");
            }
        }

        MenuSeparator {}

        // Sleep
        MenuItem {
            iconGlyph: "󰒲"
            iconColor: "#ffd60a"
            label: "Sleep"
            shortcut: ""
            onTriggered: {
                IslandBridge.dismiss();
                IslandBridge.sendCommand("systemctl", ["suspend"]);
            }
        }

        // Restart
        MenuItem {
            iconGlyph: "󰑓"
            iconColor: "#ff9f0a"
            label: "Restart..."
            shortcut: ""
            onTriggered: {
                IslandBridge.dismiss();
                IslandBridge.sendCommand("systemctl", ["reboot"]);
            }
        }

        // Shut Down
        MenuItem {
            iconGlyph: "󰐥"
            iconColor: "#ff453a"
            label: "Shut Down..."
            shortcut: ""
            onTriggered: {
                IslandBridge.dismiss();
                IslandBridge.sendCommand("systemctl", ["poweroff"]);
            }
        }

        MenuSeparator {}

        // Lock Screen
        MenuItem {
            iconGlyph: "󰌾"
            iconColor: "#ffd60a"
            label: "Lock Screen"
            shortcut: "⌃⌘Q"
            onTriggered: {
                IslandBridge.dismiss();
                IslandBridge.launchApp("swaylock");
            }
        }

        // Log Out
        MenuItem {
            iconGlyph: "󰍃"
            iconColor: "#a1a1a6"
            label: "Log Out..."
            shortcut: "⇧⌘Q"
            onTriggered: {
                IslandBridge.dismiss();
                IslandBridge.launchApp("swaymsg", ["exit"]);
            }
        }
    }

    component MenuItem: Rectangle {
        property string iconGlyph: ""
        property color iconColor: Theme.textSecondary
        property string label: ""
        property string shortcut: ""
        signal triggered()

        width: parent.width
        height: 24
        radius: 6
        color: itemHover.hovered ? Theme.accent : "transparent"

        Item {
            anchors.fill: parent
            anchors.leftMargin: 8
            anchors.rightMargin: 8

            Row {
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                spacing: 8

                Text {
                    text: iconGlyph
                    color: itemHover.hovered ? "#ffffff" : iconColor
                    font.pixelSize: 12
                    width: 14
                    horizontalAlignment: Text.AlignHCenter
                    anchors.verticalCenter: parent.verticalCenter
                }

                Text {
                    text: label
                    color: itemHover.hovered ? "#ffffff" : Theme.textPrimary
                    font.pixelSize: 11
                    anchors.verticalCenter: parent.verticalCenter
                }
            }

            Text {
                text: shortcut
                color: itemHover.hovered ? Qt.rgba(1, 1, 1, 0.7) : Theme.textSecondary
                font.pixelSize: 10
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
            }
        }

        HoverHandler { id: itemHover }
        TapHandler {
            onTapped: triggered()
        }
    }

    component MenuSeparator: Rectangle {
        width: parent.width
        height: 1
        color: Qt.rgba(1, 1, 1, 0.08)
    }
}
