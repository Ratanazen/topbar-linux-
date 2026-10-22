import QtQuick
import "../services"
import "../themes"

Item {
    id: root
    anchors.fill: parent
    clip: true

    Row {
        id: mainRow
        anchors.centerIn: parent
        spacing: 8
        height: parent.height - 18

        // =========================================================
        // 1. CPU Card (Left Column)
        // =========================================================
        Rectangle {
            id: cpuCard
            width: 114
            height: parent.height
            radius: 16
            color: cpuHover.hovered ? Qt.rgba(1, 1, 1, 0.12) : Qt.rgba(1, 1, 1, 0.06)
            border.color: cpuHover.hovered ? "#ff9f0a" : Qt.rgba(1, 1, 1, 0.10)
            border.width: 1

            HoverHandler { id: cpuHover }
            TapHandler {
                onTapped: IslandBridge.sendCommand("system", ["stats"])
            }

            Column {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 8

                // Top Orange Load Progress Bar
                Rectangle {
                    width: parent.width
                    height: 8
                    radius: 4
                    color: Qt.rgba(1, 1, 1, 0.10)
                    clip: true

                    Rectangle {
                        width: Math.max(6, parent.width * (Math.min(100, Math.max(2, IslandBridge.systemCpu)) / 100.0))
                        height: parent.height
                        radius: 4
                        gradient: Gradient {
                            orientation: Gradient.Horizontal
                            GradientStop { position: 0.0; color: "#ff9f0a" }
                            GradientStop { position: 1.0; color: "#ff375f" }
                        }

                        Behavior on width {
                            NumberAnimation { duration: 300; easing.type: Easing.OutQuad }
                        }
                    }
                }

                Item {
                    width: parent.width
                    height: 16

                    Text {
                        anchors.left: parent.left
                        text: "CPU"
                        color: Theme.textSecondary
                        font.pixelSize: 11
                        font.bold: true
                    }

                    Text {
                        anchors.right: parent.right
                        text: ""
                        color: Theme.textPrimary
                        font.pixelSize: 12
                    }
                }

                // Bottom Row: Model & Percentage
                Column {
                    width: parent.width
                    spacing: 1

                    Text {
                        text: IslandBridge.systemCpuName || "Ryzen 5"
                        color: Theme.textPrimary
                        font.pixelSize: 11
                        font.bold: true
                        elide: Text.ElideRight
                        width: parent.width
                    }

                    Text {
                        text: (IslandBridge.systemCpu || 0).toFixed(1) + "% load"
                        color: "#ff9f0a"
                        font.pixelSize: 10
                    }
                }
            }
        }

        // =========================================================
        // 2. Connectivity & Device Card (Center Column)
        // =========================================================
        Rectangle {
            id: centerCard
            width: 128
            height: parent.height
            radius: 16
            color: centerHover.hovered ? Qt.rgba(1, 1, 1, 0.12) : Qt.rgba(1, 1, 1, 0.06)
            border.color: centerHover.hovered ? Theme.accent : Qt.rgba(1, 1, 1, 0.10)
            border.width: 1

            HoverHandler { id: centerHover }

            Column {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 8

                // Top: 3 Toggle Pills (Wi-Fi, Bluetooth, Network/AirDrop)
                Row {
                    anchors.horizontalCenter: parent.horizontalCenter
                    spacing: 6

                    // Wi-Fi Toggle Pill
                    Rectangle {
                        width: 32
                        height: 48
                        radius: 10
                        color: (IslandBridge.wifiStatus && IslandBridge.wifiStatus.connected) ? Qt.rgba(0.19, 0.82, 0.35, 0.22) : Qt.rgba(1, 1, 1, 0.08)
                        border.color: (IslandBridge.wifiStatus && IslandBridge.wifiStatus.connected) ? "#30d158" : Qt.rgba(1, 1, 1, 0.14)
                        border.width: 1

                        Column {
                            anchors.centerIn: parent
                            spacing: 3

                            Text {
                                anchors.horizontalCenter: parent.horizontalCenter
                                text: "󰤨"
                                font.pixelSize: 13
                                color: (IslandBridge.wifiStatus && IslandBridge.wifiStatus.connected) ? "#30d158" : Theme.textSecondary
                            }

                            Text {
                                anchors.horizontalCenter: parent.horizontalCenter
                                text: (IslandBridge.wifiStatus && IslandBridge.wifiStatus.connected) ? "ON" : "OFF"
                                font.pixelSize: 8
                                font.bold: true
                                color: (IslandBridge.wifiStatus && IslandBridge.wifiStatus.connected) ? "#30d158" : Theme.textSecondary
                            }
                        }

                        TapHandler {
                            onTapped: IslandBridge.toggleWifi()
                        }
                    }

                    // Bluetooth Toggle Pill
                    Rectangle {
                        width: 32
                        height: 48
                        radius: 10
                        color: IslandBridge.bluetoothPowered ? Qt.rgba(0.04, 0.52, 1.0, 0.22) : Qt.rgba(1, 1, 1, 0.08)
                        border.color: IslandBridge.bluetoothPowered ? "#0a84ff" : Qt.rgba(1, 1, 1, 0.14)
                        border.width: 1

                        Column {
                            anchors.centerIn: parent
                            spacing: 3

                            Text {
                                anchors.horizontalCenter: parent.horizontalCenter
                                text: "󰂯"
                                font.pixelSize: 13
                                color: IslandBridge.bluetoothPowered ? "#0a84ff" : Theme.textSecondary
                            }

                            Text {
                                anchors.horizontalCenter: parent.horizontalCenter
                                text: IslandBridge.bluetoothPowered ? "ON" : "OFF"
                                font.pixelSize: 8
                                font.bold: true
                                color: IslandBridge.bluetoothPowered ? "#0a84ff" : Theme.textSecondary
                            }
                        }

                        TapHandler {
                            onTapped: IslandBridge.toggleBluetooth()
                        }
                    }

                    // Share / AirDrop Toggle Pill
                    Rectangle {
                        width: 32
                        height: 48
                        radius: 10
                        color: Qt.rgba(1, 1, 1, 0.08)
                        border.color: Qt.rgba(1, 1, 1, 0.14)
                        border.width: 1

                        Column {
                            anchors.centerIn: parent
                            spacing: 3

                            Text {
                                anchors.horizontalCenter: parent.horizontalCenter
                                text: "󰀝"
                                font.pixelSize: 13
                                color: Theme.textSecondary
                            }

                            Text {
                                anchors.horizontalCenter: parent.horizontalCenter
                                text: "OFF"
                                font.pixelSize: 8
                                font.bold: true
                                color: Theme.textSecondary
                            }
                        }

                        TapHandler {
                            onTapped: IslandBridge.openAirDropPicker()
                        }
                    }
                }

                // Bottom: Device Hostname Pill
                Rectangle {
                    width: parent.width
                    height: 20
                    radius: 8
                    color: Qt.rgba(1, 1, 1, 0.08)
                    anchors.horizontalCenter: parent.horizontalCenter

                    Row {
                        anchors.centerIn: parent
                        spacing: 4

                        Text {
                            text: "󰌢"
                            color: Theme.accent
                            font.pixelSize: 10
                            anchors.verticalCenter: parent.verticalCenter
                        }

                        Text {
                            text: "Ratana Arch"
                            color: Theme.textPrimary
                            font.pixelSize: 9
                            font.bold: true
                            anchors.verticalCenter: parent.verticalCenter
                        }
                    }
                }
            }
        }

        // =========================================================
        // 3. Disk Storage Card (Right Column)
        // =========================================================
        Rectangle {
            id: diskCard
            width: 114
            height: parent.height
            radius: 16
            color: diskHover.hovered ? Qt.rgba(1, 1, 1, 0.12) : Qt.rgba(1, 1, 1, 0.06)
            border.color: diskHover.hovered ? "#64d2ff" : Qt.rgba(1, 1, 1, 0.10)
            border.width: 1

            HoverHandler { id: diskHover }
            TapHandler {
                onTapped: IslandBridge.sendCommand("files", ["open"])
            }

            Column {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 8

                // Top: Disk Label and Gauge Icon
                Item {
                    width: parent.width
                    height: 24

                    Column {
                        anchors.left: parent.left
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 1
                        Text {
                            text: "Disk"
                            color: Theme.textPrimary
                            font.pixelSize: 11
                            font.bold: true
                        }
                        Text {
                            text: "Storage"
                            color: Theme.textSecondary
                            font.pixelSize: 9
                        }
                    }

                    // Circular Meter Icon
                    Rectangle {
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        width: 24
                        height: 24
                        radius: 12
                        color: Qt.rgba(0.39, 0.82, 1.0, 0.18)
                        border.color: "#64d2ff"
                        border.width: 1.5

                        Text {
                            anchors.centerIn: parent
                            text: "󰋊"
                            font.pixelSize: 11
                            color: "#64d2ff"
                        }
                    }
                }

                // Middle: Horizontal storage bar
                Rectangle {
                    width: parent.width
                    height: 6
                    radius: 3
                    color: Qt.rgba(1, 1, 1, 0.10)
                    clip: true

                    Rectangle {
                        width: Math.max(4, parent.width * (Math.min(100, Math.max(5, IslandBridge.systemDiskPct || 66)) / 100.0))
                        height: parent.height
                        radius: 3
                        color: "#64d2ff"
                    }
                }

                // Bottom: GB Used / Total
                Text {
                    text: {
                        var used = (IslandBridge.systemDiskUsed > 0) ? IslandBridge.systemDiskUsed.toFixed(1) : "288.6";
                        var tot = (IslandBridge.systemDiskTotal > 0) ? IslandBridge.systemDiskTotal.toFixed(1) : "434.6";
                        return used + "G/" + tot + "G";
                    }
                    color: Theme.textPrimary
                    font.pixelSize: 10
                    font.bold: true
                    elide: Text.ElideRight
                    width: parent.width
                }
            }
        }
    }
}
