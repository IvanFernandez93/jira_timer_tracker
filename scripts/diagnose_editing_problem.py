#!/usr/bin/env python3
"""
Diagnosi specifica per il problema di modifica delle note dell'utente.
"""

import sys
import time
from PyQt6.QtWidgets import QApplication
from views.notes_manager_dialog import NotesManagerDialog
from services.db_service import DatabaseService
from services.app_settings import AppSettings

def diagnose_editing_issue():
    """Diagnosi specifica del problema di editing."""
    
    print("🔍 DIAGNOSI PROBLEMA MODIFICA NOTE")
    print("=" * 50)
    
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
        
        # Trova la nota GENERAL che l'utente stava cercando di modificare
        all_notes = db.get_all_notes()
        general_note = None
        
        print(f"📊 Trovate {len(all_notes)} note nel database")
        
        # Cerca una nota GENERAL
        for note in all_notes:
            if note.get('jira_key') == 'GENERAL':
                general_note = note
                break
        
        if not general_note:
            print("❌ Nessuna nota GENERAL trovata nel database")
            return False
            
        print(f"✅ Trovata nota GENERAL ID: {general_note['id']}")
        
        # Carica la nota nell'editor
        dialog.load_note_in_editor(general_note['id'])
        
        print("\n🔍 ANALISI DETTAGLIATA DELLA NOTA:")
        print(f"   ID: {dialog.current_note_id}")
        print(f"   Titolo: '{dialog.title_edit.text()}'")
        print(f"   JIRA Key: '{dialog.jira_key_edit.text()}'")
        print(f"   Contenuto: '{dialog.content_edit.toPlainText()[:50]}...'")
        print(f"   Tags: '{dialog.tags_edit.text()}'")
        print(f"   Fictitious: {dialog.fictitious_cb.isChecked()}")
        
        print(f"\n🎛️ STATO CONTROLLI UI:")
        print(f"   Editing Mode: {getattr(dialog, 'current_editing_mode', 'NON DEFINITO')}")
        if hasattr(dialog, 'current_note_state') and dialog.current_note_state:
            print(f"   Note State: {dialog.current_note_state.state_name}")
            print(f"   Is Draft: {dialog.current_note_state.is_draft}")
            print(f"   Is Committed: {dialog.current_note_state.is_committed}")
        else:
            print(f"   Note State: NESSUNO STATO!")
        
        print(f"\n🔒 ACCESSIBILITÀ CAMPI:")
        content_readonly = dialog.content_edit.isReadOnly()
        title_readonly = dialog.title_edit.isReadOnly()
        jira_readonly = dialog.jira_key_edit.isReadOnly()
        tags_readonly = dialog.tags_edit.isReadOnly()
        
        print(f"   Content ReadOnly: {content_readonly} {'❌ BLOCCATO' if content_readonly else '✅ MODIFICABILE'}")
        print(f"   Title ReadOnly: {title_readonly} {'❌ BLOCCATO' if title_readonly else '✅ MODIFICABILE'}")
        print(f"   JIRA Key ReadOnly: {jira_readonly} {'❌ BLOCCATO' if jira_readonly else '✅ MODIFICABILE'}")
        print(f"   Tags ReadOnly: {tags_readonly} {'❌ BLOCCATO' if tags_readonly else '✅ MODIFICABILE'}")
        
        print(f"\n🎮 STATO PULSANTI:")
        print(f"   Save Button:")
        print(f"     - Visibile: {dialog.save_btn.isVisible()}")
        print(f"     - Abilitato: {dialog.save_btn.isEnabled()}")
        print(f"     - Testo: '{dialog.save_btn.text()}'")
        print(f"     - Tooltip: '{dialog.save_btn.toolTip()}'")
        
        print(f"   Commit Button:")
        print(f"     - Visibile: {dialog.commit_btn.isVisible()}")
        print(f"     - Abilitato: {dialog.commit_btn.isEnabled()}")
        print(f"     - Testo: '{dialog.commit_btn.text()}'")
        
        print(f"   Delete Button:")
        print(f"     - Visibile: {dialog.delete_btn.isVisible()}")
        print(f"     - Abilitato: {dialog.delete_btn.isEnabled()}")
        
        print(f"\n📝 LABEL DI STATO:")
        print(f"   Draft Status: '{dialog.draft_status_label.text()}'")
        
        # DIAGNOSI DEL PROBLEMA
        print(f"\n🏥 DIAGNOSI:")
        
        if content_readonly:
            print("🚨 PROBLEMA IDENTIFICATO: I campi sono in modalità ReadOnly!")
            print("💡 POSSIBILI CAUSE:")
            print("   1. La nota è in modalità 'committed' (readonly)")
            print("   2. Serve cliccare 'Modifica' per sbloccare l'editing")
            print("   3. Problema con il sistema di gestione degli stati")
            
            print("\n🔧 TENTATIVO DI RISOLUZIONE:")
            if dialog.save_btn.isVisible() and "Modifica" in dialog.save_btn.text():
                print("   Trovato pulsante 'Modifica' - simulando click...")
                dialog._handle_save_action()
                
                # Verifica se ora è modificabile
                time.sleep(0.5)
                if not dialog.content_edit.isReadOnly():
                    print("   ✅ RISOLTO! La nota è ora modificabile!")
                    return True
                else:
                    print("   ❌ FALLITO! La nota è ancora bloccata")
            else:
                print("   ❌ Pulsante 'Modifica' non trovato o non visibile")
                
        else:
            print("✅ I campi SONO modificabili!")
            print("💡 Il problema potrebbe essere:")
            print("   1. Auto-save non visibile all'utente")
            print("   2. Problemi con il feedback visivo")
            print("   3. L'utente non si accorge che le modifiche vengono salvate")
            
            # Test di modifica
            print("\n🧪 TEST DI MODIFICA:")
            original_content = dialog.content_edit.toPlainText()
            test_content = original_content + "\n\n--- TEST MODIFICA ---"
            
            dialog.content_edit.setPlainText(test_content)
            print(f"   Contenuto modificato: {dialog.content_edit.toPlainText() != original_content}")
            
            # Attendi auto-save
            print("   Attendendo auto-save (3 secondi)...")
            for i in range(3):
                app.processEvents()
                time.sleep(1)
                print(f"     Status: '{dialog.draft_status_label.text()}'")
            
            return True
            
        return False
        
    except Exception as e:
        print(f"❌ ERRORE DURANTE DIAGNOSI: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🩺 AVVIO DIAGNOSI PROBLEMA MODIFICA NOTE...")
    success = diagnose_editing_issue()
    
    if success:
        print("\n✅ DIAGNOSI COMPLETATA!")
        print("🔧 Controlla i risultati sopra per capire il problema specifico.")
    else:
        print("\n❌ DIAGNOSI FALLITA!")
        print("🔧 Potrebbe essere necessaria un'analisi più approfondita.")
        
    print("\n" + "=" * 50)
    sys.exit(0)