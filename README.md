# Autopot.ter
Usage

Test Usage

Demo Usage


Helpers


### List Webhook Subscriptions: 
```
curl -X GET "https://graph.facebook.com/v22.0/1271307507315130/subscriptions" -H "Authorization: Bearer {app_id}|{app_secret}"
```


### Render:
Works on Render.com using enhancedvidgen branch. 

Render command:
python autopotter_workflow --prompt <prompt_override>


### Ideas:
- Pick 2nd random config if first one fails to render, or is less than 2 sec long. 

- Build a schema for autopotter personality software so that I can deploy a 2nd one!!


- System Ideas:
Sould be able to use the GPT api to make 2ndary agents to work on things. Autopotter Bot itself should upload occasional images of the pot to see if its working and have a little personality gage that takes input and outputs little gifs that play on the screen 

