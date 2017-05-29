from flask import Flask, request
import requests
import time
import json
import apiai
import threading

app = Flask(__name__)



"""
{
  "recipient":{
    "id":"RECIPIENT_ID"
  }, "message": {
    "attachment": {
        "type": "template",
        "payload": {
            "template_type": "list",
            "top_element_style": "compact",
            "elements": [
                {
                    "title": "Classic White T-Shirt",
                    "image_url": "https://peterssendreceiveapp.ngrok.io/img/white-t-shirt.png",
                    "subtitle": "100% Cotton, 200% Comfortable",
                    "default_action": {
                        "type": "web_url",
                        "url": "https://peterssendreceiveapp.ngrok.io/view?item=100",
                        "messenger_extensions": true,
                        "webview_height_ratio": "tall",
                        "fallback_url": "https://peterssendreceiveapp.ngrok.io/"
                    },
                    "buttons": [
                        {
                            "title": "Buy",
                            "type": "web_url",
                            "url": "https://peterssendreceiveapp.ngrok.io/shop?item=100",
                            "messenger_extensions": true,
                            "webview_height_ratio": "tall",
                            "fallback_url": "https://peterssendreceiveapp.ngrok.io/"                        
                        }
                    ]                
                },
                {
                    "title": "Classic Blue T-Shirt",
                    "image_url": "https://peterssendreceiveapp.ngrok.io/img/blue-t-shirt.png",
                    "subtitle": "100% Cotton, 200% Comfortable",
                    "default_action": {
                        "type": "web_url",
                        "url": "https://peterssendreceiveapp.ngrok.io/view?item=101",
                        "messenger_extensions": true,
                        "webview_height_ratio": "tall",
                        "fallback_url": "https://peterssendreceiveapp.ngrok.io/"
                    },
                    "buttons": [
                        {
                            "title": "Buy",
                            "type": "web_url",
                            "url": "https://peterssendreceiveapp.ngrok.io/shop?item=101",
                            "messenger_extensions": true,
                            "webview_height_ratio": "tall",
                            "fallback_url": "https://peterssendreceiveapp.ngrok.io/"                        
                        }
                    ]                
                },
                {
                    "title": "Classic Black T-Shirt",
                    "image_url": "https://peterssendreceiveapp.ngrok.io/img/black-t-shirt.png",
                    "subtitle": "100% Cotton, 200% Comfortable",
                    "default_action": {
                        "type": "web_url",
                        "url": "https://peterssendreceiveapp.ngrok.io/view?item=102",
                        "messenger_extensions": true,
                        "webview_height_ratio": "tall",
                        "fallback_url": "https://peterssendreceiveapp.ngrok.io/"
                    },
                    "buttons": [
                        {
                            "title": "Buy",
                            "type": "web_url",
                            "url": "https://peterssendreceiveapp.ngrok.io/shop?item=102",
                            "messenger_extensions": true,
                            "webview_height_ratio": "tall",
                            "fallback_url": "https://peterssendreceiveapp.ngrok.io/"                        
                        }
                    ]                
                },
                {
                    "title": "Classic Gray T-Shirt",
                    "image_url": "https://peterssendreceiveapp.ngrok.io/img/gray-t-shirt.png",
                    "subtitle": "100% Cotton, 200% Comfortable",
                    "default_action": {
                        "type": "web_url",
                        "url": "https://peterssendreceiveapp.ngrok.io/view?item=103",
                        "messenger_extensions": true,
                        "webview_height_ratio": "tall",
                        "fallback_url": "https://peterssendreceiveapp.ngrok.io/"
                    },
                    "buttons": [
                        {
                            "title": "Buy",
                            "type": "web_url",
                            "url": "https://peterssendreceiveapp.ngrok.io/shop?item=103",
                            "messenger_extensions": true,
                            "webview_height_ratio": "tall",
                            "fallback_url": "https://peterssendreceiveapp.ngrok.io/"                        
                        }
                    ]                
                }
            ],
             "buttons": [
                {
                    "title": "View More",
                    "type": "postback",
                    "payload": "payload"                        
                }
            ]  
        }
    }
}
    
}
"""

def form_url(endpoint, params):
    query_string = "&".join(["{}={}".format(k, params[k]) for k in params])
    return "{}?{}".format(endpoint, query_string)

