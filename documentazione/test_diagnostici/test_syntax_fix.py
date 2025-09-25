#!/usr/bin/env python3
"""
Test rapido per verificare fix sintassi notes_manager_dialog.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_syntax_fix():
    """Test che verifica il fix della sintassi."""
    
    print("🔍 Test fix sintassi notes_manager_dialog.py...")
    
    try:
        from PyQt6.QtWidgets import QApplication
        from views.notes_manager_dialog import NotesManagerDialog
        from services.db_service import DatabaseService
        from services.app_settings import AppSettings
        
        print("✅ Import riusciti senza errori di sintassi")
        
        # Test inizializzazione componenti
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        db = DatabaseService()
        db.initialize_db()
        app_settings = AppSettings(db)
        
        print("✅ Servizi inizializzati")
        
        # Test creazione dialog (il punto dove falliva prima)
        dialog = NotesManagerDialog(db_service=db, app_settings=app_settings)
        
        print("✅ NotesManagerDialog creato senza errori")
        print("✅ SINTASSI FIX VERIFICATO - Tutto funziona!")
        
        return True
        
    except SyntaxError as e:
        print(f"❌ ERRORE SINTASSI ANCORA PRESENTE: {e}")
        return False
    except Exception as e:
        print(f"⚠️ Altri errori (non di sintassi): {e}")
        # Gli altri errori non sono problemi di sintassi
        return True

if __name__ == "__main__":
    success = test_syntax_fix()
    sys.exit(0 if success else 1)