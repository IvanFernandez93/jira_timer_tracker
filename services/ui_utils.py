from typing import Optional
import logging

logger = logging.getLogger('JiraTimeTracker')


def apply_always_on_top(window, app_settings=None, raise_window: bool = True):
    """Apply or remove the WindowStaysOnTopHint on a window based on settings.

    Args:
        window: the QWidget to modify.
        app_settings: optional AppSettings instance used to read the 'always_on_top' flag.
        raise_window: when True (default) the function will raise and activate the window
            after applying the flags. When False it will apply the flags but will not
            perform raise()/activateWindow(), which is useful when callers want to
            control stacking order themselves (e.g. show a detail window above the main
            window without main stealing focus).

    This function manipulates the flags explicitly (adds or removes the hint)
    and refreshes the window by calling show() where appropriate. It avoids blind
    calls to setWindowFlags(window.windowFlags()) which can inadvertently strip other
    flags and cause windows to disappear.
    """
    try:
        enabled = False
        if app_settings is None:
            # Can't construct AppSettings without DB service here; leave disabled
            app_settings = None

        if app_settings:
            try:
                enabled = app_settings.get_setting('always_on_top', 'false').lower() == 'true'
            except Exception:
                enabled = False

        from PyQt6.QtCore import Qt

        try:
            flags = window.windowFlags()
            if enabled:
                flags = flags | Qt.WindowType.WindowStaysOnTopHint
            else:
                # remove the bit if present
                flags = flags & ~Qt.WindowType.WindowStaysOnTopHint

            # Apply flags and refresh safely
            window.setWindowFlags(flags)
            try:
                # Only call show() if the window is not already visible. Calling
                # show() while already visible can re-trigger showEvent handlers
                # and cause reentrancy loops in some UI code.
                if not window.isVisible():
                    window.show()

                # Optionally raise/activate the window. Some callers (for example
                # when showing a detail window while the main window is always-on-top)
                # want to reapply the flags without forcing a raise here. Use the
                # raise_window parameter to control that behaviour.
                if enabled and raise_window:
                    try:
                        window.raise_()
                        window.activateWindow()
                    except Exception:
                        pass
            except Exception:
                pass
        except Exception:
            logger.exception('Failed to apply always-on-top flags')
    except Exception:
        logger.exception('apply_always_on_top unexpected error')
