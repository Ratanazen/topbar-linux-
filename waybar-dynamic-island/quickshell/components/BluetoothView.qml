import QtQuick
import "../services"
import "../themes"

Row {
    id: root
    anchors.centerIn: parent
    spacing: 10

    // Animated Pulsing Bluetooth Icon
    Rectangle {
        id: iconBg
        width: 24
        height: 24
        radius: 12
        color: IslandBridge.subtitle.indexOf("Failed") !== -1 ? Qt.rgba(1, 0.27, 0.23, 0.25) : Qt.rgba(0.04, 0.52, 1.0, 0.2)
        anchors.verticalCenter: parent.verticalCenter

        Text {
            anchors.centerIn: parent
            text: IslandBridge.icon || "󰂯"
            color: IslandBridge.subtitle.indexOf("Failed") !== -1 ? Theme.accentRed : Theme.accent
            font.pixelSize: 14
        }

        // Pulse animation when connecting
        SequentialAnimation on scale {
            running: root.visible && IslandBridge.title === "Connecting…" && !IslandBridge.reducedMotion
            loops: Animation.Infinite
            NumberAnimation { to: 1.15; duration: 600; easing.type: Easing.InOutQuad }
            NumberAnimation { to: 1.0; duration: 600; easing.type: Easing.InOutQuad }
        }
    }

    Column {
        anchors.verticalCenter: parent.verticalCenter
        spacing: 1

        Text {
            text: IslandBridge.title || "Bluetooth"
            color: Theme.textPrimary
            font.pixelSize: 12
            font.bold: true
        }

        Text {
            visible: text.length > 0
            text: IslandBridge.subtitle || ""
            color: Theme.textSecondary
            font.pixelSize: 10
            elide: Text.ElideRight
            maximumLineCount: 1
        }
    }
}
