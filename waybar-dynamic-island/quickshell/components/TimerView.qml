import QtQuick
import "../services"
import "../themes"

Row {
    id: root
    spacing: 12
    anchors.centerIn: parent

    Text {
        text: IslandBridge.icon || "󰔛"
        color: Theme.accentGreen
        font.pixelSize: 15
        anchors.verticalCenter: parent.verticalCenter
    }

    Text {
        text: IslandBridge.title || "00:00"
        color: Theme.textPrimary
        font.family: "JetBrainsMono Nerd Font, monospace"
        font.pixelSize: 14
        font.bold: true
        anchors.verticalCenter: parent.verticalCenter
    }

    // Mini Progress Bar if timer has progress
    Rectangle {
        width: 60
        height: 5
        radius: 2.5
        color: Qt.rgba(1, 1, 1, 0.15)
        anchors.verticalCenter: parent.verticalCenter
        visible: IslandBridge.progressPct > 0

        Rectangle {
            height: parent.height
            radius: 2.5
            width: Math.max(0, Math.min(parent.width, parent.width * IslandBridge.progressPct))
            color: Theme.accentGreen

            Behavior on width {
                NumberAnimation { duration: 200 }
            }
        }
    }

    Text {
        text: IslandBridge.subtitle || ""
        color: Theme.textSecondary
        font.pixelSize: 11
        anchors.verticalCenter: parent.verticalCenter
        visible: text.length > 0
    }

    // Stop Button
    Rectangle {
        width: 20
        height: 20
        radius: 10
        color: stopHover.hovered ? Qt.rgba(1, 1, 1, 0.2) : Qt.rgba(1, 1, 1, 0.08)
        anchors.verticalCenter: parent.verticalCenter

        Text {
            anchors.centerIn: parent
            text: "■"
            color: Theme.accentRed
            font.pixelSize: 10
        }

        HoverHandler { id: stopHover }
        TapHandler { onTapped: IslandBridge.stopTimer() }
    }
}
