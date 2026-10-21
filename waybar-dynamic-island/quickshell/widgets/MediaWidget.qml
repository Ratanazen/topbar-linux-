import QtQuick
import "../services"
import "../themes"

Rectangle {
    id: root
    width: 220
    height: 100
    radius: 16

    color: Theme.cardBackground
    border.color: Theme.border
    border.width: 1

    Row {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 12

        // Album Art or Icon
        Rectangle {
            width: 52
            height: 52
            radius: 10
            color: Qt.rgba(1, 1, 1, 0.08)
            border.color: Qt.rgba(1, 1, 1, 0.12)
            border.width: 1
            clip: true
            anchors.verticalCenter: parent.verticalCenter

            Image {
                id: art
                anchors.fill: parent
                source: IslandBridge.artUrl
                fillMode: Image.PreserveAspectCrop
                visible: status === Image.Ready && IslandBridge.artUrl.length > 0
                asynchronous: true
                cache: true
            }

            Text {
                anchors.centerIn: parent
                text: "󰎆"
                color: Theme.accentPurple
                font.pixelSize: 24
                visible: !art.visible
            }
        }

        // Details & Controls
        Column {
            width: parent.width - 64
            anchors.verticalCenter: parent.verticalCenter
            spacing: 4

            Text {
                text: IslandBridge.title || "No Media Playing"
                color: Theme.textPrimary
                font.pixelSize: 12
                font.bold: true
                elide: Text.ElideRight
                width: parent.width
            }

            Text {
                text: IslandBridge.subtitle || "Media Player"
                color: Theme.textSecondary
                font.pixelSize: 10
                elide: Text.ElideRight
                width: parent.width
            }

            Row {
                spacing: 12

                Rectangle {
                    width: 24
                    height: 24
                    radius: 12
                    color: Qt.rgba(1, 1, 1, 0.12)
                    Text { anchors.centerIn: parent; text: "󰒮"; color: Theme.textPrimary; font.pixelSize: 12 }
                    TapHandler { onTapped: IslandBridge.prevMedia() }
                }

                Rectangle {
                    width: 24
                    height: 24
                    radius: 12
                    color: Theme.accent
                    Text {
                        anchors.centerIn: parent
                        text: IslandBridge.icon === "󰐊" ? "󰏤" : "󰐊"
                        color: Theme.background
                        font.pixelSize: 12
                    }
                    TapHandler { onTapped: IslandBridge.toggleMedia() }
                }

                Rectangle {
                    width: 24
                    height: 24
                    radius: 12
                    color: Qt.rgba(1, 1, 1, 0.12)
                    Text { anchors.centerIn: parent; text: "󰒭"; color: Theme.textPrimary; font.pixelSize: 12 }
                    TapHandler { onTapped: IslandBridge.nextMedia() }
                }
            }
        }
    }
}
