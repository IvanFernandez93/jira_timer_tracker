#!/usr/bin/env python3
"""
Test per verificare che la gestione delle modifiche esterne funzioni correttamente
con il parsing dei metadati YAML.
"""

import sys
import tempfile
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from views.notes_manager_dialog import NotesManagerDialog
from services.db_service import DatabaseService
from services.app_settings import AppSettings
from services.notes_filesystem_manager import NotesFileSystemManager

def test_external_change_parsing():
    """Test per verificare il corretto parsing delle modifiche esterne."""
    
    print("🔍 Test parsing modifiche esterne...")
    
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
        
        # Test del parsing di un file con metadati duplicati (come nel tuo caso)
        test_content = """---
title: dd
jira_key: ddd
created: 2025-09-25T14:31:44.268625
updated: 2025-09-25T14:31:44.268625
note_id: 169
fictitious: true
---
---
title: dd
jira_key: ddd
created: 2025-09-25T14:31:23.329266
updated: 2025-09-25T14:31:23.329266
note_id: 169
fictitious: true
---
zsddddlll"""

        # Test del parser
        parsed_data = dialog.fs_manager._parse_markdown_metadata(test_content)
        
        print("📋 Dati parsati:")
        for key, value in parsed_data.items():
            print(f"   {key}: {value}")
        
        # Verifica che il contenuto sia corretto (senza metadati YAML)
        expected_content = """---
title: dd
jira_key: ddd
created: 2025-09-25T14:31:23.329266
updated: 2025-09-25T14:31:23.329266
note_id: 169
fictitious: true
---
zsddddlll"""
        
        actual_content = parsed_data.get('content', '')
        
        print(f"\n📝 Contenuto atteso (lunghezza {len(expected_content)}):")
        print(f"'{expected_content[:100]}...'")
        
        print(f"\n📝 Contenuto ottenuto (lunghezza {len(actual_content)}):")
        print(f"'{actual_content[:100]}...'")
        
        # Verifica che i metadati del primo blocco YAML siano estratti
        assert parsed_data.get('title') == 'dd', f"Title wrong: {parsed_data.get('title')}"
        assert parsed_data.get('jira_key') == 'ddd', f"JIRA key wrong: {parsed_data.get('jira_key')}"
        assert parsed_data.get('fictitious') == True, f"Fictitious wrong: {parsed_data.get('fictitious')}"
        
        # Verifica che il contenuto non contenga il primo blocco YAML
        assert not actual_content.startswith('---\ntitle: dd\njira_key: ddd'), "Content still contains first YAML block!"
        
        # Verifica che contenga 'zsddddlll'
        assert 'zsddddlll' in actual_content, "Content doesn't contain expected text!"
        
        print("✅ Parsing corretto!")
        print("✅ Metadati estratti correttamente dal primo blocco YAML")
        print("✅ Contenuto pulito dal primo blocco YAML")
        print("✅ Test completato con successo!")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_simple_parsing():
    """Test con un file semplice."""
    
    print("\n🔍 Test parsing semplice...")
    
    try:
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        
        # Initialize services
        db = DatabaseService()
        db.initialize_db()
        app_settings = AppSettings(db)
        
        # Create filesystem manager directly
        fs_manager = NotesFileSystemManager()
        
        # Test con contenuto semplice
        simple_content = """---
title: Test Note
jira_key: TEST-123
fictitious: false
tags: test, example
---
Questo è il contenuto della nota.

Con più righe.
"""
        
        parsed = fs_manager._parse_markdown_metadata(simple_content)
        
        print("📋 Dati parsati (semplice):")
        for key, value in parsed.items():
            print(f"   {key}: {value}")
        
        assert parsed.get('title') == 'Test Note'
        assert parsed.get('jira_key') == 'TEST-123'
        assert parsed.get('fictitious') == False
        assert parsed.get('tags') == 'test, example'
        assert 'Questo è il contenuto' in parsed.get('content', '')
        
        print("✅ Parsing semplice funziona!")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success1 = test_external_change_parsing()
    success2 = test_simple_parsing()
    
    if success1 and success2:
        print("\n🎉 TUTTI I TEST PASSATI!")
        print("🔧 La correzione per le modifiche esterne è pronta!")
        sys.exit(0)
    else:
        print("\n💥 ALCUNI TEST FALLITI!")
        sys.exit(1)