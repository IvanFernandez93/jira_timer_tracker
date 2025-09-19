from typing import Optional
import logging

logger = logging.getLogger('JiraTimeTracker')


def apply_always_on_top(window, app_settings=None):
    """Apply or remove the WindowStaysOnTopHint on a window based on settings.

    This function manipulates the flags explicitly (adds or removes the hint)
    and refreshes the window by calling show()/raise()/activateWindow() where
    appropriate. It avoids blind calls to setWindowFlags(window.windowFlags())
    which can inadvertently strip other flags and cause windows to disappear.
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

                if enabled:
                    # Raising/activating a visible window is safe and does not
                    # force showEvent in most toolkits
                    window.raise_()
                    window.activateWindow()
            except Exception:
                pass
        except Exception:
            logger.exception('Failed to apply always-on-top flags')
    except Exception:
        logger.exception('apply_always_on_top unexpected error')
