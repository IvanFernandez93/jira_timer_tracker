#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test per verificare la rimozione delle icone duplicate nei pulsanti
Controlla che non ci siano emoji nel testo quando i pulsanti hanno già icone.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication
from views.notes_manager_dialog import NotesManagerDialog
from services.db_service import DatabaseService
from services.app_settings import AppSettings
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_no_duplicate_icons():
    """Test che verifica l'assenza di icone duplicate nei pulsanti."""
    
    print("🧪 TEST RIMOZIONE ICONE DUPLICATE")
    print("=" * 40)
    
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    try:
        # Inizializza servizi
        db_service = DatabaseService()
        app_settings = AppSettings(db_service)
        
        # Crea dialog
        dialog = NotesManagerDialog(db_service, app_settings)
        
        # Carica una nota di test
        notes = db_service.get_all_notes()
        if not notes:
            print("❌ Nessuna nota per il test!")
            return
            
        test_note = notes[0]
        dialog.load_note_in_editor(test_note['id'])
        
        print(f"🎯 Testing nota: {test_note.get('jira_key', 'N/A')}")
        print(f"   Stato editing mode: {getattr(dialog, 'current_editing_mode', 'N/A')}")
        
        # Verifica i testi dei pulsanti non abbiano emoji duplicate
        save_text = dialog.save_btn.text()
        commit_text = dialog.commit_btn.text()
        delete_text = dialog.delete_btn.text()
        
        print(f"\n📝 TESTI PULSANTI (senza emoji):")
        print(f"   Save Button: '{save_text}'")
        print(f"   Commit Button: '{commit_text}'")
        print(f"   Delete Button: '{delete_text}'")
        
        # Controlla che non ci siano emoji nei testi
        emoji_patterns = ["💾", "✏️", "✅", "📊", "🔄"]
        
        issues_found = []
        for emoji in emoji_patterns:
            if emoji in save_text:
                issues_found.append(f"Save button ha emoji '{emoji}': '{save_text}'")
            if emoji in commit_text:
                issues_found.append(f"Commit button ha emoji '{emoji}': '{commit_text}'")
            if emoji in delete_text:
                issues_found.append(f"Delete button ha emoji '{emoji}': '{delete_text}'")
        
        # Verifica che i pulsanti abbiano le icone impostate
        save_icon = dialog.save_btn.icon()
        commit_icon = dialog.commit_btn.icon()
        delete_icon = dialog.delete_btn.icon()
        
        has_icons = not save_icon.isNull() and not commit_icon.isNull() and not delete_icon.isNull()
        
        print(f"\n🎨 ICONE PULSANTI:")
        print(f"   Save Button ha icona: {not save_icon.isNull()}")
        print(f"   Commit Button ha icona: {not commit_icon.isNull()}")
        print(f"   Delete Button ha icona: {not delete_icon.isNull()}")
        
        # Test modalità committed per vedere se cambia
        if hasattr(dialog, '_set_note_editing_mode'):
            dialog._set_note_editing_mode('committed')
            
            save_text_committed = dialog.save_btn.text()
            commit_text_committed = dialog.commit_btn.text()
            
            print(f"\n📝 TESTI IN MODALITÀ COMMITTED:")
            print(f"   Save Button: '{save_text_committed}'")
            print(f"   Commit Button: '{commit_text_committed}'")
            
            # Controlla emoji anche in modalità committed
            for emoji in emoji_patterns:
                if emoji in save_text_committed:
                    issues_found.append(f"Save button (committed) ha emoji '{emoji}': '{save_text_committed}'")
                if emoji in commit_text_committed:
                    issues_found.append(f"Commit button (committed) ha emoji '{emoji}': '{commit_text_committed}'")
        
        # Risultato test
        print(f"\n🎉 RISULTATO TEST:")
        if not issues_found and has_icons:
            print("✅ TEST SUPERATO!")
            print("   - Nessuna emoji duplicata nei testi")
            print("   - I pulsanti hanno le icone corrette")
            print("   - L'interfaccia è pulita e non confusa")
        else:
            print("❌ TEST FALLITO!")
            if issues_found:
                print("   Problemi trovati:")
                for issue in issues_found:
                    print(f"     - {issue}")
            if not has_icons:
                print("   - Alcuni pulsanti non hanno icone")
        
        print(f"\n💡 INFO:")
        print("   Ora i pulsanti dovrebbero avere solo le icone di FluentUI")
        print("   senza emoji duplicate nel testo che confondono l'utente.")
        
    except Exception as e:
        logger.error(f"Errore durante il test: {e}")
        print(f"❌ ERRORE: {e}")
    
    print("=" * 40)

if __name__ == "__main__":
    test_no_duplicate_icons()