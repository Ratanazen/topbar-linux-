import QtQuick
import "../services"
import "../themes"

Row {
    id: root
    spacing: 10
    anchors.centerIn: parent

    // Pulsing Red Recording Dot
    Rectangle {
        id: recDot
        width: 10
        height: 10
        radius: 5
        color: Theme.accentRed
        anchors.verticalCenter: parent.verticalCenter

        SequentialAnimation on opacity {
            running: root.visible && !IslandBridge.reducedMotion
            loops: Animation.Infinite
            NumberAnimation { to: 0.3; duration: 600; easing.type: Easing.InOutQuad }
            NumberAnimation { to: 1.0; duration: 600; easing.type: Easing.InOutQuad }
        }
    }

    Text {
        text: "REC"
        color: Theme.accentRed
        font.pixelSize: 12
        font.bold: true
        anchors.verticalCenter: parent.verticalCenter
    }

    Text {
        text: IslandBridge.subtitle ? IslandBridge.subtitle : "Recording"
        color: Theme.textPrimary
        font.pixelSize: 13
        font.bold: true
        anchors.verticalCenter: parent.verticalCenter
    }
}
