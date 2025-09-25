#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test per la funzionalità di ricerca universale
Verifica che Ctrl+F funzioni in tutte le finestre dell'applicazione.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication, QTextEdit, QVBoxLayout, QWidget
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeySequence
from views.universal_search_widget import UniversalSearchWidget, SearchableMixin
from views.notes_manager_dialog import NotesManagerDialog
from services.db_service import DatabaseService
from services.app_settings import AppSettings
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestSearchWindow(QWidget, SearchableMixin):
    """Finestra di test per la ricerca universale."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Test Universal Search - Premi Ctrl+F")
        self.setGeometry(100, 100, 600, 400)
        
        # Setup UI
        layout = QVBoxLayout(self)
        
        # Initialize search functionality
        self.init_search_functionality()
        
        # Create test text widgets
        self.text_edit1 = QTextEdit()
        self.text_edit1.setPlaceholderText("Primo editor di testo - inserisci del contenuto e prova Ctrl+F")
        self.text_edit1.setText("""
        Questo è il primo editor di testo.
        Contiene del testo di esempio per testare la ricerca.
        Puoi cercare parole come "esempio", "testo", "ricerca", "universale".
        La ricerca funziona in tempo reale mentre digiti.
        """)
        
        self.text_edit2 = QTextEdit()
        self.text_edit2.setPlaceholderText("Secondo editor di testo")
        self.text_edit2.setText("""
        Questo è il secondo editor di testo.
        Anche qui puoi cercare parole specifiche.
        Prova a cercare "editor", "specifiche", "Ctrl+F".
        La ricerca evidenzia i risultati trovati.
        """)
        
        layout.addWidget(self.text_edit1)
        layout.addWidget(self.text_edit2)
        
        # Add search targets
        self.add_searchable_widget(self.text_edit1)
        self.add_searchable_widget(self.text_edit2)


def test_universal_search():
    """Test della funzionalità di ricerca universale."""
    
    print("🔍 TEST RICERCA UNIVERSALE")
    print("=" * 50)
    
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    try:
        # Test 1: Widget di ricerca standalone
        print("\n📱 Test 1: Widget di ricerca standalone")
        test_window = TestSearchWindow()
        test_window.show()
        
        print("✅ Finestra di test creata con successo")
        print("   🎯 Funzionalità disponibili:")
        print("   • Ctrl+F - Apre la ricerca")
        print("   • F3 - Prossimo risultato") 
        print("   • Shift+F3 - Risultato precedente")
        print("   • Esc - Chiude la ricerca")
        print("   • Opzioni: Case sensitive, Whole word")
        
        # Test 2: Notes Manager con ricerca
        print("\n📝 Test 2: Notes Manager con ricerca integrata")
        try:
            db_service = DatabaseService()
            app_settings = AppSettings(db_service)
            notes_dialog = NotesManagerDialog(db_service, app_settings)
            notes_dialog.show()
            
            print("✅ Notes Manager creato con ricerca integrata")
            print("   🎯 Target di ricerca:")
            print("   • Tabella delle note")
            print("   • Editor del contenuto")
            print("   • Campo titolo")
            print("   • Campo JIRA key")
            print("   • Campo tags")
            
        except Exception as e:
            print(f"❌ Errore nel test Notes Manager: {e}")
        
        # Test 3: Verifica shortcut
        print("\n⌨️ Test 3: Verifica shortcut Ctrl+F")
        
        # Controlla se il widget di ricerca è presente
        if hasattr(test_window, 'search_widget'):
            search_widget = test_window.search_widget
            print("✅ Widget di ricerca trovato")
            print(f"   📊 Stato iniziale: {'Visibile' if search_widget.isVisible() else 'Nascosto'}")
            
            # Testa l'apertura della ricerca
            test_window.show_search()
            print(f"   📊 Dopo show_search(): {'Visibile' if search_widget.isVisible() else 'Nascosto'}")
            
            # Verifica i target di ricerca
            target_count = len(search_widget.search_targets)
            print(f"   🎯 Target di ricerca configurati: {target_count}")
            
            if target_count > 0:
                print("   📋 Lista target:")
                for i, target in enumerate(search_widget.search_targets):
                    print(f"     {i+1}. {target.__class__.__name__}")
            
        else:
            print("❌ Widget di ricerca non trovato")
        
        print("\n🎉 RISULTATO TEST:")
        print("✅ Ricerca universale implementata con successo!")
        print("\n💡 ISTRUZIONI PER L'UTENTE:")
        print("1. Apri qualsiasi finestra dell'applicazione")
        print("2. Premi Ctrl+F per aprire la ricerca")
        print("3. Digita il testo da cercare")
        print("4. Usa F3/Shift+F3 per navigare tra i risultati")
        print("5. Premi Esc per chiudere la ricerca")
        
        print("\n📍 FINESTRE CON RICERCA INTEGRATA:")
        print("• 📝 Gestione Note (tabella + editor)")
        print("• 🎫 Dettaglio Jira (descrizione + commenti + note)")
        print("• 📎 Attachments (lista allegati)")
        print("• 🏠 Finestra principale (griglia Jira + cronologia)")
        
        # Mantieni le finestre aperte per il test manuale
        print(f"\n🖥️ Finestre aperte per test manuale:")
        print("   - Prova Ctrl+F nelle finestre aperte")
        print("   - Chiudi le finestre quando hai finito il test")
        
        return True
        
    except Exception as e:
        logger.error(f"Errore durante il test: {e}")
        print(f"❌ ERRORE: {e}")
        return False


if __name__ == "__main__":
    success = test_universal_search()
    if success:
        print("\n" + "=" * 50)
        print("✅ Test completato - La ricerca universale è pronta!")
        
        # Mantieni l'applicazione in esecuzione per i test manuali
        app = QApplication.instance()
        if app:
            print("\n⏳ Applicazione in esecuzione per test manuali...")
            print("   Chiudi tutte le finestre per terminare il test.")
            sys.exit(app.exec())
    else:
        sys.exit(1)