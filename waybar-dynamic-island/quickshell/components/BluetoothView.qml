import QtQuick
import "../services"
import "../themes"

Item {
    id: root
    anchors.fill: parent
    anchors.margins: 10

    Column {
        anchors.fill: parent
        spacing: 8

        // -------------------------------------------------------------
        // Header Row: Title, Scan Button, Power Toggle, and Close
        // -------------------------------------------------------------
        Item {
            width: parent.width
            height: 24

            Row {
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                spacing: 6

                Text {
                    text: "󰂯"
                    color: Theme.accent
                    font.pixelSize: 14
                    anchors.verticalCenter: parent.verticalCenter
                }

                Text {
                    text: "Bluetooth"
                    color: Theme.textPrimary
                    font.pixelSize: 13
                    font.bold: true
                    anchors.verticalCenter: parent.verticalCenter
                }
            }

            Row {
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                spacing: 8

                // Scan / Discovery Radar Button
                Rectangle {
                    width: 24
                    height: 24
                    radius: 12
                    color: scanHover.hovered ? Qt.rgba(1, 1, 1, 0.20) : Qt.rgba(1, 1, 1, 0.08)
                    anchors.verticalCenter: parent.verticalCenter

                    Text {
                        anchors.centerIn: parent
                        text: "󰑐"
                        color: IslandBridge.bluetoothScanning ? Theme.accent : Theme.textSecondary
                        font.pixelSize: 12

                        RotationAnimation on rotation {
                            running: IslandBridge.bluetoothScanning
                            loops: Animation.Infinite
                            from: 0
                            to: 360
                            duration: 800
                        }
                    }

                    HoverHandler { id: scanHover }
                    TapHandler {
                        onTapped: IslandBridge.scanBluetooth()
                    }
                }

                // Adapter Power Toggle
                Rectangle {
                    width: 38
                    height: 20
                    radius: 10
                    color: IslandBridge.bluetoothPowered ? Theme.accent : Qt.rgba(1, 1, 1, 0.16)
                    anchors.verticalCenter: parent.verticalCenter

                    Rectangle {
                        width: 16
                        height: 16
                        radius: 8
                        color: "#ffffff"
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.left: IslandBridge.bluetoothPowered ? undefined : parent.left
                        anchors.right: IslandBridge.bluetoothPowered ? parent.right : undefined
                        anchors.margins: 2

                        Behavior on anchors.leftMargin { NumberAnimation { duration: 180; easing.type: Easing.OutQuad } }
                        Behavior on anchors.rightMargin { NumberAnimation { duration: 180; easing.type: Easing.OutQuad } }
                    }

                    TapHandler {
                        onTapped: IslandBridge.toggleBluetooth()
                    }
                }

                // Close Button
                Rectangle {
                    width: 22
                    height: 22
                    radius: 11
                    color: closeHover.hovered ? Qt.rgba(1, 1, 1, 0.25) : Qt.rgba(1, 1, 1, 0.08)
                    anchors.verticalCenter: parent.verticalCenter

                    Text {
                        anchors.centerIn: parent
                        text: "✕"
                        color: Theme.textSecondary
                        font.pixelSize: 10
                    }

                    HoverHandler { id: closeHover }
                    TapHandler {
                        onTapped: IslandBridge.closeBluetooth()
                    }
                }
            }
        }

        // -------------------------------------------------------------
        // Devices List Section Header
        // -------------------------------------------------------------
        Item {
            width: parent.width
            height: 16

            Text {
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                text: "DEVICES (" + (IslandBridge.bluetoothDevices ? IslandBridge.bluetoothDevices.length : 0) + ")"
                color: Theme.textSecondary
                font.pixelSize: 9
                font.bold: true
            }
        }

        // -------------------------------------------------------------
        // Devices List (Connected and Paired)
        // -------------------------------------------------------------
        Flickable {
            width: parent.width
            height: 180
            contentWidth: parent.width
            contentHeight: devListColumn.implicitHeight
            clip: true

            Column {
                id: devListColumn
                width: parent.width
                spacing: 6

                Repeater {
                    model: IslandBridge.bluetoothDevices || []

                    delegate: Rectangle {
                        required property var modelData
                        required property int index

                        width: parent.width
                        height: 40
                        radius: 10
                        color: modelData.connected
                               ? Qt.rgba(0.04, 0.52, 1.0, 0.15)
                               : (devRowHover.hovered ? Qt.rgba(1, 1, 1, 0.10) : Qt.rgba(1, 1, 1, 0.04))
                        border.color: modelData.connected ? Qt.rgba(0.04, 0.52, 1.0, 0.35) : "transparent"
                        border.width: 1

                        Row {
                            anchors.left: parent.left
                            anchors.leftMargin: 8
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: 8

                            Rectangle {
                                width: 26
                                height: 26
                                radius: 13
                                color: modelData.connected ? Qt.rgba(0.04, 0.52, 1.0, 0.25) : Qt.rgba(1, 1, 1, 0.08)
                                anchors.verticalCenter: parent.verticalCenter

                                Text {
                                    anchors.centerIn: parent
                                    text: {
                                        var ic = modelData.icon || "";
                                        if (ic.indexOf("head") !== -1 || ic.indexOf("audio") !== -1) return "󰋋";
                                        if (ic.indexOf("phone") !== -1) return "󰄜";
                                        if (ic.indexOf("mouse") !== -1) return "󰍽";
                                        if (ic.indexOf("keyboard") !== -1) return "󰌌";
                                        return "󰂱";
                                    }
                                    color: modelData.connected ? Theme.accent : Theme.textPrimary
                                    font.pixelSize: 13
                                }
                            }

                            Column {
                                anchors.verticalCenter: parent.verticalCenter
                                spacing: 1

                                Text {
                                    text: modelData.name || modelData.mac || "Bluetooth Device"
                                    color: modelData.connected ? Theme.accent : Theme.textPrimary
                                    font.pixelSize: 11
                                    font.bold: modelData.connected
                                    elide: Text.ElideRight
                                    width: parent.parent.parent.width - 150
                                }

                                Text {
                                    text: modelData.connected
                                          ? (modelData.battery !== null && modelData.battery !== undefined ? "Connected • " + modelData.battery + "%" : "Connected")
                                          : (modelData.mac || "Paired")
                                    color: Theme.textSecondary
                                    font.pixelSize: 9
                                }
                            }
                        }

                        // Connect / Disconnect Action Button
                        Rectangle {
                            anchors.right: parent.right
                            anchors.rightMargin: 8
                            anchors.verticalCenter: parent.verticalCenter
                            width: 68
                            height: 22
                            radius: 11
                            color: modelData.connected
                                   ? (btnHover.hovered ? Qt.rgba(1, 0.27, 0.23, 0.35) : Qt.rgba(1, 0.27, 0.23, 0.15))
                                   : (btnHover.hovered ? Theme.accent : Qt.rgba(1, 1, 1, 0.10))

                            Text {
                                anchors.centerIn: parent
                                text: modelData.connected ? "Disconnect" : "Connect"
                                color: modelData.connected ? Theme.accentRed : (btnHover.hovered ? "#ffffff" : Theme.textPrimary)
                                font.pixelSize: 9
                                font.bold: true
                            }

                            HoverHandler { id: btnHover }
                            TapHandler {
                                onTapped: {
                                    if (modelData.connected) {
                                        IslandBridge.disconnectBluetooth(modelData.mac);
                                    } else {
                                        IslandBridge.connectBluetooth(modelData.mac);
                                    }
                                }
                            }
                        }

                        HoverHandler { id: devRowHover }
                    }
                }

                // Empty state indicator
                Item {
                    visible: (!IslandBridge.bluetoothDevices || IslandBridge.bluetoothDevices.length === 0)
                    width: parent.width
                    height: 60

                    Text {
                        anchors.centerIn: parent
                        text: IslandBridge.bluetoothScanning ? "Scanning for devices…" : "No Bluetooth devices found"
                        color: Theme.textSecondary
                        font.pixelSize: 11
                    }
                }
            }
        }
    }
}
