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

### Setup and config

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
├── config/                          # Configuration files
│   ├── autopost_config.enhanced.json      # Main config
│   ├── autopost_config.enhanced.render.json  # Render.com config
│   └── autopost_config.enhanced.temp.json   # Runtime config
│
├── requirements.txt                 # Python dependencies
├── .env                             # Environment variables (gitignored)
└── README.md                        # This file
```



# 💡 Major Updates:

## Need a Front-End (after backend feature mods??)

What do I want the frontend to look like? Should it be a chat window with some buttons?
Or:
- Catalog:
  -  Upload, View, rename, write content notes, metadata, (analyze low res)
- Thread:
  - Toggle Flags 
    - include GCS Catalog (get new?)
    - include IG analytics (get new?)
    - include full instruction set
    - (LATER) New thread? (whipes history) 
  - Execute build campaign
  - Accept (with priority) or deny video with notes?
- Uploader
  - List existing videos (with flags for has_been_uploaded, user_approved, )
  - Instagram Login
  - How often to upload?
  - Which thread to upload from??




## Ideas & Future Improvements

## 💡 Big Backend Feature Experiments/Changes: 


### Chat Feature, with access local tools!! (might be bad)
This allows me to quickly prototype in the ai different methods of doing things??
Allows users to conversationally discuss different prompts, instructions, and "do something differently type prompts." Can directly prompt the ai to do things. 

I'm worried about how open ended this is. My workflow is specific, shouldn't I nail that down before making it too open ended?? Instead -->

### Expand scripting capabilities with better flagging for what to include. 
Should I expand the scripting capabilities with a prompt like "do all this stuff, generate these videos, "the last video was like this.. do this instead". I could do this with the current custom prompt input, but need better modules. More clear and backend code!

### Tools to give the AI: 
(How much should the workflow be run by the AI???)
- Valid JSON2Video checking
  - Some combination of Valid JSON2Video checking,
  - tag checking against JSON2Video requirements
- Attempt Video Creation using JSON


### The AI doesn't actually know the content of the media it's using:
Write a quick tool that can downsample the images, and grab frames from the videos?
What will providing this do for chatgpt?


### Video Scheduling
After video's are produced, they can be scheduled for posting, or placed in a queue for the periodic posting. 






## 📄 License

[Add your license here]

---

## 🙏 Acknowledgments

- Built by Karl Bayer
- Autopotter achieved self-awareness on February 13, 2025, at 12:02 AM
