import QtQuick
import "../services"
import "../themes"

Rectangle {
    id: root
    width: 200
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
            color: Qt.rgba(0, 0.82, 0.78, 0.18)
            anchors.verticalCenter: parent.verticalCenter

            Text {
                anchors.centerIn: parent
                text: "󰤨"
                color: Theme.accentCyan
                font.pixelSize: 18
            }
        }

        Column {
            width: parent.width - 52
            anchors.verticalCenter: parent.verticalCenter
            spacing: 2

            Text {
                text: "Network"
                color: Theme.textPrimary
                font.pixelSize: 12
                font.bold: true
            }

            Text {
                text: "Online • Connected"
                color: Theme.accentGreen
                font.pixelSize: 10
            }
        }
    }
}
