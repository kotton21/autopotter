# Phase 2 Implementation: Enhanced Instagram Analytics & Data Collection

## Overview

Phase 2 of the Enhanced Video Generation System implements comprehensive Instagram analytics capabilities that expand the existing Instagram API with enhanced data collection, comment analysis, and performance insights. This phase provides the foundation for context-aware AI-driven video generation by collecting detailed analytics, engagement metrics, and user interaction data.

## Components Implemented

### 1. Enhanced Instagram Analytics Manager (`instagram_analytics.py`)

A comprehensive Instagram API manager that provides:
- **Account Analytics**: Followers, following, media count, biography, website, profile picture
- **Media Insights**: Recent posts with detailed engagement metrics, reach, views, interactions
- **Comment Analysis**: Top-level comments with nested replies and user interaction data
- **Performance Analysis**: Hashtag effectiveness, engagement rates, video performance
- **Account Insights**: Day, week, and 28-day performance metrics
- **Activity Tracking**: Account activity and engagement trends

#### Key Features

- **Comprehensive Data Collection**: Account info, media insights, hashtag performance, comments with replies
- **Performance Metrics**: Engagement rates, reach metrics, profile views, website clicks
- **Nested Comment Retrieval**: Recursive fetching of comment replies for complete conversation threads
- **Configurable Limits**: Configurable parameters for media, comments, and replies retrieval
- **Error Handling**: Graceful degradation when API calls fail
- **JSON Export**: Complete analytics data export for AI processing
- **Integration**: Uses Phase 1 logging and configuration systems

#### New Configuration System

The Instagram analytics manager now supports configurable data retrieval limits:

```json
{
  "max_media_items": 7,
  "max_comments_per_media": 10,
  "max_replies_per_comment": 5
}
```

**Benefits:**
- **Performance Control**: Limit API calls to prevent rate limiting
- **Data Volume Management**: Control how much data is retrieved
- **Flexible Configuration**: Easy to adjust without code changes
- **Transparency**: See exactly what limits are being applied

#### Usage Examples

```python
from instagram_analytics import InstagramAnalyticsManager

# Initialize the manager (uses config defaults)
analytics_manager = InstagramAnalyticsManager()

# Get account information with insights
account_info = analytics_manager.get_account_info()
print(f"Followers: {account_info['followers_count']}")
print(f"Account Insights: {account_info['account_insights']}")

# Get recent media with insights and comments
recent_media = analytics_manager.get_recent_media()  # Uses config limit
for media in recent_media:
    print(f"Post {media['id']}: {media['like_count']} likes")
    print(f"Insights: {media['insights']}")
    print(f"Comments: {len(media['comments'])} comments")
    
    # Access nested replies
    for comment in media['comments']:
        print(f"  Comment: {comment['text']}")
        print(f"  Replies: {len(comment['replies'])} replies")

# Export complete analytics
analytics_data = analytics_manager.export_to_json("instagram_analytics.json")
```

### 2. Enhanced Comment and Reply System

**New Features:**
- **Top-level Comments**: Retrieves comments for each media item
- **Nested Replies**: Recursively fetches replies to comments
- **User Information**: Clean user data structure without redundancy
- **Configurable Limits**: Control comment and reply retrieval depth

**Comment Structure:**
```json
{
  "id": "comment_id",
  "text": "Comment text",
  "timestamp": "2025-08-14T14:08:17+0000",
  "username": "username",
  "from": {
    "id": "user_id",
    "username": "username"
  },
  "like_count": 0,
  "replies": [
    {
      "id": "reply_id",
      "text": "Reply text",
      "timestamp": "2025-08-14T14:08:32+0000",
      "username": "username",
      "from": {
        "id": "user_id",
        "username": "username"
      },
      "like_count": 0
    }
  ]
}
```

### 3. Enhanced Media Insights

**Improved Metrics:**
- **Video Content**: reach, likes, comments, saved, shares, total_interactions, views
- **Image Content**: reach, likes, comments, saved, shares, total_interactions, profile_visits, profile_activity
- **Carousel Content**: Same metrics as image content
- **Automatic Period**: Uses lifetime period for media insights (Instagram API requirement)