def query_foursquare(latitude, longitude):
    print("Foursquare: lat = {}  long = {}".format(latitude, longitude))
    endpoint = "https://api.foursquare.com/v2/venues/explore"
    params = {
        "client_id":     app.config["FOURSQUARE_CLIENT_ID"],
        "client_secret": app.config["FOURSQUARE_CLIENT_SECRET"],
        "v":             app.config["FOURSQUARE_VERSION"],
        "ll":            "{},{}".format(latitude, longitude),
        # "radius":        radius,
        # "limit":         app.config["FOURSQUARE_LIMIT"]
    }
    url = form_url(endpoint, params)

    results = requests.get(url).json()

    # Parse response
    meta = results['meta']
    response = results['response']

    keywords = reponse['keywords']
    header_location = response['headerLocation']
    groups = reponse['groups']
    for group in groups:
        group_description = group['type']
        for item in group['items']:
            item['reasons']
            item['tips']
            venue = item['venue']
            name = venue['name']
    print(json.dumps(results, sort_keys=True, indent=2, separators=(',', ' : ')))

def mark_seen(url, user_id, log=True):
    data = {
        "recipient" : {"id": user_id},
        "sender_action" : "mark_seen",
    }
    resp = requests.post(url, json=data)
    if log: print(resp)

def start_typing(url, user_id, log=True):
    data = {
        "recipient" : {"id": user_id},
        "sender_action" : "typing_on",
    }
    resp = requests.post(url, json=data)
    if log: print(resp)

def send_response(url, user_id, reply, log=True):
    data = {
        "recipient": {"id": user_id},
        "message": {"text": reply},
    }
    resp = requests.post(url, json=data)
    if log: print(resp.content)

def query_apiai(msg):
    request = ai.text_request()
    request.query = msg
    response = json.loads(request.getresponse().read())
    result = response['result']
    action = result.get('action')  # check if chatbot had something to say
    reply = result['fulfillment']['speech'] if action else ''
    return reply

def reply(user_id, msg):
    url = "https://graph.facebook.com/v2.6/me/messages"
    params = {"access_token": app.config['FACEBOOK_PAGE_ACCESS_TOKEN']}
    url = form_url(endpoint, params)

    # Immediately mark message as seen
    mark_seen(url, user_id)

    # Wait a moment so bot can "think" before starting to "type"
    delay = app.config['BOT_TIME_THINK']
    print("Thinking until +{} sec.".format(delay))
    timer_thinking = threading.Timer(delay, start_typing, args=[url, user_id])
    timer_thinking.start()

    # query API.ai chatbot with user's text
    reply = query_apiai(msg)
    if not reply:               # otherwise default to our stupid message
        punctuation = '.?!'
        append = app.config['BOT_APPEND_STRING']
        if msg[-1] in punctuation:
            reply = '{} {}{}'.format(msg.strip(punctuation), append, msg[-1])
        else:
            reply = '{} {}'.format(msg, append)
    print(user_id, reply)

    # Wait while the bot "types" before sending the message
    delay += len(reply) / app.config['BOT_TIME_CHARS_PER_SEC']
    print("Typing until +{} sec.".format(delay))
    timer_typing = threading.Timer(delay, send_response, args=[url, user_id, reply])
    timer_typing.start()


@app.route('/', methods=['GET'])
def handle_verification():
    if request.args['hub.verify_token'] == app.config['FACEBOOK_VERIFY_TOKEN']:
        return request.args['hub.challenge']
    else:
        return "Invalid verification token"


@app.route('/', methods=['POST'])
def handle_incoming_messages():
    data = request.json
    print(json.dumps(data, sort_keys=True, indent=2, separators=(',', ' : ')))

    messaging = data['entry'][0]['messaging'][0]
    sender = messaging['sender']['id']

    if "message" in messaging:
        message = messaging['message']
        if "text" in message:
            text = message['text']
            reply(sender, text)
        elif "attachments" in message:
            for attachment in message["attachments"]:
                if attachment["type"] == "location":
                    payload = attachment["payload"]
                    latitude = payload["coordinates"]["lat"]
                    longitude = payload["coordinates"]["long"]
                    query_foursquare(latitude, longitude)
        else:
            pass
    elif "delivery" in messaging:
        pass
    elif "read" in messaging:
        pass
    else:
        pass

    return "ok"


if __name__ == '__main__':
    app.config.from_pyfile('config')
    ai = apiai.ApiAI(app.config['APIAI_CLIENT_ACCESS_TOKEN'])
    app.run(port=int(app.config['PORT']), debug=True)
