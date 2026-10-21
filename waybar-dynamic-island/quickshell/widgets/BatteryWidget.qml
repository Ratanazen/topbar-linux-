import QtQuick
import "../services"
import "../themes"

Rectangle {
    id: root
    width: 180
    height: 80
    radius: 16

    color: Theme.cardBackground
    border.color: Theme.border
    border.width: 1

    Row {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 12

        Rectangle {
            width: 40
            height: 40
            radius: 20
            color: Qt.rgba(0.19, 0.82, 0.35, 0.18)
            anchors.verticalCenter: parent.verticalCenter

            Text {
                anchors.centerIn: parent
                text: "󰂄"
                color: Theme.accentGreen
                font.pixelSize: 20
            }
        }

        Column {
            width: parent.width - 52
            anchors.verticalCenter: parent.verticalCenter
            spacing: 2

            Text {
                text: "Power"
                color: Theme.textPrimary
                font.pixelSize: 12
                font.bold: true
            }

            Text {
                text: IslandBridge.deviceBattery !== null ? IslandBridge.deviceBattery + "% Available" : "AC Power"
                color: Theme.textSecondary
                font.pixelSize: 10
            }
        }
    }
}
