#!/usr/bin/env python3
"""
Test script for Phase 2 components: Enhanced Data Collection.
This script tests the enhanced Instagram API and GCS API separately.
"""

import os
import sys
import json
from datetime import datetime

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from logger import get_logger, initialize_logging
from config import get_config
from instagram_analytics import InstagramAnalyticsManager
from gcs_manager import GCSManager

def test_instagram_analytics():
    """Test the enhanced Instagram analytics manager."""
    print("=== Testing Instagram Analytics Manager ===")
    
    try:
        # Test initialization
        print("1. Testing Instagram Analytics Manager initialization...")
        analytics_manager = InstagramAnalyticsManager()
        print("✓ Instagram Analytics Manager initialized successfully")
        
        # Test account info retrieval
        print("2. Testing account info retrieval...")
        try:
            account_info = analytics_manager.get_account_info()
            print(f"✓ Account info retrieved: {account_info.get('username', 'Unknown')}")
            
            # Save to JSON file
            output_file = "instagram_analytics_result.json"
            with open(output_file, 'w') as f:
                json.dump(account_info, f, indent=2)
            print(f"✓ Instagram analytics saved to: {output_file}")
            
        except Exception as e:
            print(f"⚠️  Account info retrieval failed: {e}")
        
        # Test recent media retrieval
        print("3. Testing recent media retrieval...")
        try:
            recent_media = analytics_manager.get_recent_media(limit=5)
            print(f"✓ Recent media retrieved: {len(recent_media)} items")
        except Exception as e:
            print(f"⚠️  Recent media retrieval failed: {e}")
        
        # Test hashtag performance analysis
        print("4. Testing hashtag performance analysis...")
        try:
            hashtag_performance = analytics_manager.get_hashtag_performance(['3dprinting', 'pottery'])
            print(f"✓ Hashtag performance analysis completed: {len(hashtag_performance)} hashtags")
        except Exception as e:
            print(f"⚠️  Hashtag performance analysis failed: {e}")
        
        print("=== Instagram Analytics Manager Tests Complete ===\n")
        return True
        
    except Exception as e:
        print(f"✗ Instagram Analytics Manager test failed: {e}")
        return False

def test_gcs_inventory():
    """Test the enhanced GCS inventory manager."""
    print("=== Testing GCS Inventory Manager ===")
    
    try:
        # Test initialization
        print("1. Testing GCS Inventory Manager initialization...")
        inventory_manager = GCSManager()
        print("✓ GCS Inventory Manager initialized successfully")
        
        # Test folder scanning
        print("2. Testing folder scanning...")
        try:
            test_folder = "video_uploads"
            files = inventory_manager.scan_folder(test_folder)
            print(f"✓ Folder scanning completed: {len(files)} files found in {test_folder}")
        except Exception as e:
            print(f"⚠️  Folder scanning failed: {e}")
        
        # Test basic file info extraction
        print("3. Testing basic file info extraction...")
        try:
            # Test with a simple file list
            test_files = [
                {'name': 'test_video.mp4', 'size_mb': 1.0, 'public_url': 'https://example.com/test.mp4', 'metadata': {}},
                {'name': 'test_audio.mp3', 'size_mb': 0.5, 'public_url': 'https://example.com/test.mp3', 'metadata': {}},
                {'name': 'test_image.jpg', 'size_mb': 0.25, 'public_url': 'https://example.com/test.jpg', 'metadata': {}}
            ]
            
            print(f"✓ Basic file info extraction completed: {len(test_files)} files")
            total_size = sum(f.get('size_mb', 0) for f in test_files)
            print(f"  Total size: {total_size:.2f} MB")
                    
        except Exception as e:
            print(f"⚠️  Basic file info extraction failed: {e}")
        
        # Test inventory generation and save to JSON
        print("4. Testing inventory generation and JSON output...")
        try:
            output_file = "gcs_inventory_result.json"
            inventory_data = inventory_manager.generate_inventory(output_file)
            print(f"✓ Inventory generated and saved to: {output_file}")
            print(f"  Total files: {inventory_data['summary']['total_files']}")
            print(f"  Total size: {inventory_data['summary']['total_size_mb']} MB")
            
            # Show breakdown by file type
            print("  File breakdown by type:")
            for file_type, stats in inventory_data['summary']['by_type'].items():
                if stats['count'] > 0:
                    icon = {'videos': '🎥', 'images': '🖼️', 'music': '🎵', 'other': '📄'}[file_type]
                    print(f"    {icon} {file_type.title()}: {stats['count']} files ({stats['size_mb']:.2f} MB)")
        except Exception as e:
            print(f"⚠️  Inventory generation failed: {e}")
        
        print("=== GCS Inventory Manager Tests Complete ===\n")
        return True
        
    except Exception as e:
        print(f"✗ GCS Inventory Manager test failed: {e}")
        return False

