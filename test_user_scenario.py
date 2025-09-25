#!/usr/bin/env python3
"""
Test specifico per simulare esattamente la situazione dell'utente.
"""

import sys
import time
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from views.notes_manager_dialog import NotesManagerDialog
from services.db_service import DatabaseService
from services.app_settings import AppSettings

def test_user_scenario():
    """Test che simula esattamente la situazione dell'utente."""
    
    print("🎯 Test scenario utente - modifica note esistenti...")
    
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
        
        # Carica le note
        dialog.load_notes()
        
        # Cerca una nota con JIRA key "GENERAL"
        all_notes = db.get_all_notes()
        general_note = None
        for note in all_notes:
            if note.get('jira_key') == 'GENERAL':
                general_note = note
                break
        
        if not general_note:
            print("📝 Creando una nota GENERAL per il test...")
            # Crea una nota simile a quella dell'utente
            dialog.create_new_note()
            dialog.jira_key_edit.setText('GENERAL')
            dialog.title_edit.setText('Test Note')
            dialog.content_edit.setPlainText('ddddddddc fffffffzzzz')
            
            # Salva la nota
            note_id = dialog.save_note()
            print(f"✅ Nota creata con ID: {note_id}")
            
            # Se disponibile, committa la nota per simulare lo stato dell'utente
            if hasattr(dialog, 'commit_note'):
                try:
                    dialog.commit_note()
                    print("✅ Nota committata")
                except:
                    print("⚠️ Commit non riuscito, nota rimane in draft")
            
            dialog.load_notes()
            general_note = {'id': note_id}
        
        # Carica la nota GENERAL
        note_id = general_note['id']
        print(f"📖 Caricando nota GENERAL ID: {note_id}")
        
        dialog.load_note_in_editor(note_id)
        
        # Stato attuale dettagliato
        print("\n📊 STATO ATTUALE DELLA NOTA:")
        print(f"   ID: {dialog.current_note_id}")
        print(f"   JIRA Key: '{dialog.jira_key_edit.text()}'")
        print(f"   Title: '{dialog.title_edit.text()}'")
        print(f"   Content: '{dialog.content_edit.toPlainText()[:50]}...'")
        print(f"   Tags: '{dialog.tags_edit.text()}'")
        print(f"   Fictitious: {dialog.fictitious_cb.isChecked()}")
        
        print(f"\n🎛️ STATO MODALITÀ EDITING:")
        print(f"   Editing Mode: {getattr(dialog, 'current_editing_mode', 'Non definito')}")
        print(f"   Note State: {dialog.current_note_state.state_name if dialog.current_note_state else 'None'}")
        
        print(f"\n🔒 STATO CAMPI INPUT:")
        print(f"   Content ReadOnly: {dialog.content_edit.isReadOnly()}")
        print(f"   Title ReadOnly: {dialog.title_edit.isReadOnly()}")
        print(f"   JIRA ReadOnly: {dialog.jira_key_edit.isReadOnly()}")
        print(f"   Tags ReadOnly: {dialog.tags_edit.isReadOnly()}")
        
        print(f"\n🎮 STATO BOTTONI:")
        print(f"   Save Btn Visible: {dialog.save_btn.isVisible()}")
        print(f"   Save Btn Text: '{dialog.save_btn.text()}'")
        print(f"   Save Btn Enabled: {dialog.save_btn.isEnabled()}")
        print(f"   Commit Btn Visible: {dialog.commit_btn.isVisible()}")
        print(f"   Commit Btn Text: '{dialog.commit_btn.text()}'")
        print(f"   Delete Btn Visible: {dialog.delete_btn.isVisible()}")
        
        # Test di modifica
        print(f"\n✏️ TENTATIVO DI MODIFICA:")
        
        if dialog.content_edit.isReadOnly():
            print("🔓 Nota in modalità ReadOnly - tentando di sbloccare...")
            
            # Clicca il pulsante per modificare
            dialog._handle_save_action()
            print("✅ Azione modifica eseguita")
            
            # Verifica se ora è modificabile
            if not dialog.content_edit.isReadOnly():
                print("🎉 Nota sbloccata per modifica!")
            else:
                print("❌ Nota ancora bloccata")
        else:
            print("✅ Nota già modificabile")
        
        # Tenta modifica del contenuto
        original_content = dialog.content_edit.toPlainText()
        new_content = original_content + "\n\nTEST MODIFICA - " + str(int(time.time()))
        
        print(f"📝 Modificando contenuto...")
        print(f"   Da: '{original_content[:30]}...'")
        print(f"   A: '{new_content[:30]}...'")
        
        dialog.content_edit.setPlainText(new_content)
        
        # Verifica se il contenuto è cambiato
        current_content = dialog.content_edit.toPlainText()
        if current_content == new_content:
            print("✅ Contenuto modificato con successo!")
            
            # Attendi un po' per l'auto-save
            print("⏳ Attendendo auto-save (3 secondi)...")
            
            # Forza il processamento degli eventi per permettere l'auto-save
            for i in range(3):
                app.processEvents()
                time.sleep(1)
                print(f"   {i+1}/3...")
            
            print("✅ Test di modifica completato!")
            return True
        else:
            print(f"❌ Contenuto non modificato. Attuale: '{current_content[:30]}...'")
            return False
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_user_scenario()
    
    if success:
        print("\n🎉 DIAGNOSI: Le note POSSONO essere modificate!")
        print("💡 Possibili cause del problema dell'utente:")
        print("   1. Auto-save nascosto - l'utente non vede quando salva")
        print("   2. Note in modalità ReadOnly - bisogna cliccare 'Modifica'")
        print("   3. Feedback visivo insufficiente")
        print("\n🔧 SOLUZIONI CONSIGLIATE:")
        print("   • Verificare se il pulsante 'Modifica' è visibile")
        print("   • Aggiungere indicatori visivi per l'auto-save")
        print("   • Mostrare lo stato della nota più chiaramente")
    else:
        print("\n❌ PROBLEMA CONFERMATO!")
        print("🔧 È necessario identificare e correggere il bug")
        
    sys.exit(0 if success else 1)