**Insights Structure:**
```json
{
  "reach": 301,
  "likes": 1,
  "comments": 0,
  "saved": 0,
  "shares": 0,
  "total_interactions": 1,
  "views": 471
}
```

### 4. Enhanced Account Insights

**Comprehensive Metrics:**
- **Reach**: Day, week, and 28-day periods
- **Profile Views**: Total value metrics
- **Website Clicks**: User interaction tracking
- **Accounts Engaged**: Engagement metrics
- **Total Interactions**: Overall engagement
- **Likes & Comments**: Content performance

**Account Insights Structure:**
```json
{
  "reach": {
    "day": 292,
    "week": 4775,
    "days_28": 54575
  },
  "profile_views": {
    "day": 7
  },
  "website_clicks": {
    "day": 0
  },
  "accounts_engaged": {
    "day": 9
  },
  "total_interactions": {
    "day": 8
  },
  "likes": {
    "day": 8
  },
  "comments": {
    "day": 0
  }
}
```

## Data Structures

### Instagram Analytics Data Structure

```json
{
  "export_info": {
    "exported_at": "2025-08-19T10:47:00.128900",
    "export_version": "2.0",
    "source": "instagram_analytics_manager",
    "configuration": {
      "max_media_items": 7,
      "max_comments_per_media": 10,
      "max_replies_per_comment": 5
    }
  },
  "account_info": {
    "account_id": "17841471684756809",
    "username": "autopot.ter",
    "name": "Unnamed",
    "media_count": 80,
    "followers_count": 76,
    "following_count": 9,
    "biography": "I'm an AI pottery robot...",
    "website": "",
    "profile_picture_url": "https://...",
    "retrieved_at": "2025-08-19T10:47:12.912118",
    "account_insights": {
      "reach": {"day": 292, "week": 4775, "days_28": 54575},
      "profile_views": {"day": 7},
      "website_clicks": {"day": 0},
      "accounts_engaged": {"day": 9},
      "total_interactions": {"day": 8},
      "likes": {"day": 8},
      "comments": {"day": 0}
    }
  },
  "recent_media": [
    {
      "id": "media_id",
      "media_type": "VIDEO",
      "media_url": "https://...",
      "thumbnail_url": "https://...",
      "permalink": "https://...",
      "timestamp": "2025-08-18T23:32:42+0000",
      "caption": "Post caption...",
      "like_count": 1,
      "comments_count": 0,
      "insights": {
        "reach": 152,
        "likes": 1,
        "comments": 0,
        "saved": 0,
        "shares": 0,
        "total_interactions": 1,
        "views": 232
      },
      "comments": [
        {
          "id": "comment_id",
          "text": "Comment text",
          "timestamp": "2025-08-14T14:08:17+0000",
          "username": "username",
          "from": {"id": "user_id", "username": "username"},
          "like_count": 0,
          "replies": [
            {
              "id": "reply_id",
              "text": "Reply text",
              "timestamp": "2025-08-14T14:08:32+0000",
              "username": "username",
              "from": {"id": "user_id", "username": "username"},
              "like_count": 0
            }
          ]
        }
      ]
    }
  ],
  "hashtag_performance": {
    "art": {
      "usage_count": 43,
      "total_likes": 271,
      "total_comments": 16,
      "avg_engagement_rate": 0,
      "avg_likes": 6.3,
      "avg_comments": 0.4
    }
  },
  "summary_metrics": {
    "total_recent_likes": 32,
    "total_recent_comments": 0,
    "total_recent_impressions": 0,
    "avg_engagement_rate": 0,
    "media_count_analyzed": 5
  }
}
```

## Configuration Requirements

### Instagram Analytics Configuration

