import QtQuick
import "../services"
import "../themes"

Row {
    id: root
    anchors.centerIn: parent
    spacing: 8

    Text {
        text: IslandBridge.icon || "󰸗"
        color: Theme.accent
        font.pixelSize: 13
        anchors.verticalCenter: parent.verticalCenter
    }

    Text {
        text: IslandBridge.title || ""
        color: Theme.textPrimary
        font.pixelSize: 12
        font.bold: true
        anchors.verticalCenter: parent.verticalCenter
    }

    // Minimized Applications Pill inside Island Capsule
    Row {
        spacing: 6
        anchors.verticalCenter: parent.verticalCenter
        visible: IslandBridge.minimizedWindows && IslandBridge.minimizedWindows.length > 0

        Rectangle {
            width: 1
            height: 12
            radius: 0.5
            color: Qt.rgba(1, 1, 1, 0.2)
            anchors.verticalCenter: parent.verticalCenter
        }

        Repeater {
            model: IslandBridge.minimizedWindows ? Math.min(4, IslandBridge.minimizedWindows.length) : 0
            delegate: Rectangle {
                id: minIconPill
                required property int index
                property var win: IslandBridge.minimizedWindows[index]

                width: 20
                height: 20
                radius: 10
                color: minHover.hovered ? Qt.rgba(1, 1, 1, 0.22) : Qt.rgba(1, 1, 1, 0.09)
                border.color: minHover.hovered ? Theme.accent : Qt.rgba(1, 1, 1, 0.15)
                border.width: 1
                anchors.verticalCenter: parent.verticalCenter

                Text {
                    anchors.centerIn: parent
                    text: (minIconPill.win && minIconPill.win.icon) ? minIconPill.win.icon : "󰖲"
                    color: Theme.accentYellow
                    font.pixelSize: 11
                }

                HoverHandler { id: minHover }
                TapHandler {
                    onTapped: {
                        if (minIconPill.win && minIconPill.win.id) {
                            IslandBridge.restoreWindow(minIconPill.win.id);
                        }
                    }
                }
            }
        }
    }
}
