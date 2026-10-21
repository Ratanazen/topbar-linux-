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
    Column {
        width: parent.width
        spacing: 4
        visible: IslandBridge.minimizedWindows && IslandBridge.minimizedWindows.length > 0

        Text {
            text: "MINIMIZED WINDOWS (" + (IslandBridge.minimizedWindows ? IslandBridge.minimizedWindows.length : 0) + ")"
            color: Theme.textSecondary
            font.pixelSize: 9
            font.bold: true
        }

        Repeater {
            model: IslandBridge.minimizedWindows ? Math.min(3, IslandBridge.minimizedWindows.length) : 0
            delegate: Rectangle {
                id: minRow
                required property int index
                property var win: IslandBridge.minimizedWindows[index]

                width: parent.width
                height: 26
                radius: 6
                color: rowHov.hovered ? Qt.rgba(1, 1, 1, 0.14) : Qt.rgba(1, 1, 1, 0.06)
                border.color: rowHov.hovered ? Theme.accent : Qt.rgba(1, 1, 1, 0.1)
                border.width: 1

                Item {
                    anchors.fill: parent
                    anchors.margins: 4

                    Row {
                        anchors.left: parent.left
                        anchors.right: restoreBtn.left
                        anchors.rightMargin: 6
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 8

                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            text: (minRow.win && minRow.win.icon) ? minRow.win.icon : "󰖲"
                            color: Theme.accentYellow
                            font.pixelSize: 12
                        }

                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            text: (minRow.win && (minRow.win.title || minRow.win.name || minRow.win.app_id)) ? (minRow.win.title || minRow.win.name || minRow.win.app_id) : "Window"
                            color: Theme.textPrimary
                            font.pixelSize: 11
                            elide: Text.ElideRight
                            width: minRow.width - 90
                        }
                    }

                    Rectangle {
                        id: restoreBtn
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        width: 50
                        height: 18
                        radius: 4
                        color: Theme.accent

                        Text {
                            anchors.centerIn: parent
                            text: "Restore"
                            color: "#ffffff"
                            font.pixelSize: 9
                            font.bold: true
                        }
                    }
                }

                HoverHandler { id: rowHov }
                TapHandler {
                    onTapped: {
                        if (minRow.win && minRow.win.id) {
                            IslandBridge.restoreWindow(minRow.win.id);
                        }
                    }
                }
            }
        }
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
