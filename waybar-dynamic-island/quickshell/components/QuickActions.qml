import QtQuick
import "../services"
import "../themes"

Column {
    id: root
    anchors.fill: parent
    anchors.margins: 12
    spacing: 8

    // -------------------------------------------------------------
    // Header Row: Title + Close Button
    // -------------------------------------------------------------
    Item {
        width: parent.width
        height: 22

        Row {
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
            spacing: 6

            Text {
                text: "󰘳"
                color: "#0a84ff"
                font.pixelSize: 14
            }
            Text {
                text: "Control Center"
                color: Theme.textPrimary
                font.pixelSize: 12
                font.bold: true
            }
        }

        Rectangle {
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
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

    // -------------------------------------------------------------
    // macOS Section 1: 2-Column Grid (Connectivity & Focus / Dock)
    // -------------------------------------------------------------
    Row {
        width: parent.width
        spacing: 8

        // Left Column: Connectivity Big Card (Wi-Fi, Bluetooth, AirDrop)
        Rectangle {
            width: (parent.width - 8) / 2
            height: 126
            radius: 14
            color: Theme.cardBackground
            border.color: Theme.border
            border.width: 1

            Column {
                anchors.fill: parent
                anchors.margins: 8
                spacing: 6

                // 1. Wi-Fi Row
                Item {
                    width: parent.width
                    height: 32

                    Rectangle {
                        id: wifiCircle
                        width: 28
                        height: 28
                        radius: 14
                        color: (IslandBridge.wifiStatus && IslandBridge.wifiStatus.connected) ? "#007AFF" : Qt.rgba(1, 1, 1, 0.12)
                        anchors.left: parent.left
                        anchors.verticalCenter: parent.verticalCenter

                        Text {
                            anchors.centerIn: parent
                            text: "󰤨"
                            color: "#ffffff"
                            font.pixelSize: 14
                        }
                    }

                    Column {
                        anchors.left: wifiCircle.right
                        anchors.leftMargin: 8
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 1

                        Text {
                            text: "Wi-Fi"
                            color: Theme.textPrimary
                            font.pixelSize: 11
                            font.bold: true
                        }
                        Text {
                            text: (IslandBridge.wifiStatus && IslandBridge.wifiStatus.connected)
                                  ? (IslandBridge.wifiStatus.ssid || "Connected")
                                  : "Disconnected"
                            color: Theme.textSecondary
                            font.pixelSize: 9
                            elide: Text.ElideRight
                            width: parent.width - 6
                        }
                    }

                    HoverHandler { id: wfHover }
                    TapHandler { onTapped: IslandBridge.openWifi() }
                }

                Rectangle { width: parent.width; height: 1; color: Qt.rgba(1, 1, 1, 0.06) }

                // 2. Bluetooth Row
                Item {
                    width: parent.width
                    height: 32

                    Rectangle {
                        id: btCircle
                        width: 28
                        height: 28
                        radius: 14
                        color: IslandBridge.bluetoothPowered ? "#007AFF" : Qt.rgba(1, 1, 1, 0.12)
                        anchors.left: parent.left
                        anchors.verticalCenter: parent.verticalCenter

                        Text {
                            anchors.centerIn: parent
                            text: "󰂯"
                            color: "#ffffff"
                            font.pixelSize: 14
                        }
                    }

                    Column {
                        anchors.left: btCircle.right
                        anchors.leftMargin: 8
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 1

                        Text {
                            text: "Bluetooth"
                            color: Theme.textPrimary
                            font.pixelSize: 11
                            font.bold: true
                        }
                        Text {
                            text: (IslandBridge.bluetoothDevices && IslandBridge.bluetoothDevices.length > 0 && IslandBridge.bluetoothDevices[0].connected)
                                  ? (IslandBridge.bluetoothDevices[0].name || "Connected")
                                  : (IslandBridge.bluetoothPowered ? "Ready" : "Off")
                            color: Theme.textSecondary
                            font.pixelSize: 9
                            elide: Text.ElideRight
                            width: parent.width - 6
                        }
                    }

                    HoverHandler { id: bthHover }
                    TapHandler { onTapped: IslandBridge.openBluetooth() }
                }

                Rectangle { width: parent.width; height: 1; color: Qt.rgba(1, 1, 1, 0.06) }

                // 3. AirDrop / Smart Share Row
                Item {
                    width: parent.width
                    height: 30

                    Rectangle {
                        id: adCircle
                        width: 28
                        height: 28
                        radius: 14
                        color: "#007AFF"
                        anchors.left: parent.left
                        anchors.verticalCenter: parent.verticalCenter

                        Text {
                            anchors.centerIn: parent
                            text: "󱎰"
                            color: "#ffffff"
                            font.pixelSize: 14
                        }
                    }

                    Column {
                        anchors.left: adCircle.right
                        anchors.leftMargin: 8
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 1

                        Text {
                            text: "AirDrop"
                            color: Theme.textPrimary
                            font.pixelSize: 11
                            font.bold: true
                        }
                        Text {
                            text: "Contacts Only"
                            color: Theme.textSecondary
                            font.pixelSize: 9
                            elide: Text.ElideRight
                            width: parent.width - 6
                        }
                    }

                    HoverHandler { id: adHover }
                    TapHandler {
                        onTapped: IslandBridge.openAirDropPicker()
                    }
                }
            }
        }

        // Right Column: Stacked Focus & Dock Cards
        Column {
            width: (parent.width - 8) / 2
            spacing: 8

            // Focus / Do Not Disturb Tile
            Rectangle {
                width: parent.width
                height: 59
                radius: 14
                color: Theme.cardBackground
                border.color: Theme.border
                border.width: 1

                Row {
                    anchors.fill: parent
                    anchors.margins: 10
                    spacing: 10

                    Rectangle {
                        width: 34
                        height: 34
                        radius: 17
                        color: "#AF52DE"
                        anchors.verticalCenter: parent.verticalCenter

                        Text {
                            anchors.centerIn: parent
                            text: "󰂛"
                            color: "#ffffff"
                            font.pixelSize: 17
                        }
                    }

                    Column {
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 2

                        Text {
                            text: "Focus"
                            color: Theme.textPrimary
                            font.pixelSize: 11
                            font.bold: true
                        }
                        Text {
                            text: "Do Not Disturb"
                            color: Theme.textSecondary
                            font.pixelSize: 9
                        }
                    }
                }

                HoverHandler { id: focusHover }
                TapHandler { onTapped: IslandBridge.dndToggle() }
            }

            // Stage Manager / Dock Tile
            Rectangle {
                width: parent.width
                height: 59
                radius: 14
                color: Theme.cardBackground
                border.color: Theme.border
                border.width: 1

                Row {
                    anchors.fill: parent
                    anchors.margins: 10
                    spacing: 10

                    Rectangle {
                        width: 34
                        height: 34
                        radius: 17
                        color: IslandBridge.dockEnabled ? "#30B0C7" : Qt.rgba(1, 1, 1, 0.12)
                        anchors.verticalCenter: parent.verticalCenter

                        Text {
                            anchors.centerIn: parent
                            text: "󰀻"
                            color: "#ffffff"
                            font.pixelSize: 17
                        }
                    }

                    Column {
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 2

                        Text {
                            text: "Dock"
                            color: Theme.textPrimary
                            font.pixelSize: 11
                            font.bold: true
                        }
                        Text {
                            text: IslandBridge.dockEnabled ? "Visible" : "Hidden"
                            color: Theme.textSecondary
                            font.pixelSize: 9
                        }
                    }
                }

                HoverHandler { id: dockHover }
                TapHandler { onTapped: IslandBridge.toggleDock() }
            }
        }
    }

    // -------------------------------------------------------------
    // macOS Section 2: Display (Brightness) Pill Slider
    // -------------------------------------------------------------
    Rectangle {
        width: parent.width
        height: 40
        radius: 14
        color: Theme.cardBackground
        border.color: Theme.border
        border.width: 1

        Item {
            anchors.fill: parent
            anchors.margins: 6

            // Outer slider track
            Rectangle {
                id: brightTrack
                anchors.fill: parent
                radius: 14
                color: Qt.rgba(1, 1, 1, 0.10)
                clip: true

                // Filled portion
                Rectangle {
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    anchors.left: parent.left
                    width: parent.width * 0.75
                    radius: 14
                    color: Qt.rgba(1, 1, 1, 0.82)
                }

                // Left sun icon
                Text {
                    anchors.left: parent.left
                    anchors.leftMargin: 10
                    anchors.verticalCenter: parent.verticalCenter
                    text: "󰃠"
                    color: "#FF9500"
                    font.pixelSize: 16
                }

                // Title label
                Text {
                    anchors.left: parent.left
                    anchors.leftMargin: 34
                    anchors.verticalCenter: parent.verticalCenter
                    text: "Display"
                    color: "#1c1c1e"
                    font.pixelSize: 11
                    font.bold: true
                }
            }

            MouseArea {
                anchors.fill: parent
                onWheel: wheel => {
                    if (wheel.angleDelta.y > 0) IslandBridge.brightnessUp();
                    else IslandBridge.brightnessDown();
                }
                onClicked: IslandBridge.brightnessUp()
            }
        }
    }

    // -------------------------------------------------------------
    // macOS Section 3: Sound (Volume) Pill Slider
    // -------------------------------------------------------------
    Rectangle {
        width: parent.width
        height: 40
        radius: 14
        color: Theme.cardBackground
        border.color: Theme.border
        border.width: 1

        Item {
            anchors.fill: parent
            anchors.margins: 6

            // Outer slider track
            Rectangle {
                id: soundTrack
                anchors.fill: parent
                radius: 14
                color: Qt.rgba(1, 1, 1, 0.10)
                clip: true

                // Filled portion
                Rectangle {
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    anchors.left: parent.left
                    width: Math.max(34, Math.min(parent.width, parent.width * (IslandBridge.progressPct > 0 ? IslandBridge.progressPct : 0.65)))
                    radius: 14
                    color: Qt.rgba(1, 1, 1, 0.88)

                    Behavior on width {
                        NumberAnimation {
                            duration: IslandBridge.reducedMotion ? 0 : 80
                            easing.type: Easing.OutQuad
                        }
                    }
                }

                // Left speaker icon
                Text {
                    anchors.left: parent.left
                    anchors.leftMargin: 10
                    anchors.verticalCenter: parent.verticalCenter
                    text: IslandBridge.title === "Muted" ? "󰝟" : (IslandBridge.icon || "󰕾")
                    color: IslandBridge.title === "Muted" ? "#ff453a" : "#007AFF"
                    font.pixelSize: 16
                }

                // Title label
                Text {
                    anchors.left: parent.left
                    anchors.leftMargin: 34
                    anchors.verticalCenter: parent.verticalCenter
                    text: "Sound"
                    color: "#1c1c1e"
                    font.pixelSize: 11
                    font.bold: true
                }

                // Percentage text
                Text {
                    anchors.right: parent.right
                    anchors.rightMargin: 12
                    anchors.verticalCenter: parent.verticalCenter
                    text: Math.round((IslandBridge.progressPct > 0 ? IslandBridge.progressPct : 0.65) * 100) + "%"
                    color: "#1c1c1e"
                    font.pixelSize: 10
                    font.bold: true
                }
            }

            MouseArea {
                anchors.fill: parent
                onWheel: wheel => {
                    if (wheel.angleDelta.y > 0) IslandBridge.volumeUp();
                    else IslandBridge.volumeDown();
                }
                onClicked: function(mouse) {
                    var pct = Math.max(0, Math.min(1.0, mouse.x / parent.width));
                    var intPct = Math.round(pct * 100);
                    IslandBridge.sendCommand("volume_up", [intPct + "%"]);
                }
            }
        }
    }

    // -------------------------------------------------------------
    // macOS Section 4: Now Playing Music Player Card
    // -------------------------------------------------------------
    Rectangle {
        width: parent.width
        height: 52
        radius: 14
        color: Theme.cardBackground
        border.color: Theme.border
        border.width: 1

        Item {
            anchors.fill: parent
            anchors.margins: 8

            // Album Artwork thumbnail / Pink Music Icon
            Rectangle {
                id: artThumb
                width: 36
                height: 36
                radius: 8
                color: "#FF2D55"
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter

                Text {
                    anchors.centerIn: parent
                    text: "󰎆"
                    color: "#ffffff"
                    font.pixelSize: 18
                }
            }

            // Song & Artist Info
            Column {
                anchors.left: artThumb.right
                anchors.leftMargin: 8
                anchors.right: mediaBtns.left
                anchors.rightMargin: 6
                anchors.verticalCenter: parent.verticalCenter
                spacing: 2

                Text {
                    text: IslandBridge.title || "Now Playing"
                    color: Theme.textPrimary
                    font.pixelSize: 11
                    font.bold: true
                    elide: Text.ElideRight
                    width: parent.width
                }
                Text {
                    text: IslandBridge.subtitle || "Apple Music"
                    color: Theme.textSecondary
                    font.pixelSize: 9
                    elide: Text.ElideRight
                    width: parent.width
                }
            }

            // Playback Controls
            Row {
                id: mediaBtns
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                spacing: 8

                // Prev
                Rectangle {
                    width: 22
                    height: 22
                    radius: 11
                    color: prevHover.hovered ? Qt.rgba(1, 1, 1, 0.15) : "transparent"
                    Text { anchors.centerIn: parent; text: "󰒮"; color: Theme.textPrimary; font.pixelSize: 13 }
                    HoverHandler { id: prevHover }
                    TapHandler { onTapped: IslandBridge.prevMedia() }
                }

                // Play / Pause
                Rectangle {
                    width: 26
                    height: 26
                    radius: 13
                    color: playHover.hovered ? Qt.rgba(1, 1, 1, 0.22) : Qt.rgba(1, 1, 1, 0.12)
                    Text { anchors.centerIn: parent; text: (IslandBridge.visualState === "media" || IslandBridge.visualState === "mediaCompact" || IslandBridge.visualState === "mediaExpanded") ? "󰏤" : "󰐊"; color: Theme.textPrimary; font.pixelSize: 13 }
                    HoverHandler { id: playHover }
                    TapHandler { onTapped: IslandBridge.toggleMedia() }
                }

                // Next
                Rectangle {
                    width: 22
                    height: 22
                    radius: 11
                    color: nextHover.hovered ? Qt.rgba(1, 1, 1, 0.15) : "transparent"
                    Text { anchors.centerIn: parent; text: "󰒭"; color: Theme.textPrimary; font.pixelSize: 13 }
                    HoverHandler { id: nextHover }
                    TapHandler { onTapped: IslandBridge.nextMedia() }
                }
            }
        }
    }

    // -------------------------------------------------------------
    // macOS Section 5: Telemetry Chips & Theme Switcher Footer
    // -------------------------------------------------------------
    Row {
        width: parent.width
        spacing: 6

        // CPU Chip
        Rectangle {
            width: (parent.width - 24) / 5
            height: 26
            radius: 8
            color: Qt.rgba(0.40, 0.82, 1.0, 0.12)
            border.color: Qt.rgba(0.40, 0.82, 1.0, 0.25)
            border.width: 1

            Row {
                anchors.centerIn: parent
                spacing: 3
                Text { text: "󰍛"; color: "#64d2ff"; font.pixelSize: 10 }
                Text { text: IslandBridge.systemCpu + "%"; color: Theme.textPrimary; font.pixelSize: 9; font.bold: true }
            }
        }

        // RAM Chip
        Rectangle {
            width: (parent.width - 24) / 5
            height: 26
            radius: 8
            color: Qt.rgba(0.75, 0.35, 0.95, 0.12)
            border.color: Qt.rgba(0.75, 0.35, 0.95, 0.25)
            border.width: 1

            Row {
                anchors.centerIn: parent
                spacing: 3
                Text { text: "󰘚"; color: "#bf5af2"; font.pixelSize: 10 }
                Text { text: IslandBridge.systemMem + "%"; color: Theme.textPrimary; font.pixelSize: 9; font.bold: true }
            }
        }

        // Battery Chip
        Rectangle {
            width: (parent.width - 24) / 5
            height: 26
            radius: 8
            color: Qt.rgba(0.20, 0.82, 0.35, 0.12)
            border.color: Qt.rgba(0.20, 0.82, 0.35, 0.25)
            border.width: 1

            Row {
                anchors.centerIn: parent
                spacing: 3
                Text { text: "󰂄"; color: "#30d158"; font.pixelSize: 10 }
                Text { text: (IslandBridge.deviceBattery !== null ? IslandBridge.deviceBattery + "%" : "AC"); color: Theme.textPrimary; font.pixelSize: 9; font.bold: true }
            }
        }

        // Wallpaper Rotator Chip
        Rectangle {
            width: (parent.width - 24) / 5
            height: 26
            radius: 8
            color: Qt.rgba(1.0, 0.60, 0.10, 0.12)
            border.color: Qt.rgba(1.0, 0.60, 0.10, 0.25)
            border.width: 1

            Row {
                anchors.centerIn: parent
                spacing: 3
                Text { text: "󰸉"; color: "#ff9f0a"; font.pixelSize: 10 }
                Text { text: "Wall"; color: Theme.textPrimary; font.pixelSize: 9; font.bold: true }
            }
            HoverHandler { id: wChipHov }
            TapHandler { onTapped: IslandBridge.nextWallpaper() }
        }

        // Theme Cycler Chip
        Rectangle {
            width: (parent.width - 24) / 5
            height: 26
            radius: 8
            color: Qt.rgba(0.04, 0.52, 1.0, 0.12)
            border.color: Qt.rgba(0.04, 0.52, 1.0, 0.25)
            border.width: 1

            Row {
                anchors.centerIn: parent
                spacing: 3
                Text { text: "󰏘"; color: "#0a84ff"; font.pixelSize: 10 }
                Text { text: "Theme"; color: Theme.textPrimary; font.pixelSize: 9; font.bold: true }
            }
            HoverHandler { id: thChipHov }
            TapHandler {
                onTapped: {
                    var themes = [
                        "macos-tahoe",
                        "macos-dark",
                        "macos-glass",
                        "macos-black",
                        "hyperos-dark",
                        "originos-dark",
                        "catppuccin-mocha",
                        "minimal-dark"
                    ];
                    var idx = themes.indexOf(Theme.currentTheme);
                    var next = themes[(idx + 1) % themes.length];
                    IslandBridge.setTheme(next);
                }
            }
        }
    }
}
