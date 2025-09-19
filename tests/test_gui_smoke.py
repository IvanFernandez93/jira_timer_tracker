import pytest


def test_mainwindow_nav_visible(qtbot):
    """Simple smoke test: create the main window, show it and assert the
    left navigation rail has non-zero width and there is at least one nav item.
    This uses the project's real MainWindow which will pick up the local
    qfluentwidgets shim if the real package is not installed.
    """
    from views.main_window import MainWindow

    win = MainWindow()
    qtbot.addWidget(win)
    win.show()
    qtbot.waitForWindowShown(win)

    # small wait to let layout settle
    qtbot.wait(100)

    # navigation rail should exist and have visible width
    assert hasattr(win, '_nav_rail')
    assert win._nav_rail.width() > 0

    # navigationInterface should expose .items
    assert hasattr(win, 'navigationInterface')
    items = getattr(win.navigationInterface, 'items', None)
    assert items is not None
    assert len(items) >= 1
