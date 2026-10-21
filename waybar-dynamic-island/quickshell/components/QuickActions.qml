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
        height: 20

        Row {
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
            spacing: 6

            Text {
                text: "⚡"
                font.pixelSize: 12
            }
            Text {
                text: "Control Center"
                color: Theme.textSecondary
                font.pixelSize: 11
                font.bold: true
            }
        }

        Rectangle {
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            width: 20
            height: 20
            radius: 10
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
    // HyperOS Section 1: Dual Connectivity Tiles (Wi-Fi & Bluetooth)
    // -------------------------------------------------------------
    Row {
        width: parent.width
        spacing: 8

        // Wi-Fi Tile
        Rectangle {
            width: (parent.width - 8) / 2
            height: 48
            radius: 12
            color: wifiHover.hovered ? Qt.rgba(1, 1, 1, 0.12) : Theme.cardBackground
            border.color: Qt.rgba(1, 1, 1, 0.08)
            border.width: 1

            Row {
                anchors.fill: parent
                anchors.margins: 8
                spacing: 8

                Rectangle {
                    width: 32
                    height: 32
                    radius: 16
                    color: Qt.rgba(0, 0.82, 0.78, 0.18)
                    anchors.verticalCenter: parent.verticalCenter

                    Text {
                        anchors.centerIn: parent
                        text: "󰤨"
                        color: Theme.accent
                        font.pixelSize: 15
                    }
                }

                Column {
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 1

                    Text {
                        text: "Wi-Fi"
                        color: Theme.textPrimary
                        font.pixelSize: 11
                        font.bold: true
                    }
                    Text {
                        text: "Connected"
                        color: Theme.textSecondary
                        font.pixelSize: 9
                    }
                }
            }

            HoverHandler { id: wifiHover }
            TapHandler {
                onTapped: {
                    IslandBridge.sendCommand("network", ["status"]);
                }
            }
        }

        // Bluetooth Tile
        Rectangle {
            width: (parent.width - 8) / 2
            height: 48
            radius: 12
            color: btHover.hovered ? Qt.rgba(1, 1, 1, 0.12) : Theme.cardBackground
            border.color: Qt.rgba(1, 1, 1, 0.08)
            border.width: 1

            Row {
                anchors.fill: parent
                anchors.margins: 8
                spacing: 8

                Rectangle {
                    width: 32
                    height: 32
                    radius: 16
                    color: Qt.rgba(0.04, 0.52, 1.0, 0.18)
                    anchors.verticalCenter: parent.verticalCenter

                    Text {
                        anchors.centerIn: parent
                        text: "󰂯"
                        color: Theme.accentCyan
                        font.pixelSize: 15
                    }
                }

                Column {
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 1

                    Text {
                        text: "Bluetooth"
                        color: Theme.textPrimary
                        font.pixelSize: 11
                        font.bold: true
                    }
                    Text {
                        text: IslandBridge.subtitle ? IslandBridge.subtitle.split("•")[0].trim() : "BlueZ Active"
                        color: Theme.textSecondary
                        font.pixelSize: 9
                        elide: Text.ElideRight
                        width: parent.parent.width - 48
                    }
                }
            }

            HoverHandler { id: btHover }
            TapHandler {
                onTapped: {
                    IslandBridge.sendCommand("bluetooth", ["scan"]);
                }
            }
        }
    }

    // -------------------------------------------------------------
    // HyperOS Section 2: Volume & Brightness Dual Sliders
    // -------------------------------------------------------------
    Row {
        width: parent.width
        spacing: 8

        // Volume Bar
        Rectangle {
            width: (parent.width - 8) / 2
            height: 38
            radius: 10
            color: Theme.cardBackground
            border.color: Qt.rgba(1, 1, 1, 0.08)
            border.width: 1

            Row {
                anchors.fill: parent
                anchors.margins: 6
                spacing: 8

                Rectangle {
                    width: 26
                    height: 26
                    radius: 13
                    color: volHover.hovered ? Qt.rgba(1, 1, 1, 0.15) : Qt.rgba(1, 1, 1, 0.05)
                    anchors.verticalCenter: parent.verticalCenter

                    Text {
                        anchors.centerIn: parent
                        text: "󰕾"
                        color: Theme.accent
                        font.pixelSize: 13
                    }
                    HoverHandler { id: volHover }
                    TapHandler { onTapped: IslandBridge.volumeMute() }
                }

                Column {
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 2
                    width: parent.width - 38

                    Text {
                        text: "Volume"
                        color: Theme.textPrimary
                        font.pixelSize: 10
                        font.bold: true
                    }

                    Row {
                        spacing: 8
                        Rectangle {
                            width: 20
                            height: 16
                            radius: 4
                            color: Qt.rgba(1, 1, 1, 0.10)
                            Text { anchors.centerIn: parent; text: "－"; color: Theme.textPrimary; font.pixelSize: 10 }
                            TapHandler { onTapped: IslandBridge.volumeDown() }
                        }
                        Rectangle {
                            width: 20
                            height: 16
                            radius: 4
                            color: Qt.rgba(1, 1, 1, 0.10)
                            Text { anchors.centerIn: parent; text: "＋"; color: Theme.textPrimary; font.pixelSize: 10 }
                            TapHandler { onTapped: IslandBridge.volumeUp() }
                        }
                    }
                }
            }
        }

        // Brightness Bar
        Rectangle {
            width: (parent.width - 8) / 2
            height: 38
            radius: 10
            color: Theme.cardBackground
            border.color: Qt.rgba(1, 1, 1, 0.08)
            border.width: 1

            Row {
                anchors.fill: parent
                anchors.margins: 6
                spacing: 8

                Rectangle {
                    width: 26
                    height: 26
                    radius: 13
                    color: Qt.rgba(1, 1, 1, 0.05)
                    anchors.verticalCenter: parent.verticalCenter

                    Text {
                        anchors.centerIn: parent
                        text: "󰃠"
                        color: Theme.accentYellow
                        font.pixelSize: 13
                    }
                }

                Column {
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 2
                    width: parent.width - 38

                    Text {
                        text: "Brightness"
                        color: Theme.textPrimary
                        font.pixelSize: 10
                        font.bold: true
                    }

                    Row {
                        spacing: 8
                        Rectangle {
                            width: 20
                            height: 16
                            radius: 4
                            color: Qt.rgba(1, 1, 1, 0.10)
                            Text { anchors.centerIn: parent; text: "－"; color: Theme.textPrimary; font.pixelSize: 10 }
                            TapHandler { onTapped: IslandBridge.brightnessDown() }
                        }
                        Rectangle {
                            width: 20
                            height: 16
                            radius: 4
                            color: Qt.rgba(1, 1, 1, 0.10)
                            Text { anchors.centerIn: parent; text: "＋"; color: Theme.textPrimary; font.pixelSize: 10 }
                            TapHandler { onTapped: IslandBridge.brightnessUp() }
                        }
                    }
                }
            }
        }
    }

    // -------------------------------------------------------------
    // HyperOS Section 3: 4 Quick Utility Tiles
    // -------------------------------------------------------------
    Row {
        width: parent.width
        spacing: 6

        // 1. Pomodoro (25m)
        Rectangle {
            width: (parent.width - 18) / 4
            height: 32
            radius: 8
            color: pHover.hovered ? Qt.rgba(1, 1, 1, 0.15) : Theme.cardBackground

            Text {
                anchors.centerIn: parent
                text: "🍅 Focus"
                color: Theme.textPrimary
                font.pixelSize: 9
                font.bold: true
            }
            HoverHandler { id: pHover }
            TapHandler {
                onTapped: {
                    IslandBridge.sendCommand("pomodoro");
                    IslandBridge.dismiss();
                }
            }
        }

        // 2. DND Toggle
        Rectangle {
            width: (parent.width - 18) / 4
            height: 32
            radius: 8
            color: dndHover.hovered ? Qt.rgba(1, 1, 1, 0.15) : Theme.cardBackground

            Text {
                anchors.centerIn: parent
                text: "🔕 DND"
                color: Theme.accentRed
                font.pixelSize: 9
                font.bold: true
            }
            HoverHandler { id: dndHover }
            TapHandler {
                onTapped: {
                    IslandBridge.dndToggle();
                    IslandBridge.dismiss();
                }
            }
        }

        // 3. Cycle Theme
        Rectangle {
            width: (parent.width - 18) / 4
            height: 32
            radius: 8
            color: thHover.hovered ? Qt.rgba(1, 1, 1, 0.15) : Theme.cardBackground

            Text {
                anchors.centerIn: parent
                text: "🎨 Theme"
                color: Theme.accent
                font.pixelSize: 9
                font.bold: true
            }
            HoverHandler { id: thHover }
            TapHandler {
                onTapped: {
                    var themes = [
                        "macos-black",
                        "macos-glass",
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

        // 4. Toggle Dock
        Rectangle {
            width: (parent.width - 18) / 4
            height: 32
            radius: 8
            color: dkHover.hovered ? Qt.rgba(1, 1, 1, 0.15) : Theme.cardBackground

            Text {
                anchors.centerIn: parent
                text: "⚓ Dock"
                color: Theme.accentPurple
                font.pixelSize: 9
                font.bold: true
            }
            HoverHandler { id: dkHover }
            TapHandler {
                onTapped: IslandBridge.toggleDock()
            }
        }
    }

    // -------------------------------------------------------------
    // HyperOS Section 4: Live Hardware Telemetry Footer
    // -------------------------------------------------------------
    Rectangle {
        width: parent.width
        height: 24
        radius: 6
        color: Qt.rgba(0, 0, 0, 0.35)

        Row {
            anchors.centerIn: parent
            spacing: 16

            Text {
                text: "󰍛 CPU " + IslandBridge.systemCpu + "%"
                color: IslandBridge.systemCpu > 80 ? Theme.accentRed : Theme.textSecondary
                font.pixelSize: 9
                font.bold: true
            }

            Text {
                text: "󰘚 RAM " + IslandBridge.systemMem + "%"
                color: IslandBridge.systemMem > 85 ? Theme.accentRed : Theme.textSecondary
                font.pixelSize: 9
                font.bold: true
            }

            Text {
                text: "󰂄 Battery " + (IslandBridge.deviceBattery !== null ? IslandBridge.deviceBattery + "%" : "AC")
                color: Theme.accentGreen
                font.pixelSize: 9
                font.bold: true
            }
        }
    }
}
