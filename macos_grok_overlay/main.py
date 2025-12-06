# Python libraries
import argparse
import sys

# Local libraries.
from .constants import APP_TITLE, PERMISSION_CHECK_EXIT
from .health_checks import health_check_decorator


def _platform_kind():
    if sys.platform == "darwin":
        return "mac"
    if sys.platform.startswith("win"):
        return "win"
    return None


# Main executable for running the application from the command line.
@health_check_decorator
def main():
    parser = argparse.ArgumentParser(
        description=f"{APP_TITLE} Overlay App - Dedicated window that can be summoned and dismissed with a single keyboard command."
    )
    parser.add_argument(
        "--install-startup",
        action="store_true",
        help="Install the app to run at login",
    )
    parser.add_argument(
        "--uninstall-startup",
        action="store_true",
        help="Uninstall the app from running at login",
    )
    parser.add_argument(
        "--check-permissions",
        action="store_true",
        help="Check Accessibility permissions only"
    )
    args = parser.parse_args()

    platform_kind = _platform_kind()
    if platform_kind is None:
        print("Unsupported platform. This release currently targets macOS and Windows 10/11.")
        sys.exit(1)

    if platform_kind == "mac":
        from . import launcher as platform_launcher
    else:
        from . import windows_launcher as platform_launcher

    if args.install_startup:
        platform_launcher.install_startup()
        return

    if args.uninstall_startup:
        platform_launcher.uninstall_startup()
        return

    if args.check_permissions:
        if platform_kind == "mac":
            from .launcher import check_permissions

            is_trusted = check_permissions(ask=False)
            print("Permissions granted:", is_trusted)
            sys.exit(0 if is_trusted else PERMISSION_CHECK_EXIT)
        else:
            print("Accessibility permissions are only required on macOS.")
            sys.exit(0)

    if platform_kind == "mac":
        _run_macos_app()
    else:
        _run_windows_app()


def _run_macos_app() -> None:
    from .constants import LAUNCHER_TRIGGER
    from .app import AppDelegate, NSApplication
    from .launcher import check_permissions

    # Check permissions (make request to user) when launching, but proceed regardless.
    check_permissions()

    print()
    print(f"Starting macos-{APP_TITLE.lower()}-overlay.")
    print()
    print(f"To run at login, use:      macos-{APP_TITLE.lower()}-overlay --install-startup")
    print(f"To remove from login, use: macos-{APP_TITLE.lower()}-overlay --uninstall-startup")
    print(f"Current trigger: flags={LAUNCHER_TRIGGER['flags']} key={LAUNCHER_TRIGGER['key']}")
    print()
    app = NSApplication.sharedApplication()
    delegate = AppDelegate.alloc().init()
    app.setDelegate_(delegate)
    app.run()


def _run_windows_app() -> None:
    from .windows_app import WindowsOverlayApp

    print()
    print(f"Starting {APP_TITLE} overlay for Windows.")
    print()
    print(f"To run at login, use: macos-{APP_TITLE.lower()}-overlay --install-startup")
    print(f"To remove from login, use: macos-{APP_TITLE.lower()}-overlay --uninstall-startup")
    print()
    WindowsOverlayApp().run()



if __name__ == "__main__":
    # Execute the decorated main function.
    main()
