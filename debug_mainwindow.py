#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test di debug per la MainWindow - per identificare il problema
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication
from views.main_window import MainWindow
import logging

# Setup logging per vedere eventuali errori
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_main_window_loading():
    """Test per verificare se la MainWindow si carica correttamente."""
    
    print("🔍 DEBUG MAINWINDOW - Test di caricamento")
    print("=" * 50)
    
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    try:
        print("\n📱 Creazione MainWindow...")
        
        # Tenta di creare la MainWindow
        main_window = MainWindow()
        print("✅ MainWindow creata senza errori")
        
        # Verifica che le interfacce siano state create
        print("\n🔍 Verifica componenti:")
        
        if hasattr(main_window, 'jira_grid_view'):
            print(f"✅ jira_grid_view presente: {type(main_window.jira_grid_view)}")
        else:
            print("❌ jira_grid_view MANCANTE")
        
        if hasattr(main_window, 'history_view'):
            print(f"✅ history_view presente: {type(main_window.history_view)}")
        else:
            print("❌ history_view MANCANTE")
        
        # Verifica la ricerca universale
        print("\n🔍 Verifica ricerca universale:")
        if hasattr(main_window, 'search_widget'):
            print(f"✅ search_widget presente: {type(main_window.search_widget)}")
            if main_window.search_widget.search_targets:
                print(f"   📊 Target di ricerca: {len(main_window.search_widget.search_targets)}")
            else:
                print("   ⚠️ Nessun target di ricerca configurato")
        else:
            print("❌ search_widget MANCANTE")
        
        # Verifica che la finestra sia visualizzabile
        print("\n🖥️ Test visualizzazione:")
        main_window.show()
        print("✅ MainWindow.show() eseguito senza errori")
        
        # Verifica che le sub-interfaces siano state aggiunte
        print("\n📂 Verifica sub-interfaces:")
        navigation = main_window.navigationInterface
        if navigation:
            items = navigation.items
            print(f"   📊 Numero di item di navigazione: {len(items)}")
            for item in items:
                print(f"   • {item.text}")
        else:
            print("❌ NavigationInterface non trovato")
        
        print("\n🎉 RISULTATO:")
        print("✅ MainWindow sembra caricarsi correttamente!")
        
        return main_window
        
    except Exception as e:
        logger.error(f"Errore durante il caricamento della MainWindow: {e}")
        print(f"❌ ERRORE: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    main_window = test_main_window_loading()
    if main_window:
        print(f"\n⏳ MainWindow in esecuzione per test visuale...")
        print("   Controlla se la finestra appare correttamente.")
        print("   Chiudi la finestra per terminare il test.")
        
        app = QApplication.instance()
        if app:
            sys.exit(app.exec())
    else:
        print("\n❌ Test fallito - MainWindow non può essere caricata")
        sys.exit(1)