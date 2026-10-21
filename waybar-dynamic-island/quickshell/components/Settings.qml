import QtQuick
import "../services"
import "../themes"

Column {
    id: root
    anchors.fill: parent
    anchors.margins: 12
    spacing: 8

    // Header
    Item {
        width: parent.width
        height: 20

        Text {
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
            text: "⚙ Preferences & Themes"
            color: Theme.textSecondary
            font.pixelSize: 11
            font.bold: true
        }

        // Close button
        Rectangle {
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            width: 18
            height: 18
            radius: 9
            color: closeHov.hovered ? Qt.rgba(1, 1, 1, 0.2) : Qt.rgba(1, 1, 1, 0.08)

            Text {
                anchors.centerIn: parent
                text: "✕"
                color: Theme.textSecondary
                font.pixelSize: 9
            }

            HoverHandler { id: closeHov }
            TapHandler { onTapped: IslandBridge.dismiss() }
        }
    }

    // Row 1: Themes
    Row {
        spacing: 6
        width: parent.width

        Repeater {
            model: ["macos-black", "glass", "catppuccin-mocha", "minimal"]
            Rectangle {
                width: (parent.width - 18) / 4
                height: 26
                radius: 6
                color: {
                    if (Theme.currentTheme === modelData) return Qt.rgba(0.04, 0.52, 1.0, 0.35);
                    return thmHov.hovered ? Qt.rgba(1, 1, 1, 0.15) : Qt.rgba(1, 1, 1, 0.06);
                }
                border.color: Theme.currentTheme === modelData ? Theme.accent : "transparent"
                border.width: 1

                Text {
                    anchors.centerIn: parent
                    text: {
                        switch (modelData) {
                            case "macos-black": return "Tahoe";
                            case "glass": return "Glass";
                            case "catppuccin-mocha": return "Mocha";
                            case "minimal": return "OLED";
                            default: return modelData;
                        }
                    }
                    color: Theme.currentTheme === modelData ? Theme.accent : Theme.textPrimary
                    font.pixelSize: 10
                    font.bold: Theme.currentTheme === modelData
                }

                HoverHandler { id: thmHov }
                TapHandler {
                    onTapped: {
                        IslandBridge.setTheme(modelData);
                    }
                }
            }
        }
    }

    // Row 2: Motion, DND, Frontend
    Row {
        spacing: 6
        width: parent.width

        // Reduced Motion Toggle
        Rectangle {
            width: (parent.width - 12) / 3
            height: 28
            radius: 6
            color: motHov.hovered ? Qt.rgba(1, 1, 1, 0.18) : Qt.rgba(1, 1, 1, 0.07)

            Row {
                anchors.centerIn: parent
                spacing: 4
                Text { text: IslandBridge.reducedMotion ? "󰔢" : "󰔡"; color: Theme.accent; font.pixelSize: 11 }
                Text {
                    text: IslandBridge.reducedMotion ? "Motion: Off" : "Motion: On"
                    color: Theme.textPrimary
                    font.pixelSize: 9
                    font.bold: true
                }
            }

            HoverHandler { id: motHov }
            TapHandler {
                onTapped: {
                    var next = !IslandBridge.reducedMotion;
                    IslandBridge.sendCommand("reduced-motion", [next ? "on" : "off"]);
                }
            }
        }

        // DND Toggle
        Rectangle {
            width: (parent.width - 12) / 3
            height: 28
            radius: 6
            color: dndHov.hovered ? Qt.rgba(1, 1, 1, 0.18) : Qt.rgba(1, 1, 1, 0.07)

            Row {
                anchors.centerIn: parent
                spacing: 4
                Text { text: "🔕"; font.pixelSize: 10 }
                Text { text: "DND"; color: Theme.textPrimary; font.pixelSize: 9; font.bold: true }
            }

            HoverHandler { id: dndHov }
            TapHandler { onTapped: IslandBridge.dndToggle() }
        }

        // Quick Doctor Check
        Rectangle {
            width: (parent.width - 12) / 3
            height: 28
            radius: 6
            color: docHov.hovered ? Qt.rgba(1, 1, 1, 0.18) : Qt.rgba(1, 1, 1, 0.07)

            Row {
                anchors.centerIn: parent
                spacing: 4
                Text { text: "🩺"; font.pixelSize: 10 }
                Text { text: "Doctor"; color: Theme.textPrimary; font.pixelSize: 9; font.bold: true }
            }

            HoverHandler { id: docHov }
            TapHandler {
                onTapped: {
                    IslandBridge.sendCommand("doctor");
                    IslandBridge.dismiss();
                }
            }
        }
    }
}
