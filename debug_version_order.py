#!/usr/bin/env python3
"""
Test debug per verificare l'ordine dei timestamp nelle versioni.
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from services.db_service import DatabaseService
from services.note_manager import NoteManager, NoteData
from services.git_service import GitService
import tempfile
import shutil
import time

def debug_version_order():
    """Debug dell'ordinamento delle versioni."""
    print("=== Debug Ordinamento Versioni ===\n")
    
    # Setup temporaneo
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test.db")
    git_path = os.path.join(temp_dir, "git_repo")
    
    try:
        # Inizializza servizi
        db_service = DatabaseService(db_name=os.path.basename(db_path))
        db_service.db_path = db_path
        db_service.initialize_db()
        
        git_service = GitService(repo_path=git_path)
        note_manager = NoteManager(db_service, git_service)
        
        print("✓ Servizi inizializzati")
        
        # Crea nota
        note_data = NoteData(
            jira_key="TEST-123",
            title="Nota di Test",
            content="Contenuto iniziale",
            tags="test",
            is_fictitious=False
        )
        
        success, note_id, state = note_manager.create_new_note(note_data)
        print(f"✓ Nota creata con ID: {note_id}")
        
        # Attendi un po' per differenziare i timestamp
        time.sleep(0.1)
        
        # Modifica come bozza
        note_data.content = "Contenuto modificato"
        success = note_manager.save_draft(note_id, note_data)
        print("✓ Bozza salvata")
        
        # Verifica ordine versioni
        versions = note_manager.list_versions(note_id)
        print(f"\nVersioni trovate: {len(versions)}")
        for i, v in enumerate(versions):
            print(f"  [{i}] ID:{v['id']}, Type:{v['source_type']}, Created:{v['created_at']}, Preview:'{v['preview'][:30]}'")
        
        # Query diretta sul database per verificare
        conn = db_service.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT Id, SourceType, CreatedAt, substr(Content,1,50) 
            FROM NoteVersions 
            WHERE NoteId = ? 
            ORDER BY CreatedAt DESC
        """, (note_id,))
        rows = cursor.fetchall()
        
        print("\nQuery diretta (ORDER BY CreatedAt DESC):")
        for i, row in enumerate(rows):
            print(f"  [{i}] ID:{row[0]}, Type:{row[1]}, Created:{row[2]}, Content:'{row[3]}'")
        
        conn.close()
        
        # Verifica se il più recente è effettivamente primo
        if len(versions) >= 2:
            v0_time = versions[0]['created_at']
            v1_time = versions[1]['created_at']
            print(f"\nConfronto timestamp:")
            print(f"  versions[0]: {v0_time} ({versions[0]['source_type']})")
            print(f"  versions[1]: {v1_time} ({versions[1]['source_type']})")
            
            if v0_time > v1_time:
                print("✓ Ordine corretto: il primo è più recente")
            else:
                print("❌ Ordine sbagliato: il primo è più vecchio")
                
        return True
        
    except Exception as e:
        print(f"❌ Errore: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Cleanup
        try:
            shutil.rmtree(temp_dir)
        except:
            pass

if __name__ == "__main__":
    debug_version_order()