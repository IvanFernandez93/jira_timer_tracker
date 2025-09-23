from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PyQt6.QtGui import QIcon, QPixmap, QColor
from qfluentwidgets import IconWidget

class NetworkStatusIndicator(QWidget):
    """
    Un indicatore che mostra lo stato della connessione a internet e a JIRA.
    Appare nella barra del titolo dell'applicazione.
    """
    clicked = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(28, 24)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Crea il layout
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(2, 2, 2, 2)
        self.layout.setSpacing(0)
        
        # Crea l'icona
        from qfluentwidgets import FluentIcon as FIF
        self._icon = FIF.GLOBE  # Salva il riferimento all'icona
        self.icon_widget = IconWidget(self._icon, self)
        self.icon_widget.setFixedSize(20, 20)
        self.layout.addWidget(self.icon_widget)
        
        # Stato iniziale: disconnesso
        self._internet_connected = False
        self._jira_connected = False
        self._update_appearance()
        
        # Imposta il tooltip
        self._update_tooltip()
        
    def set_connection_status(self, internet_connected: bool, jira_connected: bool):
        """
        Imposta lo stato della connessione.
        
        Args:
            internet_connected: True se è disponibile la connessione internet
            jira_connected: True se è disponibile la connessione a JIRA
        """
        if self._internet_connected == internet_connected and self._jira_connected == jira_connected:
            return  # Nessuna modifica
        
        self._internet_connected = internet_connected
        self._jira_connected = jira_connected
        
        self._update_appearance()
        self._update_tooltip()
    
    def _update_appearance(self):
        """Aggiorna l'aspetto dell'indicatore in base allo stato."""
        from qfluentwidgets import FluentIcon as FIF
        
        if self._internet_connected and self._jira_connected:
            # Connesso a internet e JIRA - icona verde
            self._icon = FIF.GLOBE
            self.icon_widget.setStyleSheet("color: #4CAF50;")  # Verde
        elif self._internet_connected:
            # Connesso a internet ma non a JIRA - icona gialla
            self._icon = FIF.GLOBE
            self.icon_widget.setStyleSheet("color: #FFC107;")  # Giallo
        else:
            # Nessuna connessione - icona rossa
            self._icon = FIF.GLOBE # Usa la stessa icona con colore rosso
            self.icon_widget.setStyleSheet("color: #F44336;")  # Rosso
    
    def _update_tooltip(self):
        """Aggiorna il tooltip dell'indicatore."""
        if self._internet_connected and self._jira_connected:
            tooltip = "Connesso a internet e JIRA"
        elif self._internet_connected:
            tooltip = "Connesso a internet, JIRA non disponibile\nLe modifiche saranno sincronizzate quando JIRA sarà disponibile"
        else:
            tooltip = "Nessuna connessione a internet\nLe modifiche saranno salvate localmente"
        
        self.setToolTip(tooltip)
    
    def mousePressEvent(self, event):
        """Gestisce il click sull'indicatore."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)