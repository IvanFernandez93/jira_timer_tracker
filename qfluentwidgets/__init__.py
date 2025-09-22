"""Minimal shim of qfluentwidgets used by the project tests and main app.

This file provides a small, well-formed subset of the qfluentwidgets API the
application imports during development and tests. It intentionally keeps
implementation minimal and avoids complex Qt behaviour.
"""
from __future__ import annotations

from enum import Enum
from typing import Optional, Callable
import os

from PyQt6.QtWidgets import (
    QWidget, QMainWindow, QFrame, QHBoxLayout, QVBoxLayout,
    QStackedWidget, QPushButton, QSizePolicy, QSpacerItem,
    QLabel, QLineEdit, QTextEdit, QCheckBox, QComboBox, QTableWidget
)
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QTranslator
from PyQt6.QtWidgets import QLabel


class FluentIconMeta(type):
    """Metaclass that returns a default QIcon for any unknown attribute.

    This prevents AttributeError when the application references icons that
    aren't explicitly enumerated in the shim. It also caches the generated
    QIcon on the class so subsequent accesses are fast.
    """

    def __getattr__(cls, name: str):
        # Create a small colored pixmap with the first letter as a visible
        # placeholder so toolbar buttons are identifiable during development.
        # But do NOT attempt to construct QPixmap unless a QGuiApplication
        # already exists. Attempting to create a QPixmap before the
        # application is constructed triggers a fatal Qt error on startup.
        try:
            from PyQt6.QtGui import QGuiApplication
            if QGuiApplication.instance() is None:
                # Return an empty QIcon as a safe fallback at import time.
                icon = QIcon()
                setattr(cls, name, icon)
                return icon

            from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont
            from PyQt6.QtCore import Qt as _Qt
            # use a larger size so icons are visible on modern/high-DPI displays
            size = 32
            pix = QPixmap(size, size)
            # derive a color from the name for variety
            h = abs(hash(name)) % 360
            color = QColor.fromHsv(h, 200, 230)
            pix.fill(color)

            painter = QPainter(pix)
            try:
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
                # draw a subtle circular background to make icons readable against any UI
                from PyQt6.QtCore import QRectF
                r = QRectF(2, 2, size-4, size-4)
                painter.setBrush(color)
                painter.setPen(QColor(0,0,0,50))  # More prominent border
                painter.drawEllipse(r)
                # choose contrasting text color based on luminance
                l = (color.red() * 0.299 + color.green() * 0.587 + color.blue() * 0.114)
                text_color = QColor(255, 255, 255) if l < 180 else QColor(0, 0, 0)
                painter.setPen(text_color)
                font = QFont()
                font.setPointSize(14)
                font.setBold(True)
                painter.setFont(font)
                letter = (name[0].upper() if name else '?')
                rect = pix.rect()
                painter.drawText(rect, int(_Qt.AlignmentFlag.AlignCenter), letter)
            finally:
                painter.end()

            icon = QIcon(pix)
        except Exception:
            # Fall back to an empty icon if drawing fails
            icon = QIcon()

        setattr(cls, name, icon)
        return icon


