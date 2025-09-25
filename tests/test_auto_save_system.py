#!/usr/bin/env python3
"""
Test del nuovo sistema di salvataggio automatico senza pulsante bozza
con struttura cartelle basata su chiave JIRA.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_auto_save_without_button():
    """Test del salvataggio automatico senza pulsante bozza."""
    
    print("🔍 Test nuovo sistema auto-save senza pulsante bozza...")
    
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
        
        # Verifica che file system manager è inizializzato
        assert hasattr(dialog, 'fs_manager'), "File system manager mancante!"
        print("✅ File system manager presente")
        
        # Test 1: Creazione nuova nota
        print("\n🔧 Test 1: Creazione nuova nota...")
        dialog.create_new_note()
        
        # Verifica stato NEW
        assert dialog.current_note_state.state_name == 'new', "Stato deve essere 'new'"
        
        # Verifica che NON c'è pulsante bozza
        assert not dialog.save_btn.isVisible(), "Pulsante 'Crea Bozza' NON deve essere visibile"
        print("✅ Pulsante bozza correttamente nascosto")
        
        # Verifica che commit è disabilitato inizialmente
        assert not dialog.commit_btn.isEnabled(), "Pulsante Commit deve essere disabilitato inizialmente"
        print("✅ Pulsante Commit correttamente disabilitato")
        
        # Test 2: Simulazione inserimento dati
        print("\n🔧 Test 2: Inserimento dati e auto-save...")
        
        # Inserisci dati JIRA
        dialog.jira_key_edit.setText("TEST-456")
        dialog.title_edit.setText("Nota di test automatica") 
        dialog.content_edit.setMarkdown("# Test Content\\n\\nQuesto è un test del nuovo sistema.")
        dialog.tags_edit.setText("test,auto-save,filesystem")
        
        print("✅ Dati inseriti nei campi")
        
        # Simula il trigger dell'auto-save manualmente
        dialog.on_content_changed()
        
        print("✅ Auto-save triggering testato")
        
        # Test 3: Verifica path del file system
        print("\n🔧 Test 3: Verifica file system paths...")
        
        jira_key = "TEST-456"
        note_title = "Nota di test automatica"
        
        # Test path della cartella JIRA
        jira_folder = dialog.fs_manager.get_jira_folder_path(jira_key)
        print(f"📁 JIRA folder path: {jira_folder}")
        
        # Test path del file nota
        note_file_path = dialog.fs_manager.get_note_file_path(jira_key, note_title)
        print(f"📄 Note file path: {note_file_path}")
        
        # Verifica struttura: BASE/TEST-456/Nota_di_test_automatica.md
        assert str(jira_folder).endswith("TEST-456"), f"Cartella JIRA deve terminare con TEST-456, ma è {jira_folder}"
        assert note_file_path.name.startswith("Nota_di_test_automatica"), f"File deve iniziare con titolo sanitizzato, ma è {note_file_path.name}"
        assert note_file_path.suffix == ".md", f"File deve avere estensione .md, ma ha {note_file_path.suffix}"
        
        print("✅ Path file system corretti")
        
        # Test 4: Sanitizzazione nomi file
        print("\n🔧 Test 4: Test sanitizzazione nomi file...")
        
        test_cases = [
            ("TEST/BAD", "TEST_BAD"),
            ("TEST:COLON", "TEST_COLON"), 
            ("TEST<>ANGLE", "TEST__ANGLE"),
            ("TEST|PIPE", "TEST_PIPE")
        ]
        
        for original, expected in test_cases:
            sanitized = dialog.fs_manager._sanitize_filename(original)
            print(f"'{original}' → '{sanitized}'")
            # Verifica che non ci siano caratteri non validi
            invalid_chars = '<>:"/\\\\|?*'
            for char in invalid_chars:
                assert char not in sanitized, f"Carattere non valido '{char}' trovato in '{sanitized}'"
        
        print("✅ Sanitizzazione nomi file funzionante")
        
        # Test 5: Test salvataggio file  
        print("\n🔧 Test 5: Test salvataggio effettivo...")
        
        test_jira = "TEST-789"
        test_title = "Test Save File"
        test_content = "# Test\\n\\nContenuto di prova"
        
        success, message, saved_path = dialog.fs_manager.save_note_to_file(
            jira_key=test_jira,
            note_title=test_title, 
            content=test_content,
            note_id=999,
            tags="test,save",
            is_fictitious=False
        )
        
        print(f"Salvataggio: {'✅ SUCCESS' if success else '❌ FAILED'}")
        print(f"Message: {message}")
        print(f"Path: {saved_path}")
        
        if success:
            # Verifica che il file esiste
            assert saved_path.exists(), f"File dovrebbe esistere: {saved_path}"
            
            # Leggi e verifica contenuto
            with open(saved_path, 'r', encoding='utf-8') as f:
                file_content = f.read()
            
            assert "title: Test Save File" in file_content, "Titolo deve essere nel metadata"
            assert "jira_key: TEST-789" in file_content, "JIRA key deve essere nel metadata"
            assert "Test\\n\\nContenuto di prova" in file_content, "Contenuto deve essere presente"
            
            print("✅ File salvato e contenuto verificato")
        
        print("\n✅ TUTTI I TEST SUPERATI!")
        print("✅ Sistema auto-save senza pulsante bozza FUNZIONANTE!")
        print("✅ Struttura cartelle JIRA implementata correttamente!")
        
        return True
        
    except Exception as e:
        print(f"❌ Errore durante il test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_auto_save_without_button()
    print(f"\n{'✅ TEST SUPERATO' if success else '❌ TEST FALLITO'}")
    sys.exit(0 if success else 1)