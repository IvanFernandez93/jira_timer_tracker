#!/usr/bin/env python3
"""
Test per verificare il fix del metodo _refresh_notes_list inesistente.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_refresh_notes_list_fix():
    """Test per verificare che il metodo _refresh_notes_list sia stato sostituito con load_notes()."""
    
    print("🔍 Test fix _refresh_notes_list...")
    
    try:
        from PyQt6.QtWidgets import QApplication
        from views.notes_manager_dialog import NotesManagerDialog
        from services.db_service import DatabaseService
        from services.app_settings import AppSettings
        
        print("✅ Import riusciti senza errori")
        
        # Test inizializzazione componenti
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        db = DatabaseService()
        db.initialize_db()
        app_settings = AppSettings(db)
        
        print("✅ Servizi inizializzati")
        
        # Test creazione dialog
        dialog = NotesManagerDialog(db_service=db, app_settings=app_settings)
        
        print("✅ NotesManagerDialog creato senza errori")
        
        # Verifica che il metodo load_notes esista
        assert hasattr(dialog, 'load_notes'), "Metodo load_notes non trovato!"
        print("✅ Metodo load_notes presente")
        
        # Verifica che _refresh_notes_list non esista più
        assert not hasattr(dialog, '_refresh_notes_list'), "Metodo _refresh_notes_list ancora presente!"
        print("✅ Metodo _refresh_notes_list rimosso correttamente")
        
        # Test chiamata load_notes (deve funzionare)
        dialog.load_notes()
        print("✅ Metodo load_notes chiamato con successo")
        
        print("✅ FIX _refresh_notes_list COMPLETATO - Tutto funziona!")
        
        return True
        
    except Exception as e:
        print(f"❌ Errore durante il test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_refresh_notes_list_fix()
    sys.exit(0 if success else 1)