ICON_DIR = os.path.join(os.path.dirname(__file__), '..', 'resources', 'icons')
def _icon(name, fallback=None):
    path_png = os.path.join(ICON_DIR, f"{name}.png")
    path_svg = os.path.join(ICON_DIR, f"{name}.svg")
    
    # Try to load PNG first, then SVG
    try:
        if os.path.exists(path_png):
            return QIcon(path_png)
        elif os.path.exists(path_svg):
            return QIcon(path_svg)
    except Exception:
        pass

    # No icon file found: generate a visible placeholder icon using Unicode symbols
    # Only attempt to draw a QPixmap if a QGuiApplication instance exists.
    try:
        from PyQt6.QtGui import QGuiApplication
        if QGuiApplication.instance() is None:
            # Safe fallback at import time
            return fallback if fallback else QIcon()

        from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont, QBrush, QPen
        from PyQt6.QtCore import Qt as _Qt, QRect

        size = 24  # Optimal size for toolbar buttons
        pix = QPixmap(size, size)
        pix.fill(QColor(0, 0, 0, 0))  # Transparent background

        painter = QPainter(pix)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
            
            # Map icon names to Unicode symbols for better recognition
            unicode_symbols = {
                'brush': '🖌',
                'checkbox': '☑',
                'check': '✓',
                'edit': '✏',
                'delete': '🗑',
                'folder': '📁',
                'history': '🕒',
                'search': '🔍',
                'setting': '⚙',
                'play': '▶',
                'pause': '⏸',
                'close': '✕',
                'plus': '➕',
                'add': '➕',
                'minus': '➖',
                'bold': 'B',
                'italic': 'I',
                'font': 'F',
                'link': '🔗',
                'image': '🖼',
                'undo': '↶',
                'redo': '↷',
                'sync': '🔄',
                'info': 'ⓘ',
                'view': '👁',
                'grid': '▦',
                'document': '📄',
                'return': '↩',
                'update': '🔄',
                'ringer': '🔔',
                'share': '📤'
            }
            
            # Create clean background with light colors - NEVER black
            rect = QRect(2, 2, size-4, size-4)
            
            # Use very light, subtle colors for better UI integration
            if name in ['brush', 'edit']:
                # Creative tools - very light orange
                bg_color = QColor(255, 245, 235, 120)  # Light warm
                text_color = QColor(255, 140, 0)       # Orange text
            elif name in ['delete']:
                # Destructive action - very light red
                bg_color = QColor(255, 240, 240, 120)  # Light red
                text_color = QColor(220, 53, 69)       # Bootstrap red
            elif name in ['checkbox', 'check']:
                # Success action - very light green  
                bg_color = QColor(240, 255, 240, 120)  # Light green
                text_color = QColor(40, 167, 69)       # Bootstrap green
            elif name in ['folder', 'document']:
                # File operations - very light yellow
                bg_color = QColor(255, 252, 230, 120)  # Light yellow
                text_color = QColor(218, 165, 32)      # Goldenrod
            elif name in ['search', 'history']:
                # Navigation - very light blue
                bg_color = QColor(240, 248, 255, 120)  # Light blue
                text_color = QColor(0, 100, 200)       # Blue
            else:
                # Default - very light gray
                bg_color = QColor(248, 249, 250, 120)  # Light gray
                text_color = QColor(108, 117, 125)     # Bootstrap gray
            
            # Draw very subtle rounded background
            painter.setBrush(QBrush(bg_color))
            painter.setPen(QPen(text_color, 1))
            painter.drawRoundedRect(rect, 4, 4)
            
            # Draw symbol with the same color as border for consistency
            painter.setPen(QPen(text_color))
            font = QFont()
            
            if name in unicode_symbols:
                # Use Unicode symbol
                symbol = unicode_symbols[name]
                # All symbols use consistent size
                font.setPointSize(11)
                font.setBold(True)
                painter.setFont(font)
                painter.drawText(rect, _Qt.AlignmentFlag.AlignCenter, symbol)
            else:
                # Fallback to first letter
                font.setPointSize(10)
                font.setBold(True)
                painter.setFont(font)
                letter = name[0].upper() if name else '?'
                painter.drawText(rect, _Qt.AlignmentFlag.AlignCenter, letter)
            
        finally:
            painter.end()

        icon = QIcon(pix)
    except Exception:
        icon = fallback if fallback else QIcon()

    return icon

class FluentIcon(metaclass=FluentIconMeta):
    # Icons will be populated by init_icons() after QApplication is ready
    # Common icons used across the app
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
    # icons used by markdown editor and other toolbars
    FONT = QIcon()
    BOLD = QIcon()
    ITALIC = QIcon()
    LINK = QIcon()
    IMAGE = QIcon()
    UNDO = QIcon()
    REDO = QIcon()
    CHECKBOX = QIcon()
    CHECK = QIcon()
    PLUS = QIcon()
    MINUS = QIcon()
    ADD = QIcon()
    DELETE = QIcon()
    EDIT = QIcon()
    VIEW = QIcon()
    SYNC = QIcon()
    ACCEPT_MEDIUM = QIcon()
    INFO = QIcon()
    SHARE = QIcon()


