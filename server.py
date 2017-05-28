from flask import Flask, request
import requests
import time
import json
import apiai
import threading

app = Flask(__name__)

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

def reply(user_id, msg):
    url = "https://graph.facebook.com/v2.6/me/messages?access_token="
    url += app.config['PAGE_ACCESS_TOKEN']

    # Immediately mark message as seen
    data = {
        "recipient" : {"id": user_id},
        "sender_action" : "mark_seen",
    }
    resp = requests.post(url, json=data)
    print(resp)

    # send text to API.ai chatbot
    request = ai.text_request()
    request.query = msg
    response = json.loads(request.getresponse().read())
    result = response['result']
    action = result.get('action')
    if action:
        # chatbot had something to say
        reply = result['fulfillment']['speech']
    else:
        # default to our stupid message
        punctuation = '.?!'
        append = app.config['BOT_APPEND_STRING']
        if msg[-1] in punctuation:
            reply = '{} {}{}'.format(msg.strip(punctuation), append, msg[-1])
        else:
            reply = '{} {}'.format(msg, append)
    print(user_id, reply)

    # Wait a moment so bot can "think" before starting to "type"
    delay = app.config['BOT_TIME_THINK']
    print("Thinking until +{} sec.".format(delay))
    timer_thinking = threading.Timer(delay, start_typing, args=[url, user_id])
    timer_thinking.start()

    # Wait while the bot "types" before sending the message
    delay += len(reply) / app.config['BOT_TIME_CHARS_PER_SEC']
    print("Typing until +{} sec.".format(delay))
    timer_typing = threading.Timer(delay, send_response, args=[url, user_id, reply])
    timer_typing.start()


@app.route('/', methods=['GET'])
def handle_verification():
    if request.args['hub.verify_token'] == app.config['VERIFY_TOKEN']:
        return request.args['hub.challenge']
    else:
        return "Invalid verification token"


@app.route('/', methods=['POST'])
def handle_incoming_messages():
    data = request.json
    print(json.dumps(data, sort_keys=True, indent=2, separators=(',', ' : ')))

    messaging = data['entry'][0]['messaging'][0]
    sender = messaging['sender']['id']

    if "message" in messaging.keys():
        message = data['entry'][0]['messaging'][0]['message']['text']
        reply(sender, message)
    elif "delivery" in messaging.keys():
        pass
    elif "read" in messaging.keys():
        pass
    else:
        pass

    return "ok"


if __name__ == '__main__':
    app.config.from_pyfile('config')
    ai = apiai.ApiAI(app.config['APIAI_CLIENT_ACCESS_TOKEN'])
    app.run(port=int(app.config['PORT']), debug=True)
