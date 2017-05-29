from flask import Flask, request
import requests
import time
import json
import apiai
import threading
import random

METERS_PER_MILE = 1609.34

app = Flask(__name__)


def form_url(endpoint, params):
    query_string = "&".join(["{}={}".format(k, params[k]) for k in params])
    return "{}?{}".format(endpoint, query_string)

def query_foursquare(latitude, longitude, log=True):
    print("Foursquare: lat = {}  long = {}".format(latitude, longitude))
    endpoint = "https://api.foursquare.com/v2/venues/explore"
    params = {
        "client_id":     app.config["FOURSQUARE_CLIENT_ID"],
        "client_secret": app.config["FOURSQUARE_CLIENT_SECRET"],
        "v":             app.config["FOURSQUARE_VERSION"],
        "ll":            "{},{}".format(latitude, longitude),
        "limit":         app.config["FOURSQUARE_LIMIT"],
        # "radius":        radius,
    }
    url = form_url(endpoint, params)

    results = requests.get(url).json()
    if log:
        print(json.dumps(results, sort_keys=True, indent=2, separators=(',', ' : ')))

    # Parse response
    meta = results['meta']
    response = results['response']

    header_location = response['headerLocation']
    groups = response['groups']

    recommendations = []
    title = []
    for group in groups:
        group_description = group['type']
        title.append(group_description)
        for item in group['items']:
            venue = item['venue']
            if not venue['hours']['isOpen']: # ignore closed venues
                continue
            venue_id = venue['id']
            name = venue['name']
            price = '$'*venue['price']['tier'] if 'price' in venue else ''
            venue_url = venue.get("url")
            if not venue_url:
                venu_url = form_url("https://www.google.com/search", {"q": '+'.join(name.split())})
            distance = venue['location'].get('distance')
            if distance is not None:
                distance = "{:2.1f}mi".format(distance / METERS_PER_MILE)
            else:
                distance = ''
            details = {
                "id": venue_id,
                "name": name,
                "price": price,
                "url": venue_url,
                "distance": distance,
            }
            recommendations.append(details)
            # item['reasons']
            # item['tips']
    reply = {
        "title": " & ".join(title),
        "recommendations": recommendations,
    }
    return reply

def query_foursquare_photos(venue_id, photo_size="100x100", limit=10, log=True):
    endpoint = "https://api.foursquare.com/v2/venues/{}/photos".format(venue_id)
    params = {
        "client_id":     app.config["FOURSQUARE_CLIENT_ID"],
        "client_secret": app.config["FOURSQUARE_CLIENT_SECRET"],
        "v":             app.config["FOURSQUARE_VERSION"],
        "limit":         limit,
    }
    url = form_url(endpoint, params)
    results = requests.get(url).json()
    if log:
        print(json.dumps(results, sort_keys=True, indent=2, separators=(',', ' : ')))

    # Parse response
    meta = results['meta']
    response = results['response']

    photos = response['photos']
    count = photos['count']
    photo_urls = []
    for item in photos['items']:
        photo_url = "{}{}{}".format(item['prefix'], photo_size, item['suffix'])
        photo_urls.append(photo_url)
    return photo_urls

def reply_with_recommendations(user_id, latitude, longitude):
    endpoint = "https://graph.facebook.com/v2.6/me/messages"
    endpoint = "https://graph.facebook.com/me/messages"
    params = {"access_token": app.config['FACEBOOK_PAGE_ACCESS_TOKEN']}
    url = form_url(endpoint, params)

    # Immediately mark message as seen
    mark_seen(url, user_id)

    reply = query_foursquare(latitude, longitude, log=False)

    # randomly select (up to) 4 venues to show
    to_show = min(len(reply['recommendations']), 4)
    recommendations = random.sample(reply['recommendations'], to_show)

    elements = []
    for venue in recommendations:
        element = {
            "title": venue["name"],
            "subtitle": "{} {}".format(venue["price"], venue["distance"]),
            "default_action": {
                "type": "web_url",
                "url": venue["url"],
                "webview_height_ratio": "tall"
            },
        }
        photo_urls = query_foursquare_photos(venue["id"])
        if photo_urls:
            element["image_url"] = photo_urls[0]
        elements.append(element)

    # button = {
    #     "title": "View More",
    #     "type": "postback",
    #     "payload": "View more",
    # }

    list_template = {
        "template_type": "list",
        "top_element_style": "compact",
        "elements": elements,
        # "buttons": [button],
    }

    attachment = {
        "type": "template",
        "payload": list_template
    }

    data = {
        "recipient" : {"id": user_id},
        "message" : {
            "attachment": attachment,
        },
    }

    resp = requests.post(url, json=data)
    print("FB response to list:", resp)

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

def send_text(url, user_id, reply, log=True):
    data = {
        "recipient": {"id": user_id},
        "message": {"text": reply},
    }
    resp = requests.post(url, json=data)
    if log: print(resp.content)

def query_location(url, user_id, text="Where are you?", log=True):
    data = {
        "recipient" : {"id": user_id},
        "message" : {
            "text": text,
            "quick_replies": [
                {
                    "content_type": "location",
                }
            ]
        }
    }
    resp = requests.post(url, json=data)
    if log: print(resp.content)

def query_apiai(msg, log=True):
    request = ai.text_request()
    request.query = msg
    response = json.loads(request.getresponse().read())
    if log: print(response)
    result = response['result']
    action = result.get('action')  # check if chatbot had something to say
    reply = result['fulfillment']['speech'] if action else ''
    return (action, reply)

def reply(user_id, msg):
    endpoint = "https://graph.facebook.com/v2.6/me/messages"
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
    action, reply = query_apiai(msg)
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
    timer_typing = threading.Timer(delay, send_text, args=[url, user_id, reply])
    timer_typing.start()

    if action == 'smalltalk.user.bored':
        delay += 0.2
        timer_thinking2 = threading.Timer(delay, start_typing, args=[url, user_id])
        timer_thinking2.start()
        text = "But tell me where you are, and I'll find something to entertain you."
        delay += len(text) / app.config['BOT_TIME_CHARS_PER_SEC']
        timer_location = threading.Timer(delay, query_location, args=[url, user_id, text])
        timer_location.start()
        

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
                    reply_with_recommendations(sender, latitude, longitude)
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
