# Restrucutre

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

### Current Key Features

`autopotter_workflow.py`
- Orchestrates the entire pipeline: prompt drafting → video generation → Instagram upload.
- Handles retries, logging, and cleanup for each stage to keep long runs resilient.
- Reads runtime opts (config path, draft-only mode, etc.) so workflows can be scripted.

`enhanced_autodraft.py`
- Wraps GPT-driven idea generation with prompt templating and persona constraints.
- Supports batching multiple draft requests and persisting them to disk.
- Exposes CLI flags to experiment with temperature, model, and output file targets.

`config.py`
- Centralizes loading from JSON, `.env`, and environment variables with validation helpers.
- Provides typed getters for Instagram, GCS, OpenAI, and JSON2Video credentials.
- Tracks token freshness/expiry to warn when long-lived Instagram tokens need a refresh.

`autopotter_tools/instagram_api.py`
- Uploads reels via Graph API: container creation, resumable upload, publish, delete.
- Includes utilities for URL-based publishing and status polling of media containers.
- Normalizes responses/logging so callers receive creation + media IDs for follow-up ops.

`autopotter_tools/instagram_analytics.py`
- Pulls engagement metrics, follower stats, and media insights from the IG Insights API.
- Aggregates historical analytics into cached JSON for downstream reporting.
- Provides helpers to compare time windows and surface growth trends.

`autopotter_tools/json2video_manager.py`
- Manages JSON2Video project lifecycle: template selection, rendering, and downloads.
- Streams progress updates and handles polling until render completion.
- Downloads finished videos locally and reports metadata back to the workflow.

`autopotter_tools/gcs_manager.py`
- Wraps Google Cloud Storage uploads, downloads, and bucket inventory queries.
- Handles credential loading, signed URL generation, and resumable transfers.
- Offers convenience methods for syncing media libraries used by Autopotter.

`autopotter_tools/gpt_responses_manager.py`
- Stores/retrieves GPT outputs, tying responses to prompts and run metadata.
- Provides search/filter utilities to reuse past ideas or avoid duplicates.
- Formats responses for downstream systems (JSON2Video, social copy, etc.).




## Ideas & Future Improvements

## 💡 Big Backend Feature Experiments/Changes: 

### clean up config by putting the instagram token management in its own module

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

### Future Feature Highlights

`Dedicated Instagram token module`
- Extract token refresh, storage, and expiry checks out of `config.py` so workflows only see a clean credentials interface.
- Centralizes API calls for long-lived vs. short-lived tokens, making rotation safer and more testable.

`Chat feature with tool access`
- Lightweight conversational shell that can call local helpers (JSON2Video validation, caption rewrites, etc.) while you prototype.
- Keeps prompts, responses, and invoked tools logged so experiments are reproducible.

`Script-first workflow flags`
- Expand CLI/automation flags to target specific stages (“generate drafts only”, “rerender last video”, etc.).
- Makes it easier to run “do this again but tweak X” commands without editing Python files.

`AI helper toolbelt`
- Bundle JSON2Video schema validation, tag compliance checks, and dry-run renders into callable utilities.
- Expose these tools to GPT so it can iteratively fix configs before hitting paid APIs.

`Media awareness utilities`
- Downsample images and sample video frames so the AI sees lightweight previews of source assets.
- Enables smarter prompt guidance (“use the clip with the blue glaze vase”) without uploading full media.

`Scheduling and queueing`
- Add a post-production queue where approved videos wait for scheduled publish windows.
- Optionally integrate recurring cron-style posting or manual review checkpoints before pushing live.