def init_icons():
    """Initialize all FluentIcon class attributes with proper icons.
    
    Must be called after QApplication is created. This function populates
    all icon attributes with either real PNG files from resources/icons
    or generated placeholder pixmaps if the files don't exist.
    """
    from PyQt6.QtGui import QGuiApplication
    if QGuiApplication.instance() is None:
        return  # Cannot initialize icons before QApplication exists
    
    # List of all icon names that should be initialized
    icon_names = [
        'FOLDER', 'HISTORY', 'GRID', 'BRUSH', 'SEARCH', 'RINGER',
        'DOCUMENT', 'RETURN', 'UPDATE', 'SETTING', 'PLAY', 'PAUSE',
        'CLOSE', 'FONT', 'BOLD', 'ITALIC', 'LINK', 'IMAGE', 'UNDO',
        'REDO', 'CHECKBOX', 'CHECK', 'PLUS', 'MINUS', 'ADD', 'DELETE',
        'EDIT', 'VIEW', 'SYNC', 'ACCEPT_MEDIUM', 'INFO', 'SHARE'
    ]
    
    for name in icon_names:
        try:
            # Generate icon using _icon() function
            icon = _icon(name.lower())
            setattr(FluentIcon, name, icon)
        except Exception:
            # If generation fails, keep the empty QIcon
            pass


class PushButton(QPushButton):
    """Compatibility wrapper around QPushButton that accepts multiple
    convenient constructor signatures used across the app:

    - PushButton(text)
    - PushButton(icon, text)
    - PushButton(icon)
    - PushButton(text, parent)
    - PushButton(icon, text, parent)

    PyQt6's QPushButton exposes overloads but Python call sites in the app
    sometimes pass (icon) or (icon, text) in a straightforward manner; this
    wrapper normalizes args and calls the appropriate super().__init__.
    """

    def __init__(self, *args, **kwargs):
        icon = None
        text = None
        parent = None

        # positional parsing
        if len(args) == 0:
            # nothing positional; pick from kwargs
            text = kwargs.pop('text', None)
            parent = kwargs.pop('parent', None)
            icon = kwargs.pop('icon', None)
        elif len(args) == 1:
            a0 = args[0]
            if isinstance(a0, QIcon):
                icon = a0
            elif isinstance(a0, str):
                text = a0
            else:
                parent = a0
            parent = kwargs.pop('parent', parent)
        elif len(args) == 2:
            a0, a1 = args
            if isinstance(a0, QIcon) and isinstance(a1, str):
                icon, text = a0, a1
            elif isinstance(a0, str):
                text, parent = a0, a1
            else:
                # fallback: treat second as parent
                parent = a1
        else:
            # 3 or more
            a0, a1, a2 = args[:3]
            if isinstance(a0, QIcon) and isinstance(a1, str):
                icon, text, parent = a0, a1, a2
            elif isinstance(a0, str):
                text, parent = a0, a1
            else:
                parent = a2

        # Final fallbacks from kwargs
        if text is None:
            text = kwargs.pop('text', None)
        if parent is None:
            parent = kwargs.pop('parent', None)
        if icon is None:
            icon = kwargs.pop('icon', None)

        # Call the appropriate QPushButton constructor
        try:
            if icon is not None and text is not None:
                super().__init__(icon, text, parent)
            elif text is not None:
                super().__init__(text, parent)
                if icon is not None:
                    try:
                        self.setIcon(icon)
                    except Exception:
                        pass
            elif icon is not None:
                # QPushButton doesn't have icon-only Python overload; create
                # a button with empty text and set the icon.
                super().__init__("", parent)
                try:
                    self.setIcon(icon)
                except Exception:
                    pass
            else:
                super().__init__(parent)
        except TypeError:
            # Fallback to a safe call
            try:
                super().__init__(parent)
            except Exception:
                super().__init__()


class FluentTranslator(QTranslator):
    def translate(self, context, sourceText, disambiguation=None, n=-1):
        return sourceText