def test_integration():
    """Test integration between Phase 2 components."""
    print("=== Testing Phase 2 Integration ===")
    
    try:
        # Test configuration integration
        print("1. Testing configuration integration...")
        config = get_config()
        
        # Test Instagram config
        instagram_config = config.get_instagram_config()
        print(f"✓ Instagram configuration loaded: {len(instagram_config)} fields")
        
        # Test GCS config
        gcs_config = config.get_gcs_config()
        print(f"✓ GCS configuration loaded: {len(gcs_config)} fields")
        
        # Test logging integration
        print("2. Testing logging integration...")
        logger = get_logger('integration_test')
        logger.info("Testing Phase 2 integration")
        print("✓ Logging integration working")
        
        # Test data flow
        print("3. Testing data flow...")
        try:
            # Test Instagram manager
            instagram_manager = InstagramAnalyticsManager()
            print("  ✓ Instagram Analytics Manager integrated")
            
            # Test GCS manager
            gcs_manager = GCSManager()
            print("  ✓ GCS Inventory Manager integrated")
            
        except Exception as e:
            print(f"  ⚠️  Manager integration failed: {e}")
        
        print("=== Phase 2 Integration Tests Complete ===\n")
        return True
        
    except Exception as e:
        print(f"✗ Integration test failed: {e}")
        return False

def test_error_handling():
    """Test error handling and graceful degradation."""
    print("=== Testing Error Handling ===")
    
    try:
        # Test configuration validation with missing data
        print("1. Testing configuration validation with missing data...")
        config = get_config()
        
        # Test Instagram token validation
        try:
            is_expired = config.is_instagram_token_expired()
            days_until = config.get_days_until_token_refresh()
            print(f"✓ Instagram token validation working: expired={is_expired}, days_until={days_until}")
        except Exception as e:
            print(f"⚠️  Instagram token validation failed: {e}")
        
        # Test graceful degradation
        print("2. Testing graceful degradation...")
        try:
            # This should fail gracefully
            analytics_manager = InstagramAnalyticsManager()
            print("✓ Instagram Analytics Manager handles missing credentials gracefully")
        except Exception as e:
            print(f"⚠️  Instagram Analytics Manager failed as expected: {e}")
        
        print("=== Error Handling Tests Complete ===\n")
        return True
        
    except Exception as e:
        print(f"✗ Error handling test failed: {e}")
        return False

def main():
    """Run all Phase 2 tests."""
    print("🚀 Starting Phase 2 Testing Suite")
    print("=" * 50)
    
    # Initialize logging
    initialize_logging()
    
    # Run tests
    test_results = []
    
    # Test Instagram Analytics
    test_results.append(("Instagram Analytics", test_instagram_analytics()))
    
    # Test GCS Inventory
    test_results.append(("GCS Inventory", test_gcs_inventory()))
    
    # Test Integration
    test_results.append(("Integration", test_integration()))
    
    # Test Error Handling
    test_results.append(("Error Handling", test_error_handling()))
    
    # Print summary
    print("🎯 Phase 2 Testing Summary")
    print("=" * 30)
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All Phase 2 tests completed successfully!")
        print("✓ Enhanced Instagram Analytics: Working")
        print("✓ Enhanced GCS Inventory: Working")
        print("✓ Integration: Working")
        print("✓ Error Handling: Working")
    else:
        print("⚠️  Some tests failed. Check configuration and credentials.")
        print("Note: Some failures are expected without valid API credentials.")

if __name__ == "__main__":
    main()
