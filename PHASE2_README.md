# Phase 2 Implementation: Enhanced Data Collection

## Overview

Phase 2 of the Enhanced Video Generation System implements comprehensive data collection capabilities that expand the existing Instagram API and Google Cloud Storage API. This phase provides the foundation for context-aware AI-driven video generation by collecting detailed analytics and file inventories.

## Components Implemented

### 1. Enhanced Instagram Analytics Manager (`instagram_analytics.py`)

A comprehensive Instagram API manager that provides:
- **Account Analytics**: Followers, following, media count, biography, website
- **Media Insights**: Recent posts with engagement metrics, impressions, reach
- **Performance Analysis**: Hashtag effectiveness, engagement rates, video performance
- **Comment Analysis**: Recent comments with user interaction data
- **Activity Tracking**: Account activity and engagement trends

#### Key Features

- **Comprehensive Data Collection**: Account info, media insights, hashtag performance
- **Performance Metrics**: Engagement rates, play rates, comment quality analysis
- **Error Handling**: Graceful degradation when API calls fail
- **JSON Export**: Complete analytics data export for AI processing
- **Integration**: Uses Phase 1 logging and configuration systems

#### Usage Examples

```python
from instagram_analytics import InstagramAnalyticsManager

# Initialize the manager
analytics_manager = InstagramAnalyticsManager()

# Get account information
account_info = analytics_manager.get_account_info()
print(f"Followers: {account_info['followers_count']}")

# Get recent media with insights
recent_media = analytics_manager.get_recent_media(limit=25)
for media in recent_media:
    print(f"Post {media['id']}: {media['like_count']} likes")

# Analyze hashtag performance
hashtag_performance = analytics_manager.get_hashtag_performance(['3dprinting', 'pottery'])
for hashtag, stats in hashtag_performance.items():
    print(f"#{hashtag}: {stats['usage_count']} posts, {stats['avg_engagement_rate']}% engagement")

# Export complete analytics
analytics_data = analytics_manager.export_to_json("instagram_analytics.json")
```

### 2. Enhanced GCS Inventory Manager (`gcs_inventory.py`)

A comprehensive Google Cloud Storage inventory manager that provides:
- **File Categorization**: Automatic categorization by file type and extension
- **Metadata Extraction**: File size, creation time, MIME type, storage class
- **Folder Analysis**: Detailed folder structure and content analysis
- **Search Capabilities**: File search by name, metadata, or category
- **Inventory Generation**: Complete file inventory with statistics

#### Key Features

- **Smart File Categorization**: Video, audio, image, 3D model, document, archive
- **Comprehensive Metadata**: File attributes, timestamps, storage information
- **Folder Structure Analysis**: Subfolder detection and organization
- **Performance Optimization**: Efficient scanning and categorization
- **Error Handling**: Graceful handling of missing or inaccessible files

#### Usage Examples

```python
from gcs_inventory import GCSInventoryManager

# Initialize the manager
inventory_manager = GCSInventoryManager()

# Scan a specific folder
files = inventory_manager.scan_folder("video_uploads")
print(f"Found {len(files)} files in video_uploads")

# Categorize files
categories = inventory_manager.categorize_files(files)
for category, file_list in categories.items():
    if file_list:
        total_size = sum(f.get('size_mb', 0) for f in file_list)
        print(f"{category}: {len(file_list)} files, {total_size:.2f} MB")

# Generate complete inventory
inventory_data = inventory_manager.generate_inventory("gcs_inventory.json")
print(f"Total files: {inventory_data['bucket_summary']['total_files']}")

# Search for specific files
video_files = inventory_manager.get_files_by_category('video')
latest_files = inventory_manager.get_latest_files(limit=10)
search_results = inventory_manager.search_files("timelapse")
```

### 3. Simplified Testing Approach

The system now uses a simplified testing approach without unnecessary orchestration:
- **Direct Testing**: Test Instagram Analytics and GCS Inventory separately
- **JSON Output**: Tests directly output JSON result files
- **Clean Data**: GCS inventory includes only essential metadata
- **No Over-engineering**: Removed complex orchestrator layer

#### Key Benefits

- **Simpler Architecture**: Direct component testing without unnecessary abstraction
- **Cleaner Output**: JSON files contain only essential data
- **Easier Maintenance**: Fewer moving parts and dependencies
- **Better Performance**: No orchestration overhead
- **Clearer Results**: Direct output from each component

## Data Structures

