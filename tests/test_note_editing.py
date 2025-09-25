#!/usr/bin/env python3
"""
Test per verificare la possibilità di modificare note esistenti.
"""

import sys
from PyQt6.QtWidgets import QApplication
from views.notes_manager_dialog import NotesManagerDialog
from services.db_service import DatabaseService
from services.app_settings import AppSettings

def test_note_editing():
    """Test che le note esistenti possano essere modificate."""
    
    print("🔧 Test modifica note esistenti...")
    
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
        print("📋 Note caricate")
        
        # Verifica se ci sono note nel database
        all_notes = db.get_all_notes()
        print(f"📊 Trovate {len(all_notes)} note nel database")
        
        if not all_notes:
            # Crea una nota di test committata
            print("🆕 Creando una nota di test...")
            
            # Crea una nuova nota
            dialog.create_new_note()
            dialog.title_edit.setText("Test Note for Editing")
            dialog.jira_key_edit.setText("TEST-EDIT-001")
            dialog.content_edit.setPlainText("Contenuto originale della nota")
            dialog.tags_edit.setText("test,editing")
            
            # Salva come bozza
            note_id = dialog.save_note()
            print(f"✅ Nota bozza creata con ID: {note_id}")
            
            # Committa la nota
            if dialog.current_note_state and hasattr(dialog, 'commit_btn'):
                dialog.commit_note()
                print("✅ Nota committata")
            
            # Ricarica per aggiornare lo stato
            dialog.load_notes()
            
        else:
            # Usa la prima nota disponibile
            first_note = all_notes[0]
            note_id = first_note['id']
            print(f"🎯 Usando nota esistente ID: {note_id}")
        
        # Cerca di caricare e modificare una nota esistente
        if len(all_notes) > 0:
            first_note = all_notes[0]
            note_id = first_note['id']
            
            print(f"📖 Caricando nota ID {note_id}...")
            dialog.load_note_in_editor(note_id)
            
            print(f"🎛️ Stato modalità corrente: {getattr(dialog, 'current_editing_mode', 'Non definito')}")
            
            # Verifica lo stato dei campi di input
            content_readonly = dialog.content_edit.isReadOnly()
            title_readonly = dialog.title_edit.isReadOnly()
            jira_readonly = dialog.jira_key_edit.isReadOnly()
            
            print(f"📝 Content ReadOnly: {content_readonly}")
            print(f"🏷️ Title ReadOnly: {title_readonly}")
            print(f"🎫 JIRA Key ReadOnly: {jira_readonly}")
            
            # Verifica il testo del pulsante di salvataggio
            save_btn_text = dialog.save_btn.text()
            save_btn_visible = dialog.save_btn.isVisible()
            
            print(f"💾 Save button text: '{save_btn_text}'")
            print(f"👁️ Save button visible: {save_btn_visible}")
            
            # Se la nota è in committed mode, prova a convertirla in draft
            if content_readonly:
                print("🔄 Nota in committed mode - tentando conversione a draft...")
                
                # Simula click sul pulsante Modifica
                dialog._handle_save_action()
                print("✅ Azione di modifica eseguita")
                
                # Verifica se ora è modificabile
                content_readonly_after = dialog.content_edit.isReadOnly()
                print(f"📝 Content ReadOnly dopo modifica: {content_readonly_after}")
                
                if not content_readonly_after:
                    print("🎉 SUCCESS: La nota è ora modificabile!")
                    
                    # Testa una modifica
                    original_title = dialog.title_edit.text()
                    dialog.title_edit.setText(original_title + " - MODIFIED")
                    print(f"✏️ Titolo modificato da '{original_title}' a '{dialog.title_edit.text()}'")
                    
                    # Testa modifica contenuto
                    original_content = dialog.content_edit.toMarkdown()
                    dialog.content_edit.setPlainText(original_content + "\n\nContenuto aggiunto durante il test!")
                    print("✏️ Contenuto modificato")
                    
                    print("✅ MODIFICA RIUSCITA!")
                    return True
                else:
                    print("❌ ERRORE: La nota è ancora in modalità ReadOnly")
                    return False
            else:
                print("✅ La nota è già modificabile!")
                return True
        
        return False
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_note_editing()
    
    if success:
        print("\n🎉 TEST MODIFICA NOTE: SUCCESSO!")
        print("✅ Le note esistenti possono essere modificate correttamente")
        sys.exit(0)
    else:
        print("\n❌ TEST MODIFICA NOTE: FALLITO!")
        print("🔧 È necessario controllare il sistema di editing delle note")
        sys.exit(1)