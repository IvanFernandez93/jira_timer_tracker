#!/usr/bin/env python3
"""
Simple test to verify note switching logic
"""

def test_note_switching_logic():
    """Test the note switching logic without database dependencies"""

    # Simulate annotations data
    annotations = [
        ("Note 1", "Content of note 1\nWith multiple lines"),
        ("Note 2", "Content of note 2\nDifferent content"),
        ("Note 3", "Content of note 3\nYet another content")
    ]

    print("Testing note switching logic:")
    print(f"Available notes: {[title for title, _ in annotations]}")

    # Test switching to each note
    for tab_index in range(len(annotations)):
        title = annotations[tab_index][0]
        content = annotations[tab_index][1]

        print(f"\nSwitching to tab {tab_index}:")
        print(f"  Title: '{title}'")
        print(f"  Content: '{content[:30]}...'")

        # Simulate the logic in _handle_note_tab_change
        found_content = None
        for ann_title, ann_content in annotations:
            if ann_title == title:
                found_content = ann_content
                break

            if found_content:
                print(f"  ✓ Found matching content: '{found_content[:30]}...'")
                if found_content == content:
                    print("  ✓ Content matches expected!")
                else:
                    print("  ✗ Content does not match expected!")
            else:
                print("  ✗ No matching content found!")

    print("\nTest completed!")

if __name__ == "__main__":
    test_note_switching_logic()