from flask import Flask, request
import requests
import time
import json
import apiai
import threading

app = Flask(__name__)


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
    # print(json.dumps(results, sort_keys=True, indent=2, separators=(',', ' : ')))

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
            price = '$'*venue['price']['tier'] if 'price' in venue else ''
            details = {
                "name": venue['name'],
                "price": price,
            }
            recommendations.append(details)
            # item['reasons']
            # item['tips']
    reply = {
        "title": " & ".join(title),
        "recommendations": recommendations,
    }
    return reply

def reply_with_recommendations(user_id, latitude, longitude):
    endpoint = "https://graph.facebook.com/v2.6/me/messages"
    endpoint = "https://graph.facebook.com/me/messages"
    params = {"access_token": app.config['FACEBOOK_PAGE_ACCESS_TOKEN']}
    url = form_url(endpoint, params)

    # Immediately mark message as seen
    mark_seen(url, user_id)

    reply = query_foursquare(latitude, longitude)

    elements = []
    for venue in reply['recommendations']:
        element = {
            "title": venue["name"],
            "subtitle": venue["price"],
            "image_url": "https://s20.postimg.org/gbwoaexl9/SALA_1.jpg",
            "default_action": {
                "type": "web_url",
                "url": "https://www.google.com",
                "webview_height_ratio": "tall"
            },
        }
        elements.append(element)

    # Facebook only supports up to 4 elements in list
    if len(elements) > 4:
        elements = elements[:4]

    button = {
        "title": "View More",
        "type": "postback",
        "payload": "View more",
    }

    list_template = {
        "template_type": "list",
        "top_element_style": "compact",
        "elements": elements,
        "buttons": [button],
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

    # data = {
    #     "recipient" : {"id": user_id},
    #     "message" : {
    #         "text": "Where are you?",
    #         "quick_replies": [
    #             {
    #                 "content_type": "location",
    #             }
    #         ]
    #     }
    # }

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

def query_apiai(msg):
    request = ai.text_request()
    request.query = msg
    response = json.loads(request.getresponse().read())
    result = response['result']
    action = result.get('action')  # check if chatbot had something to say
    reply = result['fulfillment']['speech'] if action else ''
    return reply

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
    timer_typing = threading.Timer(delay, send_text, args=[url, user_id, reply])
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
