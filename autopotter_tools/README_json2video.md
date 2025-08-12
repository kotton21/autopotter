# Json2Video API Client

A simple Python client for the json2video API that renders videos using templates.

## Quick Demo

Run the demo with default settings:

```bash
python json2video_api.py
```

This will:
1. Render a video using the `basic_config` template
2. Download it to `./edited_video_demo.mp4`

## Custom Demo

Override any of the default values:

```bash
python json2video_api.py --video "your_video_url" --audio "your_audio_url" --text "Your voiceover text"
```

## Configuration

Edit `config_json2video.json` to change:
- API key
- Default video/audio URLs
- Default voiceover text



