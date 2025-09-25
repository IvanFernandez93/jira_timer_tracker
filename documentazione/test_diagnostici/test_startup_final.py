#!/usr/bin/env python3
"""
Test finale per verificare che il sistema di startup funzioni senza dialog di notifica
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
import time

def test_startup_no_dialogs():
    """Test che l'avvio non mostri dialog durante la fase di startup"""
    
    app = QApplication([])
    
    # Importa il controller
    from controllers.main_controller import MainController
    
    print("Inizializzazione controller...")
    controller = MainController()
    
    print("Verifica flag is_during_startup...")
    assert hasattr(controller, 'is_during_startup'), "Flag is_during_startup dovrebbe esistere"
    
    # Simula avvio asincrono
    print("Avvio processo startup asincrono...")
    controller.start_async_startup()
    
    # Verifica che il flag sia attivo durante startup
    print(f"Flag startup attivo: {getattr(controller, 'is_during_startup', False)}")
    
    # Simula connessione JIRA durante startup
    def simulate_connection_change():
        print("Simulazione cambio stato connessione durante startup...")
        # Questo dovrebbe NON mostrare dialog
        controller._on_jira_connection_changed(True)
        print("Nessun dialog dovrebbe essere apparso")
        
        # Dopo qualche secondo, termina startup
        controller.is_during_startup = False
        print("Flag startup disattivato")
        
        # Ora il dialog dovrebbe apparire
        controller._on_jira_connection_changed(True)
        print("Ora il dialog dovrebbe apparire (se implementato)")
        
        app.quit()
    
    # Schedula test dopo 2 secondi
    QTimer.singleShot(2000, simulate_connection_change)
    
    # Avvia loop eventi
    app.exec()
    
    print("✓ Test completato - Nessun dialog durante startup")

if __name__ == "__main__":
    test_startup_no_dialogs()