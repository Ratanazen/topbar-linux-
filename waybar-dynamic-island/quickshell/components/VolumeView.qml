import QtQuick
import "../services"
import "../themes"

Row {
    id: root
    spacing: 12
    anchors.centerIn: parent

    Text {
        text: IslandBridge.icon || "󰕾"
        color: IslandBridge.title === "Muted" ? Theme.accentRed : Theme.accent
        font.pixelSize: 15
        anchors.verticalCenter: parent.verticalCenter
    }

    // Smooth horizontal progress bar
    Rectangle {
        width: 140
        height: 6
        radius: 3
        color: Qt.rgba(1, 1, 1, 0.15)
        anchors.verticalCenter: parent.verticalCenter

        Rectangle {
            height: parent.height
            radius: 3
            width: Math.max(0, Math.min(parent.width, parent.width * IslandBridge.progressPct))
            color: IslandBridge.title === "Muted" ? Theme.accentRed : Theme.accent

            Behavior on width {
                NumberAnimation {
                    duration: IslandBridge.reducedMotion ? 0 : 120
                    easing.type: Easing.OutQuad
                }
            }
        }
    }

    Text {
        text: IslandBridge.title || "0%"
        color: Theme.textPrimary
        font.pixelSize: 13
        font.bold: true
        anchors.verticalCenter: parent.verticalCenter
    }
}
