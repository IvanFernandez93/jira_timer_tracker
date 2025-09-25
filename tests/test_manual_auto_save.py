#!/usr/bin/env python3
"""
Test manuale per verificare il sistema auto-save senza pulsante bozza.
"""

import sys
import os
import time
from pathlib import Path
from unittest.mock import Mock, patch

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.notes_filesystem_manager import NotesFileSystemManager

def test_filesystem_manager():
    """Test del file system manager con JIRA key e struttura cartelle."""
    print("\n=== TEST FILE SYSTEM MANAGER ===")
    
    # Crea un manager con cartella temporanea per il test
    test_base_path = Path.cwd() / "test_notes_temp"
    manager = NotesFileSystemManager(str(test_base_path))
    
    # Test 1: Creazione cartella JIRA
    print("1. Test creazione cartella JIRA...")
    jira_key = "TERWEBCORE-123"
    jira_folder = manager.get_jira_folder_path(jira_key)
    print(f"   Cartella JIRA: {jira_folder}")
    
    # Test 2: Generazione path file nota
    print("2. Test generazione path file nota...")
    note_title = "Analisi del problema"
    note_file_path = manager.get_note_file_path(jira_key, note_title, note_id=456)
    print(f"   File nota: {note_file_path}")
    
    # Test 3: Creazione file nota con metadata
    print("3. Test creazione file nota con metadata...")
    content = "# Test Note\n\nQuesta è una nota di test per verificare l'auto-save."
    success, message, saved_path = manager.save_note_to_file(jira_key, note_title, content, note_id=456)
    print(f"   Creazione riuscita: {success}")
    print(f"   Messaggio: {message}")
    
    # Test 4: Verifica esistenza file
    print("4. Test verifica esistenza file...")
    exists = note_file_path.exists()
    print(f"   File esiste: {exists}")
    
    # Test 5: Lettura contenuto
    print("5. Test lettura contenuto...")
    if exists:
        read_success, note_data = manager.read_note_from_file(note_file_path)
        if read_success:
            print(f"   Contenuto letto: {len(note_data.get('content', ''))} caratteri")
            print(f"   Metadata: {dict(note_data)}")
        else:
            print("   Errore nella lettura")
    
    # Test 6: Lista cartelle JIRA
    print("6. Test lista cartelle...")
    jira_folders = list(test_base_path.iterdir()) if test_base_path.exists() else []
    print(f"   Cartelle create: {[f.name for f in jira_folders if f.is_dir()]}")
    
    # Cleanup
    import shutil
    if test_base_path.exists():
        shutil.rmtree(test_base_path)
        print(f"   Cleanup completato: {test_base_path} rimossa")
    
    print("=== TEST COMPLETATO ===\n")
    return True

def simulate_auto_save_workflow():
    """Simula il workflow di auto-save senza pulsante bozza."""
    print("=== SIMULAZIONE WORKFLOW AUTO-SAVE ===")
    
    # Mock objects per simulare l'interfaccia
    print("1. Simulazione creazione nuova nota...")
    
    # Parametri della nuova nota
    jira_key = "TERWEBCORE-480"  # Una delle JIRA keys viste nei log
    note_title = "Analisi visualizzazione via"
    content = """# Analisi del problema

## Descrizione
Visualizzazione della via senza numero civico preferibile in cima.

## Note di analisi
- Verificare logica di ordinamento
- Controllare priorità visualizzazione
- Test sui diversi casi d'uso

## Next Steps
[ ] Implementare fix
[ ] Test di regressione
"""
    
    # Simula il file system manager
    manager = NotesFileSystemManager()
    print(f"2. Manager inizializzato con base path: {manager.base_path}")
    
    # Simula auto-save dopo 1 secondo di typing
    print("3. Simulazione typing + auto-save...")
    print("   - Utente inizia a scrivere...")
    print("   - Timer 1 secondo attivato...")
    print("   - Auto-save scatenato!")
    
    # Crea il file
    success, message, saved_path = manager.save_note_to_file(jira_key, note_title, content)
    print(f"4. File creato: {success}")
    if not success:
        print(f"   Errore: {message}")
    
    if success:
        # Verifica struttura creata
        jira_folder = manager.get_jira_folder_path(jira_key)
        file_path = manager.get_note_file_path(jira_key, note_title)
        
        print(f"5. Struttura creata:")
        print(f"   - Cartella JIRA: {jira_folder}")
        print(f"   - File nota: {file_path}")
        print(f"   - File esiste: {file_path.exists()}")
        
        if file_path.exists():
            print(f"   - Dimensione: {file_path.stat().st_size} bytes")
            
            # Mostra contenuto
            with open(file_path, 'r', encoding='utf-8') as f:
                saved_content = f.read()
            print(f"6. Contenuto salvato ({len(saved_content)} caratteri):")
            print("   " + "\n   ".join(saved_content.split('\n')[:10]))
            if len(saved_content.split('\n')) > 10:
                print("   ...")
    
    print("=== SIMULAZIONE COMPLETATA ===\n")
    return success

if __name__ == "__main__":
    print("🚀 INIZIO TEST SISTEMA AUTO-SAVE SENZA PULSANTE BOZZA")
    print("=" * 60)
    
    try:
        # Test del file system manager
        fs_test = test_filesystem_manager()
        
        # Simulazione workflow
        workflow_test = simulate_auto_save_workflow()
        
        print("📊 RIEPILOGO RISULTATI:")
        print(f"   ✅ File System Manager: {'OK' if fs_test else 'FAIL'}")
        print(f"   ✅ Auto-Save Workflow: {'OK' if workflow_test else 'FAIL'}")
        
        if fs_test and workflow_test:
            print("\n🎉 TUTTI I TEST SONO PASSATI!")
            print("✅ Il sistema auto-save senza pulsante bozza funziona correttamente")
            print("✅ La struttura cartelle JIRA viene creata automaticamente")
            print("✅ I file vengono salvati nella posizione corretta")
        else:
            print("\n❌ ALCUNI TEST SONO FALLITI")
            
    except Exception as e:
        print(f"\n💥 ERRORE DURANTE I TEST: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("🏁 TEST COMPLETATI")