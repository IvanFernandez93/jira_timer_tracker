from typing import Optional
import logging

logger = logging.getLogger('JiraTimeTracker')


def apply_always_on_top(window, app_settings=None, raise_window: bool = True, force_disabled: bool = False):
    """Apply or remove the WindowStaysOnTopHint on a window based on settings.

    Args:
        window: the QWidget to modify.
        app_settings: optional AppSettings instance used to read the 'always_on_top' flag.
        raise_window: when True (default) the function will raise and activate the window
            after applying the flags. When False it will apply the flags but will not
            perform raise()/activateWindow(), which is useful when callers want to
            control stacking order themselves (e.g. show a detail window above the main
            window without main stealing focus).
        force_disabled: when True, always disable the WindowStaysOnTopHint flag regardless
            of settings. This is useful for making windows behave independently.

    This function manipulates the flags explicitly (adds or removes the hint)
    and refreshes the window by calling show() where appropriate. It avoids blind
    calls to setWindowFlags(window.windowFlags()) which can inadvertently strip other
    flags and cause windows to disappear.
    """
    try:
        enabled = False
        if app_settings is None or force_disabled:
            # Can't construct AppSettings without DB service here; leave disabled
            # Or if force_disabled is True, keep enabled as False
            app_settings = None
        elif app_settings:
            try:
                enabled = app_settings.get_setting('always_on_top', 'false').lower() == 'true'
            except Exception:
                enabled = False
            
            # Override enabled if force_disabled is True
            if force_disabled:
                enabled = False

        from PyQt6.QtCore import Qt

        try:
            # Prefer the non-destructive API setWindowFlag which toggles a single
            # window hint without replacing the entire flags bitmask. This avoids
            # widget recreation on some platforms/toolkits which can appear as the
            # window being closed and reopened.
            try:
                window.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, bool(enabled))
                # Refresh only if needed
                if not window.isVisible():
                    try:
                        window.show()
                    except Exception:
                        pass
                if enabled and raise_window:
                    try:
                        window.raise_()
                        window.activateWindow()
                    except Exception:
                        pass
                return
            except Exception:
                # Fall back to old behavior if setWindowFlag is not available or fails
                pass

            # Fallback: manipulate full flags bitmask (existing behavior)
            flags = window.windowFlags()
            if enabled:
                flags = flags | Qt.WindowType.WindowStaysOnTopHint
            else:
                # remove the bit if present
                flags = flags & ~Qt.WindowType.WindowStaysOnTopHint

            # Apply flags and refresh safely
            window.setWindowFlags(flags)
            try:
                if not window.isVisible():
                    window.show()
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
