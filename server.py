from flask import Flask, request
import requests
import time
import json

app = Flask(__name__)

def reply(user_id, msg):
    punctuation = '.?!'
    append = app.config['BOT_APPEND_STRING']
    if msg[-1] in punctuation:
        reply = '{} {}{}'.format(msg.strip(punctuation), append, msg[-1])
    else:
        reply = '{} {}'.format(msg, append)

    url = "https://graph.facebook.com/v2.6/me/messages?access_token="
    url += app.config['PAGE_ACCESS_TOKEN']

    # Immediately mark message as seen
    data = {
        "recipient" : {"id": user_id},
        "sender_action" : "mark_seen",
    }
    resp = requests.post(url, json=data)
    print(resp)

    # Wait a moment so bot can "think"
    delay = app.config['BOT_TIME_THINK']
    print("Thinking for {} sec.".format(delay))
    time.sleep(delay)

    # Then start "typing"
    data = {
        "recipient" : {"id": user_id},
        "sender_action" : "typing_on",
    }
    resp = requests.post(url, json=data)
    print(resp)

    # Wait while the bot "types"
    delay = len(reply) / app.config['BOT_TIME_CHARS_PER_SEC']
    print("Typing for {} sec.".format(delay))
    time.sleep(delay)

    # Finally send what the bot wrote
    data = {
        "recipient": {"id": user_id},
        "message": {"text": reply},
    }
    resp = requests.post(url, json=data)
    print(resp.content)

    # Finally turn off "typing"
    data = {
        "recipient": {"id": user_id},
        "sender_action" : "typing_off",
    }
    resp = requests.post(url, json=data)
    print(resp.content)


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
    app.run(port=int(app.config['PORT']), debug=True)
