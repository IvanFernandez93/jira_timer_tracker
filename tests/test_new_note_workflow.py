#!/usr/bin/env python3
"""
Test completo del workflow di creazione note con nuovo sistema di stati.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_new_note_workflow():
    """Test completo del workflow di creazione di una nuova nota."""
    
    print("🔍 Test workflow completo nuova nota...")
    
    try:
        from PyQt6.QtWidgets import QApplication
        from views.notes_manager_dialog import NotesManagerDialog
        from services.db_service import DatabaseService
        from services.app_settings import AppSettings
        
        print("✅ Import riusciti")
        
        # Setup applicazione
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        db = DatabaseService()
        db.initialize_db()
        app_settings = AppSettings(db)
        
        # Crea dialog
        dialog = NotesManagerDialog(db_service=db, app_settings=app_settings)
        print("✅ NotesManagerDialog creato")
        
        # Test 1: Stato iniziale
        print("\n🔧 Test 1: Stato iniziale...")
        print(f"Current note ID: {dialog.current_note_id}")
        print(f"Current note state: {getattr(dialog.current_note_state, 'state_name', 'None')}")
        
        # Test 2: Creazione nuova nota
        print("\n🔧 Test 2: Creazione nuova nota...")
        dialog.create_new_note()
        
        # Verifica stato NEW
        assert dialog.current_note_id is None, "Note ID deve essere None per nuove note"
        assert dialog.current_note_state.state_name == 'new', "Stato deve essere 'new'"
        
        # Verifica campi editabili
        assert not dialog.title_edit.isReadOnly(), "Title deve essere editabile"
        assert not dialog.content_edit.isReadOnly(), "Content deve essere editabile"
        assert not dialog.jira_key_edit.isReadOnly(), "Jira key deve essere editabile"
        assert not dialog.tags_edit.isReadOnly(), "Tags deve essere editabile"
        assert dialog.fictitious_cb.isEnabled(), "Checkbox fictitious deve essere abilitato"
        print("✅ Campi correttamente editabili")
        
        # Verifica pulsanti
        assert dialog.save_btn.text() == "Crea Bozza", "Pulsante deve essere 'Crea Bozza'"
        assert dialog.save_btn.isEnabled(), "Pulsante 'Crea Bozza' deve essere abilitato"
        assert dialog.commit_btn.text() == "Commit", "Pulsante deve essere 'Commit'"
        assert not dialog.commit_btn.isEnabled(), "Pulsante 'Commit' deve essere disabilitato"
        print("✅ Pulsanti correttamente configurati")
        
        # Verifica pulsanti file system
        assert not dialog.open_folder_btn.isEnabled(), "File system non disponibile per note nuove"
        assert not dialog.open_external_btn.isEnabled(), "Editor esterno non disponibile per note nuove"
        assert not dialog.git_history_btn.isEnabled(), "Cronologia non disponibile per note nuove"
        print("✅ Pulsanti file system correttamente disabilitati")
        
        # Test 3: Simulazione inserimento dati
        print("\n🔧 Test 3: Inserimento dati nota...")
        dialog.title_edit.setText("Test Note Title")
        dialog.jira_key_edit.setText("TEST-123")
        dialog.content_edit.setMarkdown("# Test Content\\n\\nThis is a test note.")
        dialog.tags_edit.setText("test,automation")
        
        print(f"Title: {dialog.title_edit.text()}")
        print(f"Jira Key: {dialog.jira_key_edit.text()}")
        print(f"Content length: {len(dialog.content_edit.toMarkdown())}")
        print(f"Tags: {dialog.tags_edit.text()}")
        print("✅ Dati inseriti correttamente")
        
        # Test 4: Verifica che l'auto-save non sia attivo per note nuove
        print("\n🔧 Test 4: Verifica auto-save per note nuove...")
        # Per le note nuove, l'auto-save non dovrebbe partire
        assert not dialog.auto_save_timer.isActive(), "Auto-save non deve essere attivo per note nuove"
        print("✅ Auto-save correttamente inattivo per note nuove")
        
        print("\n✅ TUTTI I TEST SUPERATI!")
        print("✅ Workflow creazione nuova nota FUNZIONANTE!")
        print("✅ I campi sono editabili e il sistema di stati funziona correttamente!")
        
        return True
        
    except Exception as e:
        print(f"❌ Errore durante il test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_new_note_workflow()
    print(f"\n{'✅ TEST SUPERATO' if success else '❌ TEST FALLITO'}")
    sys.exit(0 if success else 1)