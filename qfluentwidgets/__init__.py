"""Small, well-formed shim for qfluentwidgets used during development/tests.

Only implements a minimal API surface the application imports so local
development and pytest-qt runs work without the external dependency.
"""
from __future__ import annotations

from enum import Enum
from typing import Optional, Callable

from PyQt6.QtWidgets import (
    QWidget, QMainWindow, QFrame, QHBoxLayout, QVBoxLayout,
    QStackedWidget, QPushButton, QSizePolicy, QSpacerItem
)
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QTranslator


class FluentIcon:
    FOLDER = QIcon()


class PushButton(QPushButton):
    pass


class FluentTranslator(QTranslator):
    def translate(self, context, sourceText, disambiguation=None, n=-1):
        return sourceText


class NavigationItemPosition(Enum):
    LEFT = 1
    RIGHT = 2
    TOP = 3
    BOTTOM = 4


def getIconColor(name: str) -> str:
    return '#000'


class FluentWindow(QMainWindow):
    """Minimal main window exposing titleBar, _nav_rail, _stacked and
    navigationInterface with addItem/addSeparator/setCurrentItem.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.titleBar = QFrame(self)
        central = QWidget(self)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        self._nav_rail = QFrame(central)
        self._nav_layout = QVBoxLayout(self._nav_rail)
        try:
            self._nav_rail.setFixedWidth(180)
        except Exception:
            pass
        self._stacked = QStackedWidget(central)
        layout.addWidget(self._nav_rail)
        layout.addWidget(self._stacked, 1)
        central.setLayout(layout)
        wrapper = QWidget(self)
        w = QVBoxLayout(wrapper)
        w.setContentsMargins(0, 0, 0, 0)
        w.addWidget(self.titleBar)
        w.addWidget(central, 1)
        wrapper.setLayout(w)
        self.setCentralWidget(wrapper)
        self.navigationInterface = self._make_nav_interface()

    def _make_nav_interface(self):
        parent = self

        class NavInterface:
            def __init__(self, parent):
                self.parent = parent
                self.items = []

            def addItem(self, id_, icon, label, position=None, onClick: Optional[Callable] = None, **kwargs):
                btn = PushButton(label)
                try:
                    btn.setObjectName(id_)
                    btn.setFixedHeight(34)
                except Exception:
                    pass
                try:
                    self.parent._nav_layout.addWidget(btn)
                except Exception:
                    pass
                if onClick:
                    try:
                        btn.clicked.connect(onClick)
                    except Exception:
                        pass
                try:
                    btn.show()
                except Exception:
                    pass
                self.items.append(btn)
                return btn

            def addSeparator(self):
                try:
                    self.parent._nav_layout.addItem(QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
                except Exception:
                    pass

            def setCurrentItem(self, id_or_name):
                try:
                    for i in range(self.parent._stacked.count()):
                        w = self.parent._stacked.widget(i)
                        if w.objectName() == id_or_name:
                            self.parent._stacked.setCurrentIndex(i)
                            return
                except Exception:
                    pass

        return NavInterface(parent)


__all__ = [
    'FluentWindow', 'FluentIcon', 'PushButton', 'FluentTranslator', 'NavigationItemPosition', 'getIconColor'
]

# Backwards compat name used in imports
FIF = FluentIcon
        super().__init__(*args, **kwargs)

        self.titleBar = QFrame(self)
        try:
            tl = QHBoxLayout(self.titleBar)
            tl.setContentsMargins(6, 4, 6, 4)
            tl.setSpacing(8)
            self.titleBar.setLayout(tl)
        except Exception:
            pass

        central = QWidget(self)
        central_layout = QHBoxLayout(central)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)

        self._nav_rail = QFrame(central)
        self._nav_layout = QVBoxLayout(self._nav_rail)
        self._nav_layout.setContentsMargins(6, 6, 6, 6)
        self._nav_layout.setSpacing(6)
        try:
            self._nav_rail.setFixedWidth(180)
            self._nav_rail.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        except Exception:
            try:
                self._nav_rail.setMinimumWidth(160)
            except Exception:
                pass

        self._stacked = QStackedWidget(central)

        central_layout.addWidget(self._nav_rail)
        central_layout.addWidget(self._stacked, 1)
        central.setLayout(central_layout)

        wrapper = QWidget(self)
        w_layout = QVBoxLayout(wrapper)
        w_layout.setContentsMargins(0, 0, 0, 0)
        w_layout.setSpacing(0)
        w_layout.addWidget(self.titleBar)
        w_layout.addWidget(central, 1)
        wrapper.setLayout(w_layout)
        self.setCentralWidget(wrapper)

        self.navigationInterface = self._make_nav_interface()

    def _make_nav_interface(self):
        parent = self

        class NavInterface:
            def __init__(self, parent):
                self.parent = parent
                self.items = []
                self._items_by_id = {}

            def addItem(self, id_, icon, label, position=None, onClick: Optional[Callable] = None, **kwargs):
                btn = PushButton(label)
                try:
                    btn.setObjectName(id_)
                    btn.setFixedHeight(34)
                    btn.setMinimumWidth(120)
                    btn.setStyleSheet('text-align: left; padding-left: 8px;')
                except Exception:
                    pass

                try:
                    self.parent._nav_layout.addWidget(btn)
                except Exception:
                    pass

                if onClick is not None:
                    try:
                        btn.clicked.connect(onClick)
                    except Exception:
                        pass

                try:
                    btn.show()
                    btn.setVisible(True)
                except Exception:
                    pass

                self.items.append(btn)
                self._items_by_id[id_] = btn
                return btn

            def addSeparator(self):
                spacer = QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
                try:
                    self.parent._nav_layout.addItem(spacer)
                except Exception:
                    pass

            def setCurrentItem(self, id_or_name):
                try:
                    for idx in range(self.parent._stacked.count()):
                        w = self.parent._stacked.widget(idx)
                        if w.objectName() == id_or_name:
                            self.parent._stacked.setCurrentIndex(idx)
                            return
                except Exception:
                    pass

        return NavInterface(parent)

    def addSubInterface(self, widget: QWidget, icon: QIcon, label: str):
        try:
            if not widget.objectName():
                widget.setObjectName(label)
        except Exception:
            pass

        self._stacked.addWidget(widget)

        def _cb(w=widget):
            idx = self._stacked.indexOf(w)
            if idx >= 0:
                self._stacked.setCurrentIndex(idx)

        try:
            id_name = widget.objectName() or label
            self.navigationInterface.addItem(id_name, icon, label, onClick=_cb)
        except Exception:
            try:
                btn = PushButton(label)
                btn.setObjectName(id_name)
                btn.setParent(self._nav_rail)
                self._nav_layout.addWidget(btn)
                btn.clicked.connect(_cb)
            except Exception:
                pass


__all__ = [
    'FluentWindow', 'FluentIcon', 'PushButton', 'FluentTranslator', 'NavigationItemPosition'
]

# Backwards compat alias
FIF = FluentIcon
    BOTTOM = 2


class Theme(Enum):
    LIGHT = 'light'
    DARK = 'dark'


_current_theme = Theme.LIGHT


def setTheme(theme: Theme | str):
    global _current_theme
    if isinstance(theme, str):
        theme = Theme[theme.upper()] if theme.upper() in Theme.__members__ else Theme.LIGHT
    _current_theme = theme


def isDarkTheme() -> bool:
    return _current_theme == Theme.DARK


__all__ = [
    'LineEdit', 'PushButton', 'BodyLabel', 'TextEdit', 'FluentIcon',
    'FIF', 'SwitchButton', 'ExpandLayout', 'ComboBox', 'TransparentToolButton',
    'FluentWindow', 'NavigationItemPosition', 'SubtitleLabel', 'setFont',
    'InfoBar', 'InfoBarPosition', 'IconWidget', 'Theme', 'setTheme', 'isDarkTheme',
    'TableWidget', 'SearchLineEdit', 'FluentTranslator', 'Dialog', 'ToolButton',
    'MessageBox', 'getIconColor'
]

# Backwards compat alias used by imports in the repo
FIF = FluentIcon
                    self.items.append(btn)
                    self._items_by_id[id_] = btn
                    return btn

                def addSeparator(self):
                    spacer = QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
                    try:
                        self.parent._nav_layout.addItem(spacer)
                    except Exception:
                        pass

                def setCurrentItem(self, id_or_name):
                    try:
                        for idx in range(self.parent._stacked.count()):
                            w = self.parent._stacked.widget(idx)
                            if w.objectName() == id_or_name:
                                self.parent._stacked.setCurrentIndex(idx)
                                return
                    except Exception:
                        pass

            return NavInterface(parent)

        def addSubInterface(self, widget: QWidget, icon: QIcon, label: str):
            try:
                if not widget.objectName():
                    widget.setObjectName(label)
            except Exception:
                pass

            self._stacked.addWidget(widget)

            def _cb(w=widget):
                idx = self._stacked.indexOf(w)
                if idx >= 0:
                    self._stacked.setCurrentIndex(idx)

            try:
                id_name = widget.objectName() or label
                self.navigationInterface.addItem(id_name, icon, label, onClick=_cb)
            except Exception:
                try:
                    btn = PushButton(label)
                    btn.setObjectName(id_name)
                    btn.setParent(self._nav_rail)
                    self._nav_layout.addWidget(btn)
                    btn.clicked.connect(_cb)
                except Exception:
                    pass


    class InfoBar(QWidget):
        pass


    class InfoBarPosition(Enum):
        TOP = 1
        BOTTOM = 2


    class Theme(Enum):
        LIGHT = 'light'
        DARK = 'dark'


    _current_theme = Theme.LIGHT


    def setTheme(theme: Theme | str):
        global _current_theme
        if isinstance(theme, str):
            theme = Theme[theme.upper()] if theme.upper() in Theme.__members__ else Theme.LIGHT
        _current_theme = theme


    def isDarkTheme() -> bool:
        return _current_theme == Theme.DARK


    __all__ = [
        'LineEdit', 'PushButton', 'BodyLabel', 'TextEdit', 'FluentIcon',
        'FIF', 'SwitchButton', 'ExpandLayout', 'ComboBox', 'TransparentToolButton',
        'FluentWindow', 'NavigationItemPosition', 'SubtitleLabel', 'setFont',
        'InfoBar', 'InfoBarPosition', 'IconWidget', 'Theme', 'setTheme', 'isDarkTheme',
        'TableWidget', 'SearchLineEdit', 'FluentTranslator', 'Dialog', 'ToolButton',
        'MessageBox', 'getIconColor'
    ]

    # Backwards compat alias used by imports in the repo
    FIF = FluentIcon
class FluentTranslator(QTranslator):
    def translate(self, context, sourceText, disambiguation=None, n=-1):
        return sourceText


class PushButton(QPushButton):
    pass


class Dialog(QWidget):
    pass


class ToolButton(QPushButton):
    pass


class MessageBox(QWidget):
    @staticmethod
    def information(parent, title, text):
        return None


class TableWidget(QWidget):
    pass


class LineEdit(QWidget):
    pass


class SearchLineEdit(LineEdit):
    pass


class BodyLabel(QWidget):
    pass


class TextEdit(QWidget):
    pass


class SwitchButton(QWidget):
    pass


class ExpandLayout(QVBoxLayout):
    pass


class ComboBox(QWidget):
    pass


class TransparentToolButton(QPushButton):
    pass


class NavigationItemPosition(Enum):
    LEFT = 1
    RIGHT = 2
    TOP = 3
    BOTTOM = 4


class SubtitleLabel(QWidget):
    pass


class IconWidget(QWidget):
    def __init__(self, icon: Optional[QIcon] = None, parent=None):
        super().__init__(parent)
        # no-op for the shim
        return


def getIconColor(icon_name: str) -> str:
    return '#000000'


def setFont(*args, **kwargs):
    return None


class FluentWindow(QMainWindow):
    """Minimal main window with a left navigation rail and a central stacked area.

    Exposes:
    - titleBar: a QFrame placeholder
    - _nav_rail: the left rail (QFrame)
    - _stacked: QStackedWidget for pages
    - navigationInterface: object with addItem/addSeparator/setCurrentItem

    addSubInterface(widget, icon, label) will add the widget to the stacked area
    and create a nav button for it.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # title bar placeholder
        self.titleBar = QFrame(self)
        try:
            tl = QHBoxLayout(self.titleBar)
            tl.setContentsMargins(6, 4, 6, 4)
            tl.setSpacing(8)
            self.titleBar.setLayout(tl)
        except Exception:
            pass

        # central wrapper
        central = QWidget(self)
        central_layout = QHBoxLayout(central)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)

        # nav rail
        self._nav_rail = QFrame(central)
        self._nav_layout = QVBoxLayout(self._nav_rail)
        self._nav_layout.setContentsMargins(6, 6, 6, 6)
        self._nav_layout.setSpacing(6)
        # Make sure nav rail has visible width
        try:
            self._nav_rail.setFixedWidth(180)
            self._nav_rail.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        except Exception:
            try:
                self._nav_rail.setMinimumWidth(160)
            except Exception:
                pass

        # stacked content
        self._stacked = QStackedWidget(central)

        central_layout.addWidget(self._nav_rail)
        central_layout.addWidget(self._stacked, 1)
        central.setLayout(central_layout)

        # wrapper with titleBar on top
        wrapper = QWidget(self)
        w_layout = QVBoxLayout(wrapper)
        w_layout.setContentsMargins(0, 0, 0, 0)
        w_layout.setSpacing(0)
        w_layout.addWidget(self.titleBar)
        w_layout.addWidget(central, 1)
        wrapper.setLayout(w_layout)
        self.setCentralWidget(wrapper)

        # navigation interface
        self.navigationInterface = self._make_nav_interface()

    def _make_nav_interface(self):
        parent = self

        class NavInterface:
            def __init__(self, parent):
                self.parent = parent
                self.items = []
                self._items_by_id = {}

            def addItem(self, id_, icon, label, position=None, onClick: Optional[Callable] = None, **kwargs):
                btn = PushButton(label)
                try:
                    btn.setObjectName(id_)
                    btn.setFixedHeight(34)
                    btn.setMinimumWidth(120)
                    btn.setStyleSheet('text-align: left; padding-left: 8px;')
                except Exception:
                    pass

                try:
                    self.parent._nav_layout.addWidget(btn)
                except Exception:
                    pass

                if onClick is not None:
                    try:
                        btn.clicked.connect(onClick)
                    except Exception:
                        pass

                try:
                    btn.show()
                    btn.setVisible(True)
                except Exception:
                    pass

                self.items.append(btn)
                self._items_by_id[id_] = btn
                return btn

            def addSeparator(self):
                spacer = QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
                try:
                    self.parent._nav_layout.addItem(spacer)
                except Exception:
                    pass

            def setCurrentItem(self, id_or_name):
                try:
                    for idx in range(self.parent._stacked.count()):
                        w = self.parent._stacked.widget(idx)
                        if w.objectName() == id_or_name:
                            self.parent._stacked.setCurrentIndex(idx)
                            return
                except Exception:
                    pass

        return NavInterface(parent)

    def addSubInterface(self, widget: QWidget, icon: QIcon, label: str):
        try:
            if not widget.objectName():
                widget.setObjectName(label)
        except Exception:
            pass

        self._stacked.addWidget(widget)

        def _cb(w=widget):
            idx = self._stacked.indexOf(w)
            if idx >= 0:
                self._stacked.setCurrentIndex(idx)

        try:
            id_name = widget.objectName() or label
            self.navigationInterface.addItem(id_name, icon, label, onClick=_cb)
        except Exception:
            try:
                btn = PushButton(label)
                btn.setObjectName(id_name)
                btn.setParent(self._nav_rail)
                self._nav_layout.addWidget(btn)
                btn.clicked.connect(_cb)
            except Exception:
                pass