### Instagram Analytics Data Structure

```json
{
  "export_info": {
    "exported_at": "2025-08-18T14:10:20",
    "export_version": "2.0",
    "source": "instagram_analytics_manager"
  },
  "account_info": {
    "account_id": "17841471684756809",
    "username": "autopotter",
    "followers_count": 1250,
    "following_count": 150,
    "media_count": 45,
    "biography": "3D printing pottery content...",
    "retrieved_at": "2025-08-18T14:10:20"
  },
  "recent_media": [
    {
      "id": "media_id_123",
      "media_type": "VIDEO",
      "like_count": 125,
      "comments_count": 8,
      "insights": {
        "impressions": 2500,
        "reach": 1800,
        "plays": 1200
      }
    }
  ],
  "hashtag_performance": {
    "3dprinting": {
      "usage_count": 15,
      "total_likes": 1875,
      "avg_engagement_rate": 3.2
    }
  },
  "summary_metrics": {
    "total_recent_likes": 3125,
    "total_recent_comments": 156,
    "avg_engagement_rate": 2.8
  }
}
```

### GCS Inventory Data Structure

```json
{
  "inventory_info": {
    "generated_at": "2025-08-18T14:10:20",
    "bucket_name": "autopot1-printdump",
    "folders_scanned": ["video_uploads", "music_uploads", "completed_works"],
    "inventory_version": "2.0"
  },
  "bucket_summary": {
    "total_files": 1250,
    "total_size_mb": 45.8,
    "folder_count": 3
  },
  "folder_inventories": {
    "video_uploads": {
      "folder_name": "video_uploads",
      "total_files": 310,
      "total_size_mb": 25.3,
      "file_categories": {
        "videos": [
          {
            "name": "video_uploads/timelapse_001.mp4",
            "size_mb": 15.2,
            "file_category": "video",
            "created_time": "2025-08-15T10:30:00",
            "video_metadata": {
              "format": "MP4",
              "content_type": "video"
            }
          }
        ]
      }
    }
  },
  "categorized_summary": {
    "videos": {"count": 310, "size_mb": 25.3},
    "audio": {"count": 45, "size_mb": 8.2},
    "images": {"count": 125, "size_mb": 12.3}
  }
}
```

## Configuration Requirements

### Instagram Configuration

```json
{
  "instagram_app_id": "${FB_APP_ID}",
  "instagram_app_secret": "${FB_APP_SECRET}",
  "instagram_user_id": "${INSTAGRAM_USER_ID}",
  "instagram_access_token": "${INSTAGRAM_ACCESS_TOKEN}",
  "instagram_token_expiration": "2025-08-23 21:00:33",
  "instagram_days_before_refresh": 7
}
```

### GCS Configuration

```json
{
  "gcs_bucket": "autopot1-printdump",
  "gcs_api_key_path": "${GCS_API_KEY_PATH}",
  "gcs_folders": ["video_uploads", "music_uploads", "completed_works", "wip_photos", "build_photos"],
  "gcs_draft_folder": "draft_videos"
}
```

## Testing

### Running Tests

```bash
# Activate conda environment
conda activate sympy3d

# Run the complete test suite
python3 test_phase2.py

# Check generated JSON results
ls -la *_result.json
```

### Test Coverage

The test suite covers:
- ✅ Instagram Analytics Manager initialization and methods
- ✅ GCS Inventory Manager initialization and file operations
- ✅ Integration between Phase 2 components
- ✅ Error handling and graceful degradation
- ✅ Configuration validation and requirements checking
- ✅ Direct JSON output generation

### Expected Test Results

- **Instagram Analytics**: Should pass and generate `instagram_analytics_result.json`
- **GCS Inventory**: Should pass and generate `gcs_inventory_result.json`
- **Integration**: Should pass for configuration and logging integration
- **Error Handling**: Should pass for graceful degradation testing

## Integration with Phase 1

### Logging Integration

All Phase 2 components use the Phase 1 central logging system:

```python
from logger import get_logger, get_performance_logger

# Get component-specific logger
logger = get_logger('instagram_analytics')

# Performance tracking
performance_logger = get_performance_logger()

@performance_logger.performance_logger("data_collection")
def collect_data():
    # Data collection logic
    pass
```

### Configuration Integration

All components use the Phase 1 configuration management:

```python
from config import get_config

# Get configuration
config = get_config()

# Access specific configuration sections
instagram_config = config.get_instagram_config()
gcs_config = config.get_gcs_config()
```

