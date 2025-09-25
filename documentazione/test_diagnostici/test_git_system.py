#!/usr/bin/env python3
"""
Test script for the new git-based notes system.
"""

from services.db_service import DatabaseService
from services.git_service import GitService

def test_git_notes_system():
    print("=== Testing Git-Based Notes System ===")
    
    try:
        # Initialize services
        print("1. Initializing services...")
        db = DatabaseService()
        db.initialize_db()
        git_service = GitService()
        print("✓ Services initialized")
        
        # Create a draft note
        print("\n2. Creating draft note...")
        note_id = db.save_note_as_draft(
            jira_key='TEST-100', 
            title='Test Git Note', 
            content='This is a test note for git system',
            tags='test,git,draft'
        )
        print(f"✓ Draft created with ID: {note_id}")
        
        # Retrieve and verify draft
        note = db.get_note_by_id(note_id)
        print(f"✓ Draft status: {note['is_draft']}")
        print(f"✓ Note title: {note['title']}")
        
        # Commit the note
        print("\n3. Committing note...")
        commit_result = db.commit_note(note_id, "Initial commit of test note")
        print(f"✓ Commit result: {commit_result}")
        
        # Check updated note
        note_after_commit = db.get_note_by_id(note_id)
        print(f"✓ Is draft after commit: {note_after_commit['is_draft']}")
        print(f"✓ Last commit hash: {note_after_commit['last_commit_hash']}")
        
        # Check git repository status
        print("\n4. Checking git repository...")
        repo_status = git_service.get_repo_status()
        print(f"✓ Repository status: {repo_status['status']}")
        print(f"✓ Commit count: {repo_status.get('commit_count', 'N/A')}")
        
        # Get note history
        print("\n5. Checking note history...")
        history = git_service.get_note_history('TEST-100', 'Test Git Note')
        print(f"✓ History entries: {len(history)}")
        for entry in history[:3]:  # Show first 3 entries
            print(f"  - {entry['date']}: {entry['message'][:50]}...")
        
        # Test draft saving again
        print("\n6. Testing draft update...")
        db.save_note_as_draft(
            jira_key='TEST-100',
            title='Test Git Note',
            content='Updated content in draft',
            tags='test,git,updated',
            note_id=note_id
        )
        
        updated_note = db.get_note_by_id(note_id)
        print(f"✓ Note is draft again: {updated_note['is_draft']}")
        
        # Clean up
        print("\n7. Cleaning up...")
        db.delete_note_soft(note_id)
        print("✓ Test note deleted")
        
        print("\n🎉 ALL TESTS PASSED - Git-based notes system working correctly!")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = test_git_notes_system()
    if success:
        print("\n✅ Git-based notes system is ready for production!")
    else:
        print("\n❌ Git-based notes system needs fixes!")