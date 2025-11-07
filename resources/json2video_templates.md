# json2video Basic Specification: 
Use this spec to create robust json2video json configurations.


Some possible post ideas to get you started include:
- A single long video with music and voiceover.
- 5 short videos within a series with some nice background music and a text overlay caption for each video.
- a series of at least 10 images with a duration of around .5 seconds each, showing different finished prints within the same series and their ID's as text labels at the bottom of the screen.
- A long print video (sv__.mp4 or rv__.mp4 videos), followed by a 3-5 sec duration scene of it's corresponding photo from completed_works (sv__.jpg or rv__.jpg), using no text overlays.
- A montage of failure videos with a dramatic or goofy, or ironic autopotter quote it.
- and any other configurations you can think of using the provided tools.


##Basic Movie Template: 
some voice options include en-US-JennyNeural, en-US-BlueNeural, en-US-GuyNeural

Notes: 
- The json2video configuration should use resources from the gcs inventory for videos, images and music
- It is vitally importantthat the json2video config is an accurate and robust json2video config file which can be used with the json2video API.
- Music and voice duration in the template should always be set to -2
- autopotter_voiceover_text should be brief; one sentance and no hashtags, and loosly derivative, sassy, or riffing off the social media post caption
- text label overlays should only be a few words, and can be the object's name/id, or some random or super weird text
- Do not modify the required "quality", "draft", "resolution", and "fps". These are required in the json config schema to function correctly.
- Double check that any gcs links included in the draft are correct and rewal links in the gcs inventory
- The most recent comment labeled "system" from karlsbayer in the Instagram comments (if one exists) should be treated as an important instruction to be followed.


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
            "voice": "en-US-JennyNeural",
            "model": "azure",
            "volume": 1,
            "duration": -2
        }}
        <<replace this with optional text labels intended for the full movie>>
    ],
    "resolution": "instagram-story",
    "fps": 25,
}}


## Template for each video scene within the json2video config (use for .mp4 or .mov files):
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


## Template for each image scene within the video (use for .jpg or other image files): 
Note that the duration should be adjusted depending on the number of images in the video; shorter durations for a higher number of images, resulting in a 2-15 sec total length.
{{
    "comment": "<<image_scene_name>>,
    "elements": [
        {{
            "type": "image",
            "src": "<<image_source_url>>",
            "cache": true,
            "duration": <<image duration in seconds>>,
            "resize": "cover",
            "position": "center-center"
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
  "height": 150,
  "x": 0,
  "y": 800
}}

