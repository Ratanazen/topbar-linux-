import QtQuick
import "../services"
import "../themes"

Rectangle {
    id: root
    width: 250
    height: col.implicitHeight + 24
    radius: 14
    color: Theme.background
    border.color: Theme.border
    border.width: 1

    readonly property bool hasBattery: IslandBridge.deviceBattery !== null
    readonly property int batteryPct: IslandBridge.deviceBattery !== null ? IslandBridge.deviceBattery : 100

    Column {
        id: col
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: 12
        spacing: 10

        // -------------------------------------------------------------
        // Header: Battery Icon + Status
        // -------------------------------------------------------------
        Row {
            width: parent.width
            height: 24
            spacing: 8

            Text {
                text: hasBattery ? (batteryPct > 20 ? "󰁹" : "󰂃") : "󰚥"
                color: hasBattery ? (batteryPct > 20 ? Theme.accentGreen : Theme.accentRed) : Theme.accentCyan
                font.pixelSize: 16
                anchors.verticalCenter: parent.verticalCenter
            }

            Column {
                anchors.verticalCenter: parent.verticalCenter
                spacing: 1

                Text {
                    text: hasBattery ? (batteryPct + "% Charged") : "Power Adapter Connected"
                    color: Theme.textPrimary
                    font.pixelSize: 12
                    font.bold: true
                }

                Text {
                    text: hasBattery ? "Power Source: Battery" : "Power Source: AC Power"
                    color: Theme.textSecondary
                    font.pixelSize: 10
                }
            }
        }

        Rectangle {
            width: parent.width
            height: 1
            color: Qt.rgba(1, 1, 1, 0.08)
        }

        // -------------------------------------------------------------
        // Power Mode Selection
        // -------------------------------------------------------------
        Text {
            text: "POWER MODE"
            color: Theme.textSecondary
            font.pixelSize: 9
            font.bold: true
        }

        Column {
            width: parent.width
            spacing: 4

            Repeater {
                model: [
                    { id: "balanced", name: "Balanced", icon: "󰾆", active: true },
                    { id: "power-saver", name: "Low Power Mode", icon: "󰌪", active: false }
                ]

                delegate: Rectangle {
                    required property var modelData
                    width: parent.width
                    height: 28
                    radius: 6
                    color: modeHover.hovered ? Qt.rgba(1, 1, 1, 0.12) : "transparent"

                    Row {
                        anchors.fill: parent
                        anchors.margins: 6
                        spacing: 8

                        Text {
                            text: modelData.icon
                            color: Theme.textPrimary
                            font.pixelSize: 12
                            anchors.verticalCenter: parent.verticalCenter
                        }

                        Text {
                            text: modelData.name
                            color: Theme.textPrimary
                            font.pixelSize: 11
                            anchors.verticalCenter: parent.verticalCenter
                        }
                    }

                    HoverHandler { id: modeHover }
                    TapHandler {
                        onTapped: {
                            IslandBridge.sendCommand("profile", ["set", modelData.id]);
                            IslandBridge.dismiss();
                        }
                    }
                }
            }
        }

        Rectangle {
            width: parent.width
            height: 1
            color: Qt.rgba(1, 1, 1, 0.08)
        }

        // -------------------------------------------------------------
        // Battery Settings Action
        // -------------------------------------------------------------
        Rectangle {
            width: parent.width
            height: 26
            radius: 6
            color: bHover.hovered ? Qt.rgba(1, 1, 1, 0.12) : "transparent"

            Text {
                anchors.left: parent.left
                anchors.leftMargin: 6
                anchors.verticalCenter: parent.verticalCenter
                text: "Battery Settings..."
                color: Theme.textPrimary
                font.pixelSize: 11
            }

            HoverHandler { id: bHover }
            TapHandler {
                onTapped: {
                    IslandBridge.dismiss();
                    IslandBridge.openSettings();
                }
            }
        }
    }
}
