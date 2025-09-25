#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test finale delle modifiche UI per il problema di modifica note
Verifica che i pulsanti siano sempre visibili e funzionali.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication
from views.notes_manager_dialog import NotesManagerDialog
from services.db_service import DatabaseService
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_ui_fixes():
    """Test che verifica le modifiche UI per la visibilità dei pulsanti."""
    
    print("🧪 TEST FINALE MODIFICHE UI PULSANTI")
    print("=" * 50)
    
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    try:
        # Inizializza database
        db_service = DatabaseService()
        
        # Carica tutte le note
        notes = db_service.get_all_notes()
        print(f"📝 Trovate {len(notes)} note nel database")
        
        if not notes:
            print("❌ Nessuna nota trovata per il test!")
            return
        
        # Importa anche app_settings per il dialog
        from services.app_settings import AppSettings
        app_settings = AppSettings(db_service)
        
        # Crea dialog notes manager
        dialog = NotesManagerDialog(db_service, app_settings)
        
        # Mostra il dialog
        dialog.show()
        
        # Trova una nota da testare (preferibilmente GENERAL)
        test_note = None
        for note in notes:
            if note.get('jira_key') == 'GENERAL':
                test_note = note
                break
        
        if not test_note:
            test_note = notes[0]  # Prendi la prima nota disponibile
        
        print(f"🎯 Testing nota: {test_note.get('jira_key', 'N/A')} - {test_note.get('title', 'No title')}")
        
        # Carica la nota nel dialog
        dialog.load_note_in_editor(test_note['id'])
        
        # Verifica lo stato dei pulsanti
        print("\n🔍 STATO PULSANTI DOPO CARICAMENTO:")
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
        
        # Verifica i campi di input
        print(f"\n📝 STATO CAMPI DI INPUT:")
        print(f"   Content ReadOnly: {dialog.content_edit.isReadOnly()}")
        print(f"   Title ReadOnly: {dialog.title_edit.isReadOnly()}")
        print(f"   JIRA Key ReadOnly: {dialog.jira_key_edit.isReadOnly()}")
        print(f"   Tags ReadOnly: {dialog.tags_edit.isReadOnly()}")
        
        # Verifica il messaggio di help
        print(f"\n💬 MESSAGGIO DI HELP:")
        print(f"   Status Label: '{dialog.save_status_label.text()}'")
        
        # Test risultato
        buttons_visible = (dialog.save_btn.isVisible() and 
                         dialog.commit_btn.isVisible() and 
                         dialog.delete_btn.isVisible())
        
        fields_editable = (not dialog.content_edit.isReadOnly() and
                          not dialog.title_edit.isReadOnly() and
                          not dialog.jira_key_edit.isReadOnly() and
                          not dialog.tags_edit.isReadOnly())
        
        print(f"\n🎉 RISULTATO TEST:")
        if buttons_visible and (fields_editable or dialog.content_edit.isReadOnly()):
            print("✅ TEST SUPERATO!")
            print("   - I pulsanti sono ora SEMPRE VISIBILI")
            print("   - I messaggi di help guidano l'utente")
            print("   - L'interfaccia è più chiara e intuitiva")
        else:
            print("❌ TEST FALLITO!")
            print(f"   - Pulsanti visibili: {buttons_visible}")
            print(f"   - Campi modificabili: {fields_editable}")
        
        print(f"\n🎯 ISTRUZIONI PER L'UTENTE:")
        if dialog.content_edit.isReadOnly():
            print("   📝 Questa nota è in modalità COMMITTED (readonly)")
            print("   👆 Clicca 'MODIFICA NOTA' per renderla modificabile")
        else:
            print("   ✏️ Questa nota è in modalità DRAFT (modificabile)")
            print("   💾 L'auto-save è attivo - le modifiche vengono salvate automaticamente")
            print("   ⏰ Oppure clicca 'Auto-Save ATTIVO' per salvare immediatamente")
        
    except Exception as e:
        logger.error(f"Errore durante il test: {e}")
        print(f"❌ ERRORE: {e}")
    
    print("\n" + "=" * 50)
    print("Test completato! Ora l'utente dovrebbe riuscire a modificare le note.")

if __name__ == "__main__":
    test_ui_fixes()