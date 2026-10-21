import QtQuick
import "../services"
import "../themes"

Item {
    id: root
    anchors.fill: parent
    anchors.margins: 10

    property int activeTab: 0
    property bool confirmReset: false

    Column {
        anchors.fill: parent
        spacing: 8

        // Header with Title, Tabs, and Close Button
        Item {
            width: parent.width
            height: 24

            Text {
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                text: "⚙ Settings"
                color: Theme.textPrimary
                font.pixelSize: 12
                font.bold: true
            }

            // Tab bar
            Row {
                anchors.centerIn: parent
                spacing: 4

                Repeater {
                    model: [
                        { label: "Theme", idx: 0, icon: "🎨" },
                        { label: "Genie", idx: 1, icon: "🌀" },
                        { label: "Windows", idx: 2, icon: "🪟" },
                        { label: "System", idx: 3, icon: "🛡️" }
                    ]

                    Rectangle {
                        width: 58
                        height: 22
                        radius: 5
                        color: root.activeTab === modelData.idx ? Qt.rgba(0.04, 0.52, 1.0, 0.35) : (tabHov.hovered ? Qt.rgba(1, 1, 1, 0.12) : Qt.rgba(1, 1, 1, 0.05))
                        border.color: root.activeTab === modelData.idx ? Theme.accent : "transparent"
                        border.width: 1

                        Row {
                            anchors.centerIn: parent
                            spacing: 3
                            Text { text: modelData.icon; font.pixelSize: 9 }
                            Text {
                                text: modelData.label
                                color: root.activeTab === modelData.idx ? Theme.accent : Theme.textSecondary
                                font.pixelSize: 9
                                font.bold: root.activeTab === modelData.idx
                            }
                        }

                        HoverHandler { id: tabHov }
                        TapHandler { onTapped: { root.activeTab = modelData.idx; root.confirmReset = false; } }
                    }
                }
            }

            // Close button
            Rectangle {
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                width: 20
                height: 20
                radius: 10
                color: closeHov.hovered ? Qt.rgba(1, 1, 1, 0.25) : Qt.rgba(1, 1, 1, 0.1)

                Text {
                    anchors.centerIn: parent
                    text: "✕"
                    color: Theme.textPrimary
                    font.pixelSize: 10
                    font.bold: true
                }

                HoverHandler { id: closeHov }
                TapHandler {
                    onTapped: {
                        IslandBridge.closeSettings();
                        IslandBridge.dismiss();
                    }
                }
            }
        }

        // Horizontal Separator
        Rectangle {
            width: parent.width
            height: 1
            color: Qt.rgba(1, 1, 1, 0.08)
        }

        // Tab Content Area
        Item {
            width: parent.width
            height: parent.height - 34

            // =================================================================
            // TAB 0: THEMES & APPEARANCE
            // =================================================================
            Column {
                anchors.fill: parent
                visible: root.activeTab === 0
                spacing: 7

                Text {
                    text: "THEME PRESETS"
                    color: Theme.textSecondary
                    font.pixelSize: 9
                    font.bold: true
                }

                // Theme Presets Grid (2 rows of 3)
                Grid {
                    columns: 3
                    spacing: 6
                    width: parent.width

                    Repeater {
                        model: [
                            { id: "macos-black", label: "Tahoe Black" },
                            { id: "macos-glass", label: "macOS Glass" },
                            { id: "catppuccin-mocha", label: "Mocha" },
                            { id: "minimal-dark", label: "OLED Minimal" },
                            { id: "hyperos-dark", label: "HyperOS" },
                            { id: "originos-dark", label: "OriginOS" }
                        ]

                        Rectangle {
                            width: (parent.width - 12) / 3
                            height: 28
                            radius: 6
                            color: {
                                if (Theme.currentTheme === modelData.id) return Qt.rgba(0.04, 0.52, 1.0, 0.35);
                                return thHov.hovered ? Qt.rgba(1, 1, 1, 0.15) : Qt.rgba(1, 1, 1, 0.06);
                            }
                            border.color: Theme.currentTheme === modelData.id ? Theme.accent : "transparent"
                            border.width: 1

                            Text {
                                anchors.centerIn: parent
                                text: modelData.label
                                color: Theme.currentTheme === modelData.id ? Theme.accent : Theme.textPrimary
                                font.pixelSize: 10
                                font.bold: Theme.currentTheme === modelData.id
                            }

                            HoverHandler { id: thHov }
                            TapHandler { onTapped: IslandBridge.setTheme(modelData.id) }
                        }
                    }
                }

                Item { width: parent.width; height: 2 }

                Text {
                    text: "PRESENTATION & GLASS BLUR"
                    color: Theme.textSecondary
                    font.pixelSize: 9
                    font.bold: true
                }

                Row {
                    spacing: 6
                    width: parent.width

                    // Presentation Mode Toggle
                    Rectangle {
                        width: (parent.width - 6) / 2
                        height: 28
                        radius: 6
                        color: presHov.hovered ? Qt.rgba(1, 1, 1, 0.16) : Qt.rgba(1, 1, 1, 0.07)

                        Row {
                            anchors.centerIn: parent
                            spacing: 5
                            Text { text: "📐"; font.pixelSize: 10 }
                            Text {
                                text: IslandBridge.presentationMode === "dynamic" ? "Mode: Dynamic" : "Mode: Stable Width"
                                color: Theme.textPrimary
                                font.pixelSize: 9
                                font.bold: true
                            }
                        }

                        HoverHandler { id: presHov }
                        TapHandler {
                            onTapped: {
                                var next = IslandBridge.presentationMode === "dynamic" ? "stable-width" : "dynamic";
                                IslandBridge.setSetting("presentation_mode", next);
                            }
                        }
                    }

                    // Glass Blur Toggle
                    Rectangle {
                        width: (parent.width - 6) / 2
                        height: 28
                        radius: 6
                        color: blurHov.hovered ? Qt.rgba(1, 1, 1, 0.16) : Qt.rgba(1, 1, 1, 0.07)

                        Row {
                            anchors.centerIn: parent
                            spacing: 5
                            Text { text: "✨"; font.pixelSize: 10 }
                            Text {
                                text: IslandBridge.blurEnabled ? "Blur: Enabled" : "Blur: Disabled"
                                color: Theme.textPrimary
                                font.pixelSize: 9
                                font.bold: true
                            }
                        }

                        HoverHandler { id: blurHov }
                        TapHandler {
                            onTapped: {
                                IslandBridge.setSetting("blur_enabled", !IslandBridge.blurEnabled);
                            }
                        }
                    }
                }

                Item { width: parent.width; height: 1 }

                Text {
                    text: "WALLPAPER & DESKTOP THEMES"
                    color: Theme.textSecondary
                    font.pixelSize: 9
                    font.bold: true
                }

                // Row of Wallpaper & Theme Launchers
                Row {
                    spacing: 6
                    width: parent.width

                    // Wallpaper Manager GUI
                    Rectangle {
                        width: (parent.width - 12) / 3
                        height: 26
                        radius: 6
                        color: wpMngHov.hovered ? Qt.rgba(1, 1, 1, 0.16) : Qt.rgba(1, 1, 1, 0.07)

                        Row {
                            anchors.centerIn: parent
                            spacing: 4
                            Text { text: "🖼️"; font.pixelSize: 9 }
                            Text {
                                text: "Wallpapers"
                                color: Theme.textPrimary
                                font.pixelSize: 9
                                font.bold: true
                            }
                        }

                        HoverHandler { id: wpMngHov }
                        TapHandler { onTapped: IslandBridge.openWallpaperManager() }
                    }

                    // Next Wallpaper
                    Rectangle {
                        width: (parent.width - 12) / 3
                        height: 26
                        radius: 6
                        color: wpNextHov.hovered ? Qt.rgba(1, 1, 1, 0.16) : Qt.rgba(1, 1, 1, 0.07)

                        Row {
                            anchors.centerIn: parent
                            spacing: 4
                            Text { text: "🎲"; font.pixelSize: 9 }
                            Text {
                                text: "Next Wall"
                                color: Theme.accentGreen
                                font.pixelSize: 9
                                font.bold: true
                            }
                        }

                        HoverHandler { id: wpNextHov }
                        TapHandler { onTapped: IslandBridge.nextWallpaper() }
                    }

                    // Theme Manager GUI
                    Rectangle {
                        width: (parent.width - 12) / 3
                        height: 26
                        radius: 6
                        color: thMgrHov.hovered ? Qt.rgba(1, 1, 1, 0.16) : Qt.rgba(1, 1, 1, 0.07)

                        Row {
                            anchors.centerIn: parent
                            spacing: 4
                            Text { text: "🎨"; font.pixelSize: 9 }
                            Text {
                                text: "Theme GUI"
                                color: Theme.accent
                                font.pixelSize: 9
                                font.bold: true
                            }
                        }

                        HoverHandler { id: thMgrHov }
                        TapHandler { onTapped: IslandBridge.openThemeManager() }
                    }
                }

                // 5 Full System Desktop Theme Switchers
                Row {
                    spacing: 4
                    width: parent.width

                    Repeater {
                        model: [
                            { id: "macos-dark", label: "Sonoma Dark" },
                            { id: "macos-light", label: "Sonoma Light" },
                            { id: "nordic", label: "Nordic" },
                            { id: "catppuccin", label: "Mocha" },
                            { id: "dr460nized-ember", label: "Ember" }
                        ]

                        Rectangle {
                            width: (parent.width - 16) / 5
                            height: 24
                            radius: 5
                            color: sysPillHov.hovered ? Qt.rgba(0.04, 0.52, 1.0, 0.25) : Qt.rgba(1, 1, 1, 0.05)
                            border.color: Qt.rgba(1, 1, 1, 0.08)
                            border.width: 1

                            Text {
                                anchors.centerIn: parent
                                text: modelData.label
                                color: Theme.textPrimary
                                font.pixelSize: 8
                                font.bold: true
                            }

                            HoverHandler { id: sysPillHov }
                            TapHandler {
                                onTapped: IslandBridge.setSystemTheme(modelData.id)
                            }
                        }
                    }
                }
            }

            // =================================================================
            // TAB 1: GENIE & ANIMATION PROFILES
            // =================================================================
            Column {
                anchors.fill: parent
                visible: root.activeTab === 1
                spacing: 7

                Text {
                    text: "ANIMATION PROFILE (MINIMIZE / RESTORE)"
                    color: Theme.textSecondary
                    font.pixelSize: 9
                    font.bold: true
                }

                // Animation Profile Chips
                Grid {
                    columns: 3
                    spacing: 6
                    width: parent.width

                    Repeater {
                        model: [
                            { id: "macos-lamp", label: "Magic Lamp 🪔" },
                            { id: "macos-genie-inspired", label: "Mac Genie" },
                            { id: "originos-spring", label: "OriginOS Spring" },
                            { id: "originos-morph", label: "Morph Pill" },
                            { id: "hyperos-mini", label: "HyperOS Mini" },
                            { id: "scale-fade", label: "Scale & Fade" },
                            { id: "low-resource", label: "Low-Resource" }
                        ]

                        Rectangle {
                            width: (parent.width - 12) / 3
                            height: 28
                            radius: 6
                            color: {
                                if (IslandBridge.minimizeStyle === modelData.id) return Qt.rgba(0.04, 0.52, 1.0, 0.35);
                                return prHov.hovered ? Qt.rgba(1, 1, 1, 0.15) : Qt.rgba(1, 1, 1, 0.06);
                            }
                            border.color: IslandBridge.minimizeStyle === modelData.id ? Theme.accent : "transparent"
                            border.width: 1

                            Text {
                                anchors.centerIn: parent
                                text: modelData.label
                                color: IslandBridge.minimizeStyle === modelData.id ? Theme.accent : Theme.textPrimary
                                font.pixelSize: 10
                                font.bold: IslandBridge.minimizeStyle === modelData.id
                            }

                            HoverHandler { id: prHov }
                            TapHandler {
                                onTapped: {
                                    IslandBridge.setSetting("minimize_style", modelData.id);
                                }
                            }
                        }
                    }
                }

                Item { width: parent.width; height: 2 }

                Text {
                    text: "ANIMATION SPEED & MOTION"
                    color: Theme.textSecondary
                    font.pixelSize: 9
                    font.bold: true
                }

                Row {
                    spacing: 6
                    width: parent.width

                    // Duration presets
                    Repeater {
                        model: [
                            { label: "Fast (220ms)", val: 220 },
                            { label: "Smooth (380ms)", val: 380 },
                            { label: "Cinematic (500ms)", val: 500 }
                        ]

                        Rectangle {
                            width: (parent.width - 12) / 3
                            height: 28
                            radius: 6
                            color: durHov.hovered ? Qt.rgba(1, 1, 1, 0.16) : Qt.rgba(1, 1, 1, 0.07)

                            Text {
                                anchors.centerIn: parent
                                text: modelData.label
                                color: Theme.textPrimary
                                font.pixelSize: 9
                                font.bold: true
                            }

                            HoverHandler { id: durHov }
                            TapHandler {
                                onTapped: {
                                    IslandBridge.setSetting("minimize_duration_ms", modelData.val);
                                }
                            }
                        }
                    }
                }

                // Reduced Motion switch
                Rectangle {
                    width: parent.width
                    height: 28
                    radius: 6
                    color: redHov.hovered ? Qt.rgba(1, 1, 1, 0.16) : Qt.rgba(1, 1, 1, 0.07)

                    Row {
                        anchors.centerIn: parent
                        spacing: 6
                        Text { text: IslandBridge.reducedMotion ? "󰔢" : "󰔡"; color: Theme.accent; font.pixelSize: 11 }
                        Text {
                            text: IslandBridge.reducedMotion ? "Reduced Motion: Enabled (Instant Transitions)" : "Reduced Motion: Disabled (Full Physics & Genie)"
                            color: Theme.textPrimary
                            font.pixelSize: 9
                            font.bold: true
                        }
                    }

                    HoverHandler { id: redHov }
                    TapHandler {
                        onTapped: {
                            var next = !IslandBridge.reducedMotion;
                            IslandBridge.sendCommand("reduced-motion", [next ? "on" : "off"]);
                        }
                    }
                }
            }

            // =================================================================
            // TAB 2: WINDOWS & DOCK
            // =================================================================
            Column {
                anchors.fill: parent
                visible: root.activeTab === 2
                spacing: 7

                Text {
                    text: "CAPSULE MANAGER & PREVIEWS"
                    color: Theme.textSecondary
                    font.pixelSize: 9
                    font.bold: true
                }

                Row {
                    spacing: 6
                    width: parent.width

                    // Single Capsule Mode
                    Rectangle {
                        width: (parent.width - 6) / 2
                        height: 28
                        radius: 6
                        color: capHov.hovered ? Qt.rgba(1, 1, 1, 0.16) : Qt.rgba(1, 1, 1, 0.07)

                        Row {
                            anchors.centerIn: parent
                            spacing: 5
                            Text { text: "💊"; font.pixelSize: 10 }
                            Text {
                                text: "Single Capsule (iOS)"
                                color: Theme.textPrimary
                                font.pixelSize: 9
                                font.bold: true
                            }
                        }

                        HoverHandler { id: capHov }
                        TapHandler {
                            onTapped: {
                                IslandBridge.setSetting("minimized_apps_visibility", "auto");
                            }
                        }
                    }

                    // Open Full Minimized Manager
                    Rectangle {
                        width: (parent.width - 6) / 2
                        height: 28
                        radius: 6
                        color: mgrHov.hovered ? Qt.rgba(1, 1, 1, 0.16) : Qt.rgba(1, 1, 1, 0.07)

                        Row {
                            anchors.centerIn: parent
                            spacing: 5
                            Text { text: "🗂️"; font.pixelSize: 10 }
                            Text {
                                text: "View Minimized Apps"
                                color: Theme.accent
                                font.pixelSize: 9
                                font.bold: true
                            }
                        }

                        HoverHandler { id: mgrHov }
                        TapHandler {
                            onTapped: {
                                IslandBridge.closeSettings();
                                IslandBridge.sendCommand("minimized_apps_show");
                            }
                        }
                    }
                }

                Item { width: parent.width; height: 2 }

                Text {
                    text: "PREVIEW THUMBNAIL DIMENSIONS"
                    color: Theme.textSecondary
                    font.pixelSize: 9
                    font.bold: true
                }

                Row {
                    spacing: 6
                    width: parent.width

                    Repeater {
                        model: [
                            { label: "140×90", val: "140x90" },
                            { label: "120×80", val: "120x80" },
                            { label: "100×60", val: "100x60" },
                            { label: "Icon Only", val: "icon-only" }
                        ]

                        Rectangle {
                            width: (parent.width - 18) / 4
                            height: 28
                            radius: 6
                            color: prevHov.hovered ? Qt.rgba(1, 1, 1, 0.16) : Qt.rgba(1, 1, 1, 0.07)

                            Text {
                                anchors.centerIn: parent
                                text: modelData.label
                                color: Theme.textPrimary
                                font.pixelSize: 9
                                font.bold: true
                            }

                            HoverHandler { id: prevHov }
                            TapHandler {
                                onTapped: {
                                    IslandBridge.setSetting("thumbnail_size", modelData.val);
                                }
                            }
                        }
                    }
                }

                Item { width: parent.width; height: 2 }

                Text {
                    text: "MINIMIZE TARGET"
                    color: Theme.textSecondary
                    font.pixelSize: 9
                    font.bold: true
                }

                Row {
                    spacing: 6
                    width: parent.width

                    Rectangle {
                        width: (parent.width - 6) / 2
                        height: 28
                        radius: 6
                        color: IslandBridge.minimizeTarget === "island" ? Qt.rgba(0.04, 0.52, 1.0, 0.35) : (tgtIHov.hovered ? Qt.rgba(1, 1, 1, 0.16) : Qt.rgba(1, 1, 1, 0.07))
                        border.color: IslandBridge.minimizeTarget === "island" ? Theme.accent : "transparent"
                        border.width: 1

                        Text {
                            anchors.centerIn: parent
                            text: "Target: Dynamic Island"
                            color: IslandBridge.minimizeTarget === "island" ? Theme.accent : Theme.textPrimary
                            font.pixelSize: 9
                            font.bold: true
                        }

                        HoverHandler { id: tgtIHov }
                        TapHandler { onTapped: IslandBridge.setSetting("minimize_target", "island") }
                    }

                    Rectangle {
                        width: (parent.width - 6) / 2
                        height: 28
                        radius: 6
                        color: IslandBridge.minimizeTarget === "dock" ? Qt.rgba(0.04, 0.52, 1.0, 0.35) : (tgtDHov.hovered ? Qt.rgba(1, 1, 1, 0.16) : Qt.rgba(1, 1, 1, 0.07))
                        border.color: IslandBridge.minimizeTarget === "dock" ? Theme.accent : "transparent"
                        border.width: 1

                        Text {
                            anchors.centerIn: parent
                            text: "Target: Floating Dock"
                            color: IslandBridge.minimizeTarget === "dock" ? Theme.accent : Theme.textPrimary
                            font.pixelSize: 9
                            font.bold: true
                        }

                        HoverHandler { id: tgtDHov }
                        TapHandler { onTapped: IslandBridge.setSetting("minimize_target", "dock") }
                    }
                }
            }

            // =================================================================
            // TAB 3: PRIVACY & SYSTEM
            // =================================================================
            Column {
                anchors.fill: parent
                visible: root.activeTab === 3
                spacing: 7

                Text {
                    text: "SECURITY & PRIVACY CONTROLS"
                    color: Theme.textSecondary
                    font.pixelSize: 9
                    font.bold: true
                }

                Row {
                    spacing: 6
                    width: parent.width

                    // SSID Privacy
                    Rectangle {
                        width: (parent.width - 6) / 2
                        height: 28
                        radius: 6
                        color: ssidHov.hovered ? Qt.rgba(1, 1, 1, 0.16) : Qt.rgba(1, 1, 1, 0.07)

                        Row {
                            anchors.centerIn: parent
                            spacing: 5
                            Text { text: "🔒"; font.pixelSize: 10 }
                            Text {
                                text: IslandBridge.networkSsidPrivacy ? "SSID: Masked" : "SSID: Visible"
                                color: Theme.textPrimary
                                font.pixelSize: 9
                                font.bold: true
                            }
                        }

                        HoverHandler { id: ssidHov }
                        TapHandler {
                            onTapped: {
                                IslandBridge.setSetting("network_ssid_privacy", !IslandBridge.networkSsidPrivacy);
                            }
                        }
                    }

                    // Clipboard Privacy
                    Rectangle {
                        width: (parent.width - 6) / 2
                        height: 28
                        radius: 6
                        color: Qt.rgba(0.1, 0.7, 0.3, 0.15)
                        border.color: Qt.rgba(0.1, 0.7, 0.3, 0.4)
                        border.width: 1

                        Row {
                            anchors.centerIn: parent
                            spacing: 5
                            Text { text: "🛡️"; font.pixelSize: 10 }
                            Text {
                                text: "Clipboard: Zero Leakage"
                                color: "#4cd964"
                                font.pixelSize: 9
                                font.bold: true
                            }
                        }
                    }
                }

                Item { width: parent.width; height: 2 }

                Text {
                    text: "DIAGNOSTICS & MAINTENANCE"
                    color: Theme.textSecondary
                    font.pixelSize: 9
                    font.bold: true
                }

                Row {
                    spacing: 6
                    width: parent.width

                    // Doctor Check
                    Rectangle {
                        width: (parent.width - 6) / 2
                        height: 28
                        radius: 6
                        color: docHov.hovered ? Qt.rgba(1, 1, 1, 0.18) : Qt.rgba(1, 1, 1, 0.07)

                        Row {
                            anchors.centerIn: parent
                            spacing: 5
                            Text { text: "🩺"; font.pixelSize: 10 }
                            Text {
                                text: "Run Health Check"
                                color: Theme.textPrimary
                                font.pixelSize: 9
                                font.bold: true
                            }
                        }

                        HoverHandler { id: docHov }
                        TapHandler {
                            onTapped: {
                                IslandBridge.sendCommand("doctor");
                                IslandBridge.dismiss();
                            }
                        }
                    }

                    // Reset to Factory Defaults
                    Rectangle {
                        width: (parent.width - 6) / 2
                        height: 28
                        radius: 6
                        color: root.confirmReset ? Qt.rgba(1.0, 0.2, 0.2, 0.4) : (rstHov.hovered ? Qt.rgba(1.0, 0.2, 0.2, 0.2) : Qt.rgba(1, 1, 1, 0.07))
                        border.color: root.confirmReset ? "#ff3b30" : "transparent"
                        border.width: 1

                        Row {
                            anchors.centerIn: parent
                            spacing: 5
                            Text { text: root.confirmReset ? "⚠️" : "🔄"; font.pixelSize: 10 }
                            Text {
                                text: root.confirmReset ? "Click to Confirm" : "Restore Defaults"
                                color: root.confirmReset ? "#ff3b30" : Theme.textPrimary
                                font.pixelSize: 9
                                font.bold: true
                            }
                        }

                        HoverHandler { id: rstHov }
                        TapHandler {
                            onTapped: {
                                if (root.confirmReset) {
                                    IslandBridge.resetSettings();
                                    root.confirmReset = false;
                                } else {
                                    root.confirmReset = true;
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
