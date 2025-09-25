#!/usr/bin/env python3
"""
Test per il servizio di diff esterni
"""
import sys
import os

# Aggiungi la directory root al path per gli import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.external_diff_service import ExternalDiffService

def test_external_diff_service():
    """Test del servizio diff esterno."""
    print("🔧 Test External Diff Service")
    print("=" * 50)
    
    # Test rilevamento tool disponibili
    service = ExternalDiffService()
    available_tools = service.get_available_tools()
    
    print(f"📋 Tool disponibili sul sistema:")
    for tool in available_tools:
        print(f"  ✅ {tool}")
    
    # Test miglior tool
    best_tool = service.detect_best_tool()
    print(f"\n🏆 Miglior tool rilevato: {best_tool}")
    
    # Test creazione file temporanei con diff
    content1 = """# Versione 1
Questo è il contenuto originale della nota.

## Sezione A
Contenuto della sezione A.

## Sezione B  
Contenuto della sezione B.
"""

    content2 = """# Versione 2 - Aggiornata
Questo è il contenuto modificato della nota.

## Sezione A
Contenuto della sezione A aggiornato con dettagli extra.

## Sezione B
Contenuto della sezione B.

## Sezione C - Nuova
Questa è una nuova sezione aggiunta.
"""

    print(f"\n📝 Test apertura diff con tool: {best_tool}")
    print(f"📄 Contenuto 1: {len(content1)} caratteri")
    print(f"📄 Contenuto 2: {len(content2)} caratteri")
    
    # Test con context manager per auto-cleanup
    with ExternalDiffService() as diff_service:
        success = diff_service.open_diff(
            content1, content2,
            "Versione_Originale",
            "Versione_Aggiornata",
            best_tool
        )
        
        if success:
            print(f"✅ Diff aperto con successo!")
            print(f"📂 File temporanei in: {diff_service.temp_dir}")
            print("💡 Il diff dovrebbe ora essere visibile nel tool esterno.")
            
            # Mantieni aperto per vedere il diff
            input("\n⏸️  Premi INVIO dopo aver visto il diff per continuare...")
        else:
            print(f"❌ Errore nell'apertura del diff")
    
    print("🧹 Cleanup completato automaticamente.")

def test_all_tools():
    """Test tutti i tool disponibili."""
    print("\n🛠️  Test di tutti i tool")
    print("=" * 50)
    
    content_a = "Contenuto originale\nLinea 2\nLinea 3"
    content_b = "Contenuto modificato\nLinea 2 cambiata\nLinea 3\nLinea 4 aggiunta"
    
    service = ExternalDiffService()
    
    for tool in service.supported_tools.keys():
        print(f"\n🔧 Test tool: {tool}")
        
        with ExternalDiffService() as diff_service:
            success = diff_service.open_diff(
                content_a, content_b,
                f"Test_{tool}_A",
                f"Test_{tool}_B",
                tool
            )
            
            if success:
                print(f"  ✅ {tool} funziona")
            else:
                print(f"  ❌ {tool} non disponibile o errore")

if __name__ == '__main__':
    print("🧪 Test Suite External Diff Service")
    print("=" * 60)
    
    try:
        test_external_diff_service()
        
        # Test opzionale di tutti i tool (richiede conferma)
        response = input("\n❓ Vuoi testare tutti i tool disponibili? (y/N): ").lower().strip()
        if response in ['y', 'yes', 's', 'si']:
            test_all_tools()
            
    except Exception as e:
        print(f"❌ Errore durante i test: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n✅ Test completati!")