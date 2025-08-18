#!/usr/bin/env python3
"""
Demonstration script for Phase 1 components: Central Logging System and Configuration Management.
This script shows how to use the foundation components in practice.
"""

import os
import sys
import time

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from logger import get_logger, initialize_logging, get_performance_logger
from config import get_config, ConfigManager

def demonstrate_logging():
    """Demonstrate the central logging system capabilities."""
    print("🔍 Demonstrating Central Logging System")
    print("-" * 40)
    
    # Get a logger for this demonstration
    logger = get_logger('demo')
    
    # Show different log levels
    logger.debug("This is a debug message (only visible if log_level is DEBUG)")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    
    # Show performance logging
    performance_logger = get_performance_logger()
    
    @performance_logger.performance_logger("demo_operation")
    def simulate_work():
        """Simulate some work that takes time."""
        time.sleep(0.2)
        return "Work completed"
    
    print("\n⏱️  Demonstrating performance logging...")
    result = simulate_work()
    print(f"Result: {result}")
    
    # Show context manager
    print("\n📊 Demonstrating performance context manager...")
    with performance_logger.performance_context("batch_processing"):
        for i in range(3):
            time.sleep(0.1)
            print(f"  Processing item {i+1}")
    
    print("\n✅ Logging demonstration complete\n")

def demonstrate_configuration():
    """Demonstrate the configuration management system capabilities."""
    print("⚙️  Demonstrating Configuration Management System")
    print("-" * 40)
    
    # Get configuration
    config = get_config()
    
    # Show Instagram configuration
    print("\n📱 Instagram Configuration:")
    instagram_config = config.get_instagram_config()
    for key, value in instagram_config.items():
        if key in ['app_secret', 'access_token']:
            # Mask sensitive values
            masked_value = f"{str(value)[:8]}..." if value else "Not set"
            print(f"  {key}: {masked_value}")
        else:
            print(f"  {key}: {value}")
    
    # Show GCS configuration
    print("\n☁️  Google Cloud Storage Configuration:")
    gcs_config = config.get_gcs_config()
    for key, value in gcs_config.items():
        if key == 'api_key_path':
            masked_value = f"{str(value)[:20]}..." if value else "Not set"
            print(f"  {key}: {masked_value}")
        else:
            print(f"  {key}: {value}")
    
    # Show OpenAI configuration
    print("\n🤖 OpenAI Configuration:")
    openai_config = config.get_openai_config()
    for key, value in openai_config.items():
        if key == 'api_key':
            masked_value = f"{str(value)[:8]}..." if value else "Not set"
            print(f"  {key}: {masked_value}")
        else:
            print(f"  {key}: {value}")
    
    # Show token status
    print("\n🔑 Instagram Token Status:")
    is_expired = config.is_instagram_token_expired()
    days_until = config.get_days_until_token_refresh()
    print(f"  Token expired: {is_expired}")
    print(f"  Days until refresh: {days_until}")
    
    print("\n✅ Configuration demonstration complete\n")

def demonstrate_integration():
    """Demonstrate how logging and configuration work together."""
    print("🔗 Demonstrating Integration")
    print("-" * 40)
    
    # Initialize logging with configuration
    config = get_config()
    logging_config = config.get_logging_config()
    
    print(f"📝 Logging configuration: {logging_config['log_level']} level")
    if logging_config['log_file']:
        print(f"📁 Log file: {logging_config['log_file']}")
    else:
        print("📱 Logging to terminal only")
    
    # Get logger and show integration
    logger = get_logger('integration_demo')
    logger.info("Logging system initialized with configuration")
    
    # Show how configuration changes affect logging
    print("\n🔄 Changing log level to DEBUG...")
    config.set('log_level', 'DEBUG')
    config.save_config()
    
    # Re-initialize logging with new config
    new_logging_config = config.get_logging_config()
    initialize_logging(new_logging_config)
    
    logger = get_logger('integration_demo')
    logger.debug("This debug message should now be visible")
    logger.info("Integration demonstration complete")
    
    print("\n✅ Integration demonstration complete\n")

def demonstrate_error_handling():
    """Demonstrate error handling and logging."""
    print("🚨 Demonstrating Error Handling")
    print("-" * 40)
    
    logger = get_logger('error_demo')
    
    try:
        # Simulate an error
        raise ValueError("This is a simulated error for demonstration")
    except Exception as e:
        logger.error(f"Caught an error: {e}")
        logger.exception("Full error details with stack trace:")
    
    print("\n✅ Error handling demonstration complete\n")

def main():
    """Run the Phase 1 demonstration."""
    print("🚀 Phase 1 Component Demonstration")
    print("=" * 50)
    print("This demonstration shows the capabilities of the new foundation components:")
    print("• Central Logging System with performance tracking")
    print("• Simple Configuration Management with environment variable resolution")
    print("• Integration between logging and configuration")
    print("• Error handling and logging")
    print()
    
    try:
        demonstrate_logging()
        demonstrate_configuration()
        demonstrate_integration()
        demonstrate_error_handling()
        
        print("🎉 All demonstrations completed successfully!")
        print("\n📋 Summary of Phase 1 Features:")
        print("✓ Central logging singleton accessible by all classes")
        print("✓ Structured logging with consistent format")
        print("✓ Performance tracking with decorators and context managers")
        print("✓ Log rotation and file management")
        print("✓ Simple, flat configuration structure")
        print("✓ Environment variable resolution")
        print("✓ Instagram token management preserved")
        print("✓ Basic configuration validation")
        print("✓ Zero-config logging (works out of the box)")
        
    except Exception as e:
        print(f"❌ Demonstration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
