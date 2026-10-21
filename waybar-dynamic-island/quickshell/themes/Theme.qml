pragma Singleton
import QtQuick

QtObject {
    id: root

    property string currentTheme: "macos-black"

    // Background color
    readonly property color background: {
        switch (currentTheme) {
            case "macos-tahoe-glass":
            case "macos-tahoe":
            case "tahoe":
                return Qt.rgba(0.06, 0.08, 0.14, 0.76); // Frosted Tahoe Azure Glass
            case "macos-dark-glass":
            case "macos-dark":
                return Qt.rgba(0.08, 0.08, 0.11, 0.88); // macOS Dark Glass
            case "macos-light":
                return Qt.rgba(0.92, 0.93, 0.96, 0.82); // macOS Light Glass
            case "low-resource":
                return Qt.rgba(0.08, 0.08, 0.10, 0.98); // Opaque low-resource surface
            case "macos-glass":
            case "glass":
                return Qt.rgba(0.07, 0.08, 0.10, 0.72); // Frosted dark glass
            case "hyperos-dark":
            case "hyperos":
                return Qt.rgba(0.086, 0.086, 0.102, 0.94); // HyperOS charcoal #16161a
            case "originos-dark":
            case "originos":
                return Qt.rgba(0.090, 0.094, 0.133, 0.94); // OriginOS dark indigo #171822
            case "catppuccin-mocha":
            case "catppuccin":
                return Qt.rgba(0.118, 0.118, 0.180, 0.94); // #1e1e2e
            case "minimal-dark":
            case "minimal":
                return Qt.rgba(0.0, 0.0, 0.0, 1.0); // Pure OLED black
            case "macos-black":
            default:
                return Qt.rgba(0.035, 0.035, 0.043, 0.96); // Apple obsidian #09090b
        }
    }

    // Border color
    readonly property color border: {
        switch (currentTheme) {
            case "macos-tahoe-glass":
            case "macos-tahoe":
            case "tahoe":
                return Qt.rgba(0.40, 0.70, 1.0, 0.25);
            case "macos-dark-glass":
            case "macos-dark":
                return Qt.rgba(1.0, 1.0, 1.0, 0.16);
            case "macos-light":
                return Qt.rgba(0.0, 0.0, 0.0, 0.12);
            case "low-resource":
                return Qt.rgba(0.20, 0.20, 0.24, 0.90);
            case "macos-glass":
            case "glass":
                return Qt.rgba(1.0, 1.0, 1.0, 0.24); // Frosted illuminated rim
            case "hyperos-dark":
            case "hyperos":
                return Qt.rgba(1.0, 1.0, 1.0, 0.14);
            case "originos-dark":
            case "originos":
                return Qt.rgba(0.51, 0.53, 0.70, 0.22);
            case "catppuccin-mocha":
            case "catppuccin":
                return Qt.rgba(0.192, 0.196, 0.267, 0.85); // #313244
            case "minimal-dark":
            case "minimal":
                return Qt.rgba(0.18, 0.18, 0.18, 0.95);
            case "macos-black":
            default:
                return Qt.rgba(0.161, 0.161, 0.200, 0.90); // #292933
        }
    }

    // Card background for expanded cards and widgets
    readonly property color cardBackground: {
        switch (currentTheme) {
            case "macos-tahoe-glass":
            case "macos-tahoe":
            case "tahoe":
                return Qt.rgba(1.0, 1.0, 1.0, 0.10);
            case "macos-dark-glass":
            case "macos-dark":
                return Qt.rgba(1.0, 1.0, 1.0, 0.08);
            case "macos-light":
                return Qt.rgba(1.0, 1.0, 1.0, 0.65);
            case "low-resource":
                return Qt.rgba(0.12, 0.12, 0.15, 0.95);
            case "macos-glass":
            case "glass":
                return Qt.rgba(1.0, 1.0, 1.0, 0.08);
            case "hyperos-dark":
            case "hyperos":
                return Qt.rgba(1.0, 1.0, 1.0, 0.07);
            case "originos-dark":
            case "originos":
                return Qt.rgba(0.24, 0.26, 0.38, 0.35);
            case "catppuccin-mocha":
            case "catppuccin":
                return Qt.rgba(0.19, 0.20, 0.28, 0.60);
            case "minimal-dark":
            case "minimal":
                return Qt.rgba(0.10, 0.10, 0.10, 0.90);
            case "macos-black":
            default:
                return Qt.rgba(1.0, 1.0, 1.0, 0.06);
        }
    }

    // Text colors
    readonly property color textPrimary: {
        switch (currentTheme) {
            case "macos-tahoe-glass":
            case "macos-tahoe":
            case "tahoe":
            case "macos-dark-glass":
            case "macos-dark":
            case "low-resource":
                return "#ffffff";
            case "macos-light":
                return "#1d1d1f";
            case "catppuccin-mocha":
            case "catppuccin":
                return "#cdd6f4";
            case "hyperos-dark":
            case "hyperos":
                return "#f0f0f2";
            case "originos-dark":
            case "originos":
                return "#f2f4f8";
            case "minimal-dark":
            case "minimal":
                return "#e5e5e5";
            case "macos-glass":
            case "glass":
                return "#ffffff";
            case "macos-black":
            default:
                return "#f5f5f7";
        }
    }

    readonly property color textSecondary: {
        switch (currentTheme) {
            case "macos-tahoe-glass":
            case "macos-tahoe":
            case "tahoe":
                return "#d0d8e8";
            case "macos-dark-glass":
            case "macos-dark":
                return "#b0b0b8";
            case "macos-light":
                return "#6e6e73";
            case "low-resource":
                return "#a0a0a8";
            case "catppuccin-mocha":
            case "catppuccin":
                return "#a6adc8";
            case "hyperos-dark":
            case "hyperos":
                return "#9e9ea6";
            case "originos-dark":
            case "originos":
                return "#9499ad";
            case "minimal-dark":
            case "minimal":
                return "#888888";
            case "macos-glass":
            case "glass":
                return "#c8c8d0";
            case "macos-black":
            default:
                return "#a1a1a6";
        }
    }

    // Accents
    readonly property color accent: {
        switch (currentTheme) {
            case "macos-tahoe-glass":
            case "macos-tahoe":
            case "tahoe":
                return "#409cff";
            case "macos-dark-glass":
            case "macos-dark":
            case "low-resource":
                return "#0a84ff";
            case "macos-light":
                return "#007AFF";
            case "hyperos-dark":
            case "hyperos":
                return "#00d1c7"; // Xiaomi Cyan
            case "originos-dark":
            case "originos":
                return "#5856d6"; // OriginOS Indigo
            case "catppuccin-mocha":
            case "catppuccin":
                return "#89b4fa"; // Catppuccin Blue
            case "macos-glass":
            case "glass":
                return "#5ac8fa"; // Apple Ice Blue
            case "minimal-dark":
            case "minimal":
                return "#ffffff"; // Pure White
            case "macos-black":
            default:
                return "#0a84ff"; // Apple System Blue
        }
    }

    readonly property color accentRed: "#ff453a"
    readonly property color accentGreen: "#30d158"
    readonly property color accentYellow: "#ffd60a"
    readonly property color accentPurple: "#bf5af2"
    readonly property color accentOrange: "#ff9f0a"
    readonly property color accentCyan: "#64d2ff"

    // Shadow
    readonly property color shadowColor: Qt.rgba(0, 0, 0, 0.65)
}
