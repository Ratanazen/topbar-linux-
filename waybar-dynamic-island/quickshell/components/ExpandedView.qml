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

        Row {
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
            spacing: 6

            Text {
                text: IslandBridge.icon || "󰸗"
                color: Theme.accent
                font.pixelSize: 13
                anchors.verticalCenter: parent.verticalCenter
            }

            Text {
                text: IslandBridge.title || "Dynamic Island"
                color: Theme.textPrimary
                font.pixelSize: 12
                font.bold: true
                anchors.verticalCenter: parent.verticalCenter
            }
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

    // Minimized Applications Section (if any exist)
    MinimizedAppsView {
        id: minAppsManager
        visible: IslandBridge.minimizedWindows && IslandBridge.minimizedWindows.length > 0
    }

    // Quick Action Bar
    Row {
        spacing: 8
        anchors.horizontalCenter: parent.horizontalCenter
        visible: !IslandBridge.minimizedWindows || IslandBridge.minimizedWindows.length === 0

        Rectangle {
            width: 76
            height: 26
            radius: 6
            color: act1Hov.hovered ? Qt.rgba(1, 1, 1, 0.2) : Qt.rgba(1, 1, 1, 0.08)

            Row {
                anchors.centerIn: parent
                spacing: 4
                Text { text: "󰐊"; color: Theme.accent; font.pixelSize: 10 }
                Text { text: "Media"; color: Theme.textPrimary; font.pixelSize: 10; font.bold: true }
            }

            HoverHandler { id: act1Hov }
            TapHandler { onTapped: IslandBridge.toggleMedia() }
        }

        Rectangle {
            width: 76
            height: 26
            radius: 6
            color: act2Hov.hovered ? Qt.rgba(1, 1, 1, 0.2) : Qt.rgba(1, 1, 1, 0.08)

            Row {
                anchors.centerIn: parent
                spacing: 4
                Text { text: "󰂯"; color: Theme.accent; font.pixelSize: 10 }
                Text { text: "Bluetooth"; color: Theme.textPrimary; font.pixelSize: 10; font.bold: true }
            }

            HoverHandler { id: act2Hov }
            TapHandler { onTapped: IslandBridge.sendCommand("bluetooth", ["scan"]) }
        }

        Rectangle {
            width: 76
            height: 26
            radius: 6
            color: act3Hov.hovered ? Qt.rgba(1, 1, 1, 0.2) : Qt.rgba(1, 1, 1, 0.08)

            Row {
                anchors.centerIn: parent
                spacing: 4
                Text { text: "⚙"; color: Theme.textSecondary; font.pixelSize: 10 }
                Text { text: "Settings"; color: Theme.textPrimary; font.pixelSize: 10; font.bold: true }
            }

            HoverHandler { id: act3Hov }
            TapHandler { onTapped: IslandBridge.toggleSettings() }
        }
    }
}