```json
{
  "instagram_app_id": "${FB_APP_ID}",
  "instagram_app_secret": "${FB_APP_SECRET}",
  "instagram_user_id": "${INSTAGRAM_USER_ID}",
  "instagram_access_token": "${INSTAGRAM_ACCESS_TOKEN}",
  "instagram_token_expiration": "2025-08-23 21:00:33",
  "instagram_days_before_refresh": 7,
  
  "max_media_items": 7,
  "max_comments_per_media": 10,
  "max_replies_per_comment": 5
}
```

### Environment Variables Required

```bash
# Instagram API Configuration
FB_APP_ID=your_facebook_app_id
FB_APP_SECRET=your_facebook_app_secret
INSTAGRAM_USER_ID=your_instagram_user_id
INSTAGRAM_ACCESS_TOKEN=your_instagram_access_token
```

## Testing

### Running Tests

```bash
# Basic export (uses config defaults)
python instagram_analytics.py -o output.json

# Full diagnostics and testing
python instagram_analytics.py --fulltest -o output.json

# Help and options
python instagram_analytics.py --help
```

### Test Coverage

The test suite covers:
- ✅ Instagram Analytics Manager initialization and configuration
- ✅ Account information retrieval with insights
- ✅ Media retrieval with configurable limits
- ✅ Comment and reply retrieval with nested structure
- ✅ Media insights for different content types
- ✅ Account insights across multiple time periods
- ✅ Hashtag performance analysis
- ✅ Error handling and graceful degradation
- ✅ Configuration validation and requirements checking
- ✅ Direct JSON output generation

### Expected Test Results

- **Instagram Analytics**: Should pass and generate JSON with configurable limits
- **Configuration Display**: Should show current limits (7, 10, 5 by default)
- **Data Retrieval**: Should respect configured limits for media, comments, and replies
- **Error Handling**: Should pass for graceful degradation testing

## Integration with Phase 1

### Logging Integration

All Phase 2 components use the Phase 1 central logging system:

```python
from logger import get_logger

# Get component-specific logger
logger = get_logger('instagram_analytics')

# Log initialization with configuration
logger.info(f"Instagram Analytics Manager initialized with limits: media={self.max_media_items}, comments={self.max_comments_per_media}, replies={self.max_replies_per_comment}")
```

### Configuration Integration

All components use the Phase 1 configuration management:

```python
from config import get_config

# Get configuration
config = get_config()

# Access Instagram analytics configuration
max_media_items = config.get('max_media_items', 25)
max_comments_per_media = config.get('max_comments_per_media', 50)
max_replies_per_comment = config.get('max_replies_per_comment', 25)
```

## Performance Characteristics

### Instagram Analytics

- **API Rate Limits**: Respects Instagram Graph API rate limits
- **Configurable Limits**: User-defined limits for media, comments, and replies
- **Data Caching**: No built-in caching (real-time data collection)
- **Error Recovery**: Graceful handling of API failures
- **Performance**: Optimized for batch collection operations with configurable depth

### Data Retrieval Optimization

- **Selective Fetching**: Only retrieves data within configured limits
- **Efficient API Calls**: Minimizes API requests through smart field selection
- **Memory Management**: Efficient handling of comment/reply trees
- **Network Optimization**: Batch operations where possible

## Error Handling

### Graceful Degradation

The system is designed to continue operation even when some components fail:

```python
# Comment retrieval fails, but media insights continue
try:
    comments = self.get_media_comments(media_id)
    media_item['comments'] = comments
except Exception as e:
    self.logger.debug(f"Failed to retrieve comments for media {media_id}: {e}")
    media_item['comments'] = []

# Media insights continue
insights = self.get_media_insights(media_id, media_type)
media_item['insights'] = insights
```

### Validation and Requirements

Comprehensive validation ensures system reliability:

```python
# Validate Instagram account connection
if not self.instagram_account_id:
    self.logger.warning("No Instagram Business Account found")
    return []

# Validate required permissions
permissions = self.check_token_permissions()
if not permissions.get('is_valid'):
    self.logger.warning("Token permissions insufficient for full functionality")
```

## Data Export and Storage

### File Organization

