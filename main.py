import os
from flask import Flask, request
import requests
from google import genai

app = Flask(__name__)

# Environment Variables
FB_PAGE_ACCESS_TOKEN = os.environ.get("FB_PAGE_ACCESS_TOKEN")
FB_VERIFY_TOKEN = "my_secret_bot_token"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Gemini Client အသစ်
client = genai.Client(api_key=GEMINI_API_KEY)

@app.route("/", methods=['GET'])
def verify():
    if request.args.get("hub.verify_token") == FB_VERIFY_TOKEN:
        return request.args.get("hub.challenge")
    return "Verification failed", 403

@app.route("/", methods=['POST'])
def webhook():
    data = request.json
    if data.get("object") == "page":
        for entry in data.get("entry", []):
            for messaging_event in entry.get("messaging", []):
                if messaging_event.get("message"):
                    sender_id = messaging_event["sender"]["id"]
                    user_text = messaging_event.get("message").get("text")
                    
                    if user_text:
                        try:
                            # Gemini 2.0 Flash ကို သုံးထားပါသည်
                            response = client.models.generate_content(
                                model="gemini-2.0-flash", 
                                contents=user_text
                            )
                            reply_text = response.text
                        except Exception as e:
                            print(f"Gemini Error: {e}")
                            reply_text = "စနစ် အနည်းငယ် ကြန့်ကြာနေလို့ နောက်မှ ပြန်မေးပေးပါခင်ဗျာ။"

                        send_message(sender_id, reply_text)
    return "ok", 200

def send_message(recipient_id, message_text):
    url = f"https://graph.facebook.com/v19.0/me/messages?access_token={FB_PAGE_ACCESS_TOKEN}"
    payload = {"recipient": {"id": recipient_id}, "message": {"text": message_text}}
    requests.post(url, json=payload)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
