# Autopot.ter


## List Webhook Subscriptions
curl -X GET "https://graph.facebook.com/v22.0/1271307507315130/subscriptions" -H "Authorization: Bearer {app_id}|{app_secret}"


## TODO Updates:
Instagram API Should put the last (or random middle) frame of the timelapse as the thumbnail...
Pass the name of the pot to the GPT caption generator
Pass an image of th epot 


System Ideas:
Autopotter Bot itself should upload occasional images of the pot to see if its working and have a little personality gage that takes input and outputs little gifs that play on the screen 

What's next?
Constrain the output better..

Render command:
python autopotter_workflow --prompt <prompt_override>


It works on render!
using enhancedvidgen branch. 
What's next??


"files_by_folder": {
    "https://storage.googleapis.com/autopot1-printdump/video_uploads/": [
        "timelapse__20250417_1823.mp4",
        "timelapse_cylinder-PV3.gcode_20250422_1955.mp4",
        "timelapse_cylinder-PV3.gcode_20250422_1956.mp4",
        ...
    ], 
    "https://storage.googleapis.com/autopot1-printdump/completed_works/": [
        "tm05.jpg",
        "tm34.jpg",
        "tm23.jpg",
        ...
    ]
}
old 34kb,
big is 130kb, 
new

Pick 2nd random config if first one fails to render, or is less than 2 sec long. 

Build a schema for autopotter personality software so that I can deploy a 2nd one!!

