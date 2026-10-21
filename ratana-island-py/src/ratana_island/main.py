"""CLI entry point for Ratana Island."""

import argparse
import os
import signal
import sys
from pathlib import Path


def _ensure_gtk4_layer_shell_preload() -> None:
    """Preloads libgtk4-layer-shell.so to avoid PyGObject symbol resolution issues."""
    lib_path = "/usr/lib/libgtk4-layer-shell.so"
    if not os.path.exists(lib_path):
        return

    current = os.environ.get("LD_PRELOAD", "")
    if lib_path not in current:
        os.environ["LD_PRELOAD"] = f"{lib_path}:{current}".rstrip(":")
        # Re-exec process with updated environment
        try:
            os.execv(sys.executable, [sys.executable] + sys.argv)
        except Exception:
            pass


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="ratana-island",
        description="Native Linux Dynamic Island for Sway/SwayFX",
    )
    parser.add_argument("--toggle", action="store_true", help="Toggle between compact and expanded modes")
    parser.add_argument("--expand", action="store_true", help="Expand the island")
    parser.add_argument("--collapse", action="store_true", help="Collapse the island to compact pill")
    parser.add_argument("--quit", action="store_true", help="Quit the running instance")
    parser.add_argument("--status", action="store_true", help="Print status of running instance")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose debug logging")

    args = parser.parse_args()

    # Import internal modules (after potential re-exec)
    from ratana_island.logging_config import setup_logging
    from ratana_island.utils.ipc import send_ipc_command

    logger = setup_logging(verbose=args.verbose)

    # 1. Handle IPC control commands if another instance is running
    cmd_to_send = None
    if args.quit:
        cmd_to_send = "quit"
    elif args.toggle:
        cmd_to_send = "toggle"
    elif args.expand:
        cmd_to_send = "expand"
    elif args.collapse:
        cmd_to_send = "collapse"
    elif args.status:
        cmd_to_send = "status"

    if cmd_to_send:
        resp = send_ipc_command(cmd_to_send)
        if resp is not None:
            print(resp)
            return 0
        elif cmd_to_send in ("quit", "status", "expand", "collapse"):
            print("Ratana Island is not running.")
            return 1
        # If --toggle was passed but app not running, proceed to launch!

    # 2. Ensure LD_PRELOAD for PyGObject GTK4 LayerShell
    _ensure_gtk4_layer_shell_preload()

    # 3. Check dependencies & launch GUI application
    try:
        import gi
        gi.require_version("Gtk", "4.0")
        from gi.repository import GLib, Gtk
    except Exception as e:
        logger.error(f"Failed to import GTK4: {e}")
        return 1

    from ratana_island.app import RatanaIslandApp

    app = RatanaIslandApp()

    # Handle termination signals cleanly
    def handle_signal(sig, frame):
        logger.info(f"Received signal {sig}, exiting...")
        GLib.idle_add(app.quit)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    return app.run([])


if __name__ == "__main__":
    sys.exit(main())
