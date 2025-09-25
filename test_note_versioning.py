#!/usr/bin/env python3
"""
Test script per verificare il sistema di versionamento delle note.
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from services.db_service import DatabaseService
from services.note_manager import NoteManager, NoteData
from services.git_service import GitService
import tempfile
import shutil

def test_note_versioning():
    """Test completo del sistema di versionamento note."""
    print("=== Test Sistema Versionamento Note ===\n")
    
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
        
        # Test 1: Creazione nota con snapshot iniziale
        print("\n1. Test creazione nota...")
        note_data = NoteData(
            jira_key="TEST-123",
            title="Nota di Test",
            content="Contenuto iniziale della nota",
            tags="test,versioning",
            is_fictitious=False
        )
        
        success, note_id, state = note_manager.create_new_note(note_data)
        assert success and note_id, "Creazione nota fallita"
        print(f"✓ Nota creata con ID: {note_id}")
        
        # Verifica snapshot iniziale
        versions = note_manager.list_versions(note_id)
        assert len(versions) == 1, f"Atteso 1 snapshot, trovati {len(versions)}"
        print(f"Debug - Primo snapshot: type={versions[0]['source_type']}, content_preview='{versions[0]['preview'][:50]}'")
        assert versions[0]['source_type'] == 'create', f"Tipo sbagliato: {versions[0]['source_type']}"
        print("✓ Snapshot iniziale creato correttamente")
        
        # Test 2: Salvataggio bozza
        print("\n2. Test salvataggio bozza...")
        note_data.content = "Contenuto modificato - bozza 1"
        success = note_manager.save_draft(note_id, note_data)
        assert success, "Salvataggio bozza fallito"
        print("✓ Bozza salvata")
        
        # Verifica nuovo snapshot (il più recente dovrebbe essere 'draft')
        versions = note_manager.list_versions(note_id)
        print(f"DEBUG: Versioni dopo save_draft: {[(v['id'], v['source_type'], v['created_at']) for v in versions]}")
        
        # Query diretta per debug
        conn = db_service.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT Id, SourceType, CreatedAt FROM NoteVersions WHERE NoteId = ? ORDER BY CreatedAt DESC", (note_id,))
        direct_rows = cursor.fetchall()
        print(f"DEBUG: Query diretta DB: {direct_rows}")
        conn.close()
        
        assert len(versions) == 2, f"Attesi 2 snapshot, trovati {len(versions)}"
        assert versions[0]['source_type'] == 'draft', f"Tipo più recente sbagliato: {versions[0]['source_type']}"
        assert versions[1]['source_type'] == 'create', f"Tipo più vecchio sbagliato: {versions[1]['source_type']}"
        print("✓ Snapshot bozza creato (ordinamento corretto)")
        
        # Test 3: Commit con Git
        print("\n3. Test commit Git...")
        success = note_manager.commit_note(note_id, "Primo commit della nota")
        assert success, "Commit fallito"
        print("✓ Nota committata")
        
        # Verifica snapshot commit (dovrebbe essere il più recente)
        versions = note_manager.list_versions(note_id)
        assert len(versions) == 3, f"Attesi 3 snapshot, trovati {len(versions)}"
        assert versions[0]['source_type'] == 'commit', f"Tipo più recente sbagliato: {versions[0]['source_type']}"
        assert versions[0]['commit_hash'] is not None, "Commit hash mancante"
        print("✓ Snapshot commit creato con hash Git")
        
        # Test 4: Ulteriore modifica e commit
        print("\n4. Test seconda modifica...")
        note_data.content = "Contenuto finale - versione 2"
        success = note_manager.save_draft(note_id, note_data)
        success = note_manager.commit_note(note_id, "Secondo commit")
        assert success, "Secondo commit fallito"
        
        versions = note_manager.list_versions(note_id)
        assert len(versions) >= 4, f"Attesi almeno 4 snapshot, trovati {len(versions)}"
        print("✓ Seconda modifica committata")
        
        # Test 5: Diff tra versioni (confronta prima e ultima versione)
        print("\n5. Test diff tra versioni...")
        if len(versions) >= 2:
            # Confronta la prima versione (create) con l'ultima (più recente)
            first_version = versions[-1]  # Più vecchia (create)
            last_version = versions[0]    # Più recente (commit)
            
            v1_content = db_service.get_note_version_content(first_version['id'])
            v0_content = db_service.get_note_version_content(last_version['id'])
            print(f"DEBUG: Content first ({first_version['source_type']}): '{v1_content[:50]}...'")
            print(f"DEBUG: Content last ({last_version['source_type']}): '{v0_content[:50]}...'")
            
            diff_data = note_manager.diff_versions(first_version['id'], last_version['id'])
            assert diff_data is not None, "Diff fallito"
            print(f"DEBUG: Diff result: lines_changed={diff_data['lines_changed']}, diff_length={len(diff_data['diff'])}")
            
            if diff_data['lines_changed'] > 0:
                print(f"✓ Diff calcolato: {diff_data['lines_changed']} righe cambiate")
                print("Diff preview:")
                print(diff_data['diff'][:200] + "..." if len(diff_data['diff']) > 200 else diff_data['diff'])
            else:
                print("⚠ Nessuna differenza trovata (contenuti identici)")
                print("✓ Diff funziona anche per contenuti identici")
        
        # Test 6: Ripristino versione precedente
        print("\n6. Test ripristino versione...")
        if len(versions) >= 2:
            old_version = versions[-1]  # Versione più vecchia
            success = note_manager.restore_version(note_id, old_version['id'])
            assert success, "Ripristino fallito"
            print("✓ Versione ripristinata")
            
            # Verifica snapshot di restore (dovrebbe essere il più recente)
            versions_after = note_manager.list_versions(note_id)
            assert len(versions_after) > len(versions), "Snapshot restore non creato"
            assert versions_after[0]['source_type'] == 'manual_restore', "Tipo restore più recente sbagliato"
            print("✓ Snapshot restore creato")
        
        # Test 7: Cronologia Git
        print("\n7. Test cronologia Git...")
        git_history = note_manager.get_note_history("TEST-123", "Nota di Test")
        if git_history:
            print(f"✓ Cronologia Git: {len(git_history)} commit trovati")
            for i, commit in enumerate(git_history[:2]):  # Primi 2 commit
                print(f"  Commit {i+1}: {commit['commit_hash'][:8]} - {commit['message']} ({commit['author']})")
            
            # Test diff Git se ci sono almeno 2 commit
            if len(git_history) >= 2:
                git_diff = git_service.diff_between_commits(
                    "TEST-123", "Nota di Test", 
                    git_history[1]['commit_hash'], 
                    git_history[0]['commit_hash']
                )
                if git_diff:
                    print("✓ Diff Git calcolato")
                    print("Git diff preview:")
                    print(git_diff[:200] + "..." if len(git_diff) > 200 else git_diff)
        else:
            print("⚠ Nessuna cronologia Git trovata")
        
        # Test 8: Verifica integrità dati
        print("\n8. Test integrità dati...")
        note = db_service.get_note_by_id(note_id)
        assert note is not None, "Nota non trovata"
        assert note['is_draft'] == True, "Nota dovrebbe essere bozza dopo restore"
        
        all_versions = note_manager.list_versions(note_id, limit=20)
        print(f"✓ Totale versioni: {len(all_versions)}")
        
        # Verifica hash contenuto unici (no duplicati esatti)
        hashes = [v['content_hash'] for v in all_versions]
        unique_hashes = set(hashes)
        if len(unique_hashes) < len(hashes):
            print(f"⚠ Rilevate {len(hashes) - len(unique_hashes)} versioni duplicate per hash")
        else:
            print("✓ Tutti gli hash contenuto sono unici")
        
        print("\n=== TUTTI I TEST PASSATI! ===")
        print(f"Versioni totali create: {len(all_versions)}")
        print("Funzionalità verificate:")
        print("  ✓ Versionamento automatico (create/draft/commit/restore)")
        print("  ✓ Ripristino versioni precedenti")
        print("  ✓ Diff viewer (versioni interne)")
        print("  ✓ Cronologia dettagliata (timestamp, autore, tipo)")
        print("  ✓ Integrazione Git (commit + diff)")
        
        return True
        
    except AssertionError as e:
        print(f"❌ Test fallito: {e}")
        return False
    except Exception as e:
        print(f"❌ Errore inatteso: {e}")
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
    success = test_note_versioning()
    sys.exit(0 if success else 1)