class TransparentToolButton(QPushButton):
    """Simple transparent button used as a lightweight tool button in the shim.

    Provides a flat, icon-only button style similar to the real qfluentwidgets
    TransparentToolButton so the UI looks acceptable during development.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            self.setFlat(True)
        except Exception:
            pass
        try:
            self.setStyleSheet('border: none; background: transparent;')
        except Exception:
            pass


def getIconColor(name: str) -> str:
    return '#000000'



class NavigationItemPosition(Enum):
    LEFT = 1
    RIGHT = 2
    TOP = 3
    BOTTOM = 4


def getIconColor(name: str) -> str:
    return '#000000'


class FluentWindow(QMainWindow):
    """Minimal main window exposing a titleBar, a left nav rail and a stacked area.

    The navigationInterface returned by _make_nav_interface supports addItem,
    addSeparator and setCurrentItem used by the application.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # title bar placeholder
        self.titleBar = QFrame(self)
        # ensure titleBar has a layout so callers can add widgets to it
        try:
            from PyQt6.QtWidgets import QHBoxLayout
            tb_layout = QHBoxLayout(self.titleBar)
            tb_layout.setContentsMargins(8, 2, 8, 2)
            tb_layout.setSpacing(6)
            self.titleBar.setLayout(tb_layout)
        except Exception:
            pass

        # central area
        central = QWidget(self)
        central_layout = QHBoxLayout(central)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)

        # nav rail and layout
        self._nav_rail = QFrame(central)
        self._nav_layout = QVBoxLayout(self._nav_rail)
        try:
            self._nav_rail.setFixedWidth(180)
            self._nav_rail.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        except Exception:
            pass

        # stacked area
        self._stacked = QStackedWidget(central)

        central_layout.addWidget(self._nav_rail)
        central_layout.addWidget(self._stacked, 1)
        central.setLayout(central_layout)

        # wrapper with title bar on top
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
                except Exception:
                    pass

                try:
                    if hasattr(self.parent, '_nav_layout') and self.parent._nav_layout is not None:
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
                except Exception:
                    pass

                self.items.append(btn)
                self._items_by_id[id_] = btn
                return btn

            def addSeparator(self):
                try:
                    spacer = QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
                    if hasattr(self.parent, '_nav_layout') and self.parent._nav_layout is not None:
                        self.parent._nav_layout.addItem(spacer)
                except Exception:
                    pass

            def setCurrentItem(self, id_or_name):
                try:
                    if hasattr(self.parent, '_stacked') and self.parent._stacked is not None:
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

        try:
            self._stacked.addWidget(widget)
        except Exception:
            pass

        def _cb(*_, w=widget):
            # Some Qt signals (like clicked) pass a boolean `checked` arg.
            # Accept and ignore any extra positional/keyword args so the
            # captured widget is always used for index lookup.
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
                try:
                    self._nav_layout.addWidget(btn)
                except Exception:
                    pass
                try:
                    btn.clicked.connect(_cb)
                except Exception:
                    pass
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


# Other simple components referenced across the repo (no-op implementations)
class Dialog(QWidget):
    pass


class ToolButton(QPushButton):
    """ToolButton should accept icon-only construction used by editors.

    We implement the same flexible constructor logic as PushButton so code
    that does ToolButton(FIF.SOMETHING) works.
    """

    def __init__(self, *args, **kwargs):
        # Reuse PushButton logic by delegating to PushButton.__init__ but keep
        # the class type as ToolButton.
        # Construct a temporary PushButton to parse args, then reparent.
        icon = None
        text = None
        parent = None

        if len(args) == 0:
            text = kwargs.pop('text', None)
            parent = kwargs.pop('parent', None)
            icon = kwargs.pop('icon', None)
        elif len(args) == 1:
            a0 = args[0]
            if isinstance(a0, QIcon):
                icon = a0
            elif isinstance(a0, str):
                text = a0
            else:
                parent = a0
            parent = kwargs.pop('parent', parent)
        elif len(args) == 2:
            a0, a1 = args
            if isinstance(a0, QIcon) and isinstance(a1, str):
                icon, text = a0, a1
            elif isinstance(a0, str):
                text, parent = a0, a1
            else:
                parent = a1
        else:
            a0, a1, a2 = args[:3]
            if isinstance(a0, QIcon) and isinstance(a1, str):
                icon, text, parent = a0, a1, a2
            elif isinstance(a0, str):
                text, parent = a0, a1
            else:
                parent = a2

        if text is None:
            text = kwargs.pop('text', None)
        if parent is None:
            parent = kwargs.pop('parent', None)
        if icon is None:
            icon = kwargs.pop('icon', None)

        # Initialize as a QPushButton similarly
        try:
            if icon is not None and text is not None:
                super().__init__(icon, text, parent)
            elif text is not None:
                super().__init__(text, parent)
                if icon is not None:
                    try:
                        self.setIcon(icon)
                    except Exception:
                        pass
            elif icon is not None:
                super().__init__("", parent)
                try:
                    self.setIcon(icon)
                except Exception:
                    pass
            else:
                super().__init__(parent)
        except TypeError:
            try:
                super().__init__(parent)
            except Exception:
                super().__init__()


