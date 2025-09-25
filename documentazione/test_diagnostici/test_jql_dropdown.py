#!/usr/bin/env python3
"""
Test script per diagnosticare il problema della dropdown JQL.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.db_service import DatabaseService

def test_jql_favorites():
    """Testa la funzionalità dei JQL preferiti."""
    
    print("🔍 Diagnostica JQL Favorites...")
    
    # Inizializza database
    db = DatabaseService()
    db.initialize_db()
    
    print("\n1. Controllo tabella FavoriteJQLs...")
    try:
        favorites = db.get_favorite_jqls()
        print(f"   ✓ Numero JQL preferiti trovati: {len(favorites)}")
        
        if favorites:
            print("   📋 Lista JQL preferiti:")
            for fav_id, name, query in favorites:
                print(f"     - ID: {fav_id}, Nome: '{name}', Query: '{query[:50]}...'")
        else:
            print("   ⚠️ Nessun JQL preferito trovato")
            
            # Aggiungi alcuni preferiti di esempio
            print("\n2. Aggiunta JQL preferiti di esempio...")
            try:
                db.add_favorite_jql("I miei ticket", "assignee = currentUser() AND status != \"Done\"")
                db.add_favorite_jql("Ticket aperti", "status in (\"Open\", \"In Progress\", \"Reopened\")")
                db.add_favorite_jql("Urgenti", "priority = \"High\" AND status != \"Done\"")
                
                print("   ✓ JQL preferiti di esempio aggiunti")
                
                # Ricontrolla
                favorites = db.get_favorite_jqls()
                print(f"   ✓ Ora ci sono {len(favorites)} JQL preferiti")
                
            except Exception as e:
                print(f"   ❌ Errore aggiungendo JQL preferiti: {e}")
            
    except Exception as e:
        print(f"   ❌ Errore accedendo alla tabella FavoriteJQLs: {e}")
    
    print("\n3. Test simulazione populate_jql_favorites...")
    try:
        favorites = db.get_favorite_jqls()
        
        # Simula quello che fa populate_jql_favorites
        print(f"   Simulando dropdown con {len(favorites)} elementi:")
        
        for fav_id, name, query in favorites:
            # Simula la logica di troncamento
            if len(query) <= 60:
                display_text = query
            else:
                truncated_query = query[:60]
                last_space = truncated_query.rfind(' ')
                if last_space > 20:
                    truncated_query = query[:last_space]
                display_text = f"{truncated_query}..."
            
            print(f"     - Item: '{display_text}' (data: '{query}')")
        
        print("   ✓ Simulazione completata senza errori")
        
    except Exception as e:
        print(f"   ❌ Errore nella simulazione: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_jql_favorites()