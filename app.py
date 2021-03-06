import os
import sys
import json

import requests
from flask import Flask, request

app = Flask(__name__)


@app.route('/', methods=['GET'])
def verify():
    # when the endpoint is registered as a webhook, it must echo back
    # the 'hub.challenge' value it receives in the query arguments
    if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.challenge"):
        if not request.args.get("hub.verify_token") == os.environ["VERIFY_TOKEN"]:
            return "Verification token mismatch", 403
        return request.args["hub.challenge"], 200

    return "Hello world", 200

@app.route('/start', methods=['POST'])
def start():
  data = request.get_json()
  if data["verify_token"]:
    os.environ["VERIFY_TOKEN"]=data["verify_token"]
    print(os.environ["VERIFY_TOKEN"])
  if data["access_token"]:
    os.environ["PAGE_ACCESS_TOKEN"]=data["access_token"]
    print(os.environ["PAGE_ACCESS_TOKEN"])
  if data["agent_token"]:
    os.environ["AGENT_TOKEN"]=data["agent_token"]
    print(os.environ["AGENT_TOKEN"])

  return "ok" , 200

@app.route('/', methods=['POST'])
def webhook():

    # endpoint for processing incoming messaging events

    data = request.get_json()
    log(data)  # you may not want to log every incoming message in production, but it's good for testing

    if data["object"] == "page":

        for entry in data["entry"]:
            for messaging_event in entry["messaging"]:

                if messaging_event.get("message"):  # someone sent us a message

                    sender_id = messaging_event["sender"]["id"]        # the facebook ID of the person sending you the message
                    recipient_id = messaging_event["recipient"]["id"]  # the recipient's ID, which should be your page's facebook ID
                    message_text = messaging_event["message"]["text"]  # the message's text
                    
                    response = reply(message_text)
                    send_message(sender_id, response)

                if messaging_event.get("delivery"):  # delivery confirmation
                    pass

                if messaging_event.get("optin"):  # optin confirmation
                    pass

                if messaging_event.get("postback"):  # user clicked/tapped "postback" button in earlier message
                    pass

    return "ok", 200

def reply(message_text):
  data = {
    'query' : message_text
    
  }
  agent_token = os.environ["AGENT_TOKEN"]
  req = requests.post("http://127.0.0.1:8000/respond/", data,
                        headers={'content-type': 'application/x-www-form-urlencoded','Authorization': "bearer " + agent_token}
                                 )


  data = req.content.decode(encoding="utf-8")
  data = json.loads(data)
  response = data["Speech"]
  
  return response

def send_message(recipient_id, response):

    log("sending message to {recipient}: {text}".format(recipient=recipient_id, text=response))

    params = {
        "access_token": os.environ["PAGE_ACCESS_TOKEN"]
    }
    headers = {
        "Content-Type": "application/json"
    }
    data = json.dumps({
        "recipient": {
            "id": recipient_id
        },
        "message": {
            "text": response
        }
    })
    r = requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=headers, data=data)
    if r.status_code != 200:
        log(r.status_code)
        log(r.text)


def log(message):  # simple wrapper for logging to stdout on heroku
    print str(message)
    sys.stdout.flush()


if __name__ == '__main__':
    app.run(debug=True)
