#!/usr/bin/env python3
"""
Test script to verify async startup functionality.
This script tests the database methods and imports without requiring full service initialization.
"""

import sys
import logging
from services.db_service import DatabaseService

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('AsyncStartupTest')

def test_database_methods():
    """Test the database methods for startup."""
    logger.info("Testing database methods...")
    
    try:
        # Initialize database service
        db_service = DatabaseService()
        
        # Test get_recent_issues
        logger.info("Testing get_recent_issues method...")
        recent_issues = db_service.get_recent_issues(limit=10)
        logger.info(f"✅ Found {len(recent_issues)} recent issues in cache")
        
        for issue in recent_issues:
            logger.info(f"  - {issue['key']}: {issue['summary'][:50]}...")
        
        # Test get_all_favorites
        logger.info("Testing get_all_favorites method...")
        favorites = db_service.get_all_favorites()
        logger.info(f"✅ Found {len(favorites)} favorite issues")
        
        # Test get_view_history
        logger.info("Testing get_view_history method...")
        history = db_service.get_view_history(limit=5)
        logger.info(f"✅ Found {len(history)} items in view history")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Database test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_startup_imports():
    """Test that all startup-related imports work."""
    logger.info("Testing startup imports...")
    
    try:
        from services.startup_coordinator import StartupCoordinator, BackgroundDataLoader
        logger.info("✅ StartupCoordinator imported successfully")
        
        from services.jira_service import JiraService
        logger.info("✅ JiraService imported successfully")
        
        from services.app_settings import AppSettings
        logger.info("✅ AppSettings imported successfully")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Import test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    logger.info("🚀 Starting async startup component tests...")
    
    success = True
    
    # Test imports
    if not test_startup_imports():
        success = False
    
    # Test database methods 
    if not test_database_methods():
        success = False
    
    if success:
        logger.info("🎉 All tests passed! Async startup system is ready.")
        sys.exit(0)
    else:
        logger.error("❌ Some tests failed. Check the errors above.")
        sys.exit(1)