class InfoBar(QWidget):
    pass


class InfoBarPosition(Enum):
    TOP = 1
    BOTTOM = 2


class Theme(Enum):
    LIGHT = 'light'
    DARK = 'dark'


_current_theme = Theme.LIGHT


def setTheme(theme: Theme | str):
    global _current_theme
    if isinstance(theme, str):
        theme = Theme[theme.upper()] if theme.upper() in Theme.__members__ else Theme.LIGHT
    _current_theme = theme


def isDarkTheme() -> bool:
    return _current_theme == Theme.DARK


__all__ = [
    'LineEdit', 'PushButton', 'BodyLabel', 'TextEdit', 'FluentIcon',
    'FIF', 'SwitchButton', 'ExpandLayout', 'ComboBox', 'TransparentToolButton',
    'FluentWindow', 'NavigationItemPosition', 'SubtitleLabel', 'setFont',
    'InfoBar', 'InfoBarPosition', 'IconWidget', 'Theme', 'setTheme', 'isDarkTheme',
    'TableWidget', 'SearchLineEdit', 'FluentTranslator', 'Dialog', 'ToolButton',
    'MessageBox', 'getIconColor'
]

# Backwards compat alias used by imports in the repo
FIF = FluentIcon
    def _make_nav_interface(self):
        parent = self
        class NavInterface:
            def __init__(self, parent):
                self.parent = parent
                self.items = []
                self._items_by_id = {}
                self._current = None

            def addItem(self, id_, icon, label, position=None, onClick=None, **kwargs):
                btn = PushButton(label)
                try:
                    btn.setObjectName(id_)
                    btn.setFixedHeight(34)
                    btn.setMinimumWidth(120)
                    btn.setStyleSheet('text-align: left; padding-left: 8px;')
                except Exception:
                    pass

                try:
                    if hasattr(self.parent, '_nav_rail') and self.parent._nav_rail is not None:
                        try:
                            btn.setParent(self.parent._nav_rail)
                        except Exception:
                            pass
                    if hasattr(self.parent, '_nav_layout') and self.parent._nav_layout is not None:
                        try:
                            self.parent._nav_layout.addWidget(btn)
                        except Exception:
                            pass
                except Exception:
                    pass

                try:
                    if onClick is not None:
                        btn.clicked.connect(onClick)
                except Exception:
                    pass

                try:
                    btn.show()
                    btn.setVisible(True)
                except Exception:
                    pass

                self.items.append(btn)
                self._items_by_id[id_] = btn
                return btn

            def addSeparator(self):
                try:
                    if hasattr(self.parent, '_nav_layout') and self.parent._nav_layout is not None:
                        from PyQt6.QtWidgets import QSpacerItem
                        spacer = QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
                        self.parent._nav_layout.addItem(spacer)
                except Exception:
                    pass
                return None

            def setCurrentItem(self, id_or_name):
                try:
                    self._current = id_or_name
                    if hasattr(self.parent, '_stacked') and self.parent._stacked is not None:
                        for idx in range(self.parent._stacked.count()):
                            w = self.parent._stacked.widget(idx)
                            if w.objectName() == id_or_name:
                                self.parent._stacked.setCurrentIndex(idx)
                                return
                    btn = self._items_by_id.get(id_or_name)
                    if btn is not None:
                        try:
                            btn.click()
                        except Exception:
                            pass
                except Exception:
                    pass

        return NavInterface(parent)