## Performance Characteristics

### Instagram Analytics

- **API Rate Limits**: Respects Instagram Graph API rate limits
- **Data Caching**: No built-in caching (real-time data collection)
- **Error Recovery**: Graceful handling of API failures
- **Performance**: Optimized for batch collection operations

### GCS Inventory

- **Scanning Performance**: Efficient blob listing and metadata extraction
- **Memory Usage**: Minimal memory footprint during scanning
- **Network Optimization**: Batch operations where possible
- **Error Handling**: Continues operation despite individual file errors

### Data Collection Orchestrator

- **Parallel Operations**: Sequential collection (can be enhanced for parallel)
- **Resource Management**: Efficient memory and network usage
- **Status Monitoring**: Real-time status updates
- **Export Optimization**: Organized data export with compression

## Error Handling

### Graceful Degradation

The system is designed to continue operation even when some components fail:

```python
# Instagram manager fails, but GCS continues
try:
    instagram_data = orchestrator.collect_instagram_data()
except Exception as e:
    logger.warning(f"Instagram collection failed: {e}")
    # Continue with GCS collection

# GCS collection continues
gcs_data = orchestrator.collect_gcs_data()
```

### Validation and Requirements

Comprehensive validation ensures system reliability:

```python
# Validate requirements before collection
validation = orchestrator.validate_collection_requirements()
if not validation['overall_validation']:
    logger.error("Cannot proceed with data collection")
    return

# Proceed with collection
collection_results = orchestrator.collect_all_data()
```

## Data Export and Storage

### File Organization

Collected data is organized by timestamp and source:

```
collected_data/
├── instagram_analytics_20250818_141020.json
├── gcs_inventory_20250818_141020.json
└── data_collection_summary_20250818_141020.json
```

### Export Formats

All data is exported in structured JSON format:
- **Instagram Analytics**: Complete account and media analytics
- **GCS Inventory**: File inventory with metadata and categorization
- **Collection Summary**: Orchestration results and statistics

## Benefits of Phase 2

1. **Comprehensive Data Collection**: Instagram analytics and GCS inventory
2. **Context Awareness**: Rich data for AI-driven video generation
3. **Performance Insights**: Engagement metrics and hashtag effectiveness
4. **Resource Cataloging**: Complete file inventory with metadata
5. **Unified Interface**: Single orchestrator for all data collection
6. **Error Resilience**: Graceful degradation and error handling
7. **Integration Ready**: Foundation for AI assistant integration
8. **Export Capabilities**: JSON export for AI processing

## Next Steps

Phase 2 provides the data foundation for:
- **Phase 3**: AI Assistant Integration (GPT Assistant Manager)
- **Phase 4**: Video Generation Workflow (JSON2Video integration)
- **Phase 5**: Approval & Posting Workflow (Auto-posting system)

## Technical Notes

- **Dependencies**: Requires `google-cloud-storage` package
- **API Limits**: Respects Instagram Graph API rate limits
- **Memory Management**: Efficient handling of large file inventories
- **Error Recovery**: Comprehensive error handling and logging
- **Performance**: Optimized for production data collection
- **Scalability**: Designed for growing data volumes

## Troubleshooting

### Common Issues

1. **Instagram API Errors**: Check access token validity and permissions
2. **GCS Access Issues**: Verify service account key and bucket permissions
3. **Configuration Errors**: Ensure all required environment variables are set
4. **Rate Limiting**: Instagram API has strict rate limits
5. **File Access**: Some GCS files may be inaccessible due to permissions

### Debug Mode

Enable debug logging for detailed troubleshooting:

```python
from logger import initialize_logging
initialize_logging({'log_level': 'DEBUG'})
```

## Files Created/Modified

- **`instagram_analytics.py`** - Enhanced Instagram analytics manager
- **`gcs_inventory.py`** - Enhanced GCS inventory manager (simplified output)
- **`test_phase2.py`** - Simplified test suite with direct JSON output
- **`PHASE2_README.md`** - This documentation

## Generated Output Files

- **`instagram_analytics_result.json`** - Instagram account analytics data
- **`gcs_inventory_result.json`** - Simplified GCS file inventory (name, size, URL, metadata)

## Dependencies

- **Phase 1 Components**: `logger.py`, `config.py`
- **External Packages**: `google-cloud-storage`, `requests`
- **Python Version**: 3.7+ for type hints and modern features
- **Conda Environment**: `sympy3d` (recommended)
