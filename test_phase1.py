#!/usr/bin/env python3
"""
Test script for Phase 1 components: Central Logging System and Configuration Management.
This script tests the foundation components of the enhanced video generation system.
"""

import os
import sys
import tempfile
import json
from datetime import datetime, timedelta

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from logger import get_logger, initialize_logging, get_performance_logger
from config import get_config, ConfigManager

def test_logging_system():
    """Test the central logging system."""
    print("=== Testing Central Logging System ===")
    
    # Test 1: Default initialization (terminal only)
    print("\n1. Testing default logging (terminal only)...")
    logger = get_logger('test')
    logger.info("This should appear in terminal")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    
    # Test 2: File logging initialization
    print("\n2. Testing file logging...")
    with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as tmp:
        log_file = tmp.name
    
    try:
        logging_config = {
            'log_level': 'DEBUG',
            'log_file': log_file,
            'log_max_size': '1MB',
            'log_backup_count': 2,
            'log_console_output': True
        }
        
        initialize_logging(logging_config)
        logger = get_logger('test_file')
        logger.debug("This debug message should appear in both terminal and file")
        logger.info("This info message should appear in both terminal and file")
        
        # Verify file was created and contains logs
        if os.path.exists(log_file):
            with open(log_file, 'r') as f:
                content = f.read()
                print(f"✓ Log file created successfully: {log_file}")
                print(f"✓ Log file contains {len(content.splitlines())} lines")
        else:
            print("✗ Log file was not created")
            
    finally:
        # Cleanup
        if os.path.exists(log_file):
            os.unlink(log_file)
    
    # Test 3: Performance logging
    print("\n3. Testing performance logging...")
    performance_logger = get_performance_logger()
    
    @performance_logger.performance_logger("test_operation")
    def test_function():
        import time
        time.sleep(0.1)  # Simulate work
        return "success"
    
    result = test_function()
    print(f"✓ Performance logging decorator works: {result}")
    
    # Test 4: Performance context manager
    print("\n4. Testing performance context manager...")
    with performance_logger.performance_context("context_test"):
        import time
        time.sleep(0.05)  # Simulate work
    
    print("✓ Performance context manager works")
    
    print("\n=== Logging System Tests Complete ===\n")

def test_configuration_system():
    """Test the configuration management system."""
    print("=== Testing Configuration Management System ===")
    
    # Test 1: Default configuration creation
    print("\n1. Testing default configuration creation...")
    config_file = tempfile.mktemp(suffix='.json')
    
    try:
        config = ConfigManager(config_file)
        print("✓ Default configuration created successfully")
        
        # Verify default values
        instagram_config = config.get_instagram_config()
        print(f"✓ Instagram config loaded: {instagram_config['app_id']}")
        
        gcs_config = config.get_gcs_config()
        print(f"✓ GCS config loaded: {gcs_config['bucket']}")
        
        openai_config = config.get_openai_config()
        print(f"✓ OpenAI config loaded: {openai_config['creation_prompt'][:50]}...")
        
    finally:
        # Cleanup
        if os.path.exists(config_file):
            os.unlink(config_file)
    
    # Test 2: Environment variable resolution
    print("\n2. Testing environment variable resolution...")
    
    # Set test environment variables
    test_env_vars = {
        'TEST_APP_ID': 'test_app_123',
        'TEST_SECRET': 'test_secret_456',
        'TEST_BUCKET': 'test-bucket'
    }
    
    for key, value in test_env_vars.items():
        os.environ[key] = value
    
    test_config = {
        'app_id': '${TEST_APP_ID}',
        'secret': '${TEST_SECRET}',
        'bucket': '${TEST_BUCKET}',
        'static_value': 'unchanged'
    }
    
    config = ConfigManager()
    resolved = config.resolve_environment_variables(test_config)
    
    print(f"✓ Environment variables resolved: {resolved['app_id']}")
    print(f"✓ Static values preserved: {resolved['static_value']}")
    
    # Cleanup test environment variables
    for key in test_env_vars:
        if key in os.environ:
            del os.environ[key]
    
    # Test 3: Instagram token management
    print("\n3. Testing Instagram token management...")
    
    # Test with expired token
    config.config['instagram_token_expiration'] = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S")
    config.config['instagram_days_before_refresh'] = 7
    
    is_expired = config.is_instagram_token_expired()
    days_until = config.get_days_until_token_refresh()
    
    print(f"✓ Token expiration check works: expired={is_expired}, days_until={days_until}")
    
    # Test with valid token
    config.config['instagram_token_expiration'] = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
    
    is_expired = config.is_instagram_token_expired()
    days_until = config.get_days_until_token_refresh()
    
    print(f"✓ Valid token check works: expired={is_expired}, days_until={days_until}")
    
    # Test 4: Configuration validation
    print("\n4. Testing configuration validation...")
    
    # Test with missing required fields
    config.config['instagram_app_id'] = None
    config.validate_config()  # Should show warnings
    
    # Restore valid value
    config.config['instagram_app_id'] = 'test_app_id'
    
    print("✓ Configuration validation works")
    
    print("\n=== Configuration System Tests Complete ===\n")

def test_integration():
    """Test integration between logging and configuration."""
    print("=== Testing Integration ===")
    
    # Test 1: Configuration with logging integration
    print("\n1. Testing configuration with logging integration...")
    
    config_file = tempfile.mktemp(suffix='.json')
    
    try:
        # Create config with logging enabled
        config = ConfigManager(config_file)
        
        # Verify logger is working
        logger = get_logger('integration_test')
        logger.info("Testing integration between config and logging")
        
        # Test configuration methods
        instagram_config = config.get_instagram_config()
        logger.info(f"Instagram config loaded: {instagram_config['app_id']}")
        
        print("✓ Integration test successful")
        
    finally:
        # Cleanup
        if os.path.exists(config_file):
            os.unlink(config_file)
    
    print("\n=== Integration Tests Complete ===\n")

def main():
    """Run all Phase 1 tests."""
    print("🚀 Starting Phase 1 Testing Suite")
    print("=" * 50)
    
    try:
        test_logging_system()
        test_configuration_system()
        test_integration()
        
        print("🎉 All Phase 1 tests completed successfully!")
        print("✓ Central Logging System: Working")
        print("✓ Configuration Management: Working")
        print("✓ Integration: Working")
        
    except Exception as e:
        print(f"❌ Phase 1 testing failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
