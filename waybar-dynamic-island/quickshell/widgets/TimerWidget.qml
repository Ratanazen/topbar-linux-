import QtQuick
import "../services"
import "../themes"

Rectangle {
    id: root
    width: 200
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
            color: Qt.rgba(1, 0.41, 0.38, 0.18)
            anchors.verticalCenter: parent.verticalCenter

            Text {
                anchors.centerIn: parent
                text: "🍅"
                font.pixelSize: 20
            }
        }

        Column {
            width: parent.width - 56
            anchors.verticalCenter: parent.verticalCenter
            spacing: 2

            Text {
                text: "Focus Timer"
                color: Theme.textPrimary
                font.pixelSize: 12
                font.bold: true
            }

            Text {
                text: IslandBridge.activeState === "timer" || IslandBridge.activeState === "pomodoro" ? IslandBridge.title : "25:00 Ready"
                color: Theme.accentRed
                font.pixelSize: 11
                font.bold: true
            }

            Row {
                spacing: 8

                Rectangle {
                    width: 50
                    height: 18
                    radius: 5
                    color: Qt.rgba(1, 1, 1, 0.10)
                    Text { anchors.centerIn: parent; text: "Start"; color: Theme.textPrimary; font.pixelSize: 9; font.bold: true }
                    TapHandler { onTapped: IslandBridge.sendCommand("pomodoro") }
                }

                Rectangle {
                    width: 50
                    height: 18
                    radius: 5
                    color: Qt.rgba(1, 1, 1, 0.10)
                    Text { anchors.centerIn: parent; text: "Stop"; color: Theme.textSecondary; font.pixelSize: 9; font.bold: true }
                    TapHandler { onTapped: IslandBridge.stopTimer() }
                }
            }
        }
    }
}
