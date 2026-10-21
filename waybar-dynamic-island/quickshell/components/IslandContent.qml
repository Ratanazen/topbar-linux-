import QtQuick
import "../services"
import "../themes"

Item {
    id: root
    anchors.fill: parent

    // Smooth opacity transition between state views
    Behavior on opacity {
        NumberAnimation {
            duration: IslandBridge.reducedMotion ? 0 : 140
            easing.type: Easing.InOutQuad
        }
    }

    // Expose compact idle content width for dynamic pill sizing
    readonly property real compactImplicitWidth: compactIdleView.implicitWidth

    property bool isDragHovered: false

    // 1. Idle View (Compact Clock & Date)
    CompactView {
        id: compactIdleView
        visible: !root.isDragHovered && IslandBridge.visualState === "idle"
    }

    // 2. Media View (Compact or Expanded)
    MediaView {
        id: mediaView
        visible: !root.isDragHovered && (IslandBridge.visualState === "mediaCompact" || IslandBridge.visualState === "mediaExpanded" || IslandBridge.visualState === "media")
    }

    // 3. Bluetooth View
    BluetoothView {
        id: bluetoothView
        visible: !root.isDragHovered && IslandBridge.visualState === "bluetooth"
    }

    // 4. Volume View
    VolumeView {
        id: volumeView
        visible: !root.isDragHovered && IslandBridge.visualState === "volume"
    }

    // 5. Brightness View
    BrightnessView {
        id: brightnessView
        visible: !root.isDragHovered && IslandBridge.visualState === "brightness"
    }

    // 6. Recording View
    RecordingView {
        id: recordingView
        visible: !root.isDragHovered && IslandBridge.visualState === "recording"
    }

    // 7. Notification View
    NotificationView {
        id: notificationView
        visible: !root.isDragHovered && IslandBridge.visualState === "notification"
    }

    // 8. Timer & Pomodoro View
    TimerView {
        id: timerView
        visible: !root.isDragHovered && (IslandBridge.visualState === "timer" || IslandBridge.visualState === "pomodoro")
    }

    // 9. Quick Actions View
    QuickActions {
        id: quickActionsView
        visible: !root.isDragHovered && IslandBridge.visualState === "quickActions"
    }

    // 10. Settings & Theme View
    Settings {
        id: settingsView
        visible: !root.isDragHovered && IslandBridge.visualState === "settings"
    }

    // 11. Generic Expanded Card View
    ExpandedView {
        id: expandedView
        visible: !root.isDragHovered && IslandBridge.visualState === "expanded"
    }

    // 12. Drag Active Drop Zone View
    DragActiveView {
        id: dragActiveView
        visible: root.isDragHovered || IslandBridge.visualState === "dragActive"
    }

    // 13. Smart Share Interactive Picker View
    SmartShareView {
        id: smartShareView
        visible: !root.isDragHovered && IslandBridge.visualState === "sharePicker"
    }

    // 14. Transient Event View (Network, Battery, Charging, Clipboard, Task, Language, System, Window Animation, Error)
    EventView {
        id: eventView
        visible: !root.isDragHovered && (
                 IslandBridge.visualState === "network" ||
                 IslandBridge.visualState === "clipboard" ||
                 IslandBridge.visualState === "battery" ||
                 IslandBridge.visualState === "charging" ||
                 IslandBridge.visualState === "low-battery" ||
                 IslandBridge.visualState === "battery_warning" ||
                 IslandBridge.visualState === "task" ||
                 IslandBridge.visualState === "system" ||
                 IslandBridge.visualState === "language" ||
                 IslandBridge.visualState === "windowAnimation" ||
                 IslandBridge.visualState === "minimized" ||
                 IslandBridge.visualState === "restoring" ||
                 IslandBridge.visualState === "share_launching" ||
                 IslandBridge.visualState === "share_error" ||
                 IslandBridge.visualState === "error")
    }
}
