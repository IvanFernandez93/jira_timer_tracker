from PyQt6.QtGui import QIcon

class FluentIconBase:
    """Minimal base class for fluent icons used in the app."""
    def __init__(self, name:str=''):
        self.name = name

class Icon(QIcon):
    """Alias to QIcon for compatibility with code expecting qfluentwidgets.common.icon.Icon"""
    pass
