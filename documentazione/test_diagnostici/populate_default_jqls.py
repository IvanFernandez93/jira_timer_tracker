#!/usr/bin/env python3
"""
Popola il database con JQL preferiti utili di default.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def populate_default_jqls():
    """Popola il database con JQL di default utili."""
    
    print("🔧 Popolazione JQL preferiti di default...")
    
    try:
        from services.db_service import DatabaseService
        
        db = DatabaseService()
        db.initialize_db()
        
        # JQL utili di default
        default_jqls = [
            ("I miei task", "assignee = currentUser() AND status != Done"),
            ("Task da fare", "assignee = currentUser() AND status = 'To Do'"),
            ("Task in corso", "assignee = currentUser() AND status = 'In Progress'"),
            ("Task urgenti", "assignee = currentUser() AND priority in (Highest, High) AND status != Done"),
            ("Bug aperti", "type = Bug AND status in (Open, Reopened, 'In Progress')"),
            ("Creati da me", "reporter = currentUser() ORDER BY created DESC"),
            ("Aggiornati oggi", "updated >= startOfDay() ORDER BY updated DESC"),
            ("Scadenza vicina", "duedate <= 7d AND status != Done ORDER BY duedate ASC"),
            ("Senza assegnatario", "assignee is EMPTY AND status != Done"),
            ("Review in attesa", "status = 'In Review' ORDER BY updated ASC")
        ]
        
        added_count = 0
        existing_count = 0
        
        for name, jql in default_jqls:
            try:
                db.add_favorite_jql(name, jql)
                added_count += 1
                print(f"   ✓ Aggiunto: '{name}'")
            except Exception as e:
                if "UNIQUE constraint failed" in str(e):
                    existing_count += 1
                    print(f"   - Esistente: '{name}'")
                else:
                    print(f"   ❌ Errore per '{name}': {e}")
        
        print(f"\n📊 Risultato:")
        print(f"   ✓ JQL aggiunti: {added_count}")
        print(f"   - JQL già esistenti: {existing_count}")
        print(f"   📝 Totale JQL disponibili: {len(db.get_favorite_jqls())}")
        
        print(f"\n✅ Popolazione completata!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Errore durante la popolazione: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = populate_default_jqls()
    sys.exit(0 if success else 1)