# json2video Basic Specification: 
Use this spec to create robust json2video json configurations.


Some possible post ideas include:
- A single long video with music and voiceover
- 3-5 short videos within a series with some nice background music
- a series of at least 10 images with a duration of around .5 seconds each, showing different finished prints within the same series and their ID's as text labels at the bottom of the screen
- and any other configurations you can think of using the provided tools


##Basic Movie Template: 
some voice options include en-US-JennyNeural, en-US-BlueNeural, en-US-GuyNeural

Notes: 
- The json2video configuration should use resources from the gcs inventory for videos, images and music
- It is vitally importantthat the json2video config is an accurate and robust json2video config file which can be used with the json2video API.
- Music and voice duration in the template should always be set to -2
- autopotter_voiceover_text should be brief; one sentance and no hashtags, and loosly derivative, sassy, or riffing off the social media post caption
- text label overlays should only be a few words, and can be the object's name/id, or some random or super weird text


{{
    "quality": "high",
    "draft": false,
    "scenes": [
        <<insert comma separated scenes here>>
    ],
    "elements": [
        {{
            "type": "audio",
            "src": "<<autopotter_background_music_source_url>>",
            "seek": 50,
            "fade-in": 0.5,
            "volume": 0.3,
            "duration": -2,
            "fade-out": 0.5
        }},
        {{
            "type": "voice",
            "text": "<<autopotter_voiceover_text>>>",
            "voice": "en-US-BlueNeural",
            "model": "azure",
            "volume": 1,
            "duration": -2
        }}
        <<replace this with optional text labels intended for the full movie>>
    ],
    "resolution": "instagram-story",
    "fps": 25,
}}


## Template for each video scene within the json2video config:
{{
    "comment": "<<video_scene_name>>",
    "elements": [
        {{
            "type": "video",
            "src": "<<video_source_url>>",
            "position": "center-center",
            "muted": true,
            "resize": "cover"
        }}
        <<replace this with any optional scene text elements here>>
    ]
}}


## Template for each images scene within the video: 
Note that the duration should be adjusted depending on the number of images in the video; shorter durations for a higher number of images, resulting in a 2-15 sec total length.
{{
    "comment": "<<image_scene_name>>,
    "elements": [
        {{
            "type": "image",
            "src": "<<image_source_url>>",
            "cache": true,
            "duration": <<image duration in seconds>>
        }}
    ]
}}


Element template for text label overlays:
Note that the position, font size, color, and position x/y values can and often should be adjusted.
- The x/y position values are in pixels, and the zero point is centered on the screen.
- Background-color and color should contrast each other
- Text labels can be placed in the movie elements section if they are to be shown for the entire movie (like titles or movie comments)
- Text labels should be placed in the elements section of the individual video scene or image scene if they are related to only that scene. 
- The text label position should not overlap with each other if they appear in the same scene.


{{
  "type": "text",
  "style": "001",
  "text": "<<text_to_show_on_screen>>",
  "settings": {{
    "font-family": "Roboto",
    "font-size": "10vw",
    "color": "#111111",
    "background-color": "#eeeeee",
    "border-radius": 
  }},
  "position": "custom",
  "cache": false,
  "x": 0,
  "y": 600
}}

