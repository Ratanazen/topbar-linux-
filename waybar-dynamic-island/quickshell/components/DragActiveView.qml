import QtQuick
import "../services"
import "../themes"

Item {
    id: root
    anchors.fill: parent

    Row {
        anchors.centerIn: parent
        spacing: 12

        // Pulsing Icon Capsule
        Rectangle {
            width: 34
            height: 34
            radius: 17
            color: Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.2)
            border.color: Theme.accent
            border.width: 1.5
            anchors.verticalCenter: parent.verticalCenter

            Text {
                anchors.centerIn: parent
                text: "󰒍"
                color: Theme.accent
                font.pixelSize: 18

                SequentialAnimation on scale {
                    running: root.visible
                    loops: Animation.Infinite
                    PropertyAnimation { to: 1.15; duration: 600; easing.type: Easing.InOutQuad }
                    PropertyAnimation { to: 1.0; duration: 600; easing.type: Easing.InOutQuad }
                }
            }
        }

        // Text labels
        Column {
            anchors.verticalCenter: parent.verticalCenter
            spacing: 2

            Text {
                text: "Drop to Share"
                color: Theme.textPrimary
                font.pixelSize: 13
                font.bold: true
            }

            Text {
                text: "Files, images, or media"
                color: Theme.textSecondary
                font.pixelSize: 11
            }
        }
    }
}
