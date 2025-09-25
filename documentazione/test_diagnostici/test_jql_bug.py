#!/usr/bin/env python3
"""
Test specifico del bug nella dropdown JQL.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

def test_jql_bug_specific():
    """Test specifico del bug nella dropdown JQL."""
    
    print("🔍 Test specifico bug JQL Dropdown...")
    
    try:
        # Crea l'applicazione Qt
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        
        # Importa i componenti necessari
        from views.jira_grid_view import JiraGridView
        
        print("\n1. Creo JiraGridView...")
        
        # Crea JiraGridView
        grid_view = JiraGridView()
        combo = grid_view.jql_combo
        
        print(f"   ✓ Items iniziali: {combo.count()}")
        print(f"   ✓ Current index: {combo.currentIndex()}")
        print(f"   ✓ Current text: '{combo.currentText()}'")
        
        print("\n2. Test impostazione testo manuale...")
        
        # Imposta testo manualmente nel combo
        test_jql = "assignee = currentUser()"
        combo.setCurrentText(test_jql)
        
        print(f"   ✓ Impostato: '{test_jql}'")
        print(f"   ✓ Current text dopo set: '{combo.currentText()}'")
        print(f"   ✓ Current index dopo set: {combo.currentIndex()}")
        
        # Verifica item data
        current_index = combo.currentIndex()
        if current_index >= 0:
            item_data = combo.itemData(current_index)
            print(f"   ✓ Item data: {item_data}")
        
        print("\n3. Test get_jql_text...")
        
        result = grid_view.get_jql_text()
        print(f"   ✓ get_jql_text() risultato: '{result}'")
        
        print("\n4. Test case edge...")
        
        # Test caso senza selezione
        combo.setCurrentIndex(-1)
        print(f"   ✓ Index -1, current text: '{combo.currentText()}'")
        print(f"   ✓ get_jql_text() con index -1: '{grid_view.get_jql_text()}'")
        
        # Ri-imposta il testo
        combo.setCurrentText(test_jql)
        print(f"   ✓ Ri-impostato testo: '{combo.currentText()}'")
        print(f"   ✓ Index dopo re-set: {combo.currentIndex()}")
        print(f"   ✓ get_jql_text() dopo re-set: '{grid_view.get_jql_text()}'")
        
        print("\n5. Analisi dettagliata logica get_jql_text...")
        
        current_index = combo.currentIndex()
        print(f"   • Current index: {current_index}")
        print(f"   • Index >= 0: {current_index >= 0}")
        
        if current_index >= 0:
            item_data = combo.itemData(current_index)
            current_text = combo.currentText()
            
            print(f"   • Item data: {item_data}")
            print(f"   • Item data is not None: {item_data is not None}")
            print(f"   • Current text: '{current_text}'")
            print(f"   • Is management option: {current_text == '📚 Gestisci cronologia e preferiti...'}")
            
            if item_data is not None:
                print(f"   → Dovrebbe ritornare item_data: '{item_data}'")
            elif current_text == "📚 Gestisci cronologia e preferiti...":
                print(f"   → Dovrebbe ritornare stringa vuota")
            else:
                print(f"   → Dovrebbe ritornare current_text: '{current_text}'")
        
        print("\n✅ Test completato!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Errore durante il test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_jql_bug_specific()
    sys.exit(0 if success else 1)