class InfoBar(QWidget):
    pass

class InfoBarPosition(Enum):
    TOP = 1
    BOTTOM = 2

class Theme(Enum):
    LIGHT = 'light'
    DARK = 'dark'

_current_theme = Theme.LIGHT

def setTheme(theme: Theme | str):
    global _current_theme
    if isinstance(theme, str):
        theme = Theme(theme.upper()) if theme.upper() in Theme.__members__ else Theme.LIGHT
    _current_theme = theme

def isDarkTheme() -> bool:
    return _current_theme == Theme.DARK

__all__ = [
    'LineEdit', 'PushButton', 'BodyLabel', 'StrongBodyLabel', 'FluentIcon',
    'FIF', 'TextEdit', 'SwitchButton', 'ExpandLayout', 'ComboBox',
    'TransparentToolButton', 'FluentWindow', 'NavigationItemPosition',
    'SubtitleLabel', 'setFont', 'InfoBar', 'InfoBarPosition', 'IconWidget',
    'Theme', 'setTheme', 'isDarkTheme', 'TableWidget', 'SearchLineEdit',
    'FluentTranslator', 'Dialog', 'ToolButton', 'MessageBox', 'getIconColor',
    'PrimaryPushButton'
]

FIF = FluentIcon
from PyQt6.QtWidgets import (
    QPushButton, QLabel, QLineEdit, QTextEdit, QCheckBox, QComboBox,
    QVBoxLayout, QWidget, QMainWindow, QTableWidget, QTableWidgetItem, QHeaderView,
        try:
            class _NavInterface:
                def __init__(self, parent):
                    self.parent = parent
                    self.items = []
                    self._items_by_id = {}
                    self._current = None

                def addItem(self, id_, icon, label, position=None, onClick=None, **kwargs):
                    btn = PushButton(label)
                    # Basic styling/size so text is visible
                    try:
                        btn.setObjectName(id_)
                        btn.setFixedHeight(32)
                        btn.setMinimumWidth(120)
                        btn.setStyleSheet('text-align: left; padding-left: 10px;')
                    except Exception:
                        pass

                    from PyQt6.QtWidgets import (
                        QPushButton, QLabel, QLineEdit, QTextEdit, QCheckBox, QComboBox,
                        QVBoxLayout, QWidget, QMainWindow, QTableWidget, QTableWidgetItem, QHeaderView,
                        QFrame, QHBoxLayout, QStackedWidget, QSizePolicy
                    )
                    from PyQt6.QtGui import QIcon
                    from PyQt6.QtCore import QTranslator
                    from enum import Enum

                    class FluentIcon:
                        FOLDER = QIcon()
                        HISTORY = QIcon()
                        GRID = QIcon()
                        BRUSH = QIcon()
                        SEARCH = QIcon()
                        RINGER = QIcon()
                        DOCUMENT = QIcon()
                        RETURN = QIcon()
                        UPDATE = QIcon()
                        SETTING = QIcon()
                        PLAY = QIcon()
                        PAUSE = QIcon()
                        CLOSE = QIcon()

                    class FluentTranslator(QTranslator):
                        def __init__(self):
                            super().__init__()
                        def translate(self, context, sourceText, disambiguation=None, n=-1):
                            return sourceText

                    class Dialog(QWidget):
                        pass

                    class ToolButton(QPushButton):
                        pass

                    class MessageBox(QWidget):
                        @staticmethod
                        def information(parent, title, text):
                            return None

                    class TableWidget(QTableWidget):
                        def __init__(self, *args, **kwargs):
                            super().__init__(*args, **kwargs)
                            try:
                                self.setColumnCount(5)
                            except Exception:
                                pass

                    class LineEdit(QLineEdit):
                        pass

                    class SearchLineEdit(LineEdit):
                        pass

                    class PushButton(QPushButton):
                        pass

                    class PrimaryPushButton(PushButton):
                        pass

                    class BodyLabel(QLabel):
                        pass

                    class StrongBodyLabel(QLabel):
                        pass

                    class TextEdit(QTextEdit):
                        pass

                    class SwitchButton(QCheckBox):
                        def __init__(self, text=''):
                            super().__init__(text)

                    class ExpandLayout(QVBoxLayout):
                        pass

                    class ComboBox(QComboBox):
                        pass

                    class TransparentToolButton(QPushButton):
                        pass

                    class NavigationItemPosition(Enum):
                        LEFT = 1
                        RIGHT = 2
                        TOP = 3
                        BOTTOM = 4

                    class SubtitleLabel(QLabel):
                        pass

                    class IconWidget(QLabel):
                        def __init__(self, icon=None, parent=None):
                            super().__init__(parent)
                            if icon is not None:
                                try:
                                    self.setPixmap(icon.pixmap(16, 16))
                                except Exception:
                                    pass

                    def getIconColor(icon_name):
                        return '#000000'

                    def setFont(*args, **kwargs):
                        return None

                    class FluentWindow(QMainWindow):
                        def __init__(self, *args, **kwargs):
                            super().__init__(*args, **kwargs)

                            # Title bar placeholder
                            self.titleBar = QFrame(self)
                            try:
                                tl = QHBoxLayout(self.titleBar)
                                tl.setContentsMargins(6, 4, 6, 4)
                                tl.setSpacing(8)
                                self.titleBar.setLayout(tl)
                            except Exception:
                                pass

                            # Central area with nav rail and stacked pages
                            central = QWidget(self)
                            central_layout = QHBoxLayout(central)
                            central_layout.setContentsMargins(0, 0, 0, 0)
                            central_layout.setSpacing(0)

                            # Navigation rail
                            self._nav_rail = QFrame(central)
                            try:
                                self._nav_layout = QVBoxLayout(self._nav_rail)
                                self._nav_layout.setContentsMargins(6, 6, 6, 6)
                                self._nav_layout.setSpacing(6)
                                self._nav_rail.setLayout(self._nav_layout)
                                # Fixed width so it is always visible
                                try:
                                    self._nav_rail.setFixedWidth(180)
                                    self._nav_rail.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
                                except Exception:
                                    try:
                                        self._nav_rail.setMinimumWidth(160)
                                    except Exception:
                                        pass
                                try:
                                    self._nav_rail.setFrameShape(QFrame.Shape.StyledPanel)
                                    self._nav_rail.setStyleSheet('background-color: rgba(250,250,250,1);')
                                except Exception:
                                    pass
                            except Exception:
                                self._nav_layout = None

                            # Stacked content
                            try:
                                self._stacked = QStackedWidget(central)
                            except Exception:
                                self._stacked = None

                            try:
                                central_layout.addWidget(self._nav_rail)
                                central_layout.addWidget(self._stacked, 1)
                                try:
                                    central_layout.setStretch(0, 0)
                                    central_layout.setStretch(1, 1)
                                except Exception:
                                    pass
                            except Exception:
                                pass

                            wrapper = QWidget(self)
                            try:
                                from PyQt6.QtWidgets import QVBoxLayout
                                w_layout = QVBoxLayout(wrapper)
                                w_layout.setContentsMargins(0, 0, 0, 0)
                                w_layout.setSpacing(0)
                                w_layout.addWidget(self.titleBar)
                                w_layout.addWidget(central, 1)
                                wrapper.setLayout(w_layout)
                                self.setCentralWidget(wrapper)
                            except Exception:
                                try:
                                    self.setCentralWidget(central)
                                except Exception:
                                    pass

                            # Navigation interface
                            self.navigationInterface = self._make_nav_interface()

                        def _make_nav_interface(self):
                            parent = self
                            class NavInterface:
                                def __init__(self, parent):
                                    self.parent = parent
                                    self.items = []
                                    self._items_by_id = {}
                                    self._current = None

                                def addItem(self, id_, icon, label, position=None, onClick=None, **kwargs):
                                    btn = PushButton(label)
                                    try:
                                        btn.setObjectName(id_)
                                        btn.setFixedHeight(34)
                                        btn.setMinimumWidth(120)
                                        btn.setStyleSheet('text-align: left; padding-left: 8px;')
                                    except Exception:
                                        pass

                                    try:
                                        if hasattr(self.parent, '_nav_rail') and self.parent._nav_rail is not None:
                                            try:
                                                btn.setParent(self.parent._nav_rail)
                                            except Exception:
                                                pass
                                        if hasattr(self.parent, '_nav_layout') and self.parent._nav_layout is not None:
                                            try:
                                                self.parent._nav_layout.addWidget(btn)
                                            except Exception:
                                                pass
                                    except Exception:
                                        pass

                                    try:
                                        if onClick is not None:
                                            btn.clicked.connect(onClick)
                                    except Exception:
                                        pass

                                    try:
                                        btn.show()
                                        btn.setVisible(True)
                                    except Exception:
                                        pass

                                    self.items.append(btn)
                                    self._items_by_id[id_] = btn
                                    return btn

                                def addSeparator(self):
                                    try:
                                        if hasattr(self.parent, '_nav_layout') and self.parent._nav_layout is not None:
                                            from PyQt6.QtWidgets import QSpacerItem
                                            spacer = QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
                                            self.parent._nav_layout.addItem(spacer)
                                    except Exception:
                                        pass
                                    return None

                                def setCurrentItem(self, id_or_name):
                                    try:
                                        self._current = id_or_name
                                        if hasattr(self.parent, '_stacked') and self.parent._stacked is not None:
                                            for idx in range(self.parent._stacked.count()):
                                                w = self.parent._stacked.widget(idx)
                                                if w.objectName() == id_or_name:
                                                    self.parent._stacked.setCurrentIndex(idx)
                                                    return
                                        btn = self._items_by_id.get(id_or_name)
                                        if btn is not None:
                                            try:
                                                btn.click()
                                            except Exception:
                                                pass
                                    except Exception:
                                        pass

                            return NavInterface(parent)

                    class InfoBar(QWidget):
                        pass

                    class InfoBarPosition(Enum):
                        TOP = 1
                        BOTTOM = 2

                    class Theme(Enum):
                        LIGHT = 'light'
                        DARK = 'dark'

                    _current_theme = Theme.LIGHT

                    def setTheme(theme: Theme | str):
                        global _current_theme
                        if isinstance(theme, str):
                            theme = Theme(theme.upper()) if theme.upper() in Theme.__members__ else Theme.LIGHT
                        _current_theme = theme

                    def isDarkTheme() -> bool:
                        return _current_theme == Theme.DARK

                    __all__ = [
                        'LineEdit', 'PushButton', 'BodyLabel', 'StrongBodyLabel', 'FluentIcon',
                        'FIF', 'TextEdit', 'SwitchButton', 'ExpandLayout', 'ComboBox',
                        'TransparentToolButton', 'FluentWindow', 'NavigationItemPosition',
                        'SubtitleLabel', 'setFont', 'InfoBar', 'InfoBarPosition', 'IconWidget',
                        'Theme', 'setTheme', 'isDarkTheme', 'TableWidget', 'SearchLineEdit',
                        'FluentTranslator', 'Dialog', 'ToolButton', 'MessageBox', 'getIconColor',
                        'PrimaryPushButton'
                    ]

                    FIF = FluentIcon
                                                pass
    def addSubInterface(self, widget, icon, label):
        """Add a widget as a page in the stacked content area. The label is
        used as a fallback objectName so pages can be selected by nav id/name.
        """
        try:
            if widget.objectName() == '':
                widget.setObjectName(label)
        except Exception:
            try:
                widget.setObjectName(label)
            except Exception:
                pass
        try:
            if hasattr(self, '_stacked') and self._stacked is not None:
                self._stacked.addWidget(widget)
                # If this is the first page, show it
                try:
                    if self._stacked.count() == 1:
                        self._stacked.setCurrentIndex(0)
                except Exception:
                    pass
                # Also create a navigation item for this subinterface so the
                # application's calls to addSubInterface behave like the real
                # qfluentwidgets: navigation entries are created automatically.
                try:
                    id_name = widget.objectName() or label
                    # define a click callback which sets the stacked page
                    def _make_callback(w=widget):
                        def _cb():
                            try:
                                if hasattr(self, '_stacked') and self._stacked is not None:
                                    idx = self._stacked.indexOf(w)
                                    if idx >= 0:
                                        self._stacked.setCurrentIndex(idx)
                            except Exception:
                                pass
                        return _cb

                    try:
                        # Use navigationInterface if available, otherwise directly add a button
                        if hasattr(self, 'navigationInterface') and self.navigationInterface is not None:
                            self.navigationInterface.addItem(id_name, icon, label, onClick=_make_callback())
                        else:
                            # fallback: add a simple button to nav rail
                            btn = PushButton(label)
                            try:
                                btn.setObjectName(id_name)
                                if hasattr(self, '_nav_layout') and self._nav_layout is not None:
                                    self._nav_layout.addWidget(btn)
                                try:
                                    btn.clicked.connect(_make_callback())
                                except Exception:
                                    pass
                            except Exception:
                                pass
                    except Exception:
                        pass
                except Exception:
                    pass
        except Exception:
            # best-effort: set parent so it at least exists in the widget hierarchy
            try:
                widget.setParent(self)
            except Exception:
                pass


class InfoBar(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class InfoBarPosition(Enum):
    TOP = 1
    BOTTOM = 2


# Minimal theme support used by some views
class Theme(Enum):
    LIGHT = 'light'
    DARK = 'dark'


_current_theme = Theme.LIGHT

def setTheme(theme: Theme | str):
    global _current_theme
    if isinstance(theme, str):
        theme = Theme(theme.upper()) if theme.upper() in Theme.__members__ else Theme.LIGHT
    _current_theme = theme


def isDarkTheme() -> bool:
    return _current_theme == Theme.DARK


__all__ = [
    'LineEdit', 'PushButton', 'BodyLabel', 'StrongBodyLabel', 'FluentIcon',
    'FIF', 'TextEdit', 'SwitchButton', 'ExpandLayout', 'ComboBox',
    'TransparentToolButton', 'FluentWindow', 'NavigationItemPosition',
    'SubtitleLabel', 'setFont', 'InfoBar', 'InfoBarPosition', 'IconWidget',
    'Theme', 'setTheme', 'isDarkTheme', 'TableWidget', 'SearchLineEdit',
    'FluentTranslator', 'Dialog', 'ToolButton', 'MessageBox', 'getIconColor',
    'PrimaryPushButton'
]

# Backwards compat name used in imports
FIF = FluentIcon
