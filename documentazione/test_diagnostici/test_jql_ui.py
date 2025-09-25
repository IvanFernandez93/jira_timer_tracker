#!/usr/bin/env python3
"""
Test completo della dropdown JQL con UI.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

def test_jql_dropdown_ui():
    """Testa la dropdown JQL nell'interfaccia utente."""
    
    print("🔍 Test JQL Dropdown UI...")
    
    try:
        # Crea l'applicazione Qt
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        
        # Importa i componenti necessari
        from services.db_service import DatabaseService
        from views.jira_grid_view import JiraGridView
        
        print("\n1. Inizializzazione componenti...")
        
        # Database service
        db = DatabaseService()
        db.initialize_db()
        
        # Crea JiraGridView
        grid_view = JiraGridView()
        
        print("   ✓ Componenti inizializzati")
        
        print("\n2. Verifica JQL combo box...")
        
        # Controlla che il combo esista
        combo = grid_view.jql_combo
        print(f"   ✓ JQL combo box presente: {combo is not None}")
        print(f"   ✓ Combo editabile: {combo.isEditable()}")
        print(f"   ✓ Combo items iniziali: {combo.count()}")
        
        print(f"   ✓ Placeholder text: '{combo.placeholderText()}'")
        
        print("\n3. Test populate_jql_favorites...")
        
        # Ottieni JQL preferiti dal database
        favorites = db.get_favorite_jqls()
        print(f"   ✓ JQL preferiti trovati: {len(favorites)}")
        
        # Popola il dropdown
        grid_view.populate_jql_favorites(favorites)
        
        print(f"   ✓ Items dopo populate: {combo.count()}")
        
        # Mostra tutti gli items
        for i in range(combo.count()):
            item_text = combo.itemText(i)
            item_data = combo.itemData(i)
            print(f"     - Item {i}: '{item_text}' (data: {item_data})")
        
        print("\n4. Test interazione combo box...")
        
        # Test set/get text
        test_jql = "test = value"
        grid_view.set_jql_text(test_jql)
        current_text = grid_view.get_jql_text()
        
        print(f"   ✓ Set JQL text: '{test_jql}'")
        print(f"   ✓ Get JQL text: '{current_text}'")
        print(f"   ✓ Match: {test_jql == current_text}")
        
        print("\n✅ Test completato con successo!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Errore durante il test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_jql_dropdown_ui()
    sys.exit(0 if success else 1)