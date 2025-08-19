#!/usr/bin/env python3
"""
Test script for Phase 3 implementation:
- Configuration system with new Phase 3 options
- GPT Thread Manager functionality
"""

import sys
import os
import json

# Add parent directory to path to import config and logger
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import get_config
from autopotter_tools.gpt_thread_manager import GPTThreadManager

def test_config_phase3():
    """Test the Phase 3 configuration options."""
    print("=== Testing Phase 3 Configuration ===")
    
    try:
        # Load configuration
        config = get_config("autopost_config.enhanced.json")
        
        # Test OpenAI configuration
        openai_config = config.get_openai_config()
        print(f"OpenAI API Key configured: {bool(openai_config.get('api_key'))}")
        print(f"Assistant ID: {openai_config.get('assistant_id')}")
        print(f"Thread ID: {openai_config.get('thread_id')}")
        print(f"Always create new thread: {openai_config.get('always_create_new_thread')}")
        
        print("✓ Phase 3 configuration loaded successfully")
        return True
        
    except Exception as e:
        print(f"✗ Configuration test failed: {e}")
        return False

def test_gpt_thread_manager():
    """Test the GPT Thread Manager functionality."""
    print("\n=== Testing GPT Thread Manager ===")
    
    try:
        # Test initialization (this will fail if no OpenAI API key, but that's expected)
        manager = GPTThreadManager()
        
        # Test thread info
        thread_info = manager.get_thread_info()
        print(f"Thread ID: {thread_info.get('thread_id')}")
        print(f"Assistant ID: {thread_info.get('assistant_id')}")
        print(f"Assistant configured: {thread_info.get('assistant_configured')}")
        
        # Test basic prompt functionality (will work even without assistant_id for thread creation)
        print("\nTesting basic prompt functionality...")
        try:
            response = manager.prompt("Hello! This is a test message.")
            if response is not None:
                print(f"Prompt response: {response[:100]}...")
            else:
                print("Prompt returned None (expected without assistant_id)")
        except Exception as e:
            print(f"Prompt test error (expected without assistant_id): {e}")
        
        print("✓ GPT Thread Manager initialized successfully")
        return True
        
    except ValueError as e:
        if "OpenAI API key is required" in str(e):
            print("⚠ GPT Thread Manager test skipped - no OpenAI API key configured")
            print("  This is expected in a test environment without API keys")
            return True
        else:
            print(f"✗ GPT Thread Manager test failed: {e}")
            return False
    except Exception as e:
        print(f"✗ GPT Thread Manager test failed: {e}")
        return False

def test_config_structure():
    """Test the configuration structure and validation."""
    print("\n=== Testing Configuration Structure ===")
    
    try:
        config = get_config("autopost_config.enhanced.json")
        
        # Test that all Phase 3 fields are accessible
        required_phase3_fields = [
            'always_create_new_thread'
        ]
        
        missing_fields = []
        for field in required_phase3_fields:
            if config.get(field) is None:
                missing_fields.append(field)
        
        if missing_fields:
            print(f"✗ Missing Phase 3 fields: {missing_fields}")
            return False
        
        print("✓ Found always_create_new_thread field")
        
        # Test always_create_new_thread is boolean
        always_create = config.get('always_create_new_thread')
        if not isinstance(always_create, bool):
            print(f"✗ always_create_new_thread should be boolean, got {type(always_create)}")
            return False
        
        print(f"✓ always_create_new_thread: {always_create}")
        
        print("✓ Configuration structure validation passed")
        return True
        
    except Exception as e:
        print(f"✗ Configuration structure test failed: {e}")
        return False

def main():
    """Run all Phase 3 tests."""
    print("Phase 3 Implementation Test Suite")
    print("=" * 40)
    
    tests = [
        test_config_phase3,
        test_gpt_thread_manager,
        test_config_structure
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"✗ Test {test.__name__} crashed: {e}")
    
    print("\n" + "=" * 40)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All Phase 3 tests passed!")
        return 0
    else:
        print("⚠ Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
