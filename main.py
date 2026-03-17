import os
from flask import Flask, request
import requests
import google.generativeai as genai

app = Flask(__name__)

# Key တွေကို Render ရဲ့ Environment Variables ကနေ ဆွဲယူပါမယ်
FB_PAGE_ACCESS_TOKEN = os.environ.get("FB_PAGE_ACCESS_TOKEN")
FB_VERIFY_TOKEN = "my_secret_bot_token"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)

# Model နာမည်ကို models/gemini-1.5-flash ဟု အပြည့်အစုံ ပြောင်းလဲထားပါသည်
model = genai.GenerativeModel('models/gemini-1.5-flash')

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
                            # Gemini AI ကနေ အဖြေတောင်းခြင်း
                            response = model.generate_content(user_text)
                            reply_text = response.text
                        except Exception as e:
                            print(f"Gemini Error: {e}")
                            reply_text = "ခဏနေမှ ပြန်ကြိုးစားပေးပါခင်ဗျာ။"

                        # Facebook ဆီ အဖြေပြန်ပို့ခြင်း
                        send_message(sender_id, reply_text)
    return "ok", 200

def send_message(recipient_id, message_text):
    url = f"https://graph.facebook.com/v19.0/me/messages?access_token={FB_PAGE_ACCESS_TOKEN}"
    payload = {"recipient": {"id": recipient_id}, "message": {"text": message_text}}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"FB Send Error: {e}")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
