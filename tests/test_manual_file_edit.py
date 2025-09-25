#!/usr/bin/env python3
"""Test manual file modification to verify file watcher works."""

import time
from pathlib import Path

def main():
    print("📁 Manual File Modification Test")
    print("=" * 50)
    
    # Path where notes are typically stored
    notes_base = Path.home() / "Documents" / "JiraTrackerNotes"
    
    if not notes_base.exists():
        print(f"❌ Notes directory not found: {notes_base}")
        print("Create some notes in the application first!")
        return
    
    print(f"📂 Looking for note files in: {notes_base}")
    
    # Find all .md files
    md_files = list(notes_base.rglob("*.md"))
    
    if not md_files:
        print("❌ No .md note files found!")
        print("Create some notes in the application first!")
        return
    
    print(f"✅ Found {len(md_files)} note files:")
    for i, file_path in enumerate(md_files[:5], 1):  # Show first 5
        print(f"   {i}. {file_path.name} ({file_path.parent.name}/)")
    
    if len(md_files) > 5:
        print(f"   ... and {len(md_files) - 5} more")
    
    print("\n🔧 Instructions to test file watcher:")
    print("1. Open the Jira Timer Tracker application")
    print("2. Open the Notes Manager")
    print("3. Select a note to edit")
    print("4. While the note is open in the app, manually edit one of these files:")
    
    # Show the most recent file
    most_recent = max(md_files, key=lambda f: f.stat().st_mtime)
    print(f"\n📝 Most recent file to try:")
    print(f"   File: {most_recent}")
    print(f"   Content preview:")
    
    try:
        with open(most_recent, 'r', encoding='utf-8') as f:
            content = f.read()
            preview = content[:200] + "..." if len(content) > 200 else content
            print(f"   '{preview}'")
    except Exception as e:
        print(f"   (Error reading file: {e})")
    
    print("\n5. Save the file after making changes")
    print("6. The application should show a dialog asking if you want to update")
    print("\n✨ This tests the external file change detection!")

if __name__ == "__main__":
    main()