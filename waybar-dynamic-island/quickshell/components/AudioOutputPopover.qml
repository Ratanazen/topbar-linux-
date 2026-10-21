import QtQuick
import "../services"
import "../themes"

Rectangle {
    id: root
    width: 290
    height: contentCol.implicitHeight + 24
    radius: 14
    color: Theme.background
    border.color: Theme.border
    border.width: 1

    Column {
        id: contentCol
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: 12
        spacing: 10

        // -------------------------------------------------------------
        // Header: Volume & Live Percentage & Mute
        // -------------------------------------------------------------
        Item {
            width: parent.width
            height: 24

            Row {
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                spacing: 6

                Text {
                    text: IslandBridge.icon || "󰕾"
                    color: Theme.accent
                    font.pixelSize: 15
                    anchors.verticalCenter: parent.verticalCenter
                }

                Text {
                    text: "Sound"
                    color: Theme.textPrimary
                    font.pixelSize: 13
                    font.bold: true
                    font.family: Theme.fontFamily
                    anchors.verticalCenter: parent.verticalCenter
                }
            }

            Row {
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                spacing: 6

                // Mute / Unmute pill
                Rectangle {
                    width: muteText.implicitWidth + 14
                    height: 22
                    radius: 11
                    color: muteHover.hovered ? Qt.rgba(1, 1, 1, 0.18) : Qt.rgba(1, 1, 1, 0.08)

                    Text {
                        id: muteText
                        anchors.centerIn: parent
                        text: IslandBridge.title === "Muted" ? "Unmute" : (IslandBridge.title || "Mute")
                        color: IslandBridge.title === "Muted" ? Theme.accentRed : Theme.textPrimary
                        font.pixelSize: 10
                        font.bold: true
                    }

                    HoverHandler { id: muteHover }
                    TapHandler { onTapped: IslandBridge.volumeMute() }
                }

                // Close Button
                Rectangle {
                    width: 22
                    height: 22
                    radius: 11
                    color: closeHover.hovered ? Qt.rgba(1, 1, 1, 0.20) : Qt.rgba(1, 1, 1, 0.08)

                    Text {
                        anchors.centerIn: parent
                        text: "✕"
                        color: Theme.textSecondary
                        font.pixelSize: 10
                    }

                    HoverHandler { id: closeHover }
                    TapHandler { onTapped: IslandBridge.dismiss() }
                }
            }
        }

        // -------------------------------------------------------------
        // Interactive Volume Slider Bar (macOS Pill Slider)
        // -------------------------------------------------------------
        Rectangle {
            id: sliderTrack
            width: parent.width
            height: 32
            radius: 12
            color: Qt.rgba(1, 1, 1, 0.12)
            clip: true

            Rectangle {
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                anchors.left: parent.left
                radius: 12
                width: Math.max(32, Math.min(parent.width, parent.width * (IslandBridge.progressPct > 0 ? IslandBridge.progressPct : 0.65)))
                color: Qt.rgba(1, 1, 1, 0.88)

                Behavior on width {
                    NumberAnimation {
                        duration: IslandBridge.reducedMotion ? 0 : 80
                        easing.type: Easing.OutQuad
                    }
                }
            }

            // Left speaker icon in Apple blue
            Text {
                anchors.verticalCenter: parent.verticalCenter
                anchors.left: parent.left
                anchors.leftMargin: 10
                text: IslandBridge.title === "Muted" ? "󰝟" : (IslandBridge.icon || "󰕾")
                color: IslandBridge.title === "Muted" ? "#ff453a" : "#007AFF"
                font.pixelSize: 15
            }

            // Percentage text right-aligned
            Text {
                anchors.verticalCenter: parent.verticalCenter
                anchors.right: parent.right
                anchors.rightMargin: 10
                text: Math.round(IslandBridge.progressPct * 100) + "%"
                color: "#1c1c1e"
                font.pixelSize: 11
                font.bold: true
                font.family: Theme.fontFamily
            }

            MouseArea {
                anchors.fill: parent
                onClicked: function(mouse) {
                    var pct = Math.max(0, Math.min(1.0, mouse.x / parent.width));
                    var intPct = Math.round(pct * 100);
                    IslandBridge.sendCommand("volume_up", [intPct + "%"]);
                }
                onWheel: wheel => {
                    if (wheel.angleDelta.y > 0) IslandBridge.volumeUp();
                    else IslandBridge.volumeDown();
                }
            }
        }

        Rectangle {
            width: parent.width
            height: 1
            color: Qt.rgba(1, 1, 1, 0.08)
        }

        // -------------------------------------------------------------
        // Output Devices Section
        // -------------------------------------------------------------
        Text {
            text: "OUTPUT DEVICE"
            color: Theme.textSecondary
            font.pixelSize: 9
            font.bold: true
        }

        Column {
            width: parent.width
            spacing: 4

            Repeater {
                model: IslandBridge.audioSinks && IslandBridge.audioSinks.length > 0
                       ? IslandBridge.audioSinks
                       : [{ id: "default", name: "Default Audio Output", description: "Internal Audio Output", is_default: true }]

                delegate: Rectangle {
                    required property var modelData
                    width: parent.width
                    height: 32
                    radius: 8
                    color: sinkHover.hovered
                           ? Qt.rgba(1, 1, 1, 0.12)
                           : (modelData.is_default ? Qt.rgba(0.25, 0.60, 1.0, 0.15) : "transparent")

                    Row {
                        anchors.fill: parent
                        anchors.margins: 6
                        spacing: 8

                        Text {
                            text: modelData.is_default ? "✓" : " "
                            color: Theme.accent
                            font.pixelSize: 12
                            font.bold: true
                            anchors.verticalCenter: parent.verticalCenter
                            width: 14
                        }

                        Text {
                            text: (modelData.name && modelData.name.toLowerCase().indexOf("head") !== -1) ? "󰋋" : "󰓃"
                            color: Theme.textPrimary
                            font.pixelSize: 13
                            anchors.verticalCenter: parent.verticalCenter
                        }

                        Column {
                            anchors.verticalCenter: parent.verticalCenter
                            width: parent.width - 50

                            Text {
                                text: modelData.description || modelData.name || "Output Sink"
                                color: Theme.textPrimary
                                font.pixelSize: 11
                                font.bold: Boolean(modelData.is_default)
                                elide: Text.ElideRight
                                width: parent.width
                            }
                        }
                    }

                    HoverHandler { id: sinkHover }
                    TapHandler {
                        onTapped: {
                            if (modelData.name) {
                                IslandBridge.setAudioSink(modelData.name);
                            }
                        }
                    }
                }
            }
        }

        // -------------------------------------------------------------
        // Microphone Status Row
        // -------------------------------------------------------------
        Rectangle {
            width: parent.width
            height: 1
            color: Qt.rgba(1, 1, 1, 0.08)
        }

        Row {
            width: parent.width
            spacing: 8

            Text {
                text: "󰍬"
                color: IslandBridge.micActive ? Theme.accentOrange : Theme.textSecondary
                font.pixelSize: 13
                anchors.verticalCenter: parent.verticalCenter
            }

            Text {
                text: IslandBridge.micActive ? "Microphone: In Use" : "Microphone: Idle"
                color: IslandBridge.micActive ? Theme.accentOrange : Theme.textSecondary
                font.pixelSize: 10
                anchors.verticalCenter: parent.verticalCenter
            }
        }
    }
}
