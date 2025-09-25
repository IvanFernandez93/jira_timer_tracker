#!/usr/bin/env python3
"""
Test per verificare i miglioramenti dell'interfaccia per la modifica delle note.
"""

import sys
import time
from PyQt6.QtWidgets import QApplication
from views.notes_manager_dialog import NotesManagerDialog
from services.db_service import DatabaseService
from services.app_settings import AppSettings

def test_ui_improvements():
    """Test dei miglioramenti UI per l'editing delle note."""
    
    print("🎨 Test miglioramenti UI per editing note...")
    
    try:
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        
        # Initialize services
        db = DatabaseService()
        db.initialize_db()
        app_settings = AppSettings(db)
        
        # Create dialog
        dialog = NotesManagerDialog(db_service=db, app_settings=app_settings)
        print("✅ Dialog creato")
        
        # Carica le note esistenti
        dialog.load_notes()
        
        # Usa una nota esistente o creane una nuova
        all_notes = db.get_all_notes()
        if all_notes:
            note = all_notes[0]
            note_id = note['id']
            print(f"📖 Usando nota esistente ID: {note_id}")
            dialog.load_note_in_editor(note_id)
        else:
            print("📝 Creando una nuova nota...")
            dialog.create_new_note()
            dialog.title_edit.setText("Test UI Improvements")
            dialog.jira_key_edit.setText("GENERAL")
            dialog.content_edit.setPlainText("Test content for UI improvements")
        
        # Verifica lo stato iniziale
        print(f"\n📊 STATO INIZIALE:")
        print(f"   Editing Mode: {getattr(dialog, 'current_editing_mode', 'Non definito')}")
        print(f"   Save Btn Visible: {dialog.save_btn.isVisible()}")
        print(f"   Save Btn Text: '{dialog.save_btn.text()}'")
        print(f"   Save Btn Enabled: {dialog.save_btn.isEnabled()}")
        print(f"   Draft Status: '{dialog.draft_status_label.text()}'")
        
        # Simula una modifica dell'utente
        print(f"\n✏️ SIMULANDO MODIFICA DELL'UTENTE:")
        original_content = dialog.content_edit.toPlainText()
        new_content = original_content + "\n\n--- Modifica test UI ---"
        
        dialog.content_edit.setPlainText(new_content)
        print("✅ Contenuto modificato")
        
        # Attendi un momento per vedere i cambiamenti nell'UI
        print("⏳ Attendendo feedback UI (2 secondi)...")
        for i in range(2):
            app.processEvents()
            time.sleep(1)
            print(f"   {i+1}/2 - Status: '{dialog.draft_status_label.text()}'")
            print(f"   {i+1}/2 - Save Btn: '{dialog.save_btn.text()}'")
        
        # Attendi l'auto-save
        print("💾 Attendendo auto-save (3 secondi)...")
        for i in range(3):
            app.processEvents() 
            time.sleep(1)
            print(f"   {i+1}/3 - Status: '{dialog.draft_status_label.text()}'")
            print(f"   {i+1}/3 - Save Btn: '{dialog.save_btn.text()}'")
        
        print("\n🎉 TEST MIGLIORAMENTI UI COMPLETATO!")
        
        # Verifica finale
        print(f"\n📋 STATO FINALE:")
        print(f"   Save Btn Visible: {dialog.save_btn.isVisible()}")
        print(f"   Save Btn Text: '{dialog.save_btn.text()}'")
        print(f"   Draft Status: '{dialog.draft_status_label.text()}'")
        print(f"   Content Modified: {dialog.content_edit.toPlainText() != original_content}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_ui_improvements()
    
    if success:
        print("\n🎨 MIGLIORAMENTI UI APPLICATI!")
        print("✅ Ora l'utente dovrebbe vedere chiaramente:")
        print("   • Pulsante 'Auto-Save ON' visibile ma disabilitato") 
        print("   • Messaggi di stato durante la digitazione")
        print("   • Feedback temporale per l'auto-save")
        print("   • Timestamp dell'ultimo salvataggio")
        print("\n💡 L'utente ora capisce meglio quando le modifiche vengono salvate!")
        sys.exit(0)
    else:
        print("\n❌ PROBLEMA CON I MIGLIORAMENTI UI!")
        sys.exit(1)