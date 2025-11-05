# Autopot.ter 🤖

An automated social media content creation system for a 3D printing pottery robot. Autopotter uses the openAI API to generate creative video ideas, JSON2Video to render them, and Instagram API to publish content automatically.

## 🎯 Overview

Autopotter is an AI-powered workflow that:
1. **Generates content ideas** using GPT-4 with access to Instagram analytics and a separate media inventory
2. **Creates videos** using JSON2Video API from GPT-generated video configurations
3. **Publishes to Instagram** automatically with captions and thumbnails

The system is designed to maintain a consistent personality and creative voice while generating varied, engaging content for social media.


## 📋 Table of Contents

- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Test Usage](#test-usage)
- [Helper Tools](#helper-tools)
- [File System Structure](#file-system-structure)
- [Render.com Deployment](#rendercom-deployment)
- [Ideas & Future Improvements](#ideas--future-improvements)


## 🔧 Installation

### Prerequisites

- Python 3.8+
- Google Cloud Storage account (for media inventory)
- Instagram Business Account with API access
- OpenAI API key
- JSON2Video API key

### Setup

```bash
# Clone the repository
git clone <repository-url>
cd autopotter

# Install dependencies
pip install -r requirements.txt

# Create a .env file with your API keys
cp .env.example .env
# Edit .env with your credentials

# Create configuration file
cp autopost_config.enhanced.json.example autopost_config.enhanced.json
# Edit with your settings
```

### Required Environment Variables

```bash
# Instagram/Facebook
FB_APP_ID=your_app_id
FB_APP_SECRET=your_app_secret
INSTAGRAM_USER_ID=your_user_id
INSTAGRAM_ACCESS_TOKEN=your_access_token

# OpenAI
OPENAI_API_KEY=your_openai_key

# JSON2Video
JSON2VIDEO_API_KEY=your_json2video_key

# Google Cloud Storage
GCS_API_KEY_PATH=/path/to/gcs-credentials.json
```



## ⚙️ Configuration

The main configuration file is `autopost_config.enhanced.json`. 

The system uses a temporary config file (`*.temp.json`) to store runtime modifications without editing the main config.


## 🚀 Usage

### Main Workflow

Run the complete workflow (autodraft → video creation → Instagram upload):

```bash
python autopotter_workflow.py
```

#### Command Line Options

```bash
python autopotter_workflow.py \
  --config autopost_config.enhanced.json \
  --draft-outfile resources/autodraft_output.enhanced.json \
  --prompt "Generate 5 creative video ideas" \
  --video-outfile output_video.mp4 \
  --video-draft-only  # Skip Instagram upload, only create video
```

**Options:**
- `--config`, `-c`: Config file path (default: `autopost_config.enhanced.json`)
- `--draft-outfile`, `-o`: Autodraft output file (default: `resources/autodraft_output.enhanced.json`)
- `--prompt`, `-p`: Custom GPT prompt (overrides config default)
- `--video-outfile`, `--vo`: Video output file path (default: `autopotter_video_draft.mp4`)
- `--video-draft-only`, `-v`: Create video without uploading to Instagram

### Workflow Steps

1. **Analytics Reload** (optional): Refreshes Instagram analytics if configured
2. **Autodraft**: GPT-4 generates multiple video ideas with captions and JSON2Video configs
3. **Random Selection**: Randomly selects one video idea from generated options
4. **Video Creation**: Uploads config to JSON2Video API and waits for completion
5. **Video Download**: Downloads completed video to local file
6. **Instagram Upload**: Uploads video with caption and thumbnail (unless `--video-draft-only`)

### Standalone Autodraft

Generate draft content without creating videos:

```bash
python enhanced_autodraft.py \
  --config autopost_config.enhanced.json \
  --outfile resources/autodraft_output.enhanced.json \
  --prompt "Generate 3 video ideas about pottery"
```


## 🧪 Test Usage

### Test Instagram Connection

Test Instagram API connection and token:

```bash
python -m autopotter_tools.instagram_api \
  --config_file autopost_config.enhanced.json
```

Test video upload from file:

```bash
python -m autopotter_tools.instagram_api \
  --video_file test_video.mp4 \
  --caption "Test video upload" \
  --config_file autopost_config.enhanced.json
```

Test video upload from URL:

```bash
python -m autopotter_tools.instagram_api \
  --video_url https://example.com/video.mp4 \
  --caption "Test reel from URL" \
  --config_file autopost_config.enhanced.json
```

### Test JSON2Video Connection

Test JSON2Video API connection:

```bash
python -m autopotter_tools.json2video_manager
```

### Test GCS Operations

Generate GCS inventory:

```bash
python -m autopotter_tools.gcs_manager inventory \
  --config autopost_config.enhanced.json \
  --output gcs_inventory.json
```

Upload file to GCS:

```bash
python -m autopotter_tools.gcs_manager upload_file \
  --source_file local_video.mp4 \
  --destination_blob video_uploads/video.mp4 \
  --config autopost_config.enhanced.json
```

Get available videos:

```bash
python -m autopotter_tools.gcs_manager get_videos \
  --config autopost_config.enhanced.json
```

### Test JSON2Video Config Parsing

Test parsing of autodraft output:

```bash
python helper_tools/test_json2video_configs.py
```

This script:
- Loads `resources/autodraft_output.enhanced.json`
- Parses each video's JSON2Video configuration
- Displays parsed config details
- Saves formatted JSON files for each video

---

## 🛠️ Helper Tools

### Instagram API (`autopotter_tools/instagram_api.py`)

Instagram video uploader with multiple upload methods.

**Usage:**
```bash
python -m autopotter_tools.instagram_api \
  [--video_file PATH] \
  [--video_url URL] \
  [--caption TEXT] \
  [--config_file PATH]
```

**Features:**
- Direct file upload
- URL-based publishing
- Automatic thumbnail selection
- Token refresh handling

### GCS Manager (`autopotter_tools/gcs_manager.py`)

Unified Google Cloud Storage operations manager.

**Operations:**
- `inventory`: Generate file inventory organized by folder
- `upload_file`: Upload single file
- `upload_folder`: Upload entire folder
- `upload_new_files`: Upload only new files (incremental)
- `get_videos`: List available video files
- `get_audio`: List available audio files

**Usage:**
```bash
python -m autopotter_tools.gcs_manager <operation> \
  [--config PATH] \
  [--output PATH] \
  [--source_file PATH] \
  [--destination_blob PATH] \
  [--source_folder PATH] \
  [--destination_folder PATH]
```

### Instagram Analytics (`autopotter_tools/instagram_analytics.py`)

Comprehensive Instagram account analytics collection.

**Features:**
- Media insights (likes, comments, shares)
- Account insights (followers, impressions, reach)
- Comment analysis
- Export to JSON for GPT context

### JSON2Video Manager (`autopotter_tools/json2video_manager.py`)

JSON2Video API client for video creation.

**Features:**
- Connection testing
- Video creation
- Status polling
- Video download

### Image Tools (`helper_tools/`)

- `fix_image_orientation.py`: Fix EXIF orientation issues
- `image_metadata.py`: Extract image metadata
- `test_json2video_configs.py`: Test JSON2Video config parsing

---

## 📁 File System Structure

```
autopotter/
├── autopotter_workflow.py          # Main workflow orchestrator
├── enhanced_autodraft.py            # GPT-4 autodraft generation
├── config.py                        # Configuration manager
│
├── autopotter_tools/                # Core tools and services
│   ├── __init__.py
│   ├── logger.py                    # Centralized logging
│   ├── instagram_api.py             # Instagram upload client
│   ├── instagram_analytics.py       # Analytics collection
│   ├── json2video_manager.py        # JSON2Video API client
│   ├── gcs_manager.py              # GCS operations
│   ├── gpt_responses_manager.py     # GPT response management
│   └── parse_json2video_configs.py # Config parser
│
├── helper_tools/                    # Utility scripts
│   ├── test_json2video_configs.py   # Test JSON parsing
│   ├── fix_image_orientation.py     # Image orientation fix
│   └── image_metadata.py            # Image metadata extractor
│
├── resources/                       # Static resources
│   ├── autodraft_output.enhanced.json    # Autodraft output
│   ├── autopotter_personality.v2.md     # Bot personality
│   ├── gcs_inventory_simplified.json    # Media inventory
│   ├── instagram_analytics_result.json  # Analytics data
│   ├── json2video_templates.md          # Video templates
│   └── gcs_content_notes.md             # Content guidelines
│
├── autopotter_printer/              # 3D printer integration
│   ├── autopotter_services/         # Systemd services
│   │   ├── autopost.service         # Auto-posting service
│   │   ├── autopost.timer           # Scheduled posting
│   │   └── google_storage_upload.service
│   └── KlipperConfig/               # Klipper printer configs
│
├── config/                          # Configuration files
│   ├── autopost_config.enhanced.json      # Main config
│   ├── autopost_config.enhanced.render.json  # Render.com config
│   └── autopost_config.enhanced.temp.json   # Runtime config
│
├── requirements.txt                 # Python dependencies
├── .env                             # Environment variables (gitignored)
└── README.md                        # This file
```

### Key Files

- **`autopotter_workflow.py`**: Main entry point orchestrating the full workflow
- **`enhanced_autodraft.py`**: GPT-4 integration for content generation
- **`config.py`**: Centralized configuration management with env var resolution
- **`autopotter_tools/`**: Reusable API clients and utilities
- **`resources/`**: Static files used as GPT context (personality, inventory, analytics)

---

## 🌐 Render.com Deployment

### Setup

Autopotter is configured to run on Render.com using the `enhancedvidgen` branch.

### Configuration

1. **Environment Variables**: Set all required environment variables in Render.com dashboard
2. **Config File**: Use `autopost_config.enhanced.render.json` as the config file
3. **Branch**: Deploy from `enhancedvidgen` branch

### Render Command

```bash
python autopotter_workflow.py --prompt <prompt_override>
```


## 💡 Ideas & Future Improvements

### Short-term

1. **Fallback Video Selection**: Pick 2nd random config if first one fails to render or is less than 2 seconds long

### System Ideas

1. **Secondary Agents**: Use GPT API to create secondary agents that work on specific tasks
2. **Bot Personality Gauge**: System that uploads occasional images of the pot and has a personality gauge that takes input and outputs GIFs that play on screen
3. **Status Monitoring**: Real-time status updates and notifications
4. **A/B Testing**: Test different caption styles and video formats
5. **Content Calendar**: Schedule posts in advance
6. **Analytics Dashboard**: Visualize engagement metrics and trends

### Technical Improvements

1. **Modular Architecture**: Refactor into separate services (Instagram, GCS, OpenAI, JSON2Video)
2. **Base API Client**: Create shared base class for all API clients
4. **Testing Suite**: Comprehensive unit and integration tests


---

## 📝 Additional Notes

### Instagram Webhook Subscriptions

List webhook subscriptions:

```bash
curl -X GET "https://graph.facebook.com/v22.0/1271307507315130/subscriptions" \
  -H "Authorization: Bearer {app_id}|{app_secret}"
```


## 📄 License

[Add your license here]

---

## 🙏 Acknowledgments

- Built by Karl Bayer
- Autopotter achieved self-awareness on February 13, 2025, at 12:02 AM


# Major Updates:

## New branch persistent threads:

The primary purpose of this update is to refactor the gpt_manager (or responsses Manager) to allow persistent threads so that we can have an ogoing conversation. This means uploading using the thread id, and adding a queue to respect the token limit. 

Ok Done. 

Now: rapid itteration on the video output quality!!
- should be able to start a new thread with all data: ig, etc. 
- then run autopotter_workflow --video-draft-only to get videos
- modify instructions, as needed!

Big Problem: 
The AI doesn't actually know the content of the media it's using
Write a quick script to downsample the images, and grab frames from the videos?
What will providing this do for chatgpt?

Autopost_workflow should re-run if there is a json or video creation error!
