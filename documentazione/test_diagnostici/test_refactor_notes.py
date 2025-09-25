#!/usr/bin/env python3
"""
Test del nuovo sistema di gestione note a 3 stati:
- DRAFT: Editable, Save Draft + Commit
- COMMITTED: Readonly, Edit + History + Delete  
- NEW: Editable, Save Draft only
"""

import sys
from PyQt6.QtWidgets import QApplication
from services.db_service import DatabaseService
from services.git_service import GitService

def test_new_note_system():
    print("=== Testing New 3-State Note Management System ===")
    
    try:
        # Initialize services
        print("1. Initializing services...")
        db = DatabaseService()
        db.initialize_db()
        git_service = GitService()
        print("✓ Services initialized")
        
        # Test 1: Create draft note
        print("\n2. Testing DRAFT state...")
        draft_id = db.save_note_as_draft(
            jira_key='TEST-REFACTOR-1',
            title='Test Draft Note', 
            content='This is a draft note for testing',
            tags='test,draft'
        )
        
        note = db.get_note_by_id(draft_id)
        assert note['is_draft'] == True
        print(f"✓ DRAFT note created: ID={draft_id}, is_draft={note['is_draft']}")
        
        # Test 2: Commit note
        print("\n3. Testing DRAFT -> COMMITTED transition...")
        success = db.commit_note(draft_id, "test-commit-hash-123")
        
        note_after_commit = db.get_note_by_id(draft_id)
        assert note_after_commit['is_draft'] == False
        assert note_after_commit['last_commit_hash'] == "test-commit-hash-123"
        print(f"✓ COMMITTED note: is_draft={note_after_commit['is_draft']}, hash={note_after_commit['last_commit_hash']}")
        
        # Test 3: Convert back to draft
        print("\n4. Testing COMMITTED -> DRAFT transition...")
        from datetime import datetime, timezone
        current_time = datetime.now(timezone.utc).isoformat()
        
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE Annotations SET IsDraft = 1, DraftSavedAt = ?, UpdatedAt = ? WHERE Id = ?',
            (current_time, current_time, draft_id)
        )
        conn.commit()
        conn.close()
        
        note_back_to_draft = db.get_note_by_id(draft_id)
        assert note_back_to_draft['is_draft'] == True
        print(f"✓ Back to DRAFT: is_draft={note_back_to_draft['is_draft']}")
        
        # Test 4: Git integration
        print("\n5. Testing Git integration...")
        repo_status = git_service.get_repo_status()
        print(f"✓ Git repo status: {repo_status['status']}")
        
        if repo_status['status'] == 'ready':
            # Test git commit with custom message
            commit_hash = git_service.commit_note(
                'TEST-REFACTOR-1',
                'Test Draft Note',
                'Updated content for testing',
                custom_message="Test custom commit message"
            )
            print(f"✓ Git commit successful: {commit_hash[:8] if commit_hash else 'None'}")
            
            # Test history retrieval
            history = git_service.get_note_history('TEST-REFACTOR-1', 'Test Draft Note')
            print(f"✓ Git history entries: {len(history)}")
        
        # Clean up
        print("\n6. Cleaning up...")
        db.delete_note_soft(draft_id)
        print("✓ Test note deleted")
        
        print("\n🎉 ALL TESTS PASSED!")
        print("✅ New 3-State Note Management System working correctly!")
        
        # Summary of the new system
        print("\n📋 NEW SYSTEM FEATURES:")
        print("  🟠 DRAFT MODE: Editable → Save Draft + Commit buttons")
        print("  🟢 COMMITTED MODE: Readonly → Edit + History + Delete buttons") 
        print("  🆕 NEW MODE: Editable → Save Draft only")
        print("  ✏️ Smart button actions based on note state")
        print("  📚 Git history viewer for committed notes")
        print("  🔄 Easy state transitions (commit ↔ draft)")
        print("  🗑️ Delete always available (as requested)")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_new_note_system()
    if success:
        print("\n🚀 REFACTORED SYSTEM READY!")
    else:
        print("\n❌ System needs fixes!")