import QtQuick
import "../services"
import "../themes"

Row {
    id: root
    spacing: 12
    anchors.centerIn: parent
    width: parent.width - 24

    Rectangle {
        width: 32
        height: 32
        radius: 16
        color: Qt.rgba(1, 1, 1, 0.1)
        anchors.verticalCenter: parent.verticalCenter

        Text {
            anchors.centerIn: parent
            text: IslandBridge.icon ? IslandBridge.icon : (IslandBridge.priority >= 75 ? "󰵚" : "󰂚")
            color: IslandBridge.priority >= 75 ? Theme.accentRed : Theme.accent
            font.pixelSize: 16
        }
    }

    Column {
        anchors.verticalCenter: parent.verticalCenter
        width: root.width - 70
        spacing: 2

        Text {
            text: IslandBridge.title || "Notification"
            color: Theme.textPrimary
            font.pixelSize: 13
            font.bold: true
            elide: Text.ElideRight
            width: parent.width
        }

        Text {
            text: IslandBridge.subtitle || ""
            color: Theme.textSecondary
            font.pixelSize: 11
            elide: Text.ElideRight
            width: parent.width
            visible: text.length > 0
        }
    }

    // Dismiss X button
    Rectangle {
        width: 22
        height: 22
        radius: 11
        color: dismissHover.hovered ? Qt.rgba(1, 1, 1, 0.2) : Qt.rgba(1, 1, 1, 0.08)
        anchors.verticalCenter: parent.verticalCenter

        Text {
            anchors.centerIn: parent
            text: "✕"
            color: Theme.textSecondary
            font.pixelSize: 10
        }

        HoverHandler {
            id: dismissHover
        }

        TapHandler {
            onTapped: IslandBridge.dismiss()
        }
    }
}
