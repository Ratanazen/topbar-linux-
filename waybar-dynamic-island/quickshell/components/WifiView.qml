import QtQuick
import "../services"
import "../themes"

Item {
    id: root
    anchors.fill: parent
    anchors.margins: 10

    property string selectedSsid: ""
    property bool isPromptingPassword: false
    property string enteredPassword: ""

    Column {
        anchors.fill: parent
        spacing: 8

        // -------------------------------------------------------------
        // Header Row: Title, Scan Button, Radio Toggle, and Close
        // -------------------------------------------------------------
        Item {
            width: parent.width
            height: 24

            Row {
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                spacing: 6

                Text {
                    text: "󰤨"
                    color: Theme.accentCyan
                    font.pixelSize: 14
                    anchors.verticalCenter: parent.verticalCenter
                }

                Text {
                    text: "Wi-Fi"
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

                // Rescan / Refresh Button
                Rectangle {
                    width: 24
                    height: 24
                    radius: 12
                    color: scanHover.hovered ? Qt.rgba(1, 1, 1, 0.20) : Qt.rgba(1, 1, 1, 0.08)
                    anchors.verticalCenter: parent.verticalCenter

                    Text {
                        id: scanIcon
                        anchors.centerIn: parent
                        text: "󰑐"
                        color: IslandBridge.wifiScanning ? Theme.accentCyan : Theme.textSecondary
                        font.pixelSize: 12

                        RotationAnimation on rotation {
                            running: IslandBridge.wifiScanning
                            loops: Animation.Infinite
                            from: 0
                            to: 360
                            duration: 800
                        }
                    }

                    HoverHandler { id: scanHover }
                    TapHandler {
                        onTapped: IslandBridge.scanWifi()
                    }
                }

                // Radio Toggle Pill
                Rectangle {
                    width: 38
                    height: 20
                    radius: 10
                    color: (IslandBridge.wifiStatus && IslandBridge.wifiStatus.enabled) ? Theme.accent : Qt.rgba(1, 1, 1, 0.16)
                    anchors.verticalCenter: parent.verticalCenter

                    Rectangle {
                        width: 16
                        height: 16
                        radius: 8
                        color: "#ffffff"
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.left: (IslandBridge.wifiStatus && IslandBridge.wifiStatus.enabled) ? undefined : parent.left
                        anchors.right: (IslandBridge.wifiStatus && IslandBridge.wifiStatus.enabled) ? parent.right : undefined
                        anchors.margins: 2

                        Behavior on anchors.leftMargin { NumberAnimation { duration: 180; easing.type: Easing.OutQuad } }
                        Behavior on anchors.rightMargin { NumberAnimation { duration: 180; easing.type: Easing.OutQuad } }
                    }

                    TapHandler {
                        onTapped: IslandBridge.toggleWifi()
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
                        onTapped: IslandBridge.closeWifi()
                    }
                }
            }
        }

        // -------------------------------------------------------------
        // Active Connection Card
        // -------------------------------------------------------------
        Rectangle {
            width: parent.width
            height: 48
            radius: 12
            color: (IslandBridge.wifiStatus && IslandBridge.wifiStatus.connected)
                   ? Qt.rgba(0.04, 0.52, 1.0, 0.18)
                   : Theme.cardBackground
            border.color: (IslandBridge.wifiStatus && IslandBridge.wifiStatus.connected)
                          ? Qt.rgba(0.04, 0.52, 1.0, 0.40)
                          : Qt.rgba(1, 1, 1, 0.08)
            border.width: 1

            Row {
                anchors.left: parent.left
                anchors.leftMargin: 10
                anchors.verticalCenter: parent.verticalCenter
                spacing: 10

                Rectangle {
                    width: 30
                    height: 30
                    radius: 15
                    color: (IslandBridge.wifiStatus && IslandBridge.wifiStatus.connected)
                           ? Qt.rgba(0.04, 0.52, 1.0, 0.3)
                           : Qt.rgba(1, 1, 1, 0.1)
                    anchors.verticalCenter: parent.verticalCenter

                    Text {
                        anchors.centerIn: parent
                        text: (IslandBridge.wifiStatus && IslandBridge.wifiStatus.icon) ? IslandBridge.wifiStatus.icon : "󰤮"
                        color: (IslandBridge.wifiStatus && IslandBridge.wifiStatus.connected) ? Theme.accent : Theme.textSecondary
                        font.pixelSize: 15
                    }
                }

                Column {
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 1

                    Text {
                        text: (IslandBridge.wifiStatus && IslandBridge.wifiStatus.connected)
                              ? (IslandBridge.wifiStatus.ssid || "Connected")
                              : "Not Connected"
                        color: Theme.textPrimary
                        font.pixelSize: 12
                        font.bold: true
                        elide: Text.ElideRight
                    }

                    Text {
                        text: (IslandBridge.wifiStatus && IslandBridge.wifiStatus.connected)
                              ? ("Signal: " + IslandBridge.wifiStatus.signal + "% • Active")
                              : "Select a network below to connect"
                        color: Theme.textSecondary
                        font.pixelSize: 10
                    }
                }
            }

            // Disconnect Button
            Rectangle {
                visible: (IslandBridge.wifiStatus && IslandBridge.wifiStatus.connected)
                anchors.right: parent.right
                anchors.rightMargin: 10
                anchors.verticalCenter: parent.verticalCenter
                width: 70
                height: 24
                radius: 12
                color: disconnHover.hovered ? Qt.rgba(1, 0.27, 0.23, 0.35) : Qt.rgba(1, 0.27, 0.23, 0.18)

                Text {
                    anchors.centerIn: parent
                    text: "Disconnect"
                    color: Theme.accentRed
                    font.pixelSize: 10
                    font.bold: true
                }

                HoverHandler { id: disconnHover }
                TapHandler {
                    onTapped: IslandBridge.disconnectWifi()
                }
            }
        }

        // -------------------------------------------------------------
        // Inline Password Prompt Dialog (if connecting to secure network)
        // -------------------------------------------------------------
        Rectangle {
            visible: root.isPromptingPassword
            width: parent.width
            height: 60
            radius: 10
            color: Qt.rgba(1, 1, 1, 0.08)
            border.color: Theme.accent
            border.width: 1

            Column {
                anchors.fill: parent
                anchors.margins: 6
                spacing: 4

                Row {
                    width: parent.width
                    spacing: 6

                    Text {
                        text: "Password for " + root.selectedSsid + ":"
                        color: Theme.textPrimary
                        font.pixelSize: 10
                        font.bold: true
                        elide: Text.ElideRight
                        width: parent.width - 130
                    }

                    // Cancel
                    Rectangle {
                        width: 50
                        height: 18
                        radius: 9
                        color: pwdCancelHover.hovered ? Qt.rgba(1, 1, 1, 0.25) : Qt.rgba(1, 1, 1, 0.12)

                        Text {
                            anchors.centerIn: parent
                            text: "Cancel"
                            color: Theme.textSecondary
                            font.pixelSize: 9
                        }
                        HoverHandler { id: pwdCancelHover }
                        TapHandler {
                            onTapped: {
                                root.isPromptingPassword = false;
                                root.enteredPassword = "";
                            }
                        }
                    }

                    // Join
                    Rectangle {
                        width: 50
                        height: 18
                        radius: 9
                        color: pwdJoinHover.hovered ? Theme.accent : Qt.rgba(0.04, 0.52, 1.0, 0.6)

                        Text {
                            anchors.centerIn: parent
                            text: "Join"
                            color: "#ffffff"
                            font.pixelSize: 9
                            font.bold: true
                        }
                        HoverHandler { id: pwdJoinHover }
                        TapHandler {
                            onTapped: {
                                IslandBridge.connectWifi(root.selectedSsid, pwdInput.text);
                                root.isPromptingPassword = false;
                                root.enteredPassword = "";
                            }
                        }
                    }
                }

                Rectangle {
                    width: parent.width
                    height: 22
                    radius: 6
                    color: Qt.rgba(0, 0, 0, 0.35)
                    border.color: Qt.rgba(1, 1, 1, 0.15)
                    border.width: 1

                    TextInput {
                        id: pwdInput
                        anchors.fill: parent
                        anchors.margins: 3
                        color: Theme.textPrimary
                        font.pixelSize: 11
                        echoMode: TextInput.Password
                        focus: root.isPromptingPassword
                        onAccepted: {
                            IslandBridge.connectWifi(root.selectedSsid, pwdInput.text);
                            root.isPromptingPassword = false;
                            root.enteredPassword = "";
                        }
                    }
                }
            }
        }

        // -------------------------------------------------------------
        // Available Networks Section Header
        // -------------------------------------------------------------
        Item {
            width: parent.width
            height: 16

            Text {
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                text: "AVAILABLE NETWORKS (" + (IslandBridge.wifiNetworks ? IslandBridge.wifiNetworks.length : 0) + ")"
                color: Theme.textSecondary
                font.pixelSize: 9
                font.bold: true
            }
        }

        // -------------------------------------------------------------
        // Scrollable Networks List
        // -------------------------------------------------------------
        Flickable {
            width: parent.width
            height: root.isPromptingPassword ? 100 : 160
            contentWidth: parent.width
            contentHeight: networkListColumn.implicitHeight
            clip: true

            Column {
                id: networkListColumn
                width: parent.width
                spacing: 4

                Repeater {
                    model: IslandBridge.wifiNetworks || []

                    delegate: Rectangle {
                        required property var modelData
                        required property int index

                        width: parent.width
                        height: 34
                        radius: 8
                        color: netRowHover.hovered ? Qt.rgba(1, 1, 1, 0.12) : Qt.rgba(1, 1, 1, 0.04)
                        border.color: modelData.in_use ? Qt.rgba(0.04, 0.52, 1.0, 0.3) : "transparent"
                        border.width: 1

                        Row {
                            anchors.left: parent.left
                            anchors.leftMargin: 8
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: 8

                            Text {
                                text: modelData.icon || "󰤨"
                                color: modelData.in_use ? Theme.accent : Theme.textPrimary
                                font.pixelSize: 13
                                anchors.verticalCenter: parent.verticalCenter
                            }

                            Text {
                                text: modelData.ssid || "Unknown Network"
                                color: modelData.in_use ? Theme.accent : Theme.textPrimary
                                font.pixelSize: 11
                                font.bold: modelData.in_use
                                elide: Text.ElideRight
                                width: parent.parent.width - 150
                                anchors.verticalCenter: parent.verticalCenter
                            }
                        }

                        Row {
                            anchors.right: parent.right
                            anchors.rightMargin: 8
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: 6

                            // Lock Icon
                            Text {
                                visible: modelData.is_secure
                                text: "󰌾"
                                color: Theme.textSecondary
                                font.pixelSize: 10
                                anchors.verticalCenter: parent.verticalCenter
                            }

                            // Signal %
                            Text {
                                text: modelData.signal + "%"
                                color: Theme.textSecondary
                                font.pixelSize: 9
                                anchors.verticalCenter: parent.verticalCenter
                            }

                            // Connect Button
                            Rectangle {
                                width: 50
                                height: 20
                                radius: 10
                                color: modelData.in_use ? Qt.rgba(0.04, 0.52, 1.0, 0.2) : (rowConnHover.hovered ? Theme.accent : Qt.rgba(1, 1, 1, 0.1))
                                anchors.verticalCenter: parent.verticalCenter

                                Text {
                                    anchors.centerIn: parent
                                    text: modelData.in_use ? "Active" : "Join"
                                    color: modelData.in_use ? Theme.accent : "#ffffff"
                                    font.pixelSize: 9
                                    font.bold: true
                                }

                                HoverHandler { id: rowConnHover }
                                TapHandler {
                                    onTapped: {
                                        if (modelData.in_use) return;
                                        if (modelData.is_secure) {
                                            root.selectedSsid = modelData.ssid;
                                            root.isPromptingPassword = true;
                                        } else {
                                            IslandBridge.connectWifi(modelData.ssid, "");
                                        }
                                    }
                                }
                            }
                        }

                        HoverHandler { id: netRowHover }
                    }
                }

                // Empty / Scanning state indicator
                Item {
                    visible: (!IslandBridge.wifiNetworks || IslandBridge.wifiNetworks.length === 0)
                    width: parent.width
                    height: 60

                    Text {
                        anchors.centerIn: parent
                        text: IslandBridge.wifiScanning ? "Scanning for networks…" : "No Wi-Fi networks found"
                        color: Theme.textSecondary
                        font.pixelSize: 11
                    }
                }
            }
        }
    }
}
