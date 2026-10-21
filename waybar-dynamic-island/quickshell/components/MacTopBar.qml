import QtQuick
import Quickshell
import Quickshell.Wayland
import "../services"
import "../themes"

PanelWindow {
    id: topBarWindow
    required property var screenTarget
    screen: screenTarget

    WlrLayershell.layer: WlrLayer.Top
    WlrLayershell.namespace: "ratana-topbar"
    WlrLayershell.keyboardFocus: anyPopoverOpen ? WlrKeyboardFocus.OnDemand : WlrKeyboardFocus.None
    WlrLayershell.exclusionMode: ExclusionMode.Normal
    exclusionMode: ExclusionMode.Normal

    // Top anchored full-width menu bar
    anchors.top: true
    anchors.left: true
    anchors.right: true
    anchors.bottom: anyPopoverOpen

    implicitHeight: anyPopoverOpen ? (screenTarget ? screenTarget.height : 1080) : IslandBridge.topBarHeight
    color: "transparent"
    visible: IslandBridge.topBarEnabled

    readonly property bool anyPopoverOpen: IslandBridge.systemMenuOpen ||
                                           IslandBridge.audioPopoverOpen ||
                                           IslandBridge.batteryPopoverOpen ||
                                           IslandBridge.calendarPopoverOpen ||
                                           IslandBridge.wifiOpen ||
                                           IslandBridge.bluetoothOpen ||
                                           IslandBridge.controlCenterOpen ||
                                           activeMenuIndex !== -1

    property int activeMenuIndex: -1 // -1: None, 0: File, 1: Edit, 2: View, 3: Window, 4: Help

    // Input hit test: when popover open, entire window catches clicks (for off-click dismiss)
    mask: anyPopoverOpen ? null : barMask

    Region {
        id: barMask
        item: barBackground
    }

    // Dismiss backdrop when clicking outside popovers
    MouseArea {
        anchors.fill: parent
        visible: anyPopoverOpen
        z: 0
        onClicked: {
            activeMenuIndex = -1;
            IslandBridge.dismiss();
        }
    }

    Item {
        anchors.fill: parent
        focus: anyPopoverOpen
        Keys.onEscapePressed: {
            activeMenuIndex = -1;
            IslandBridge.dismiss();
        }
    }

    // -------------------------------------------------------------
    // Main Slim macOS Tahoe Glass Top Bar Background
    // -------------------------------------------------------------
    Rectangle {
        id: barBackground
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: IslandBridge.topBarHeight
        z: 1

        color: Theme.background
        border.color: Theme.border
        border.width: 1

        // Top specular highlight rim (authentic macOS Tahoe glass edge)
        Rectangle {
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            height: 1
            color: Qt.rgba(1, 1, 1, 0.14)
        }

        // Bottom subtle border edge
        Rectangle {
            anchors.bottom: parent.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            height: 1
            color: Qt.rgba(0, 0, 0, 0.30)
        }

        // Top bar inner items row
        Item {
            anchors.fill: parent
            anchors.leftMargin: 12
            anchors.rightMargin: 12

            // =========================================================
            // LEFT SECTION: Apple Logo + App Title + Standard Menus
            // =========================================================
            Row {
                id: leftSection
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                spacing: 12

                // System Logo / Apple Icon
                Rectangle {
                    width: 22
                    height: 22
                    anchors.verticalCenter: parent.verticalCenter
                    color: (appleHover.hovered || IslandBridge.systemMenuOpen) ? Qt.rgba(1, 1, 1, 0.16) : "transparent"
                    radius: 4

                    Text {
                        anchors.centerIn: parent
                        text: ""
                        color: Theme.textPrimary
                        font.pixelSize: 15
                    }

                    HoverHandler { id: appleHover }
                    TapHandler {
                        onTapped: {
                            activeMenuIndex = -1;
                            IslandBridge.toggleSystemMenu();
                        }
                    }
                }

                // Active Application Title (Bold)
                Text {
                    text: IslandBridge.activeAppTitle || "Finder"
                    color: Theme.textPrimary
                    font.pixelSize: 12
                    font.bold: true
                    font.family: Theme.fontFamily
                    anchors.verticalCenter: parent.verticalCenter
                    elide: Text.ElideRight
                    maximumLineCount: 1
                }

                // Application Menu Bar (File, Edit, View, Window, Help)
                Row {
                    spacing: 4
                    anchors.verticalCenter: parent.verticalCenter

                    Repeater {
                        model: ["File", "Edit", "View", "Window", "Help"]

                        delegate: Rectangle {
                            required property string modelData
                            required property int index

                            width: menuText.implicitWidth + 12
                            height: 22
                            radius: 4
                            color: (mHover.hovered || activeMenuIndex === index) ? Qt.rgba(1, 1, 1, 0.14) : "transparent"

                            Text {
                                id: menuText
                                anchors.centerIn: parent
                                text: modelData
                                color: Theme.textPrimary
                                font.pixelSize: 12
                                font.family: Theme.fontFamily
                            }

                            HoverHandler { id: mHover }
                            TapHandler {
                                onTapped: {
                                    IslandBridge.closeAllPopovers();
                                    if (activeMenuIndex === index) {
                                        activeMenuIndex = -1;
                                    } else {
                                        activeMenuIndex = index;
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // =========================================================
            // CENTER SECTION: Notch / Dynamic Island Safe Area Spacer
            // =========================================================
            Item {
                id: centerSpacer
                anchors.centerIn: parent
                width: Math.max(IslandBridge.notchEnabled ? IslandBridge.notchWidth : 160, IslandBridge.capsuleWidth + 24)
                height: parent.height
            }

            // =========================================================
            // RIGHT SECTION: Status Glyphs, Toggles, Control Center, Clock
            // =========================================================
            Row {
                id: rightSection
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                spacing: 8

                // 1. Keyboard Layout Indicator
                Rectangle {
                    width: lanRow.implicitWidth + 8
                    height: 20
                    radius: 4
                    color: lanHover.hovered ? Qt.rgba(1, 1, 1, 0.12) : "transparent"
                    anchors.verticalCenter: parent.verticalCenter

                    Row {
                        id: lanRow
                        anchors.centerIn: parent
                        spacing: 3
                        Text {
                            text: "󰌌"
                            color: Theme.textSecondary
                            font.pixelSize: 11
                        }
                        Text {
                            text: (IslandBridge.title && IslandBridge.title.indexOf("KH") !== -1) ? "KH" : "US"
                            color: Theme.textPrimary
                            font.pixelSize: 11
                            font.bold: true
                            font.family: Theme.fontFamily
                        }
                    }
                    HoverHandler { id: lanHover }
                    TapHandler {
                        onTapped: IslandBridge.sendCommand("layout", ["next"])
                    }
                }

                // 2. Privacy Streaming Indicator (Active Microphone / Recording)
                Rectangle {
                    width: micRow.implicitWidth + 8
                    height: 20
                    radius: 10
                    color: Qt.rgba(1.0, 0.60, 0.0, 0.20)
                    visible: IslandBridge.micActive
                    anchors.verticalCenter: parent.verticalCenter

                    Row {
                        id: micRow
                        anchors.centerIn: parent
                        spacing: 3
                        Text {
                            text: "●"
                            color: "#ff9f0a"
                            font.pixelSize: 8
                            anchors.verticalCenter: parent.verticalCenter
                        }
                        Text {
                            text: "󰍬"
                            color: "#ff9f0a"
                            font.pixelSize: 11
                            anchors.verticalCenter: parent.verticalCenter
                        }
                    }
                    TapHandler {
                        onTapped: IslandBridge.toggleAudioPopover()
                    }
                }

                // 3. Screen Mirroring / AirPlay
                Rectangle {
                    width: 22
                    height: 22
                    radius: 4
                    color: airplayHover.hovered ? Qt.rgba(1, 1, 1, 0.14) : "transparent"
                    anchors.verticalCenter: parent.verticalCenter

                    Text {
                        anchors.centerIn: parent
                        text: "󰕟"
                        color: airplayHover.hovered ? "#007AFF" : Theme.textPrimary
                        font.pixelSize: 13
                    }
                    HoverHandler { id: airplayHover }
                    TapHandler {
                        onTapped: IslandBridge.sendCommand("event", ["--title", "Screen Mirroring", "--message", "AirPlay / Wayland Display Ready", "--duration", "3"])
                    }
                }

                // 4. Wi-Fi Status Icon & Popover Toggle
                Rectangle {
                    width: 22
                    height: 22
                    radius: 4
                    color: (wifiBtnHover.hovered || IslandBridge.wifiOpen) ? Qt.rgba(1, 1, 1, 0.14) : "transparent"
                    anchors.verticalCenter: parent.verticalCenter

                    Text {
                        anchors.centerIn: parent
                        text: IslandBridge.wifiStatus ? (IslandBridge.wifiStatus.icon || "󰤨") : "󰤨"
                        color: (IslandBridge.wifiStatus && IslandBridge.wifiStatus.connected) ? "#007AFF" : Theme.textSecondary
                        font.pixelSize: 13
                    }
                    HoverHandler { id: wifiBtnHover }
                    TapHandler {
                        onTapped: {
                            activeMenuIndex = -1;
                            IslandBridge.toggleWifiView();
                        }
                    }
                }

                // 5. Bluetooth Status Icon & Popover Toggle
                Rectangle {
                    width: 22
                    height: 22
                    radius: 4
                    color: (btBtnHover.hovered || IslandBridge.bluetoothOpen) ? Qt.rgba(1, 1, 1, 0.14) : "transparent"
                    anchors.verticalCenter: parent.verticalCenter

                    Text {
                        anchors.centerIn: parent
                        text: "󰂯"
                        color: IslandBridge.bluetoothPowered ? "#007AFF" : Theme.textSecondary
                        font.pixelSize: 13
                    }
                    HoverHandler { id: btBtnHover }
                    TapHandler {
                        onTapped: {
                            activeMenuIndex = -1;
                            IslandBridge.toggleBluetoothView();
                        }
                    }
                }

                // 6. Volume / Sound Icon & Output Selector Toggle
                Rectangle {
                    width: 22
                    height: 22
                    radius: 4
                    color: (volBtnHover.hovered || IslandBridge.audioPopoverOpen) ? Qt.rgba(1, 1, 1, 0.14) : "transparent"
                    anchors.verticalCenter: parent.verticalCenter

                    Text {
                        anchors.centerIn: parent
                        text: IslandBridge.title === "Muted" ? "󰝟" : (IslandBridge.icon || "󰕾")
                        color: IslandBridge.title === "Muted" ? "#ff453a" : Theme.textPrimary
                        font.pixelSize: 13
                    }
                    HoverHandler { id: volBtnHover }
                    TapHandler {
                        onTapped: {
                            activeMenuIndex = -1;
                            IslandBridge.toggleAudioPopover();
                        }
                    }
                }

                // 7. Battery Status (Color-coded Icon + Percentage)
                Rectangle {
                    id: battContainer
                    width: battRow.implicitWidth + 8
                    height: 20
                    radius: 4
                    color: (battBtnHover.hovered || IslandBridge.batteryPopoverOpen) ? Qt.rgba(1, 1, 1, 0.14) : "transparent"
                    anchors.verticalCenter: parent.verticalCenter

                    readonly property int battLevel: IslandBridge.deviceBattery !== null ? IslandBridge.deviceBattery : 100
                    readonly property bool isCharging: IslandBridge.deviceCharging || (IslandBridge.deviceBattery === null)
                    readonly property color battColor: {
                        if (isCharging) return "#30d158";
                        if (battLevel <= 20) return "#ff453a";
                        if (battLevel <= 50) return "#ffd60a";
                        return "#30d158";
                    }

                    Row {
                        id: battRow
                        anchors.centerIn: parent
                        spacing: 4

                        Text {
                            text: battContainer.isCharging ? "󰂄" : (battContainer.battLevel <= 20 ? "󰂃" : (battContainer.battLevel <= 50 ? "󰁽" : "󰁹"))
                            color: battContainer.battColor
                            font.pixelSize: 13
                            anchors.verticalCenter: parent.verticalCenter
                        }

                        Text {
                            text: IslandBridge.deviceBattery !== null ? (IslandBridge.deviceBattery + "%") : "100%"
                            color: Theme.textPrimary
                            font.pixelSize: 11
                            font.family: Theme.fontFamily
                            anchors.verticalCenter: parent.verticalCenter
                        }
                    }
                    HoverHandler { id: battBtnHover }
                    TapHandler {
                        onTapped: {
                            activeMenuIndex = -1;
                            IslandBridge.toggleBatteryPopover();
                        }
                    }
                }

                // 8. Notification Bell / Do Not Disturb Toggle
                Rectangle {
                    width: 22
                    height: 22
                    radius: 4
                    color: dndBtnHover.hovered ? Qt.rgba(1, 1, 1, 0.14) : "transparent"
                    anchors.verticalCenter: parent.verticalCenter

                    Text {
                        anchors.centerIn: parent
                        text: IslandBridge.dndEnabled ? "󰂛" : "󰂚"
                        color: IslandBridge.dndEnabled ? "#AF52DE" : Theme.textPrimary
                        font.pixelSize: 13
                    }
                    HoverHandler { id: dndBtnHover }
                    TapHandler {
                        onTapped: IslandBridge.dndToggle()
                    }
                }

                // 9. Spotlight Search Button (Launches fuzzel)
                Rectangle {
                    width: 22
                    height: 22
                    radius: 4
                    color: spotHover.hovered ? Qt.rgba(1, 1, 1, 0.14) : "transparent"
                    anchors.verticalCenter: parent.verticalCenter

                    Text {
                        anchors.centerIn: parent
                        text: "󰍉"
                        color: spotHover.hovered ? "#007AFF" : Theme.textPrimary
                        font.pixelSize: 13
                    }
                    HoverHandler { id: spotHover }
                    TapHandler {
                        onTapped: IslandBridge.launchApp("fuzzel")
                    }
                }

                // 10. Siri / Apple Intelligence Button
                Rectangle {
                    width: 22
                    height: 22
                    radius: 11
                    color: siriHover.hovered ? Qt.rgba(0.75, 0.35, 0.95, 0.25) : "transparent"
                    anchors.verticalCenter: parent.verticalCenter

                    Text {
                        anchors.centerIn: parent
                        text: "󰚩"
                        color: "#bf5af2"
                        font.pixelSize: 13
                    }
                    HoverHandler { id: siriHover }
                    TapHandler {
                        onTapped: IslandBridge.launchApp("fuzzel")
                    }
                }

                // 11. Control Center Toggle Button
                Rectangle {
                    width: 22
                    height: 22
                    radius: 4
                    color: (ccBtnHover.hovered || IslandBridge.controlCenterOpen) ? Qt.rgba(1, 1, 1, 0.14) : "transparent"
                    anchors.verticalCenter: parent.verticalCenter

                    Text {
                        anchors.centerIn: parent
                        text: "󰘳"
                        color: (ccBtnHover.hovered || IslandBridge.controlCenterOpen) ? "#007AFF" : Theme.textPrimary
                        font.pixelSize: 13
                    }
                    HoverHandler { id: ccBtnHover }
                    TapHandler {
                        onTapped: {
                            activeMenuIndex = -1;
                            IslandBridge.toggleControlCenter();
                        }
                    }
                }

                // 12. Clock & Date
                Rectangle {
                    id: clockBtn
                    width: clockLabel.implicitWidth + 8
                    height: 20
                    radius: 4
                    color: (clockHover.hovered || IslandBridge.calendarPopoverOpen) ? Qt.rgba(1, 1, 1, 0.14) : "transparent"
                    anchors.verticalCenter: parent.verticalCenter

                    Text {
                        id: clockLabel
                        anchors.centerIn: parent
                        text: Qt.formatDateTime(clockTimer.currentTime, "ddd MMM d  h:mm A")
                        color: Theme.textPrimary
                        font.pixelSize: 12
                        font.bold: true
                        font.family: Theme.fontFamily
                    }

                    HoverHandler { id: clockHover }
                    TapHandler {
                        onTapped: {
                            activeMenuIndex = -1;
                            IslandBridge.toggleCalendarPopover();
                        }
                    }
                }
            }
        }
    }

    // Live clock ticker
    Timer {
        id: clockTimer
        interval: 1000
        repeat: true
        running: true
        property var currentTime: new Date()
        onTriggered: currentTime = new Date()
    }

    // =============================================================
    // FLOATING POPOVERS & DROPDOWNS
    // =============================================================

    // 1. System Menu Dropdown
    SystemMenuView {
        id: sysMenu
        anchors.top: barBackground.bottom
        anchors.topMargin: 4
        anchors.left: parent.left
        anchors.leftMargin: 8
        visible: IslandBridge.systemMenuOpen
        z: 10
    }

    // 2. Generic App Menu Dropdown (File, Edit, View, Window, Help)
    Rectangle {
        id: appMenuDropdown
        anchors.top: barBackground.bottom
        anchors.topMargin: 4
        anchors.left: parent.left
        anchors.leftMargin: Math.max(10, 80 + activeMenuIndex * 45)
        width: 180
        height: appMenuCol.implicitHeight + 16
        radius: 10
        color: Theme.background
        border.color: Theme.border
        border.width: 1
        visible: activeMenuIndex !== -1
        z: 10

        Column {
            id: appMenuCol
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.margins: 8
            spacing: 2

            Repeater {
                model: {
                    if (activeMenuIndex === 0) return [
                        { label: "New Window", sc: "⌘N", cmd: "new" },
                        { label: "Close Window", sc: "⌘W", cmd: "close" },
                        { label: "Preferences...", sc: "⌘,", cmd: "pref" }
                    ];
                    if (activeMenuIndex === 1) return [
                        { label: "Undo", sc: "⌘Z", cmd: "undo" },
                        { label: "Redo", sc: "⇧⌘Z", cmd: "redo" },
                        { label: "Cut", sc: "⌘X", cmd: "cut" },
                        { label: "Copy", sc: "⌘C", cmd: "copy" },
                        { label: "Paste", sc: "⌘V", cmd: "paste" },
                        { label: "Select All", sc: "⌘A", cmd: "select_all" }
                    ];
                    if (activeMenuIndex === 2) return [
                        { label: "Toggle Fullscreen", sc: "⌃⌘F", cmd: "fullscreen" },
                        { label: "Actual Size", sc: "⌘0", cmd: "zoom_reset" },
                        { label: "Zoom In", sc: "⌘+", cmd: "zoom_in" },
                        { label: "Zoom Out", sc: "⌘-", cmd: "zoom_out" }
                    ];
                    if (activeMenuIndex === 3) return [
                        { label: "Minimize", sc: "⌘M", cmd: "minimize" },
                        { label: "Zoom", sc: "", cmd: "zoom" },
                        { label: "Tile Left", sc: "⌃⌥←", cmd: "tile_left" },
                        { label: "Tile Right", sc: "⌃⌥→", cmd: "tile_right" }
                    ];
                    return [
                        { label: "Search Help", sc: "", cmd: "search" },
                        { label: "Keyboard Shortcuts", sc: "⌘?", cmd: "shortcuts" },
                        { label: "About Application", sc: "", cmd: "about" }
                    ];
                }

                delegate: Rectangle {
                    required property var modelData
                    width: parent.width
                    height: 24
                    radius: 4
                    color: amHover.hovered ? Theme.accent : "transparent"

                    Item {
                        anchors.fill: parent
                        anchors.margins: 6

                        Text {
                            text: modelData.label
                            color: amHover.hovered ? "#ffffff" : Theme.textPrimary
                            font.pixelSize: 11
                            font.family: Theme.fontFamily
                            anchors.left: parent.left
                            anchors.verticalCenter: parent.verticalCenter
                        }

                        Text {
                            text: modelData.sc
                            color: amHover.hovered ? Qt.rgba(1, 1, 1, 0.7) : Theme.textSecondary
                            font.pixelSize: 10
                            font.family: Theme.fontFamily
                            anchors.right: parent.right
                            anchors.verticalCenter: parent.verticalCenter
                        }
                    }

                    HoverHandler { id: amHover }
                    TapHandler {
                        onTapped: {
                            if (modelData.cmd === "minimize") {
                                if (IslandBridge.focusedWindow && IslandBridge.focusedWindow.id) {
                                    IslandBridge.minimizeWindow(IslandBridge.focusedWindow.id);
                                }
                            } else if (modelData.cmd === "close") {
                                IslandBridge.launchApp("swaymsg", ["kill"]);
                            } else if (modelData.cmd === "fullscreen") {
                                IslandBridge.launchApp("swaymsg", ["fullscreen", "toggle"]);
                            } else if (modelData.cmd === "pref") {
                                IslandBridge.openSettings();
                            }
                            activeMenuIndex = -1;
                        }
                    }
                }
            }
        }
    }

    // 3. Wi-Fi Popover
    Rectangle {
        id: wifiPopoverContainer
        anchors.top: barBackground.bottom
        anchors.topMargin: 4
        anchors.right: parent.right
        anchors.rightMargin: 110
        width: 320
        height: 380
        radius: 14
        color: Theme.background
        border.color: Theme.border
        border.width: 1
        visible: IslandBridge.wifiOpen
        z: 10

        WifiView {
            anchors.fill: parent
        }
    }

    // 4. Bluetooth Popover
    Rectangle {
        id: btPopoverContainer
        anchors.top: barBackground.bottom
        anchors.topMargin: 4
        anchors.right: parent.right
        anchors.rightMargin: 80
        width: 300
        height: 350
        radius: 14
        color: Theme.background
        border.color: Theme.border
        border.width: 1
        visible: IslandBridge.bluetoothOpen
        z: 10

        BluetoothView {
            anchors.fill: parent
        }
    }

    // 5. Audio Output Popover
    AudioOutputPopover {
        id: audioPopover
        anchors.top: barBackground.bottom
        anchors.topMargin: 4
        anchors.right: parent.right
        anchors.rightMargin: 50
        visible: IslandBridge.audioPopoverOpen
        z: 10
    }

    // 6. Battery Popover
    BatteryPopover {
        id: battPopover
        anchors.top: barBackground.bottom
        anchors.topMargin: 4
        anchors.right: parent.right
        anchors.rightMargin: 30
        visible: IslandBridge.batteryPopoverOpen
        z: 10
    }

    // 7. Calendar Popover
    CalendarPopover {
        id: calendarPopover
        anchors.top: barBackground.bottom
        anchors.topMargin: 4
        anchors.right: parent.right
        anchors.rightMargin: 8
        visible: IslandBridge.calendarPopoverOpen
        z: 10
    }

    // 8. Control Center Panel (Compact macOS Tahoe style)
    Rectangle {
        id: ccPopoverContainer
        anchors.top: barBackground.bottom
        anchors.topMargin: 4
        anchors.right: parent.right
        anchors.rightMargin: 8
        width: 320
        height: 350
        radius: 14
        color: Theme.background
        border.color: Theme.border
        border.width: 1
        visible: IslandBridge.controlCenterOpen
        z: 10

        QuickActions {
            anchors.fill: parent
        }
    }
}
