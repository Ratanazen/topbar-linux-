import QtQuick
import "../services"
import "../themes"

Item {
    id: root
    anchors.fill: parent

    readonly property bool isExpanded: IslandBridge.visualState === "mediaExpanded"

    // -------------------------------------------------------------
    // Compact Layout (fits in 38px height)
    // -------------------------------------------------------------
    Row {
        id: compactRow
        visible: !root.isExpanded
        anchors.centerIn: parent
        spacing: 10

        Text {
            text: IslandBridge.icon === "󰐊" ? "󰐊" : (IslandBridge.icon || "󰎆")
            color: Theme.accentPurple
            font.pixelSize: 14
            anchors.verticalCenter: parent.verticalCenter
        }

        Text {
            text: IslandBridge.title || "No Media"
            color: Theme.textPrimary
            font.pixelSize: 13
            font.bold: true
            elide: Text.ElideRight
            maximumLineCount: 1
            anchors.verticalCenter: parent.verticalCenter
        }

        Text {
            text: IslandBridge.subtitle ? "•  " + IslandBridge.subtitle : ""
            color: Theme.textSecondary
            font.pixelSize: 12
            elide: Text.ElideRight
            maximumLineCount: 1
            visible: text.length > 0
            anchors.verticalCenter: parent.verticalCenter
        }
    }

    // -------------------------------------------------------------
    // Expanded Layout (Card presentation with real Album Art)
    // -------------------------------------------------------------
    Column {
        id: expandedColumn
        visible: root.isExpanded
        anchors.fill: parent
        anchors.margins: 14
        spacing: 8

        // Top Row: Album artwork / Fallback Icon + Metadata
        Row {
            width: parent.width
            spacing: 12

            // Artwork Container with rounded corners
            Rectangle {
                width: 48
                height: 48
                radius: 10
                color: Qt.rgba(1, 1, 1, 0.08)
                border.color: Qt.rgba(1, 1, 1, 0.12)
                border.width: 1
                clip: true

                Image {
                    id: albumArt
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
                    visible: !albumArt.visible
                }
            }

            Column {
                width: parent.width - 64
                anchors.verticalCenter: parent.verticalCenter
                spacing: 2

                Row {
                    width: parent.width
                    spacing: 6

                    Text {
                        text: IslandBridge.title || "Now Playing"
                        color: Theme.textPrimary
                        font.pixelSize: 14
                        font.bold: true
                        elide: Text.ElideRight
                        width: Math.min(implicitWidth, parent.width - (playerTag.visible ? playerTag.width + 8 : 0))
                    }

                    Rectangle {
                        id: playerTag
                        visible: IslandBridge.playerName.length > 0
                        width: tagText.implicitWidth + 8
                        height: 16
                        radius: 4
                        color: Qt.rgba(1, 1, 1, 0.10)
                        anchors.verticalCenter: parent.verticalCenter

                        Text {
                            id: tagText
                            anchors.centerIn: parent
                            text: IslandBridge.playerName
                            color: Theme.textSecondary
                            font.pixelSize: 9
                            font.bold: true
                        }
                    }
                }

                Text {
                    text: IslandBridge.subtitle || "Media Player"
                    color: Theme.textSecondary
                    font.pixelSize: 12
                    elide: Text.ElideRight
                    width: parent.width
                }
            }
        }

        // Progress Bar with Elapsed / Duration Timers
        Column {
            width: parent.width
            spacing: 3

            Rectangle {
                width: parent.width
                height: 4
                radius: 2
                color: Qt.rgba(1, 1, 1, 0.15)

                Rectangle {
                    height: parent.height
                    radius: 2
                    width: Math.max(0, Math.min(parent.width, parent.width * IslandBridge.progressPct))
                    color: Theme.accent
                }
            }

            Row {
                width: parent.width
                visible: IslandBridge.positionStr.length > 0 || IslandBridge.durationStr.length > 0

                Text {
                    text: IslandBridge.positionStr || "00:00"
                    color: Theme.textSecondary
                    font.pixelSize: 10
                }

                Item { width: Math.max(0, parent.width - (timeTotal.width + 40)) }

                Text {
                    id: timeTotal
                    text: IslandBridge.durationStr || ""
                    color: Theme.textSecondary
                    font.pixelSize: 10
                    anchors.right: parent.right
                }
            }
        }

        // Transport Controls Row (Centered)
        Row {
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: 24

            // Previous
            Rectangle {
                width: 32
                height: 32
                radius: 16
                color: prevHover.hovered ? Qt.rgba(1, 1, 1, 0.15) : Qt.rgba(1, 1, 1, 0.05)

                Text {
                    anchors.centerIn: parent
                    text: "󰒮"
                    color: Theme.textPrimary
                    font.pixelSize: 16
                }

                HoverHandler { id: prevHover }
                TapHandler { onTapped: IslandBridge.prevMedia() }
            }

            // Play / Pause (Apple style filled circle)
            Rectangle {
                width: 36
                height: 36
                radius: 18
                color: Theme.textPrimary

                Text {
                    anchors.centerIn: parent
                    text: IslandBridge.icon === "󰐊" ? "󰏤" : "󰐊"
                    color: Theme.background
                    font.pixelSize: 18
                }

                TapHandler { onTapped: IslandBridge.toggleMedia() }
            }

            // Next
            Rectangle {
                width: 32
                height: 32
                radius: 16
                color: nextHover.hovered ? Qt.rgba(1, 1, 1, 0.15) : Qt.rgba(1, 1, 1, 0.05)

                Text {
                    anchors.centerIn: parent
                    text: "󰒭"
                    color: Theme.textPrimary
                    font.pixelSize: 16
                }

                HoverHandler { id: nextHover }
                TapHandler { onTapped: IslandBridge.nextMedia() }
            }
        }
    }
}
