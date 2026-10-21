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

    Row {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 12

        Rectangle {
            width: 44
            height: 44
            radius: 22
            color: Qt.rgba(0.04, 0.52, 1.0, 0.18)
            anchors.verticalCenter: parent.verticalCenter

            Text {
                anchors.centerIn: parent
                text: "󰂯"
                color: Theme.accent
                font.pixelSize: 22
            }
        }

        Column {
            width: parent.width - 56
            anchors.verticalCenter: parent.verticalCenter
            spacing: 2

            Text {
                text: "Bluetooth"
                color: Theme.textPrimary
                font.pixelSize: 12
                font.bold: true
            }

            Text {
                text: IslandBridge.activeState === "bluetooth" ? IslandBridge.title : "BlueZ Active"
                color: Theme.textSecondary
                font.pixelSize: 10
                elide: Text.ElideRight
                width: parent.width
            }

            Rectangle {
                width: 60
                height: 20
                radius: 6
                color: Qt.rgba(1, 1, 1, 0.10)

                Text {
                    anchors.centerIn: parent
                    text: "Scan"
                    color: Theme.textPrimary
                    font.pixelSize: 9
                    font.bold: true
                }

                TapHandler {
                    onTapped: IslandBridge.sendCommand("bluetooth", ["scan"])
                }
            }
        }
    }
}
