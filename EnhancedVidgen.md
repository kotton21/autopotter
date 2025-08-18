# Enhanced Video Generation System

## Overview
This document outlines the enhanced video generation system that replaces the current rigid, linear video generation flow with a context-aware AI-driven approach. The system will catalog available resources, leverage AI assistance for creative video proposals, and implement an automated approval and posting workflow.

## System Architecture

### Core Components

#### 1. Data Collection Layer
- **Instagram API Module** (`instagram_api.py`)
- **Google Cloud Storage Module** (`gcs_api.py`)
- **Configuration Management** (`config.py`)

#### 2. AI Assistant Layer
- **GPT Assistant Manager** (`gpt_assistant.py`)
- **Thread Management**
- **File Upload Capabilities**

#### 3. Video Generation Layer
- **JSON2Video API Integration**
- **Draft Management**
- **Resource Coordination**

#### 4. Workflow Management Layer
- **Google Sheets Integration**
- **Status Tracking**
- **Auto-posting System** (`autopost.py`)

#### 5. Logging & Monitoring Layer
- **Centralized Logging System**
- **Structured Logging with Context**
- **Log Rotation and Management**

## Implementation Plan

### Phase 1: Foundation - Logging & Configuration

#### Central Logging System (`logger.py`)
- **Standalone logging singleton** accessible by all classes
- **Structured logging** with consistent format across components
- **Log levels** (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- **Log rotation** to prevent disk space issues
- **Performance logging** decorators and context managers
- **Thread-safe** initialization and operation
- **Terminal output by default** when no log file is specified

#### Configuration Management (`config.py`)
- **Simple, flat configuration structure** for easy maintenance
- **Environment variable resolution** for secure credential management
- **Basic validation** of required configuration sections
- **Instagram token management** - preserve existing refresh capabilities:
  - Token expiration checking
  - Short-lived to long-lived token conversion
  - Automatic refresh before expiration
- **Minimal complexity** - avoid over-engineering

### Phase 2: Enhanced Data Collection

#### Instagram API Expansion (`instagram_api.py`)
- Download account information (followers, following, activity)
- Retrieve insights on recent video performance
- Collect recent comments and interactions
- Output structured JSON with account analytics

#### GCS API Enhancement (`gcs_api.py`)
- Walk configured GCS folders from config file
- Categorize files by parent folder structure
- Extract file metadata and attributes
- Generate categorized file inventory JSON

### Phase 3: AI Assistant Integration

#### GPT Assistant Manager (`gpt_assistant.py`)
- Create new assistant threads if none exist
- Handle thread creation failures gracefully
- Support for uploading JSON data files and additional context files
- Store assistant ID and thread ID in configuration

### Phase 4: Video Generation Workflow

#### Main Generation Flow
1. **Data Acquisition & Upload**
   - Collect Instagram analytics JSON
   - Gather GCS file inventory JSON
   - Create or retrieve existing assistant thread
   - Upload additional context files

2. **AI Proposal Generation**
   - Assistant analyzes available resources
   - Generates video ideas based on intent prompts
   - Outputs structured JSON with multiple draft proposals, each containing:
     - Video strategy description
     - Resource utilization plan
     - The draft's JSON2Video configuration

3. **Draft Generation & Storage**
   - Execute JSON2Video API calls for each draft
   - Upload generated videos to GCS draft folder
   - Log entries in Google Sheets with columns:
     - Status (Draft/Approved/Posted/Denied)
     - Video number
     - Production date
     - Caption
     - Link
     - Strategy description

### Phase 5: Approval & Posting Workflow

#### Auto-posting System (`autopost.py`)
- Poll Google Sheets for status changes to "Approved"
- Post latest approved video to Instagram
- Implement timeout mechanism to prevent infinite execution
- Store posting configuration in dedicated config file

## Configuration Structure

### Main Configuration File
```yaml
# Enhanced Video Generation Configuration
# Keep configuration simple and flat for easy maintenance

# Instagram Configuration
instagram_app_id: "${FB_APP_ID}"
instagram_app_secret: "${FB_APP_SECRET}"
instagram_user_id: "${INSTAGRAM_USER_ID}"
instagram_access_token: "${INSTAGRAM_ACCESS_TOKEN}"
instagram_token_expiration: "2025-08-23 21:00:33"
instagram_days_before_refresh: 7

# GCS Configuration
gcs_bucket: "autopot1-printdump"
gcs_api_key_path: "${GCS_API_KEY_PATH"
gcs_folders: ["video_uploads", "music_uploads", "completed_works", "wip_photos", "build_photos"]
gcs_draft_folder: "draft_videos"

# OpenAI Configuration
openai_api_key: "${OPENAI_API_KEY}"
gpt_assistant_id: null  # Will be populated after creation
gpt_thread_id: null     # Will be populated after creation
gpt_creation_prompt: "You are a creative AI assistant for 3D printing pottery content."

# JSON2Video Configuration
json2video_api_key: "${JSON2VIDEO_API_KEY}"
json2video_base_url: "https://api.json2video.com/v2"
json2video_timeout: 300

# Google Sheets Configuration
sheets_spreadsheet_id: "${GOOGLE_SHEETS_ID}"
sheets_credentials_path: "${GOOGLE_CREDENTIALS_PATH}"

# Auto-posting Configuration
autopost_timeout: 300
autopost_poll_interval: 30

# Logging Configuration (all optional - defaults to terminal output)
log_level: "INFO"                    # Optional: DEBUG, INFO, WARNING, ERROR, CRITICAL
log_file: null                       # Optional: null = terminal only, "path/to/file.log" = file + terminal
log_max_size: "10MB"                # Optional: only used if log_file is specified
log_backup_count: 5                 # Optional: only used if log_file is specified
log_console_output: true            # Optional: always true if no log_file specified
```

## Foundation Components

### Central Logging System (`logger.py`)
- **Global singleton** accessible by importing `from logger import get_logger`
- **Automatic initialization** when first accessed
- **Performance tracking** with decorators and context managers
- **Error logging** with full stack traces
- **Log rotation** based on file size (only if log file specified)
- **Terminal output by default** - no configuration required for basic operation
- **File + terminal output** when log file is specified in config

### Simple Configuration Management (`config.py`)
- **Flat key-value structure** for easy reading and editing
- **Environment variable substitution** for sensitive data
- **Basic validation** of required fields
- **Instagram token helper methods** for refresh operations
- **No complex nested structures** or over-engineering
- **Graceful defaults** - system works even with minimal configuration

### Instagram Token Management
The configuration system maintains essential Instagram token capabilities:
- **Simple token expiration checking** - days until refresh
- **Basic refresh functionality** - convert short to long tokens
- **Minimal configuration** - just the essential fields needed
- **Integration with existing logic** - preserve current refresh behavior

## Class Structure

### InstagramAPIManager
- `get_account_info()` - Retrieve account analytics
- `get_recent_activity()` - Fetch recent interactions
- `get_video_insights()` - Retrieve video performance
- `export_to_json()` - Generate analytics JSON
- **Preserved methods:**
  - `check_refresh_access_token()` - Check and refresh if needed
  - `get_long_lived_token()` - Convert short to long token
  - `is_token_expired()` - Check token expiration status

### GCSFileManager
- `scan_folders()` - Walk configured GCS directories
- `categorize_files()` - Group files by folder structure
- `extract_metadata()` - Get file attributes
- `generate_inventory()` - Create file catalog JSON

### GPTAssistantManager
- `create_or_get_thread()` - Handle thread lifecycle
- `upload_files()` - Add context files to assistant
- `generate_proposals()` - Request video ideas
- `parse_responses()` - Extract structured proposals

### VideoGenerator
- `create_drafts()` - Execute JSON2Video API calls
- `upload_to_gcs()` - Store generated videos
- `log_to_sheets()` - Update tracking spreadsheet

### AutoPostManager
- `monitor_approvals()` - Watch for status changes
- `post_to_instagram()` - Upload approved videos
- `handle_timeout()` - Prevent infinite execution

## Logical Flow

```
1. Foundation Setup
   ├── Initialize Central Logging System
   ├── Load Simple Configuration
   └── Validate Essential Settings

2. Data Collection
   ├── Instagram Analytics → JSON (with token refresh)
   ├── GCS File Inventory → JSON
   └── Context Files → Assistant

3. AI Analysis
   ├── Upload Resources to Assistant
   ├── Generate Video Proposals
   └── Output Structured JSON

4. Draft Generation
   ├── Execute JSON2Video API
   ├── Upload to GCS Draft Folder
   └── Log to Google Sheets

5. Approval Workflow
   ├── Manual Review Process
   ├── Status Update to "Approved"
   └── Auto-posting Trigger

6. Posting Execution
   ├── Retrieve Approved Video
   ├── Upload to Instagram (with token validation)
   └── Update Status to "Posted"
```

## Key Benefits

- **Varied Content**: AI-driven proposals ensure diverse video styles
- **Context Awareness**: Leverages all available resources and analytics
- **Automated Workflow**: Streamlined approval and posting process
- **Resource Optimization**: Efficient use of existing content library
- **Performance Tracking**: Built-in analytics and status monitoring
- **Robust Logging**: Comprehensive logging for debugging and monitoring
- **Token Reliability**: Maintains Instagram API access without interruption
- **Simple Configuration**: Easy to maintain and modify
- **Zero-Config Logging**: Works out of the box with terminal output

## Implementation Notes

- **Start with logging and configuration** - build foundation first
- **Keep configuration simple** - avoid complex nested structures
- **Preserve existing Instagram token refresh logic** completely
- **Logging works without configuration** - defaults to terminal output
- Maintain existing error handling patterns
- Use async operations where appropriate for API calls
- Implement proper logging throughout the system
- Ensure configuration validation on startup
- Add unit tests for critical components
- Document API rate limits and timeout handling
- Implement log rotation and management (only if file logging enabled)
- Add performance monitoring and metrics
- Ensure backward compatibility with existing Instagram functionality



My Prompt to generate the above plan: 
The system is too rigid and linear, resulting in all the videos looking the same. I want a more varied videos generation using context aware ai prompts. To accomplish this, the system should catalog the various available resources, then hand the entirety of available information to an AI assitant which will propose social media posts. That available information is as follows:
	1. Expand the instagram api to generate a json document which provides info about my account, followers, following, new activity, insights on the last video's comments and interactions, recent comments, etc.
	2. Google Cloud Storage; I have a bucket which contains some royalty free music, timelapse videos of my 3d printed pottery being printed, photos of completed works after glazing and firing, wip photos and videos, videos of my 3d printer being constructed, stl files of printed and un-printed pieces, and other design files. The GCS api should create a json file which lists all available files and metadata from this folder to hand off to the content generation assistant.
	3. The robot's personality document, or create an openai platform assistant thread using the personality document (specify in config) 4. additional information files like model descriptions, build notes, name mappings between completed works images and the print video files, etc. 

Video Generation Logic Flow: 
1. Acquire and upload all the available information docs to an openai platform assistent (create a new thread if one if it doesn't exist or is broken). The assistent id and thread id should be stored in the config file. Assistant creation prompts should be also stored in the config file. 
2. Assistant proposes video generation ideas based on the available information and some pre-defined intent prompts (stored in the config file). The video generation ideas will be ouptut from the assistant in json format with a full description of the intent, the resources used, and the json2video configuration of the proposed video drafts. 
3. Whenever the assistant produces drafts, the system should attempt to generate them via the json2video api, then they should be uploaded to gcs in a draft folder, and the entries logged in a google sheets spreadsheet with collumns for Status (Draft, Approved, Posted, Denied), video number, date the video was produced, Caption, Link, and a 1 sentance brief strategy description.  

Draft approval and posting to instagram logic flow:
1. A separate entry-point for autopost.py will poll the status of the google sheet rows for changes to "approved" and then it will post the latest approoved video to instagram before terminating, it also has a timeout to prevent it from running forever. These settings should be stored in the autopost config file.  

Create a high-level summary of this feature update in a readme file to modifiy the curent codebase to meet this goal. Include the high level structural shifts, the basic structure of new files and classes, and the logic flow. Avoid unnecessary complexity and over-engineering. Include technical considerations and analyze any gaps in the specifications.