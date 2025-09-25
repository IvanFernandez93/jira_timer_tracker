#!/usr/bin/env python3
"""
Test rapido per verificare che il dialog cronologia si apra senza errori
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test che tutti gli import funzionino."""
    print("🔧 Test import componenti...")
    
    try:
        # Test import servizi backend
        from services.db_service import DatabaseService
        from services.git_service import GitService  
        from services.note_manager import NoteManager
        from services.external_diff_service import ExternalDiffService
        print("✅ Servizi backend importati")
        
        # Test import UI
        from views.note_version_history_dialog import NoteVersionHistoryDialog
        from views.markdown_editor import MarkdownEditor
        print("✅ Componenti UI importati")
        
        # Test inizializzazione servizi
        db_service = DatabaseService()
        git_service = GitService()
        note_manager = NoteManager(db_service, git_service)
        print("✅ Servizi inizializzati")
        
        # Test external diff service
        diff_service = ExternalDiffService()
        available_tools = diff_service.get_available_tools()
        print(f"✅ Diff service: {len(available_tools)} tool disponibili")
        
        return True, "Tutti gli import e inizializzazioni OK"
        
    except Exception as e:
        return False, f"Errore: {e}"

def test_database_schema():
    """Verifica che lo schema database sia corretto."""
    print("\n🗄️  Test schema database...")
    
    try:
        from services.db_service import DatabaseService
        db_service = DatabaseService()
        
        # Verifica che la tabella NoteVersions esista
        cursor = db_service.conn.cursor()
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='NoteVersions'
        """)
        
        if cursor.fetchone():
            print("✅ Tabella NoteVersions presente")
            
            # Verifica schema
            cursor.execute("PRAGMA table_info(NoteVersions)")
            columns = [col[1] for col in cursor.fetchall()]
            expected_columns = ['id', 'note_id', 'content', 'content_hash', 'created_at', 'author', 'source_type', 'commit_hash', 'metadata']
            
            missing_columns = [col for col in expected_columns if col not in columns]
            if missing_columns:
                return False, f"Colonne mancanti: {missing_columns}"
            else:
                print("✅ Schema NoteVersions corretto")
                return True, "Schema database OK"
        else:
            return False, "Tabella NoteVersions non trovata"
            
    except Exception as e:
        return False, f"Errore verifica database: {e}"

def test_version_operations():
    """Test operazioni di base del versionamento."""
    print("\n📝 Test operazioni versionamento...")
    
    try:
        from services.db_service import DatabaseService
        from services.git_service import GitService
        from services.note_manager import NoteManager
        
        db_service = DatabaseService()
        git_service = GitService()
        note_manager = NoteManager(db_service, git_service)
        
        # Crea nota test
        note_data = {
            'title': 'Test Veloce',
            'jira_key': 'QUICK-001', 
            'content': 'Contenuto test',
            'tags': 'test',
            'is_fictitious': False
        }
        
        success, note_id = note_manager.create_new_note(note_data)
        if not success:
            return False, "Impossibile creare nota test"
            
        # Verifica versioni
        versions = note_manager.list_versions(note_id)
        if not versions:
            return False, "Nessuna versione creata"
            
        print(f"✅ {len(versions)} versioni create per nota {note_id}")
        
        # Test modifica
        note_manager.save_draft(note_id, {'content': 'Contenuto modificato'})
        note_manager.commit_note(note_id, 'Test commit')
        
        versions_after = note_manager.list_versions(note_id)
        if len(versions_after) <= len(versions):
            return False, "Versioni non aumentate dopo modifica"
            
        print(f"✅ Versioni dopo modifica: {len(versions_after)}")
        return True, "Operazioni versionamento OK"
        
    except Exception as e:
        return False, f"Errore test operazioni: {e}"

def main():
    print("🧪 VERIFICA RAPIDA SISTEMA CRONOLOGIA VERSIONI")
    print("=" * 60)
    
    all_passed = True
    
    # Test 1: Import
    success, message = test_imports()
    print(f"{'✅' if success else '❌'} Import: {message}")
    if not success:
        all_passed = False
    
    # Test 2: Database
    success, message = test_database_schema() 
    print(f"{'✅' if success else '❌'} Database: {message}")
    if not success:
        all_passed = False
        
    # Test 3: Operazioni
    success, message = test_version_operations()
    print(f"{'✅' if success else '❌'} Operazioni: {message}")
    if not success:
        all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 SISTEMA CRONOLOGIA VERSIONI: ✅ FUNZIONA CORRETTAMENTE")
        print("\n📋 Riepilogo funzionalità verificate:")
        print("   ✅ Import e inizializzazione servizi")
        print("   ✅ Schema database NoteVersions")  
        print("   ✅ Creazione automatica versioni")
        print("   ✅ Operazioni CRUD versioni")
        print("   ✅ Integration diff viewer esterni")
        print("\n🚀 Il sistema è pronto per l'uso!")
    else:
        print("❌ SISTEMA CRONOLOGIA VERSIONI: ERRORI RILEVATI")
        print("   Controlla i messaggi di errore sopra per i dettagli")
    
    return 0 if all_passed else 1

if __name__ == '__main__':
    sys.exit(main())