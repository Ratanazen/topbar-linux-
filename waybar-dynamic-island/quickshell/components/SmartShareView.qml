import QtQuick
import "../services"
import "../themes"

Column {
    id: root
    anchors.fill: parent
    anchors.margins: 14
    spacing: 10

    // Header bar
    Item {
        width: parent.width
        height: 24

        Row {
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
            spacing: 8

            Text {
                text: "󰒍"
                color: Theme.accent
                font.pixelSize: 16
                anchors.verticalCenter: parent.verticalCenter
            }

            Text {
                text: IslandBridge.title || ("Share " + IslandBridge.droppedFiles.length + " File(s)")
                color: Theme.textPrimary
                font.pixelSize: 13
                font.bold: true
                anchors.verticalCenter: parent.verticalCenter
            }
        }

        // Cancel / Close button
        Rectangle {
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            width: 22
            height: 22
            radius: 11
            color: closeHov.hovered ? Qt.rgba(1, 1, 1, 0.2) : Qt.rgba(1, 1, 1, 0.08)

            Text {
                anchors.centerIn: parent
                text: "✕"
                color: Theme.textSecondary
                font.pixelSize: 10
            }

            HoverHandler { id: closeHov }
            TapHandler { onTapped: IslandBridge.cancelShare() }
        }
    }

    // Dropped files list / chips container
    Rectangle {
        width: parent.width
        height: 56
        radius: 10
        color: Qt.rgba(0, 0, 0, 0.25)
        border.color: Qt.rgba(1, 1, 1, 0.08)
        clip: true

        ListView {
            id: filesList
            anchors.fill: parent
            anchors.margins: 6
            orientation: ListView.Horizontal
            spacing: 8
            model: IslandBridge.droppedFiles

            delegate: Rectangle {
                width: Math.min(180, Math.max(120, fileRow.implicitWidth + 16))
                height: 44
                radius: 8
                color: Qt.rgba(1, 1, 1, 0.06)
                border.color: Qt.rgba(1, 1, 1, 0.1)

                Row {
                    id: fileRow
                    anchors.fill: parent
                    anchors.margins: 6
                    spacing: 8

                    Text {
                        text: modelData.icon || "󰈔"
                        color: Theme.accent
                        font.pixelSize: 16
                        anchors.verticalCenter: parent.verticalCenter
                    }

                    Column {
                        anchors.verticalCenter: parent.verticalCenter
                        width: parent.width - 32
                        spacing: 2

                        Text {
                            text: modelData.name || "File"
                            color: Theme.textPrimary
                            font.pixelSize: 11
                            font.bold: true
                            elide: Text.ElideMiddle
                            width: parent.width
                        }

                        Text {
                            text: (modelData.size_human || "") + (modelData.mime ? " • " + modelData.mime.split("/")[1] : "")
                            color: Theme.textSecondary
                            font.pixelSize: 9
                            elide: Text.ElideRight
                            width: parent.width
                        }
                    }
                }
            }
        }
    }

    // Section title
    Text {
        text: "Select Destination Application"
        color: Theme.textSecondary
        font.pixelSize: 10
        font.bold: true
    }

    // Sharing targets grid
    Grid {
        width: parent.width
        columns: 2
        spacing: 8

        Repeater {
            model: IslandBridge.shareTargets

            delegate: Rectangle {
                id: targetCard
                width: (parent.width - 8) / 2
                height: 52
                radius: 10
                color: {
                    if (!modelData.available) return Qt.rgba(1, 1, 1, 0.02);
                    return targetHov.hovered ? Qt.rgba(1, 1, 1, 0.15) : Qt.rgba(1, 1, 1, 0.06);
                }
                border.color: {
                    if (!modelData.available) return Qt.rgba(1, 1, 1, 0.04);
                    return targetHov.hovered ? Theme.accent : Qt.rgba(1, 1, 1, 0.1);
                }
                opacity: modelData.available ? 1.0 : 0.45

                Behavior on color { ColorAnimation { duration: 120 } }
                Behavior on border.color { ColorAnimation { duration: 120 } }

                Row {
                    anchors.fill: parent
                    anchors.margins: 8
                    spacing: 10

                    Rectangle {
                        width: 34
                        height: 34
                        radius: 8
                        color: Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.15)
                        anchors.verticalCenter: parent.verticalCenter

                        Text {
                            anchors.centerIn: parent
                            text: modelData.icon || "󰋼"
                            color: Theme.accent
                            font.pixelSize: 16
                        }
                    }

                    Column {
                        anchors.verticalCenter: parent.verticalCenter
                        width: parent.width - 48
                        spacing: 2

                        Text {
                            text: modelData.name || "Target"
                            color: Theme.textPrimary
                            font.pixelSize: 11
                            font.bold: true
                            elide: Text.ElideRight
                            width: parent.width
                        }

                        Text {
                            text: modelData.available ? (modelData.description || "") : (modelData.disabled_reason || "Unavailable")
                            color: Theme.textSecondary
                            font.pixelSize: 9
                            elide: Text.ElideRight
                            width: parent.width
                        }
                    }
                }

                HoverHandler { id: targetHov; enabled: modelData.available }
                TapHandler {
                    enabled: modelData.available
                    onTapped: {
                        IslandBridge.executeShare(modelData.id);
                    }
                }
            }
        }
    }

    // Bottom Action Bar
    Item {
        width: parent.width
        height: 28

        Row {
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            spacing: 8

            Rectangle {
                width: 90
                height: 26
                radius: 6
                color: cancelHov.hovered ? Qt.rgba(1, 1, 1, 0.15) : Qt.rgba(1, 1, 1, 0.06)

                Text {
                    anchors.centerIn: parent
                    text: "Cancel"
                    color: Theme.textSecondary
                    font.pixelSize: 10
                    font.bold: true
                }

                HoverHandler { id: cancelHov }
                TapHandler { onTapped: IslandBridge.cancelShare() }
            }

            Rectangle {
                width: 110
                height: 26
                radius: 6
                color: copyHov.hovered ? Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.35) : Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.2)
                border.color: Theme.accent

                Row {
                    anchors.centerIn: parent
                    spacing: 4

                    Text {
                        text: "󰅍"
                        color: Theme.accent
                        font.pixelSize: 11
                    }

                    Text {
                        text: "Copy Paths"
                        color: Theme.textPrimary
                        font.pixelSize: 10
                        font.bold: true
                    }
                }

                HoverHandler { id: copyHov }
                TapHandler { onTapped: IslandBridge.executeShare("clipboard") }
            }
        }
    }
}
