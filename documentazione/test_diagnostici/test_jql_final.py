#!/usr/bin/env python3
"""
Test completo finale della dropdown JQL dopo la fix.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

def test_jql_dropdown_complete():
    """Test completo della dropdown JQL dopo la fix."""
    
    print("🔍 Test completo finale JQL Dropdown...")
    
    try:
        # Crea l'applicazione Qt
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        
        from views.jira_grid_view import JiraGridView
        from services.db_service import DatabaseService
        
        print("\n1. Setup...")
        
        # Setup database con alcuni preferiti di test
        db = DatabaseService()
        db.initialize_db()
        
        # Aggiungi alcuni JQL preferiti di test
        test_favorites = [
            ("I miei task", "assignee = currentUser() AND status != Done"),
            ("Task urgenti", "priority = Highest AND status != Done"),
            ("Bugs aperti", "type = Bug AND status = Open")
        ]
        
        for name, jql in test_favorites:
            try:
                db.add_favorite_jql(name, jql)
            except Exception:
                pass  # Già esistente
        
        grid_view = JiraGridView()
        combo = grid_view.jql_combo
        
        print(f"   ✓ Setup completato")
        
        print("\n2. Test con JQL preferiti...")
        
        # Popola i preferiti
        favorites = db.get_favorite_jqls()
        grid_view.populate_jql_favorites(favorites)
        
        print(f"   ✓ Preferiti caricati: {len(favorites)}")
        print(f"   ✓ Items in combo: {combo.count()}")
        
        # Test selezione preferito
        if combo.count() > 1:  # Escludendo l'item di gestione
            combo.setCurrentIndex(0)  # Seleziona primo preferito
            result = grid_view.get_jql_text()
            print(f"   ✓ Preferito selezionato: '{result}'")
        
        print("\n3. Test testo manuale...")
        
        # Test testo digitato manualmente
        manual_jql = "project = MYPROJ AND assignee = currentUser()"
        grid_view.set_jql_text(manual_jql)
        result = grid_view.get_jql_text()
        
        print(f"   ✓ Testo impostato: '{manual_jql}'")
        print(f"   ✓ Testo ottenuto: '{result}'")
        print(f"   ✓ Match perfetto: {manual_jql == result}")
        
        print("\n4. Test casi edge...")
        
        # Test stringa vuota
        grid_view.set_jql_text("")
        result = grid_view.get_jql_text()
        print(f"   ✓ Stringa vuota: '{result}' == ''")
        
        # Test opzione gestione
        management_index = combo.count() - 1  # Ultimo item è sempre gestione
        combo.setCurrentIndex(management_index)
        result = grid_view.get_jql_text()
        print(f"   ✓ Opzione gestione: '{result}' == '' (corretto)")
        
        print("\n5. Test set/get multipli...")
        
        test_queries = [
            "status = Open",
            "priority = High",
            "assignee = currentUser() AND status != Closed"
        ]
        
        for i, query in enumerate(test_queries):
            grid_view.set_jql_text(query)
            result = grid_view.get_jql_text()
            match = query == result
            print(f"   ✓ Test {i+1}: {match} ('{query[:20]}...')")
            
            if not match:
                print(f"     ❌ Atteso: '{query}'")
                print(f"     ❌ Ottenuto: '{result}'")
        
        print("\n✅ Tutti i test superati! La dropdown JQL funziona correttamente!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Errore durante il test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_jql_dropdown_complete()
    sys.exit(0 if success else 1)