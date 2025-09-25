#!/usr/bin/env python3

"""
Test script for the fictitious ticket detection system.
"""

import sys
import os

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.jira_service import JiraService

def test_jira_service():
    """Test JiraService fictitious ticket detection."""
    print("=== Testing JiraService Fictitious Ticket Detection ===")
    
    jira_service = JiraService()
    
    # Test cases from conversation
    test_cases = [
        ("ZTL-7", False, "Standard Jira format - should be real"),
        ("ZTL-5", False, "Standard Jira format - should be real"), 
        ("ZTL-4", False, "Standard Jira format - should be real"),
        ("FAKE-123", True, "Obvious fake ticket"),
        ("fitizzia", True, "Random word - likely fake"),
        ("FITIZZIA", True, "Random word uppercase - likely fake"),
        ("cdff", True, "Random letters - likely fake"),
        ("PROJECT-456", False, "Standard format - should be real"),
        ("ABC-999", False, "Standard format - should be real"),
    ]
    
    all_passed = True
    
    for ticket, expected, description in test_cases:
        result = jira_service.is_likely_fictitious_ticket(ticket)
        status = "✅ PASS" if result == expected else "❌ FAIL"
        if result != expected:
            all_passed = False
        print(f"{status} {ticket}: {result} (expected {expected}) - {description}")
    
    print()
    
    # Test manual management
    print("=== Testing Manual Fictitious Ticket Management ===")
    
    # Mark a real-looking ticket as fictitious manually
    jira_service.mark_ticket_as_fictitious("PROJECT-999")
    manual_result = jira_service.is_ticket_marked_as_fictitious("PROJECT-999")
    print(f"Manual marking: PROJECT-999 is fictitious: {manual_result} (should be True)")
    
    # Mark it back as real
    jira_service.unmark_ticket_as_fictitious("PROJECT-999")
    real_result = jira_service.is_ticket_marked_as_fictitious("PROJECT-999")
    print(f"Manual unmarking: PROJECT-999 is fictitious: {real_result} (should be False)")
    
    print()
    
    # Test cache behavior
    print("=== Testing Cache Behavior ===")
    print(f"Cache size: {len(jira_service._fictitious_tickets)}")
    print(f"Cached tickets: {list(jira_service._fictitious_tickets)}")
    
    return all_passed

def test_database_schema():
    """Test that database schema supports IsFictitious column."""
    print("=== Testing Database Schema ===")
    
    try:
        from services.db_service import DatabaseService
        
        # Test with a temporary database file
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
        
        try:
            db_service = DatabaseService(db_path)
            
            # Initialize the database (create tables)
            db_service.initialize_db()
            
            # Try to create a note with is_fictitious flag
            note_id = db_service.create_note(
                jira_key="TEST-123",
                title="Test Note", 
                content="Test content",
                tags="test",
                is_fictitious=True
            )
            
            print(f"✅ Successfully created note {note_id} with is_fictitious=True")
            
            # Try to retrieve it
            note = db_service.get_note_by_id(note_id)
            if note:
                print(f"✅ Successfully retrieved note: {note}")
                if 'is_fictitious' in note:
                    print(f"✅ Successfully retrieved note with is_fictitious={note['is_fictitious']}")
                    return True
                else:
                    print(f"❌ Missing is_fictitious field. Available fields: {list(note.keys())}")
                    return False
            else:
                print("❌ Failed to retrieve note")
                return False
                
        finally:
            # Clean up
            try:
                os.unlink(db_path)
            except:
                pass
                
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

if __name__ == "__main__":
    print("Testing Fictitious Ticket Detection System")
    print("=" * 50)
    
    jira_passed = test_jira_service()
    print()
    
    db_passed = test_database_schema()
    print()
    
    if jira_passed and db_passed:
        print("🎉 All tests passed! The fictitious ticket system is working correctly.")
        sys.exit(0)
    else:
        print("💥 Some tests failed. Please check the implementation.")
        sys.exit(1)