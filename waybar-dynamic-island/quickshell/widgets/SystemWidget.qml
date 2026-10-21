import QtQuick
import "../services"
import "../themes"

Rectangle {
    id: root
    width: 220
    height: 90
    radius: 16

    color: Theme.cardBackground
    border.color: Theme.border
    border.width: 1

    Column {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 8

        Text {
            text: "System Telemetry"
            color: Theme.textSecondary
            font.pixelSize: 10
            font.bold: true
        }

        // CPU Bar
        Column {
            width: parent.width
            spacing: 2

            Row {
                width: parent.width
                Text { text: "CPU"; color: Theme.textPrimary; font.pixelSize: 10; font.bold: true }
                Item { width: parent.width - 70 }
                Text {
                    text: IslandBridge.systemCpu + "%"
                    color: IslandBridge.systemCpu > 80 ? Theme.accentRed : Theme.accent
                    font.pixelSize: 10
                    anchors.right: parent.right
                }
            }

            Rectangle {
                width: parent.width
                height: 4
                radius: 2
                color: Qt.rgba(1, 1, 1, 0.12)

                Rectangle {
                    height: parent.height
                    radius: 2
                    width: Math.max(0, Math.min(parent.width, parent.width * (IslandBridge.systemCpu / 100.0)))
                    color: IslandBridge.systemCpu > 80 ? Theme.accentRed : Theme.accent
                }
            }
        }

        // RAM Bar
        Column {
            width: parent.width
            spacing: 2

            Row {
                width: parent.width
                Text { text: "RAM"; color: Theme.textPrimary; font.pixelSize: 10; font.bold: true }
                Item { width: parent.width - 70 }
                Text {
                    text: IslandBridge.systemMem + "%"
                    color: IslandBridge.systemMem > 85 ? Theme.accentRed : Theme.accentCyan
                    font.pixelSize: 10
                    anchors.right: parent.right
                }
            }

            Rectangle {
                width: parent.width
                height: 4
                radius: 2
                color: Qt.rgba(1, 1, 1, 0.12)

                Rectangle {
                    height: parent.height
                    radius: 2
                    width: Math.max(0, Math.min(parent.width, parent.width * (IslandBridge.systemMem / 100.0)))
                    color: IslandBridge.systemMem > 85 ? Theme.accentRed : Theme.accentCyan
                }
            }
        }
    }
}