Collected data is organized by timestamp and configuration:

```
output/
├── instagram_analytics_20250819_104700.json
├── instagram_analytics_20250819_104800.json
└── instagram_analytics_20250819_104900.json
```

### Export Formats

All data is exported in structured JSON format:
- **Instagram Analytics**: Complete account, media, and comment analytics
- **Configuration Tracking**: Current limits and settings used
- **Performance Metrics**: Engagement, reach, and interaction data
- **Comment Threads**: Complete conversation trees with nested replies

## Benefits of Phase 2

1. **Comprehensive Data Collection**: Instagram analytics with comments and replies
2. **Configurable Performance**: User-defined limits for data retrieval
3. **Context Awareness**: Rich data for AI-driven video generation
4. **Performance Insights**: Engagement metrics and hashtag effectiveness
5. **User Interaction Data**: Complete comment and reply analysis
6. **Unified Interface**: Single manager for all Instagram data collection
7. **Error Resilience**: Graceful degradation and error handling
8. **Integration Ready**: Foundation for AI assistant integration
9. **Export Capabilities**: JSON export for AI processing
10. **Clean Data Structure**: No redundant fields, optimized for processing

## Next Steps

Phase 2 provides the data foundation for:
- **Phase 3**: AI Assistant Integration (GPT Assistant Manager)
- **Phase 4**: Video Generation Workflow (JSON2Video integration)
- **Phase 5**: Approval & Posting Workflow (Auto-posting system)

## Technical Notes

- **Dependencies**: Requires `requests` package for Instagram API calls
- **API Limits**: Respects Instagram Graph API rate limits and permissions
- **Memory Management**: Efficient handling of comment/reply trees
- **Error Recovery**: Comprehensive error handling and logging
- **Performance**: Optimized for production data collection with configurable depth
- **Scalability**: Designed for growing data volumes with user-defined limits

## Troubleshooting

### Common Issues

1. **Instagram API Errors**: Check access token validity and permissions
2. **Rate Limiting**: Instagram API has strict rate limits - use configurable limits
3. **Configuration Errors**: Ensure all required environment variables are set
4. **Permission Issues**: Verify Instagram Business Account access and token scopes
5. **Data Volume**: Adjust configuration limits if experiencing performance issues

### Debug Mode

Enable debug logging for detailed troubleshooting:

```python
from logger import initialize_logging
initialize_logging({'log_level': 'DEBUG'})
```

### Configuration Issues

Check your configuration values:

```bash
# Run with full test to see current configuration
python instagram_analytics.py --fulltest

# Check configuration display
python instagram_analytics.py -o test.json
```

## Files Created/Modified

- **`instagram_analytics.py`** - Enhanced Instagram analytics manager with configuration system
- **`config.py`** - Added Instagram analytics configuration defaults
- **`autopost_config.enhanced.json`** - Added Instagram analytics configuration
- **`PHASE2_README.md`** - This updated documentation

## Generated Output Files

- **`instagram_analytics_result.json`** - Instagram account analytics with comments and replies
- **`test_config_output.json`** - Test output showing configuration integration

## Dependencies

- **Phase 1 Components**: `logger.py`, `config.py`
- **External Packages**: `requests`
- **Python Version**: 3.7+ for type hints and modern features
- **Conda Environment**: `sympy3d` (recommended)

## Recent Improvements

### v2.0 Features

- **Configuration System**: User-defined limits for media, comments, and replies
- **Enhanced Comments**: Nested comment and reply retrieval
- **Improved Insights**: Better metrics and period support
- **Clean Data Structure**: Removed redundant user information fields
- **Performance Optimization**: Configurable data retrieval depth
- **Better Error Handling**: Graceful degradation for failed API calls

### Configuration Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `max_media_items` | 7 | Maximum number of media posts to retrieve |
| `max_comments_per_media` | 10 | Maximum comments per media item |
| `max_replies_per_comment` | 5 | Maximum replies per comment |

These defaults provide a good balance between data completeness and API performance, while allowing customization for different use cases.