class MessageBox(QWidget):
    @staticmethod
    def information(parent, title, text):
        return None


class Flyout(QWidget):
    """Minimal Flyout shim used by the app.

    The real Flyout provides a small, transient message anchored to a
    target widget. For the shim we provide a simple static `create`
    helper that shows a non-modal QLabel-like popup near the target and
    auto-closes after an optional timeout.
    """

    @staticmethod
    def create(title: str, content: str, target: Optional[QWidget] = None, parent: Optional[QWidget] = None, timeout: int = 3000):
        try:
            from PyQt6.QtWidgets import QLabel, QFrame
            from PyQt6.QtCore import Qt, QTimer

            # Create a frameless label to act as the flyout
            popup = QLabel(parent or target)
            popup.setWindowFlag(Qt.WindowType.Tool)
            popup.setWindowFlag(Qt.WindowType.FramelessWindowHint)
            popup.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
            popup.setFrameStyle(QFrame.Shape.Panel.value)
            popup.setText(f"<b>{title}</b><br>{content}")
            popup.setStyleSheet("background: #ffffff; border: 1px solid #888; padding: 8px;")

            # Position near the target if available
            if target is not None:
                try:
                    pos = target.mapToGlobal(target.rect().bottomLeft())
                    popup.move(pos.x(), pos.y())
                except Exception:
                    pass

            popup.show()

            # Auto-close after timeout milliseconds
            timer = QTimer(popup)
            timer.setSingleShot(True)
            timer.timeout.connect(popup.close)
            timer.start(timeout)
            return popup
        except Exception:
            # Fallback: print to console
            try:
                print(f"{title}: {content}")
            except Exception:
                pass
            return None


class TableWidget(QTableWidget):
    """Thin wrapper around QTableWidget so code expecting the original
    qfluentwidgets.TableWidget can call methods like horizontalHeader().
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        # Minimal defaults that the app may rely on
        try:
            self.setColumnCount(0)
            self.setRowCount(0)
        except Exception:
            pass


class LineEdit(QLineEdit):
    pass


class SearchLineEdit(LineEdit):
    pass


class BodyLabel(QLabel):
    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)



class TextEdit(QTextEdit):
    pass


class SwitchButton(QCheckBox):
    def __init__(self, text: str = ''):
        super().__init__(text)


class ExpandLayout(QVBoxLayout):
    pass


class ComboBox(QComboBox):
    pass


class TransparentToolButton(PushButton):
    pass


class SubtitleLabel(QLabel):
    pass


class StrongBodyLabel(QLabel):
    pass


class PrimaryPushButton(PushButton):
    pass


class IconWidget(QWidget):
    def __init__(self, icon: Optional[QIcon] = None, parent=None):
        super().__init__(parent)
        # no-op for the shim
        return


def setFont(*args, **kwargs):
    return None


__all__ = [
    'FluentWindow', 'FluentIcon', 'PushButton', 'FluentTranslator', 'NavigationItemPosition',
    'getIconColor', 'Theme', 'setTheme', 'isDarkTheme', 'Dialog', 'ToolButton', 'MessageBox',
    'TableWidget', 'LineEdit', 'SearchLineEdit', 'BodyLabel', 'TextEdit', 'SwitchButton',
    'ExpandLayout', 'ComboBox', 'TransparentToolButton', 'SubtitleLabel', 'IconWidget', 'setFont',
    'InfoBar', 'InfoBarPosition', 'FIF'
]

# Backwards compat name used in imports
FIF = FluentIcon
